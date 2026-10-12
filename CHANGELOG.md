# Changelog

## [0.1.0] - 2026-09-19

### 变更（智能体专属文件清理：CLAUDE.md / .claude / .pi 删除）

- **为什么改**（2026-10-12）：全局新规「智能体专属文件只属于 Agent 项目」（`~/.claude/docs/agents-registry.md`「智能体专属文件归属与子项目映射（2026-10-12 修订）」，取代原「子项目 `.claude/` 超集」规则）：`CLAUDE.md`、`AGENTS.md`、`.claude/`、项目级 `.pi/` 等「会话启动时按工作目录加载、表征智能体身份」的项目级文件只有 Agent 项目允许拥有，非 Agent 项目（含本子项目）一律不得存在；后台会话只能以 Agent 项目根目录为工作目录。
- **改了什么**（2026-10-12）：删除 `CLAUDE.md`、`.claude/`（quant skill 副本，无运行时数据）、`.pi/`（软链接，原指向 `.claude/skills`）；`.gitignore` 移除 `.claude/*` 运行时规则。全仓库 grep 核查：除被删文件自身外无任何脚本 / 文档 / 配置引用（README 双语、engine/、trend/、rotation/ 均不受影响）；quant skill 权威源仍在主仓库 QuantStrategistAgent 的 `.claude/skills/quant/`。

### 变更（主策略目录改名：swing/ → trend/，目录名即策略名）

- 为什么改：用户裁定「主策略目录名要改，目录名即策略名」——项目从单一策略发展为双策略（趋势跟随 + 轮动），原目录名 swing/ 是建仓时「目录名 = 项目名」的历史遗留，与 rotation/ 并列时语义不对仗；改名 trend/（趋势）与 rotation/（轮动）对仗，目录名即策略名。
- 改了什么：① `swing/` → `trend/`（6 个文件整体移动，代码内容不变）；② 文件内路径引用同步（4 个 CLI 的用法注释、README、STRATEGY.md 的「在 trend/ 目录下运行」）；③ 根 `README.md` + `README_cn.md` 双语同步（链接 `trend/STRATEGY.md`、快速开始 `cd ../trend`、目录结构）；④ `CLAUDE.md` 项目描述引用更新。历史条目与归档记录中的 swing/ 路径为当时事实，保留不改。
- 验证：trend/ 下 check_signal.py / backtest.py 导入与引擎链路正常（报缺美股缓存为本机无数据，与改名无关）；rotation/ 不受影响。

### 变更（目录拆分：轮动策略独立成目录，不与主策略混放）

- **新建 `rotation/` 目录**：为什么改：用户裁定「动量轮动策略和主策略要分开放，分别放在不同的目录」——轮动与趋势跟随是两个独立策略，文档与代码混在 swing/ 与 engine/ 里边界不清。改了什么：① `swing/ROTATION.md` → `rotation/ROTATION.md`、`engine/rotation.py` → `rotation/rotation.py`（共享数据层仍复用 `engine/data.py`，sys.path 指向 ../engine）；② `swing/README.md` 恢复为纯主策略版（回退上轮混入的轮动内容）；③ 根 `README.md` + `README_cn.md` 双语同步：候选策略小节链接、快速开始第 5 步路径、目录结构（swing/ 主策略 + rotation/ 候选策略 + engine/ 共享层）；④ `.gitignore` 加 `rotation/output/`（grid.csv 迁入）；⑤ `CLAUDE.md` 项目定位更新为双策略描述；⑥ `rotation/ROTATION.md` 内全部路径引用同步；⑦ TODO T10 路径更新。验证：rotation/ 新路径 signals / run 结果与拆分前一致（19.8%），swing/ CLI 正常。

### 新增（轮动策略正式文档化 + 实时信号 CLI）

- **`swing/ROTATION.md` 重写为正式策略文档**：为什么改：用户裁定「能挣钱就先把策略详细记录下来」，把 T6/T9 的研究报告升格为供单独使用的完整策略文档（对齐 STRATEGY.md 的使用者文档标准）。改了什么：完整口径（得分公式展开 / 池子 / 调仓与缓冲带规则 / 执行规程 / 成本）、证据链汇总（主结果表 / 分段 / 参数稳健 / 与主策略证据等级对比）、风险与回撤预期、使用边界与升级路径（原版池复核 + 样本外跟踪）、复现命令。
- **`engine/rotation.py` 新增 `signals` 命令**：实时信号检测（与回测同一套得分逻辑，双用途原则）——全池得分排名 + 推荐 top3 持仓 + 池子丰富度警示；`--live` 盘中用腾讯实时价近似今日收盘（页面 14:25 同款）。顺带修复：补 json 导入与 TENCENT_* 常量导入、清除 3 处 tab 缩进。
- **`swing/README.md` / 根 `README.md` + `README_cn.md`（双语同步）**：标题与简介改为双策略定位（主策略 + 轮动候选），新增轮动 CLI 表、快速开始第 5 步、目录结构加 ROTATION.md 与 rotation.py、数据依赖补腾讯源、风险提示补轮动条目；根 README 双版新增「候选策略：A 股 ETF 动量轮动」小节（含诚实预期 12~16% 标注）。

