# Changelog

## [Unreleased]

### 变更

- **assets/logo.svg**：副标题由「Day-K Trend Strategy · 日K趋势跟随策略」改为纯英文「Day-K Trend-Following Strategy」。为什么改：logo 作为视觉标识不应混入中文（中文受众看 README_cn.md 即可），且统一用英文与 README 英文版标题口径一致，也避免 SVG 字体回退导致的中文渲染差异。

## 0.1.0（2026-09-12）

### 新增

- **建仓**：从 QuantStrategistAgent（QSAgent）私有主仓库拆出 swing 日 K 趋势跟随策略为独立公开仓库。为什么拆：QSAgent 主体转入私有研发（日内策略进入实盘化阶段），而 swing 策略基于公共方法学（Donchian 突破 + ATR trailing，海龟交易法体系）、日线稀疏信号、次日开盘市价执行——公开不影响策略有效性，且完整的研究文档（20 年 × 37 只回测、四重泛化验证、诚实标注局限、已证伪方案清单）本身是量化研究能力的重要展示面。
- **初始内容**：`swing/`（策略完整文档 STRATEGY.md + 三个 CLI：信号检测 / 回测 / 分析）、`engine/`（数据层 data.py + 回测引擎 backtest.py + 三套策略实现，自 QSAgent quant 数据层迁移，`common.py` 引擎路径改为本仓库 `engine/`）、MIT 许可证与项目标配文件。
- 注意：本仓库为**定稿发布快照**（fresh init、不带历史）——策略参数与结论以本文档为准，后续若有大幅调优将另行评估公开粒度。
