# 架构说明 — LangGraph-financial-agent (Nice Invest)

> 最后更新：2026-05-20

---

## 目录结构

```
LangGraph-financial-agent/
├── CLAUDE.md              ← 项目架构 + 协作规则
├── PROGRESS.md            ← 阶段进度看板（完整历史）
├── README.md              ← 安装/运行说明
├── requirements.txt       ← Python 依赖
├── config.example.py      ← 配置模板
├── config.py              ← 实际配置（gitignore）
├── main.py                ← Gradio 调试入口（开发用）
├── server.py              ← FastAPI 后端入口（正式 API）
│
├── Guidance/              ← 项目文档目录
│   ├── PROGRESS.md        ← 阶段进度（精简版）
│   ├── bug-log.md         ← Bug 记录（B1-B17 + C1-C3 + U1）
│   ├── pattern-library.md ← 解决范式库（P1-P12）
│   ├── project-log.md     ← 对话日志
│   └── architecture.md    ← 本文件
│
├── src/
│   ├── __init__.py
│   ├── graph.py            ← LangGraph 编排（Router → Send → Summary）
│   ├── state.py            ← 全局状态定义（add reducer）
│   ├── auth.py             ← 邮箱验证码登录 + Resend
│   ├── logger.py           ← 结构化日志（终端 + 文件）
│   ├── stock_registry.py   ← A 股注册表（5517 只，本地缓存）
│   │
│   ├── agents/
│   │   ├── template.py     ← 七条铁律 + 两段式 + JSON Schema
│   │   ├── analyst.py      ← 基本面 Agent
│   │   ├── technical.py    ← 技术面 Agent
│   │   ├── valuation.py    ← 估值 Agent
│   │   ├── news.py         ← 新闻 Agent
│   │   └── summary.py      ← Summary Agent（ReAct）
│   │
│   └── mcp_tools/
│       ├── tushare_api.py  ← Tushare Pro 封装
│       ├── news_api.py     ← akshare 新闻 + 财务/行情（15s 超时）
│       ├── yahoo_api.py    ← yfinance 封装（海外兜底）
│       └── calculator.py   ← 财务计算（杜邦/PEG/比率）
│
├── web/                   ← React 前端
│   ├── src/pages/
│   │   ├── Landing.tsx    ← 落地页（确定性 K 线）
│   │   ├── Login.tsx      ← 邮箱验证码登录
│   │   ├── Dashboard.tsx  ← 分析工作台
│   │   └── Report.tsx     ← 报告页
│   └── src/lib/
│       ├── api.ts          ← API 调用 + SSE
│       └── charts.tsx      ← SVG 图表
│
├── .github/workflows/
│   └── docker-build.yml   ← CI/CD（ACR 推送）
│
├── tests/                 ← 测试报告
├── logs/                  ← 推理日志
├── Dockerfile             ← 多阶段构建
├── render.yaml            ← Render 部署（已停用）
└── .dockerignore
```

## 核心文件说明

| 文件 | 作用 |
|------|------|
| `server.py` | FastAPI 入口，5 API 端点 + SSE + 输出清洗 + 体验 Key 注入 |
| `src/graph.py` | LangGraph 状态机，Router → 4 Agent 并行 → Summary → Evaluation |
| `src/agents/template.py` | 七条铁律 + 五段式模板 + 5 种 JSON Schema |
| `src/mcp_tools/news_api.py` | akshare 主力工具（15s 超时保护） |
| `src/mcp_tools/yahoo_api.py` | yfinance 兜底工具 |
| `src/stock_registry.py` | A 股注册表 + 安全护栏 |
| `web/src/lib/api.ts` | 前端 API 层（SSE 解析 + Auth + 清洗兜底） |
| `web/src/pages/Dashboard.tsx` | 分析工作台（搜索 + Agent 网格 + Modal + 配置） |
| `web/src/pages/Report.tsx` | 报告页（研报风格，Markdown 渲染） |

## 变更历史

| 日期 | 变更 | 影响 |
|------|------|------|
| 2026-05-15 | 核心链路搭建 + 首轮测试 | 4 Agent + Summary + Gradio UI |
| 2026-05-17 | 前后端整合（React + FastAPI） | 全新 web/ + server.py |
| 2026-05-18 | 全量 Bug 修复 + 部署上线 | B1-B15 + A 股护栏 + Render |
| 2026-05-19 | 数据源升级 + Sealos 迁移 | B16/B17 + yfinance + ACR CI/CD |
| 2026-05-20 | Guidance 文档体系建立 | 新建 Guidance/ 5 个文件 |