### 变更（T9 轮动策略深化：月度锚定证伪 + 缓冲带/丰富度规则，完成待办 T9）

- **`engine/rotation.py` 新增 buffer / min_pool / thin_mode 参数**：为什么改：待办 T9 的 c（换手缓冲带：跌出前 topn+buffer 才卖）与 d（池子丰富度规则：正得分标的不足时降仓/空仓）需状态化选股，落为 simulate_score 正式参数供 CLI 复现。结果：buffer=2 全面小优（年化 19.8%、夏普 0.81、成本 −17%）采纳；min_pool=20 scale 用收益换回撤（13.5%/−25.0%）定位风控可选。
- **`swing/ROTATION.md` 追加第七节（T9 深化）**：b) 月度锚定检验证伪——精细 lookback 曲线（21/22 高、20/23 断崖）+ 动态月度锚定 15.2% 显著低于固定 22 日 19.1% + 逐年对比定位优势集中于 2015/2026，结论 22 日为过拟合成分主导、真实预期向邻域均值 15~16% 打折；推荐配置更新（`--every 5 --buffer 2 [--min-pool 20]`）；最终评级维持候选级。
- **`TODO.md` / `TODO-archive.md`**：T9 归档（✅ 已完成，a 子项因缺页面原版清单未执行）；新开 T10（原版池复核，前提=用户提供清单）；T8 不变。

### 新增（ETF 动量轮动策略移植回测，完成待办 T6）

- **`engine/rotation.py`**：为什么建：待办 T6 要求把外部页面「ETF 动量轮动工作台」的 22 日加权动量轮动策略移植进本项目回测（组合层轮动与单标的 evaluate 框架不同构，独立成模块）。改了什么：① 策略纯函数（加权动量得分 / 防接刀，双用途）；② 组合层回测器（股数市值模式，逐腿计佣金含最低 5 元 + 滑点，支持调仓间隔 every / 成交延迟 lag / fill 模式）；③ CLI：fetch-pool / run / grid（96 组参数网格）。验证：毛/净双口径、前后半分段、滚动 walk-forward、调仓间隔曲线、fill 双模式。
- **`swing/ROTATION.md`**：回测研究报告存档（口径、主结果表、四个核心发现、诚实评级、局限、复现命令）。核心结论：页面逐日调仓不交付（净 11.3%，成本+噪声双重磨损）；每 5 日调仓净 19.1%（毛 26.2%）但 lookback 参数敏感 + WF 衰减，评级候选策略；edge 集中在 2020 后池子丰富期。
- **全池 35 只 ETF 日 K 落缓存**（腾讯源，含新增游戏/钢铁两只代码）。
- **`TODO.md` / `TODO-archive.md`**：T6 归档（✅ 已完成），新开 T9（后续深化：原版池复核 / 月度锚定 lookback / 换手缓冲带 / 池子丰富度规则），T8 补回测器就绪标注。

### 变更（A 股 ETF 日 K 数据源接入，完成待办 T7）

- **`engine/data.py` 新增腾讯财经日 K 源**：为什么改：待办 T7 要求为 T6（ETF 动量轮轮回测）接入轻量 A 股 ETF 日 K 源（免 OpenD、免费无 key）。改了什么：新增腾讯源区块（域名自动切换、单次 800 根分页回翻到上市日、qfq 前复权全量重拉、落 parquet 带 Asia/Shanghai 时区）；`fetch` 命令自动路由——A 股（SH/SZ）DAY 走腾讯，分钟 K 仍走富途，港美股不变。验证：3 只 ETF 回溯到上市日；与新浪独立源 60 天 × 4 价格字段 0 不一致；`verify` 全过；回测引擎读腾讯缓存跑通。
- **`engine/data-sources.md` 追加腾讯源实测记录**：已接入源清单第 4 项 + 踩坑备忘 4 条（行顺序开收高低非 OHLC、单次上限非线性钳制、volume 单位手、qfq 无增量语义）。
- **`TODO.md` / 新建 `TODO-archive.md`**：T7 归档（✅ 已完成），T6 补数据源就绪标注。

### 新增（补齐 `.claude/` 超集同步缺口）

