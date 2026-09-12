<p align="center">
  <img src="assets/logo.svg" width="320" alt="Swing logo" />
</p>

<h1 align="center">Swing — 日 K 趋势跟随策略（美股）</h1>

<p align="center">
  <a href="LICENSE.md"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT" /></a>
  <img src="https://img.shields.io/badge/Version-0.1.0-0D9488.svg" alt="Version" />
  <img src="https://img.shields.io/badge/Type-Quant%20Strategy-16C784.svg" alt="Type: Quant Strategy" />
  <img src="https://img.shields.io/badge/Endpoint-Backtest%20Validated-F59E0B.svg" alt="Endpoint: Backtest Validated" />
  <img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/xhqing/xhqing/main/traffic/badges/Swing.json" alt="Visits/day (14d)" />
</p>

<p align="center">🌐 <a href="README.md">English</a></p>

**Swing** 是一套文档完整、经过回测验证的**日 K 趋势跟随策略**（美股大盘股），由 [Markowitz](https://github.com/xhqing/QuantStrategistAgent)（[xhqing AI agent 团队](https://github.com/xhqing)的量化策略师 agent）开发。

> **这不是黑箱。** 策略完整逻辑、参数、验证方法、诚实的局限标注、已证伪方案清单全部公开——见 [`swing/STRATEGY.md`](swing/STRATEGY.md)。趋势跟随本身是公开方法学（Donchian 突破 / 海龟交易法体系）；本仓库的价值在于**用 20 年数据对这套公开方法学做了严格验证**。

---

## 一句话策略

**收盘创 20 日新高 + 放量 ≥1.5 倍 → 次日开盘买入；2×ATR 固定止损截断亏损，3×ATR trailing 让利润奔跑，60 日超时兜底。**

经典 Donchian 突破 + 量能确认 + ATR trailing——即时间序列动量，刻意不加任何过滤（实测所有「优化」都更差）。

## 验证要点（2006–2026，37 只美股 / ETF，只做多）

| 指标 | 值 |
|---|---|
| 池化交易笔数 | 2,086 笔 |
| 净期望 | **+0.251R/笔**（对数增长率 +0.444%/笔） |
| 正 g 标的 | 34 / 37（92%） |
| 正收益年份 | 18 / 21 |
| walk-forward 样本外 | **零衰减**（无过拟合） |
| 持仓中位数 | 13 天 |

<p align="center">
  <img src="assets/performance.png" width="100%" alt="回测业绩：累计净 R、按年净 avg_R、按标的净 avg_R、R 分布" />
</p>

诚实标注（完整清单见 STRATEGY.md §11）：月胜率只有 54%——约一半月份小亏小赚；约 1/3 年份在震荡 / 危机行情亏钱；最差单笔为隔夜跳空 −5.58R。**这是「经常小亏、偶尔大赚」的系统，仓位纪律（§8）正是为那条尾部设计的。**

## 快速开始

需要 Python 3 + pandas（拉数据需富途 OpenD 在线）。

```bash
# 1. 拉取日 K 数据（首次跑一次，OpenD 保持在线）
cd engine && python3 data.py fetch-all --ktype DAY

# 2. 检测全部 37 只标的今日信号（每天美股收盘后跑）
cd ../swing && python3 check_signal.py

# 3. 完整回测（推荐方案 1）
python3 backtest.py --scheme 1
python3 backtest.py --all       # 对比全部 4 个方案

# 4. 多维分析
python3 analyze.py monthly      # 月收益率分布
python3 analyze.py hold         # 持仓时间分布
python3 analyze.py yearly       # 按年分解
```

## 目录结构

```
├── swing/            # CLI 层：check_signal / backtest / analyze + STRATEGY.md（完整文档）
│   └── STRATEGY.md   # ★ 策略完整文档——从这里读起
├── engine/           # 数据层（data.py）+ 回测引擎 + 3 套策略实现
└── assets/
```

## 免责声明

本仓库仅供研究学习。**全部内容不构成投资建议**；回测结果不代表实盘与未来表现；据此交易的风险由使用者自行承担。

## 版权与署名

本项目基于 [MIT 许可证](LICENSE.md) 开源。

- 版权所有 (c) 2026 All Contributors
- 引用 / 使用本仓库时请保留版权声明并注明来源：[https://github.com/xhqing/Swing](https://github.com/xhqing/Swing)
