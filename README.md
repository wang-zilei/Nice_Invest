# 基于 LangGraph 的金融分析 Multi-Agent 系统


## 简介

本项目基于 LangGraph + ReAct 模式，设计了一个面向金融分析场景的 Multi-Agent 系统。系统支持：
- **4 个分析 Agent 并行执行**：基本面、技术面、估值、新闻
- **MCP 工具链 + Function Call**：Tushare Pro（主数据源）+ akshare（新闻 + 限流备选）
- **Summary Agent（ReAct 模式）**：交叉验证 + 数据一致性核实 + 加权综合评分
- **React 19 前端 + FastAPI 后端 + SSE 流式推送**：3 页 SPA（Landing → 分析工作台 → 研报）
- **两段式输出**：Markdown 正文+ JSON 代码块（前端渲染）

## 快速开始

### 后端（FastAPI + LangGraph）

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 API Key
cp config.example.py config.py
# 编辑 config.py（可选；也可在前端 UI 中配置）

# 3. 启动后端
python server.py
# → http://localhost:8000
# API 文档: http://localhost:8000/docs
```

### 前端（React + Vite）

```bash
cd web
npm install
npm run dev
# → http://localhost:5173
```

### 测试（可选）

```bash
# 结构回归测试（无需 API Key，62 项检查）
python tests/test_structural.py

# Gradio 调试入口（开发用，非正式 UI）
python main.py
```

## 项目结构

```
LangGraph-financial-agent/
├── CLAUDE.md              ← 项目架构与 Agent 设计（新会话必读）
├── PROGRESS.md            ← 进度看板
├── README.md              ← 本文件
├── requirements.txt       ← Python 依赖
├── config.example.py      ← 配置模板
├── config.py              ← 实际配置（gitignore）
├── server.py              ← FastAPI 后端入口（正式 API + SSE）
├── main.py                ← Gradio 调试入口（开发用，非正式 UI）
│
├── src/
│   ├── graph.py            ← LangGraph 编排（Router → Send 并行 → Summary ReAct → Eval）
│   ├── state.py            ← 全局状态定义
│   ├── agents/
│   │   ├── template.py     ← 四条铁律 + 两段式输出 + 5 种 JSON Schema
│   │   ├── analyst.py      ← 基本面 Agent（Tushare + akshare 备选）
│   │   ├── technical.py    ← 技术面 Agent
│   │   ├── valuation.py    ← 估值 Agent（Tushare + akshare 备选 + PEG）
│   │   ├── news.py         ← 新闻 Agent（akshare 东方财富 + 财联社）
│   │   └── summary.py      ← Summary Agent（ReAct，交叉验证 + 加权评分 + ReportData JSON）
│   └── mcp_tools/
│       ├── tushare_api.py  ← Tushare Pro 封装（动态 token 支持）
│       ├── news_api.py     ← akshare 新闻 + 财务备选数据
│       └── calculator.py   ← 财务计算（杜邦/PEG/CAGR/比率）
│
├── web/                    ← React 19 前端（TypeScript + Tailwind + Three.js）
│   ├── src/
│   │   ├── App.tsx          ← 三页路由（Landing ↔ Dashboard ↔ Report）
│   │   ├── lib/api.ts       ← API 调用层（REST + SSE 解析）
│   │   ├── lib/charts.tsx   ← SVG 图表组件（雷达图/柱状图，零依赖）
│   │   └── pages/
│   │       ├── Landing.tsx  ← 落地页（3D K 线背景）
│   │       ├── Dashboard.tsx← 分析工作台（搜索+SSE+配置+历史+Modal）
│   │       └── Report.tsx   ← 报告页（研报风格）
│   └── ...
│
├── tests/
│   ├── README.md
│   ├── test_structural.py
│   └── ...
│
└── logs/                   ← 推理日志
```

## 输出示例

每个 Agent 按照统一五段式模板输出：

```
一、元信息（数据来源、完整性声明、分析时间）
二、核心结论（一句话总结 + 综合评分）
三、详细分析（按维度展开，量化表述，标注来源）
四、关键指标明细表（指标/数值/行业基准/评价/数据来源）
五、风险提示（风险描述/影响程度/应对建议）
```

详见 [CLAUDE.md](CLAUDE.md) 了解完整架构与 Agent 设计。
