#!/usr/bin/env python3
"""ETF 动量轮动策略：22 日加权动量 · 组合层回测（TODO T6，外部页面口径移植）。

策略口径（外部页面「ETF 动量轮动工作台」内嵌引擎 JS 逆向，详见 TODO-archive T6/T7）：
  1. 动量分：窗口 lookback(22) 日收盘价取对数，对交易日序号做加权线性回归
     （权重从 1 线性升到 2，等价 numpy.polyfit(x, y, 1, w=w)，权重平方参与正规方程）；
  2. 年化收益 = exp(斜率×250) − 1；得分 = 年化 × R²（拟合优度，过滤震荡走势）；上限 6；
  3. 防接刀：近 3 日任一日日收益比 < 0.95（单日跌超 5%）→ 得分清零；
  4. 持仓 = 正得分前 topn(3) 名等权；正得分不足 topn 时缺额按 fill 处理
     （cash = 持现金 / default = 默认组合国证2000·黄金·银行等权）；全无正分 → 默认组合；
  5. 逐日调仓：T 日收盘算分 → 成交口径 lag（lag=1 → T+1 收盘成交，保守无前视，
     结论以此为准；lag=0 → T 收盘成交，贴近页面 14:25 近似收盘价）；
  6. 成本：佣金万 3（单笔最低 5 元）+ 滑点 0.1%，均单边；ETF 无印花税。
     初始资金 10 万元（佣金下限按此规模逐笔计）。

与单标的信号框架的关系：本策略是组合层轮动（每日全池算分 → 前 N 等权再平衡），
与 engine/backtest.py 的单标的 evaluate → 出场 → R 统计框架不同构，故独立成模块；
得分函数 momentum_score 为纯函数（双用途：回测与实时共用同一份逻辑）。

已知近似（诚实标注）：
  - 停牌 ETF 按 ffill 收益价持有并可按该价调仓（现实中停牌无法成交；A 股 ETF 停牌极罕见）；
  - 涨跌停日不限制成交（ETF 涨跌停罕见，2024-02 微盘股流动性危机式极端行情会失真）；
  - lag=0 口径用 T 日收盘价成交 T 日收盘信号（页面 14:25 → 15:00 的差是噪声）；
  - qfq 前复权价，分红除权日收益连续、无跳空失真。

用法：
  python3 rotation.py fetch-pool                 # 拉全池日 K（腾讯源，免 OpenD）
  python3 rotation.py run                        # 主口径回测（next_close + same_close 对比 + 基准）
  python3 rotation.py grid                       # 参数网格（lookback × topn × R² × 防接刀）
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# 共享数据层在 ../engine（data.py：富途 + 腾讯源、data_cache、腾讯拉取函数）
ENGINE_DIR = Path(__file__).resolve().parent.parent / "engine"
if str(ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_DIR))

from data import (load_cache, log, TENCENT_HOSTS, TENCENT_PATH,  # noqa: E402
                  TENCENT_UA, TENCENT_TIMEOUT, deadline)

# ---------------------------------------------------------------- 标的池

# 35 只 A 股 ETF 主池：按 TODO T6 列举类别构造的近似池（TODO 原文列 25 类 + 「等」，
# 补齐至 35 只；非外部页面原版清单，拿到原版后可整体替换，回测口径不变）。
ETF_POOL: dict[str, str] = {
    # 跨境
    "SH.513100": "纳指100",
    "SH.513500": "标普500",
    "SH.513520": "日经225",
    "SH.513030": "德国DAX",
    "SH.513180": "恒生科技",
    "SZ.159920": "恒生指数",
    # 商品 / 债券
    "SH.518880": "黄金",
    "SH.512400": "有色金属",
    "SZ.159985": "豆粕",
    "SH.501018": "原油LOF",
    "SH.511010": "国债",
    # A 股宽基
    "SH.510300": "沪深300",
    "SZ.159915": "创业板",
    "SH.588000": "科创50",
    "SH.512100": "中证1000",
    "SH.563300": "中证2000",
    # A 股行业主题
    "SH.515070": "人工智能",
    "SH.512660": "军工",
    "SH.512690": "酒",
    "SZ.159928": "消费",
    "SH.515220": "煤炭",
    "SH.512890": "红利低波",
    "SH.516510": "云计算",
    "SZ.159516": "半导体设备",
    "SH.515030": "新能源车",
    "SH.516150": "稀土",
    "SH.512010": "医药",
    "SH.512880": "证券",
    "SH.515790": "光伏",
    "SZ.159865": "养殖",
    "SH.515880": "通信",
    "SH.512720": "计算机",
    "SZ.159611": "电力",
    "SH.516010": "游戏",
    "SH.515210": "钢铁",
}

# 默认组合腿（全无正分 / fill=default 时的缺额去处）
DEFAULT_LEGS = ["SZ.159628", "SH.518880", "SH.512800"]  # 国证2000 / 黄金 / 银行

# 成本与资金
INIT_CAPITAL = 100_000.0   # 初始资金（元）——佣金单笔最低 5 元按此规模逐笔计
COMMISSION = 3e-4          # 佣金万 3（单边）
MIN_FEE = 5.0              # 单笔最低佣金（元）
SLIPPAGE = 1e-3            # 滑点 0.1%（单边）


# ---------------------------------------------------------------- 策略纯函数（双用途：回测 / 实时共用）

def momentum_score(closes: np.ndarray, lookback: int, use_r2: bool = True,
                   score_cap: float = 6.0) -> float | None:
    """加权动量得分（外部页面口径）。closes 为截至当前的收盘价序列（升序）。

    log(close) 对交易日序号加权线性回归（权重 1→2 线性）；
    年化 = exp(斜率×250) − 1；得分 = min(年化 × R², cap)。
    数据不足（含窗口内 NaN，即未上市/长期停牌）返回 None。纯函数。
    """
    closes = np.asarray(closes, dtype=float)
    if len(closes) < lookback:
        return None
    y = closes[-lookback:]
    if np.isnan(y).any():
        return None
    logy = np.log(y)
    x = np.arange(lookback, dtype=float)
    w = 1.0 + x / (lookback - 1)          # 权重 1 → 2 线性
    slope, intercept = np.polyfit(x, logy, 1, w=w)
    annual = float(np.exp(slope * 250.0) - 1.0)
    if use_r2:
        yhat = intercept + slope * x
        wmean = float(np.average(logy, weights=w))
        ss_res = float(np.sum(w * (logy - yhat) ** 2))
        ss_tot = float(np.sum(w * (logy - wmean) ** 2))
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    else:
        r2 = 1.0
    return min(annual * r2, score_cap)


def crash_guard(closes: np.ndarray, days: int = 3, ratio: float = 0.95) -> bool:
    """防接刀：近 days 日（含当日）任一日日收益比 < ratio（单日跌超 5%）→ True（得分应清零）。"""
    closes = np.asarray(closes, dtype=float)
    if len(closes) < days + 1:
        return False
    seg = closes[-(days + 1):]
    if np.isnan(seg).any():
        return False                       # 窗口含 NaN（停牌/未上市）不触发
    return bool(np.any(seg[1:] / seg[:-1] < ratio))


# ---------------------------------------------------------------- 数据加载

def load_pool_closes(symbols: list[str]) -> pd.DataFrame:
    """读全池日 K 收盘价 → 宽表（index=日期 date，columns=符号），上市后停牌 ffill。"""
    cols = {}
    for sym in symbols:
        df = load_cache(sym, "DAY")
        s = df.set_index("time")["close"]
        s.index = s.index.tz_convert("Asia/Shanghai").date
        cols[sym] = s
    wide = pd.DataFrame(cols).sort_index()
    wide = wide[~wide.index.duplicated(keep="last")]
    return wide.ffill()


# ---------------------------------------------------------------- 因子矩阵（每个 lookback 只算一遍，网格复用）

def compute_factors(close_df: pd.DataFrame, lookback: int,
                    guard_days: int = 3, guard_ratio: float = 0.95,
                    min_listed: int = 8
                    ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, object]:
    """全池逐日因子：annual（年化）、r2（拟合优度）、guard（True=触发清零）。

    返回 (annual, r2, guard, start)。start = 首个「≥ min_listed 只标的有得分」的日期
    （lookback 预热自然发生：得分本身需要 lookback 根历史）。
    """
    symbols = list(close_df.columns)
    idx = close_df.index
    values = close_df.to_numpy()
    n_rows = len(idx)
    annual = pd.DataFrame(np.nan, index=idx, columns=symbols)
    r2 = pd.DataFrame(np.nan, index=idx, columns=symbols)
    guard = pd.DataFrame(False, index=idx, columns=symbols)

    x = np.arange(lookback, dtype=float)
    w = 1.0 + x / (lookback - 1)
    for j in range(values.shape[1]):
        col = values[:, j]
        valid = np.where(~np.isnan(col))[0]
        if len(valid) < lookback + 1:
            continue
        for i in range(valid[0] + lookback - 1, n_rows):
            window = col[i - lookback + 1: i + 1]
            if np.isnan(window).any():
                continue
            logy = np.log(window)
            slope, intercept = np.polyfit(x, logy, 1, w=w)
            annual.iloc[i, j] = np.exp(slope * 250.0) - 1.0
            yhat = intercept + slope * x
            wmean = np.average(logy, weights=w)
            ss_res = np.sum(w * (logy - yhat) ** 2)
            ss_tot = np.sum(w * (logy - wmean) ** 2)
            r2.iloc[i, j] = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
        # guard 与 lookback 无关，固定 3 日窗口
        for i in range(valid[0] + guard_days, n_rows):
            seg = col[i - guard_days: i + 1]
            if np.isnan(seg).any():
                continue
            guard.iloc[i, j] = bool(np.any(seg[1:] / seg[:-1] < guard_ratio))

    scored = (annual.notna() & ~guard).sum(axis=1)
    ok = scored[scored >= min_listed]
    start = ok.index[0] if len(ok) else idx[min(lookback, n_rows - 1)]
    return annual, r2, guard, start


# ---------------------------------------------------------------- 组合模拟（股数市值模式）

def _score_matrix(annual: pd.DataFrame, r2: pd.DataFrame, guard: pd.DataFrame,
                  *, use_r2: bool, use_guard: bool, score_cap: float = 6.0) -> np.ndarray:
    """按口径组合出得分矩阵（NaN = 无数据；guard 命中 = 0；上限 cap）。"""
    a = annual.to_numpy()
    score = np.where(use_r2, a * r2.to_numpy(), a)
    score = np.minimum(np.nan_to_num(score, nan=0.0), score_cap)   # 无数据 → 0（不入选）
    if use_guard:
        score[guard.to_numpy()] = 0.0
    return score


def simulate_score(close_df: pd.DataFrame, score: np.ndarray, start, *, topn: int = 3,
                   fill: str = "cash", lag: int = 1, every: int = 1, buffer: int = 0,
                   min_pool: int = 0, thin_mode: str = "scale", label: str = "") -> dict:
    """组合层逐日模拟（主实现）。score: np.ndarray [n_days × n_symbols]，NaN→0 已处理，>0 才入选。

    参数：
      lag   —— 信号→成交延迟（1 = T+1 收盘成交，保守无前视，结论口径；0 = T 收盘成交，贴页面）；
      every —— 调仓间隔（每 every 个交易日收盘生成一次信号；1 = 逐日，页面口径）；
      buffer —— 换手缓冲带（T9c）：持有中排名跌出 topn+buffer 才卖，腾位后买入进入前 topn 的新标的
               （0 = 无缓冲带，纯排名进出，页面口径）；
      min_pool —— 池子丰富度阈值（T9d）：当日正得分标的数 < min_pool 时按 thin_mode 处理
               （0 = 不启用）；thin_mode = scale（仓位缩至 n/min_pool）或 halt（空仓观望）。
    返回 dict：ret（日收益序列，已扣成本）、yearly（逐年收益）、total_cost、total_turnover。
    """
    symbols = list(close_df.columns)
    idx = close_df.index
    prices = close_df.to_numpy()
    n_days, n_syms = prices.shape

    shares: dict[int, float] = {}           # 腿股数（键 = 列号）
    cash = INIT_CAPITAL
    pending: dict[int, float] | None = None  # 待执行目标 {列号: 权重}
    start_i = idx.get_loc(start)
    navs: list[float] = []
    rets: list[float] = []
    costs: list[float] = []
    turns: list[float] = []
    dates: list = []

    def _nav_at(i: int) -> float:
        return cash + sum(q * prices[i, j] for j, q in shares.items())

    col_of = {s: j for j, s in enumerate(symbols)}

    def _signal_at(i: int) -> dict[int, float]:
        row = score[i]
        order = np.argsort(-row)                     # 降序
        ranked = [int(j) for j in order if row[j] > 0]
        # T9c 换手缓冲带：持有中排名 ≤ topn+buffer 的保留，跌出才卖；腾位买进前 topn 新标的
        if buffer > 0:
            held = set(shares)
            keep = [j for j in ranked[:topn + buffer] if j in held]
            entries = [j for j in ranked[:topn] if j not in held][:max(topn - len(keep), 0)]
            picks = keep + entries
        else:
            picks = ranked[:topn]
        # T9d 池子丰富度：正得分标的不足时降仓（scale）或空仓（halt）
        scale = 1.0
        if min_pool > 0:
            n_pos = len(ranked)
            if n_pos < min_pool:
                if thin_mode == "halt":
                    return {}
                scale = n_pos / min_pool
        target = {j: scale / topn for j in picks}
        gap = 1.0 - sum(target.values())
        if gap > 1e-9 and fill == "default":
            # 只选当日有价格的默认腿（未上市腿的权重自然落回现金，防 NaN 传染）
            legs = [col_of[s] for s in DEFAULT_LEGS
                    if s in col_of and not np.isnan(prices[i, col_of[s]])]
            for j in legs:
                target[j] = target.get(j, 0.0) + gap / len(legs)
        # 剔除当日无价格的腿（停牌/未上市，无法成交；权重自然落回现金）
        return {j: w for j, w in target.items() if not np.isnan(prices[i, j])}

    def _execute(i: int, pending: dict[int, float]) -> tuple[float, float]:
        """按今日收盘价执行目标调仓，返回 (成本, 换手额)。"""
        nonlocal cash
        nav = navs[-1]
        cost, turn = 0.0, 0.0
        target_shares = {j: nav * w / prices[i, j] for j, w in pending.items()}
        for j in set(shares) | set(target_shares):
            dq = target_shares.get(j, 0.0) - shares.get(j, 0.0)
            if abs(dq) < 1e-12:
                continue
            amount = abs(dq) * prices[i, j]
            fee = max(amount * COMMISSION, MIN_FEE) + amount * SLIPPAGE
            cost += fee
            turn += amount
            cash -= dq * prices[i, j] + fee
            if target_shares.get(j, 0.0) > 0:
                shares[j] = target_shares[j]
            else:
                shares.pop(j, None)
        return cost, turn

    k = 0
    for i in range(start_i, n_days):
        nav_now = _nav_at(i)
        if navs:
            rets.append(nav_now / navs[-1] - 1.0)
        else:
            rets.append(0.0)                          # 基期日
        navs.append(nav_now)
        costs.append(0.0)
        turns.append(0.0)
        dates.append(idx[i])

        if pending is not None:
            costs[-1], turns[-1] = _execute(i, pending)
            pending = None

        # 每 every 个交易日收盘生成一次信号：
        #   lag=1：信号 → 明日收盘执行（循环明日走到「执行 pending」段）；
        #   lag=0：信号当日收盘立即执行（当日收益已结算完，等价于收盘瞬间换仓）。
        k += 1
        if k % every == 0:
            if lag == 0:
                costs[-1], turns[-1] = _execute(i, _signal_at(i))
            else:
                pending = _signal_at(i)

    ret = pd.Series(rets, index=dates, name=label or "rotation")
    years = ret.index.map(lambda d: d.year)
    yearly = {int(y): float((1 + g).prod() - 1) for y, g in ret.groupby(years)}
    return {
        "label": label,
        "ret": ret,
        "nav": navs,
        "yearly": yearly,
        "total_cost": float(sum(costs)),
        "total_turnover": float(sum(turns)),
        "n_days": len(ret),
    }


# ---------------------------------------------------------------- 指标

def perf_stats(ret: pd.Series, label: str = "") -> dict:
    """组合层指标：几何年化、年化波动、夏普、最大回撤、卡玛、日胜率。"""
    n = len(ret)
    if n < 2:
        return {"label": label, "days": n}
    total = float((1 + ret).prod() - 1)
    years = n / 250.0
    ann = (1 + total) ** (1 / years) - 1 if total > -1 else -1.0
    vol = float(ret.std(ddof=1) * np.sqrt(250))
    nav = (1 + ret).cumprod()
    dd = float((nav / nav.cummax() - 1).min())
    sharpe = ann / vol if vol > 0 else 0.0
    calmar = ann / abs(dd) if dd < 0 else 0.0
    win = float((ret > 0).mean())
    return {"label": label, "days": n, "total": total, "ann": ann, "vol": vol,
            "sharpe": sharpe, "maxdd": dd, "calmar": calmar, "win_daily": win}


def _fmt_row(s: dict) -> str:
    if "ann" not in s:
        return f"{s['label']:<30} 数据不足"
    return (f"{s['label']:<30} 总收益 {s['total']:>8.1%}  年化 {s['ann']:>7.1%}  "
            f"波动 {s['vol']:>6.1%}  夏普 {s['sharpe']:>5.2f}  最大回撤 {s['maxdd']:>7.1%}  "
            f"卡玛 {s['calmar']:>5.2f}")


# ---------------------------------------------------------------- 基准

def benchmark_equal_weight(close_df: pd.DataFrame, start, rebalance_days: int = 21) -> pd.Series:
    """等权全池基准（约月度再平衡，不含成本——用于池子本身的参照；成本量级见轮动结果）。"""
    idx = [d for d in close_df.index if d >= start]
    pos = {s: close_df.columns.get_loc(s) for s in close_df.columns}
    prices = close_df.to_numpy()
    rets = []
    weights: dict[int, float] = {}
    last_reb = -10**9
    for k, day in enumerate(idx):
        i = close_df.index.get_loc(day)
        if k > 0:
            pi = close_df.index.get_loc(idx[k - 1])
            r = sum(w * (prices[i, j] / prices[pi, j] - 1) for j, w in weights.items())
            rets.append(r)
        if k - last_reb >= rebalance_days:
            avail = [j for j in range(close_df.shape[1]) if not np.isnan(prices[i, j])]
            if avail:
                weights = {j: 1 / len(avail) for j in avail}
                last_reb = k
    return pd.Series(rets, index=idx[1:], name="等权全池(月再平衡)")


def benchmark_buy_hold(close_df: pd.DataFrame, start, symbol: str) -> pd.Series:
    """单标的买入持有基准（无成本；一次买入费率对各基准同量级，不影响对比结论）。"""
    s = close_df[symbol]
    s = s[s.index >= start]
    return s.pct_change().dropna().rename(f"持有{ETF_POOL.get(symbol, symbol)}")


def benchmark_default_legs(close_df: pd.DataFrame, start) -> pd.Series:
    """默认组合等权持有（约月度再平衡）——「无脑默认」参照。"""
    legs = [s for s in DEFAULT_LEGS if s in close_df.columns]
    return benchmark_equal_weight(close_df[legs], start).rename("默认组合等权")


# ---------------------------------------------------------------- CLI

def cmd_fetch_pool(args) -> None:
    from data import fetch_symbol_tencent
    for sym in sorted(set(ETF_POOL) | set(DEFAULT_LEGS)):
        fetch_symbol_tencent(sym)


def cmd_run(args) -> None:
    closes = load_pool_closes(sorted(set(ETF_POOL) | set(DEFAULT_LEGS)))
    annual, r2, guard, start = compute_factors(closes, lookback=args.lookback)
    log(f"数据：{closes.shape[0]} 个交易日 × {closes.shape[1]} 只；回测起点 {start}（≥8 只有得分的首日）")
    score_kwargs = dict(use_r2=not args.no_r2, use_guard=not args.no_guard)

    for lag, name in [(1, "next_close(保守·结论口径)"), (0, "same_close(贴页面)")]:
        score = _score_matrix(annual, r2, guard, **score_kwargs)
        res = simulate_score(closes, score, start, topn=args.topn, fill=args.fill,
                             lag=lag, every=args.every, buffer=args.buffer,
                             min_pool=args.min_pool, thin_mode=args.thin_mode, label=name)
        tag = (f"轮动lb{args.lookback} top{args.topn} 每{args.every}日"
               + (f" buf{args.buffer}" if args.buffer else "")
               + (f" mp{args.min_pool}{args.thin_mode[0]}" if args.min_pool else ""))
        st = perf_stats(res["ret"], f"{tag} [{name}]")
        print(_fmt_row(st))
        print(f"{'':<30} 累计成本 {res['total_cost']:,.0f} 元  累计换手 {res['total_turnover'] / INIT_CAPITAL:.0f} 倍净值")
        yearly_line = "  ".join(f"{y}:{r:+.1%}" for y, r in sorted(res["yearly"].items()))
        print(f"{'':<30} 逐年：{yearly_line}\n")

    for ret in [benchmark_equal_weight(closes, start),
                benchmark_buy_hold(closes, start, "SH.510300"),
                benchmark_default_legs(closes, start)]:
        print(_fmt_row(perf_stats(ret, ret.name)))


def cmd_grid(args) -> None:
    closes = load_pool_closes(sorted(set(ETF_POOL) | set(DEFAULT_LEGS)))
    rows = []
    for lookback in (15, 22, 30, 45):
        annual, r2, guard, start = compute_factors(closes, lookback=lookback)
        for every in (1, 5):
            for topn in (2, 3, 5):
                for use_r2 in (True, False):
                    for use_guard in (True, False):
                        score = _score_matrix(annual, r2, guard, use_r2=use_r2, use_guard=use_guard)
                        tag = f"lb{lookback} n{topn} ev{every} r2{int(use_r2)} g{int(use_guard)}"
                        res = simulate_score(closes, score, start, topn=topn, every=every,
                                             lag=1, label=tag)
                        st = perf_stats(res["ret"], tag)
                        st.update({"lookback": lookback, "every": every, "topn": topn,
                                   "r2": use_r2, "guard": use_guard, "cost": res["total_cost"]})
                        rows.append(st)
                        print(_fmt_row(st) + f"  成本 {res['total_cost']:>7,.0f} 元")
    df = pd.DataFrame(rows)
    out = Path(__file__).resolve().parent / "output"
    out.mkdir(parents=True, exist_ok=True)
    df.to_csv(out / "grid.csv", index=False)
    log(f"网格结果 → {out / 'grid.csv'}（{len(df)} 组，next_close 保守口径）")


def cmd_signals(args) -> None:
    """实时信号（跟踪用，与回测同一套得分逻辑）：最新收盘日全池得分排名 + 推荐目标持仓。

    --live：盘中运行时用腾讯实时价近似今日收盘价拼入序列（页面 14:25 同款近似），
    信号对应「今日尾盘调仓」场景；不加则用最近已收盘日数据。
    """
    from data import _tencent_code, _tencent_request
    closes = load_pool_closes(sorted(set(ETF_POOL) | set(DEFAULT_LEGS)))

    live_prices: dict[str, float] = {}
    live_day = None
    if args.live:
        import datetime as _dt
        import urllib.request
        for sym in closes.columns:
            code = _tencent_code(sym)
            try:
                url = (f"https://{TENCENT_HOSTS[0]}{TENCENT_PATH}?param={code},day,,,1,qfq")
                req = urllib.request.Request(url, headers={"User-Agent": TENCENT_UA})
                with deadline(TENCENT_TIMEOUT):
                    with urllib.request.urlopen(req) as resp:
                        payload = json.loads(resp.read().decode("utf-8"))
                qt = payload["data"][code]["qt"][code]
                live_prices[sym] = float(qt[3])          # qt[3] = 实时价
                live_day = qt[30][:8] if len(qt) > 30 else None   # yyyymmddHHMMSS
            except Exception as e:
                log(f"  ⚠️ {sym} 实时价拉取失败：{e}（该标的用最近收盘价）")
        if live_prices and live_day:
            d = _dt.date(int(live_day[:4]), int(live_day[4:6]), int(live_day[6:8]))
            if d > closes.index[-1]:                      # 盘中：今日实时价拼入序列尾部
                        new_row = {s: live_prices.get(s, closes.iloc[-1][s]) for s in closes.columns}
                        closes.loc[d] = new_row
                        log(f"实时价已拼入（{d}，{len(live_prices)}/{closes.shape[1]} 只拉到）")

    lookback = args.lookback
    last = closes.index[-1]
    scores: dict[str, float] = {}
    for sym in closes.columns:
        series = closes[sym].dropna().to_numpy()
        sc = momentum_score(series, lookback, use_r2=not args.no_r2)
        if sc is None:
            continue
        if crash_guard(series):
            sc = 0.0
        scores[sym] = sc

    ranked = sorted(scores.items(), key=lambda kv: -kv[1])
    n_pos = sum(1 for _, v in ranked if v > 0)
    print(f"\n=== ETF 动量轮动信号（{last}，lookback={lookback}） ===")
    print(f"池子丰富度：正得分标的 {n_pos}/{len(scores)}" + ("  ⚠️ <20（edge 条件不满足，降仓/观望）" if n_pos < 20 else ""))
    print(f"{'排名':<4}{'代码':<12}{'名称':<8}{'得分':>8}  状态")
    for k, (sym, sc) in enumerate(ranked[:10], 1):
        name = ETF_POOL.get(sym) or {"SZ.159628": "国证2000", "SH.512800": "银行"}.get(sym, "")
        tag = "🟢 入选" if k <= args.topn and sc > 0 else ("⛔ 防接刀清零" if sc == 0 else "")
        print(f"{k:<4}{sym:<12}{name:<8}{sc:>8.2f}  {tag}")
    picks = [sym for sym, sc in ranked[:args.topn] if sc > 0]
    print(f"\n推荐目标持仓（纯排名 top{args.topn}，等权）：{picks if picks else '无 → 默认组合（国证2000/黄金/银行）等权'}")
    print(f"缓冲带规则（若启用 buffer）：持有中跌出前 {args.topn + args.buffer} 才卖，腾位买入新进前 {args.topn}")
    print("提醒：候选级策略（非稳健交付级），预期年化 12~16%，详见 rotation/ROTATION.md；不构成投资建议。")


def main() -> None:
    parser = argparse.ArgumentParser(prog="rotation.py", description="ETF 动量轮动策略回测（T6）")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("fetch-pool", help="拉全池日 K（腾讯源）")
    p.set_defaults(fn=cmd_fetch_pool)

    p = sub.add_parser("run", help="主口径回测（next_close + same_close + 基准）")
    p.add_argument("--lookback", type=int, default=22)
    p.add_argument("--topn", type=int, default=3)
    p.add_argument("--fill", choices=["cash", "default"], default="cash")
    p.add_argument("--every", type=int, default=1, help="调仓间隔（交易日，1=逐日页面口径）")
    p.add_argument("--buffer", type=int, default=0, help="换手缓冲带（跌出前 topn+buffer 才卖；0=无）")
    p.add_argument("--min-pool", type=int, default=0, help="池子丰富度阈值（正得分标的 < 此数时降仓/空仓；0=不启用）")
    p.add_argument("--thin-mode", choices=["scale", "halt"], default="scale", help="丰富度不足时的处理（scale=降仓 / halt=空仓）")
    p.add_argument("--no-r2", action="store_true")
    p.add_argument("--no-guard", action="store_true")
    p.set_defaults(fn=cmd_run)

    p = sub.add_parser("grid", help="参数网格（lookback × topn × R² × 防接刀，保守口径）")
    p.set_defaults(fn=cmd_grid)

    p = sub.add_parser("signals", help="实时信号：最新收盘日得分排名 + 推荐目标持仓")
    p.add_argument("--lookback", type=int, default=22)
    p.add_argument("--topn", type=int, default=3)
    p.add_argument("--buffer", type=int, default=2)
    p.add_argument("--no-r2", action="store_true")
    p.add_argument("--live", action="store_true", help="盘中用实时价近似今日收盘（页面 14:25 同款）")
    p.set_defaults(fn=cmd_signals)

    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
