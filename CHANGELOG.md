# Changelog

## [0.1.0] - 2026-09-19

### 变更（体系叙事同步：删去 Victor / DayTradingAgent 关联表述，量化策略独立开发）

- **为什么改**（2026-09-19）：主仓库 QuantStrategistAgent 叙事修正（用户裁定：Markowitz 量化策略独立开发、与 DayTradingAgent 无关系），随附嵌文与本地文件同步清理，避免旧叙事继续误导。
- **改了什么**（2026-09-19）：① `CLAUDE.md` 随附嵌文同步主仓库 5 处修订（定位句独立开发、第 4 步沉淀策略库、独立边界块、中性化表述）；② `assets/markowitz_workflow.svg` 与主仓库同步（STEP 4 Deliver→Library、底部改独立边界条）；③ `engine/schema.md` 6 处「Victor」改为「使用方 / 调用方」中性表述（stop_loss_ref 说明、诊断成分、实战 f、g>0 门槛、样本量降权等）；④ `engine/backtest.py` 1 处同步。保留：schema.md / backtest.py 中 `g` 公式推导出处链接（参考文献引用，非交付关系）。

### 新增

- **TODO.md（自 Intraday 私有仓库迁入三条日 K 级别研究待办 T6~T8）**：T6 外部页面「ETF 动量轮动工作台」22 日加权动量轮动策略移植回测、T7 腾讯财经日 K 接口接入（A 股 ETF 日 K 数据源）、T8 全天候风险平价立项评估。为什么迁：三条均日 K / 组合配置级别，与本项目（日 K 策略）同尺度、与 Intraday 仓库（日内研究）不同尺度，用户 2026-09-13 裁定「日 K 级别的内容可以移动到 Swing」。改了什么：本仓库首建 TODO.md（项目标配，含个人隐私类待办分流指引）；三条保留原编号 T6~T8 便于跨仓库追溯（本项目后续新编号自 T9 起），正文与原记录时间保留，仅修订跨仓库指向（原「T1」指 Intraday 仓库的 A 股日内待办）与体系措辞（Victor 加权输入语境改为单标的信号策略）。敏感检查：三条正文仅为策略口径、公开接口与技术参数，无账户 / 密钥 / 个人隐私，可进公开仓库。

### 变更

- **assets/logo.svg**：副标题由「Day-K Trend Strategy · 日K趋势跟随策略」改为纯英文「Day-K Trend-Following Strategy」。为什么改：logo 作为视觉标识不应混入中文（中文受众看 README_cn.md 即可），且统一用英文与 README 英文版标题口径一致，也避免 SVG 字体回退导致的中文渲染差异。

## 0.1.0（2026-09-12）

### 新增

- **建仓**：从 QuantStrategistAgent（QSAgent）私有主仓库拆出 swing 日 K 趋势跟随策略为独立公开仓库。为什么拆：QSAgent 主体转入私有研发（日内策略进入实盘化阶段），而 swing 策略基于公共方法学（Donchian 突破 + ATR trailing，海龟交易法体系）、日线稀疏信号、次日开盘市价执行——公开不影响策略有效性，且完整的研究文档（20 年 × 37 只回测、四重泛化验证、诚实标注局限、已证伪方案清单）本身是量化研究能力的重要展示面。
- **初始内容**：`swing/`（策略完整文档 STRATEGY.md + 三个 CLI：信号检测 / 回测 / 分析）、`engine/`（数据层 data.py + 回测引擎 backtest.py + 三套策略实现，自 QSAgent quant 数据层迁移，`common.py` 引擎路径改为本仓库 `engine/`）、MIT 许可证与项目标配文件。
- 注意：本仓库为**定稿发布快照**（fresh init、不带历史）——策略参数与结论以本文档为准，后续若有大幅调优将另行评估公开粒度。