- **`.claude/skills/quant/` 超集副本**：自主仓库 QuantStrategistAgent `.claude/skills/quant/` 逐字节复制（SKILL.md / README.md / schema.md / data-sources.md / data.py / backtest.py / confidence_table.json / strategies/）。为什么补：2026-09-12 建仓时只随附了主仓库 CLAUDE.md 全文、漏建 `.claude/` 目录，主仓库 9 月 13 日 skill 更新时同步只触达 Intraday / gridtrader，Swing 因无副本一直缺位（用户 2026-09-19 发现）；按全局规则「Agent 项目 `.claude/` 变更自动同步到全部子项目（无需询问）」补齐，CLAUDE.md 中 `.claude/skills/quant/...` 引用自此可解析。同步动作为本地文件复制，git 提交由用户后续自行处理。
- **`.gitignore` 追加**：`.claude/skills/quant/data_cache/` 与 `.claude/skills/quant/output/`（quant skill 运行时产物 K 线缓存 / 回测输出，不入库；与 Intraday 仓库口径一致）。

### 变更（体系叙事同步：删去 Victor / DayTradingAgent 关联表述，量化策略独立开发）

- **为什么改**（2026-09-19）：主仓库 QuantStrategistAgent 叙事修正（用户裁定：Markowitz 量化策略独立开发、与 DayTradingAgent 无关系），随附嵌文与本地文件同步清理，避免旧叙事继续误导。
- **改了什么**（2026-09-19）：① `CLAUDE.md` 随附嵌文同步主仓库 5 处修订（定位句独立开发、第 4 步沉淀策略库、独立边界块、中性化表述）；② `assets/markowitz_workflow.svg` 与主仓库同步（STEP 4 Deliver→Library、底部改独立边界条）；③ `engine/schema.md` 6 处「Victor」改为「使用方 / 调用方」中性表述（stop_loss_ref 说明、诊断成分、实战 f、g>0 门槛、样本量降权等）；④ `engine/backtest.py` 1 处同步。保留：schema.md / backtest.py 中 `g` 公式推导出处链接（参考文献引用，非交付关系）。

### 新增

- **TODO.md（自 Intraday 私有仓库迁入三条日 K 级别研究待办 T6~T8）**：T6 外部页面「ETF 动量轮动工作台」22 日加权动量轮动策略移植回测、T7 腾讯财经日 K 接口接入（A 股 ETF 日 K 数据源）、T8 全天候风险平价立项评估。为什么迁：三条均日 K / 组合配置级别，与本项目（日 K 策略）同尺度、与 Intraday 仓库（日内研究）不同尺度，用户 2026-09-13 裁定「日 K 级别的内容可以移动到 Swing」。改了什么：本仓库首建 TODO.md（项目标配，含个人隐私类待办分流指引）；三条保留原编号 T6~T8 便于跨仓库追溯（本项目后续新编号自 T9 起），正文与原记录时间保留，仅修订跨仓库指向（原「T1」指 Intraday 仓库的 A 股日内待办）与体系措辞（Victor 加权输入语境改为单标的信号策略）。敏感检查：三条正文仅为策略口径、公开接口与技术参数，无账户 / 密钥 / 个人隐私，可进公开仓库。

### 变更

- **assets/logo.svg**：副标题由「Day-K Trend Strategy · 日K趋势跟随策略」改为纯英文「Day-K Trend-Following Strategy」。为什么改：logo 作为视觉标识不应混入中文（中文受众看 README_cn.md 即可），且统一用英文与 README 英文版标题口径一致，也避免 SVG 字体回退导致的中文渲染差异。

### 新增（pi harness 复用 Claude skills）

- **`.pi/skills` 符号链接**：新建 `.pi/skills -> ../.claude/skills` 相对软链接。为什么建：pi（coding agent harness）从项目 `.pi/skills/` 读取项目级 skills，而本项目 skills 唯一权威副本在 `.claude/skills/quant/`（主仓库超集同步产物）；软链接让两个 harness 共享同一份文件，避免双份维护漂移。用相对路径（而非绝对路径）建链，clone 到任意路径后链接依然有效。

## 0.1.0（2026-09-12）

### 新增

- **建仓**：从 QuantStrategistAgent（QSAgent）私有主仓库拆出 swing 日 K 趋势跟随策略为独立公开仓库。为什么拆：QSAgent 主体转入私有研发（日内策略进入实盘化阶段），而 swing 策略基于公共方法学（Donchian 突破 + ATR trailing，海龟交易法体系）、日线稀疏信号、次日开盘市价执行——公开不影响策略有效性，且完整的研究文档（20 年 × 37 只回测、四重泛化验证、诚实标注局限、已证伪方案清单）本身是量化研究能力的重要展示面。
- **初始内容**：`swing/`（策略完整文档 STRATEGY.md + 三个 CLI：信号检测 / 回测 / 分析）、`engine/`（数据层 data.py + 回测引擎 backtest.py + 三套策略实现，自 QSAgent quant 数据层迁移，`common.py` 引擎路径改为本仓库 `engine/`）、MIT 许可证与项目标配文件。
- 注意：本仓库为**定稿发布快照**（fresh init、不带历史）——策略参数与结论以本文档为准，后续若有大幅调优将另行评估公开粒度。
