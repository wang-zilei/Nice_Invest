# 项目对话日志 — LangGraph-financial-agent

> 每次会话的简短总结，用于快速回顾历史

---

## 2026-05-20 — 项目一阶段复盘 + Harness 优化 + 文件清理

- **主题**：项目复盘写入 + Harness 优化 + 文件清理
- **关键内容**：
  - 完成一阶段复盘（Agent 框架/UI-UX 设计/部署 Bug 全量整理）
  - 创建 `docs/bug-log.md`（17 个 Bug 全记录）和 `docs/pattern-library.md`（12 个范式）
  - 清理已停用的 Procfile/railway.toml/Office 临时文件
  - 更新 auto memory 到阶段十一完成状态
- **产出文件**：`docs/bug-log.md` + `docs/pattern-library.md` + memory 更新

## 2026-05-19 — 数据源架构升级 + Sealos 部署

- **主题**：yfinance 数据源引入 + Sealos 迁移 + API Key 修复
- **关键内容**：
  - 新增 yahoo_api.py 封装（5 个数据函数）
  - 4 个 Agent 集成 yfinance 三阶段降级
  - GitHub Actions + 阿里云 ACR CI/CD
  - Sealos 国内云部署，B16/B17/C1/C2/C3 修复
  - 数据源优先级翻转（akshare 国内主力）
- **产出文件**：`src/mcp_tools/yahoo_api.py` + `.github/workflows/docker-build.yml`

## 2026-05-18 — 输出格式 + 数据源翻转 + A 股护栏 + 部署

- **主题**：全量 Bug 修复 + 部署上线
- **关键内容**：
  - B1-B8 修复（花括号/游客模式/CORS/历史查询/输出清洗/数据源翻转/报告UI/股票名称）
  - A 股注册表 + 安全护栏（5517 只全量）
  - Railway → Render 部署切换
  - 体验 Key config.py 兜底恢复
  - Markdown 符号去除 + 报告页精修
- **产出文件**：`src/stock_registry.py` + 多文件改动

## 2026-05-17 — 前后端整合 + UI 精修

- **主题**：React SPA + FastAPI + 邮箱登录
- **关键内容**：
  - FastAPI 后端（5 API 端点 + SSE）
  - React 19 SPA（Landing/Login/Dashboard/Report）
  - 邮箱验证码登录 + 游客模式
  - Agent 两段式输出（Markdown + JSON）
  - 落地页确定性 K 线 + 研报风格报告页
- **产出文件**：`server.py` + `web/` + `src/auth.py` + `src/logger.py`

## 2026-05-15 — 核心链路首轮测试

- **主题**：4 Agent 并行 + Summary + 评判 Agent
- **关键内容**：
  - LangGraph 编排完成（Router → 4 Agent → Summary）
  - Gradio Web UI
  - 平安银行 000001.SZ 全量分析 PASS
  - 结构回归测试 62 PASS 0 FAIL
- **产出文件**：`tests/` 测试报告

## 2026-05-26 - Landing page stabilization + mist refinement

- **主题**：公开站点落地页体验修复与视觉微调
- **关键内容**：
  - 修复根路径自动进入 Dashboard 的问题：访问 `/` 先停留在 Landing，点击入口后再检查 session。
  - 移除落地页首次加载时的整体翻转：将 `mouse/smoothMouse` 初始值从极端坐标改为中心点，并加 `hasPointer` 防护。
  - 移除粒子时间驱动入场闪烁：不再依赖 `uTime/getElapsedTime`，粒子亮度改为稳定随机值。
  - 约束随机 K 线纵向位置：生成后按整体中心归零，使 K 线稳定围绕标题作为背景。
  - 初步柔化 Gaussian mist 鼠标交互：去掉固定半径硬光圈，改为高斯衰减的轻雾拨开效果。
- **Git 检查点**：`7d927d3 Stabilize landing page entry` 保存了稳定落地页状态；之后的 mist 参数微调仍为未提交工作区改动。
- **产出文件**：`web/src/App.tsx`、`web/src/pages/Landing.tsx`、`web/public/landing.html`、`web/dist/landing.html`

## 2026-05-27 - Report page polish

- **主题**：报告详情页信息层级与返回状态修复
- **关键内容**：
  - 去掉报告标题状态行左侧的方向箭头/趋势 icon，只保留文字结论。
  - 移除报告正文之后单独的“风险清单”模块，避免与正文第五段风险清单重复。
  - 从报告页点击“返回分析工作台”时保留 Dashboard 已完成分析状态，不回到空白初始页。
- **产出文件**：`web/src/App.tsx`、`web/src/pages/Report.tsx`
