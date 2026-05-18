# LangGraph-financial-agent 项目架构

> 最后更新：2026-05-19（数据源优先级翻转为 akshare 国内主力 + Sealos 部署后 API Key 读取 Bug 修复 + 环境变量兼容 5 种命名）

---

## 项目定位

基于 LangGraph + ReAct 的金融分析 Multi-Agent 系统，面向非技术背景的 AI 产品经理面试场景，强调：
1. Agent 架构设计与编排能力
2. MCP/Function Call 工具链集成
3. 金融场景评测与幻觉检测（**内部工具，不在用户 UI 展示**）

**数据来源**：akshare（东方财富/同花顺，国内主力）→ Tushare Pro（第一备选）→ yfinance（Yahoo Finance，海外兜底），三级降级策略
**部署**：Sealos 国内云（镜像仓库：阿里云 ACR），GitHub Actions CI/CD 自动构建推送
**Web UI**：React 19 + TypeScript + Tailwind CSS 4 + Three.js（3D 动效），后端 FastAPI 提供 REST + SSE

---

## 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| 编排 | LangGraph | Agent 状态机、ReAct 循环编排 |
| Agent | LangChain + LLM | 4 个分析 Agent + 1 个 Summary Agent（ReAct）+ 1 个评判 Agent |
| 数据(主) | akshare | 财务摘要、估值参考、日线行情、新闻舆情（东方财富+财联社），国内源免费不限流 |
| 数据(备1) | Tushare Pro SDK | 股票行情、财务指标补充（限流时自动降级） |
| 数据(备2) | yfinance | 股票信息、财务报表、日线行情、新闻舆情（Yahoo Finance），海外兜底，国内服务正常时不需要 |
| 计算 | 自定义函数 | 杜邦分析、PEG、CAGR、财务比率计算 |
| 后端 API | FastAPI | REST API + SSE 流式推送 |
| 前端 | React 19 + TypeScript + Tailwind + Three.js | 3 页 SPA：落地页 → 分析工作台 → 报告页 |
| 配置 | Python Config + 前端用户配置 | API Key 管理（后端 config.py + 前端用户自填） |

---

## 系统架构

```
┌─────────────────────────────────────────────────────┐
│                    前端 (React)                      │
│  Landing → Login(邮箱验证码) → Dashboard(搜索+Agent) → Report(报告) │
└──────────────────────┬──────────────────────────────┘
                       │ REST + SSE
┌──────────────────────▼──────────────────────────────┐
│                  后端 (FastAPI)                      │
│  /api/auth/*  /api/search  /api/analyze  /api/history  /api/config│
└──────────────────────┬──────────────────────────────┘
                       │
              ┌────────▼────────┐
              │  LangGraph 图    │
              │  Router → 4 Agent│
              │  → Summary      │
              └─────────────────┘

分析链路（LangGraph 编排）：
  用户输入 → Router(路由判断) → 4 Agent 并行(基本面/技术面/估值/新闻)
  → Summary(ReAct汇总: 交叉验证+一致性核实+加权评分) → 结构化报告输出

评判链路（内部工具，不在用户 UI 展示）：
  评判 Agent 独立调用：原始数据 + 模型输出 → 4 维度打分
  支持多模型并行对比（GPT-4o / DeepSeek / Qwen）
  仅用于面试展示 Agent 评测能力，不出现在前端页面
```

---

## Agent 职责定义

### 4 个分析 Agent（ReAct 模式）

每个 Agent 的 ReAct 循环：Thought → Action（tool call）→ Observation → 推理判断

| Agent | 职责 | 核心工具 | 关键指标 |
|-------|------|----------|----------|
| 基本面 | 财务健康分析 | akshare财务摘要(主) + Tushare财务指标(备1) + yfinance财务数据(备2) + 杜邦/CAGR | ROE、净利率、营收增速、资产负债率 |
| 技术面 | 量价技术分析 | akshare日线(主,60日OHLCV+MA) + Tushare日线(备1) + yfinance日线(备2) | 趋势、量价关系、支撑压力位、波动率 |
| 估值 | 估值模型与对比 | akshare估值快照(主,PE/PB/PS/市值/股息率) + Tushare估值(备1) + yfinance估值(备2) + PEG/流动比率 | PE/PB/PS、PEG、股息率 |
| 新闻 | 舆情与事件分析 | akshare东方财富个股新闻+财联社快讯(主) + yfinance新闻(备) | 情感分析、重大事件提取、资金面 |

### Summary Agent（ReAct 模式，含 3 个工具）

- `cross_validate_agents`：交叉验证不同 Agent 结论是否存在矛盾
- `verify_data_consistency`：核实同一指标在不同数据源的一致性
- `calculate_weighted_score`：加权计算综合评分（基本面35%/技术面20%/估值30%/新闻15%）
- 输出五段式综合投资报告：投资倾向 → 交叉分析 → 综合评分 → 情景分析 → 风险清单

### 评判 Agent（内部工具，不在用户 UI 展示）

> **重要**：评判 Agent 仅用于面试展示 Agent 评测能力，**不出现在前端用户 UI 中**。前端 3 个页面（Landing / Dashboard / Report）均不包含评测相关入口或展示。

**工作流**：读取原始数据 → 读取模型输出 → 逐项检查 → 输出评分报告

**4 个评测维度**：
1. **幻觉检测**：输出中的事实/数值是否与原始数据一致（对照 Tushare 真实数据）
2. **推理质量**：分析逻辑是否完整、结论是否有数据支撑
3. **风险敏感度**：是否识别到关键风险因素、风险提示是否充分
4. **工具调用准确率**：工具选择是否正确、参数是否合理、调用链是否完整

**多模型对比**：同一分析任务分别用 GPT-4o / DeepSeek / Qwen 执行，评判 Agent 统一打分，输出雷达图对比报告。

---

## MCP 工具链

### akshare 工具（主力数据源，`src/mcp_tools/news_api.py`，15s 超时保护）

| 工具名 | 功能 | 输入 | 输出 |
|--------|------|------|------|
| `get_eastmoney_news` | 东方财富个股新闻 | ts_code | 新闻标题+时间+来源 |
| `get_cls_global_news` | 财联社全球财经快讯 | limit | 市场快讯标题+内容 |
| `get_combined_news` | 综合新闻（个股+全球） | ts_code | 合并新闻摘要 |
| `get_daily_quote_ak` | 日线行情 | ts_code | OHLCV + MA均线统计 + 区间涨跌幅 |
| `get_stock_financial_summary` | 财务摘要 | ts_code | ROE/净利润/营收/负债率 |
| `get_stock_valuation_snapshot` | 估值参考 | ts_code | 每股净资产/ROE/负债率 |

akshare 采用懒加载模式，所有 API 调用已通过 `_ak_call()` 包裹 15s `concurrent.futures` 超时保护。

### Tushare Pro 工具（第一备选数据源）

| 工具名 | 功能 | 输入 | 输出 |
|--------|------|------|------|
| `get_stock_basic` | 获取股票基本信息 | ts_code | 名称、行业、市值、PE/PB |
| `get_financial_report` | 获取财务报表 | ts_code, period | ROE/净利率/营收等 |
| `get_daily_quote` | 获取日线行情 | ts_code, start_date, end_date | OHLCV 数据 |
| `search_stock` | 按关键词搜索股票 | keyword | 匹配的股票列表 |

### yfinance 工具（海外兜底数据源，`src/mcp_tools/yahoo_api.py`，国内服务正常时不需要）

| 工具名 | 功能 | 输入 | 输出 |
|--------|------|------|------|
| `get_stock_info_yahoo` | 股票信息+估值快照 | ts_code | 名称/行业/PE/PB/PS/PEG/股息率/ROE/利润率等 |
| `get_financials_yahoo` | 财务报表 | ts_code | 年度+季度利润表、资产负债表 |
| `get_daily_quote_yahoo` | 日线行情 | ts_code, days | 60日 OHLCV + MA均线 + 波动率 |
| `get_news_yahoo` | 个股新闻 | ts_code, limit | 新闻标题+来源+时间 |
| `get_comprehensive_yahoo` | 综合快照 | ts_code | 基本信息+估值+行情摘要 |

自动将 Tushare 代码格式转为 Yahoo Finance 格式（`.SH` → `.SS`）。懒加载模式，未安装时返回友好错误。

### 计算工具（Function Call）

| 工具名 | 功能 | 公式 |
|--------|------|------|
| `calc_dupont` | 杜邦分析 | ROE = 净利率 × 资产周转率 × 权益乘数 |
| `calc_pe_growth` | PEG 计算 | PEG = PE / 净利润增速 |
| `calc_financial_ratio` | 通用财务比率 | 流动比率、速动比率等 |

---

## 配置文件

```python
# config.py（gitignore）
TUSHARE_TOKEN = "your_tushare_token"
OPENAI_API_KEY = "your_openai_key"
DEEPSEEK_API_KEY = "your_deepseek_key"
QWEN_API_KEY = "your_qwen_key"
DEFAULT_MODEL = "gpt-4o"  # 可切换默认模型
```

---

## 项目约束与面试要点

### 设计约束（2026-05-17 新增）

**字体体系**（2026-05-17 更新）：
| 用途 | 字体 | 备注 |
|------|------|------|
| 品牌标题（Nice Invest） | Playfair Display 700 italic | 落地页专用 |
| 副标题 | DM Sans 300 | 落地页 "Based on Multi-agent" |
| 正文 | Inter / PingFang SC / Microsoft YaHei | 全局 sans-serif |
| 研报标题 | Noto Serif SC | 报告页 serif |
| 二级标题/表格说明 | FangSong / 仿宋 / STFangsong bold | 数字子编号（1.1、3.2）+ 表格前说明文字 |
| 技术数据 | Space Grotesk | Dashboard 用 font-tech |

**反 AI 元素原则**：UI/UX 严格避免常见 AI 产品痕迹：
- 禁止紫色/蓝色渐变、机器人图标、Sparkles 图标、✨/🤖 emoji
- 禁止"AI-Powered"、"智能"、"赋能"等标签
- 禁止打字机效果、脉冲呼吸动画
- 参考专业研报风格（中金/中信/摩根士丹利）：克制、权威、信息密度高

**落地页 K 线**：确定性种子（seededRandom(42)），160 根固定 K 线 + 2 条 MA（10/20），背景 `#1A1D24`，动态发光脉冲 + 均线透明度波动 + 环境粒子

**配色方案**（暖调专业色）：
| 变量 | 色值 | 用途 |
|------|------|------|
| `--floral-white` | `#fffcf2` | 报告页主背景 |
| `--dust-grey` | `#ccc5b9` | 边框/分隔线 |
| `--charcoal-brown` | `#403d39` | 正文 |
| `--carbon-black` | `#252422` | 标题 |
| `--spicy-paprika` | `#eb5e28` | 功能强调/关键指标/警示 |

**品牌统一**：前端 "Nice Invest" = 后端展示名。Dashboard 顶部 **不使用 Sparkles 图标**。

**设计文档**：详见 `output/LangGraph金融分析-UI设计文档.md` v2

### 面试可解释性要求（非技术背景友好）
- 每个 Agent 的 Tool 调用链路可追溯、可解释
- 评判 Agent 的打分逻辑有明确的检查清单
- 避免黑箱操作，所有分析结论需标注数据来源

### Agent 输出规范（2026-05-17 升级）

所有 Agent 输出采用**两段式**：
1. **Markdown 正文**（人类阅读，用于 Modal/Accordion）
2. **结构化 JSON**（` ```json ` 代码块，用于前端组件渲染）

前端从 Markdown 中提取 JSON 代码块渲染指标卡/评分图/风险清单；解析失败时降级为纯 Markdown 展示。

| Agent | JSON 输出字段 | 说明 |
|------|-------------|------|
| 基本面 | `fundamental_report` | key_metrics + dupont_decomposition + score |
| 技术面 | `technical_report` | key_metrics + price_range + volume_trend + score |
| 估值 | `valuation_report` | key_metrics + peer_comparison + score |
| 新闻 | `news_report` | key_metrics + sentiment + major_events + score |
| Summary | `ReportData` | 完整结构化报告，供 Page 3 渲染 |

详细字段定义见 `output/LangGraph金融分析-UI设计文档.md` 第七节。

### 输出模板铁律（`src/agents/template.py`）
- **七条铁律**：①禁止暴露思考过程（最重要） ②禁止 Markdown 格式符号（`#`/`**`/`---`等，表格`|`除外） ③数据来源标注 ④失败兜底声明 ⑤量化优于定性 ⑥不确定性标注 ⑦完整输出（每维度≥200字）
- **五段式模板**：元信息 → 核心结论 → 详细分析 → 关键指标明细表 → 风险提示
- **Summary 五段式**：投资倾向 → 交叉分析 → 综合评分 → 情景分析 → 风险清单
- **输出规范**：纯文本格式，中文编号（一、二、三）区分层级，表格使用 `|` 管道符（前端渲染对齐）

### 输出清洗机制（2026-05-18 更新）
- **服务端清洗**：`server.py` 中 `_clean_agent_output()` 函数，在 SSE 推送前自动去除：
  - DeepSeek `思考.../思考` 标签和推理链
  - 12 种常见过渡/思考句式（"现在我来..."、"下面给出..."等）
  - Markdown 格式符号（`####`/`###`/`##`/`#` 标题标记、`---` 分隔线、`**粗体**`/`*斜体*` 标记）
  - 多余空行和开头空白
- **客户端兜底**：`web/src/lib/api.ts` 中 `cleanAnalysisText()` 同样做 Markdown 符号清洗（含 `####` 四级标题），双重保障
- **前端展示**：AgentModal 和 Report 页使用 `FormattedMarkdown`/`ReportMarkdown` 组件渲染：
  - 中文编号标题（一、二、三）→ 一级标题（serif bold）
  - 数字子编号（1.1、3.2）→ 二级标题（仿宋 bold）
  - 表格前说明文字 → 仿宋加粗（预扫描检测表格紧前非标题行）
  - 表格 → HTML `<table>` 带列对齐和自动换行（标题行字号+2）
  - 正文 → 字号+2、字间距 tracking-wide
  - 列表、段落等基础元素
- **关键指标**：AgentModal 底部指标英文 key → 中文名称映射（18 个指标），中文用 serif semibold（颜色 `#252422`），数值用 tech 字体

### 股票名称显示规范（2026-05-18 新增）
- `stockDisplayName(code, name)` 当 name 为空或等于 code 时自动查询本地 20 只股票列表补充
- 覆盖位置：Dashboard 头部、历史面板、查看报告、历史回放、搜索框共 5 处
- 原则：代码与名称始终成对出现，名称缺失时不得以代码替代

### 简历 Bullet 对应关系
- **Bullet 1（Multi-Agent架构）**：LangGraph 状态机、4 Agent 并行、Summary 汇总 → 对应 `src/graph.py`
- **Bullet 2（MCP/FunctionCall）**：Tushare Pro MCP 封装、财务计算 Function Call → 对应 `src/mcp_tools/`
- **Bullet 3（评测能力）**：评判 Agent 4 维度打分、多模型对比 → 对应评判模式

### 不做的（控制范围）
- 不做 Docker/K8s/Redis 等生产级基础设施
- 不做实时监控/告警系统
- 不做回测/交易功能
- **不做评判模块前端展示**：评判 Agent 仅内部使用，3 个用户页面均不涉及

### 认证与鉴权（2026-05-17 新增）
- **邮箱验证码登录**：Resend API 发送 6 位验证码（免费 100 封/天），`src/auth.py` 管理 CodeStore/SessionStore/UserStore
- **Session 管理**：内存存储 24h 过期，前端 localStorage 持久化，Dashboard 401 → 自动退回 Landing
- **体验 Key 自动注入**：用户配了 Key → 用自己的；没配 Key → 后端自动注入体验 Key（三级读取：os.environ → config.py → 默认值），无次数限制
- **4 个 Auth 端点**：`POST /api/auth/send-code`、`POST /api/auth/verify-code`、`GET /api/auth/session`、`GET /api/auth/usage`
- **Resend 降级**：Resend 发送失败时自动降级为终端打印验证码（`fallback: true` + `dev_code` 返回前端）

### API 配置策略（2026-05-17）
- **LLM-only**：用户仅配置模型 + API Key + Base URL，支持任意 OpenAI 兼容端点（DeepSeek/OpenAI/Qwen/第三方代理）
- **数据源免配置**：优先使用 akshare/东方财富等免费 API；Tushare 在后端可选配置（前端不暴露）
- **公开体验 Key**：后端管理 DeepSeek 体验 Key，无使用次数限制，用户无需配置即可体验
- **校验端点**：`POST /api/config/validate` 校验 LLM 连接有效性（`request_timeout=10` + `asyncio.wait_for(12s)`）

### 日志系统（2026-05-17 新增）
- `src/logger.py` — Python logging 双输出：终端彩色 + 文件 `logs/server.log`
- 记录事件：用户登录/验证码发送/分析请求/Agent 执行/API 异常/分析耗时
- 启动时打印统计摘要（累计注册用户数、累计分析次数）

### 前后端分离约定
- **前端**：React SPA（`web/`），仅通过 REST API + SSE 与后端通信，不直接调用 LangGraph
- **后端**：FastAPI（`server.py`），暴露 `/api/auth/*`、`/api/search`、`/api/analyze`（SSE）、`/api/history`、`/api/config/validate`
- **Gradio**：`main.py` 降级为开发调试入口，不再作为正式 UI
- **评判 Agent**：仅在 `evaluation_node` 中保留，通过 `/api/evaluate`（内部接口）调用，前端不展示

---

## 目录结构

```
LangGraph-financial-agent/
├── CLAUDE.md              ← 本文件
├── PROGRESS.md            ← 进度看板
├── README.md              ← 安装/运行说明
├── requirements.txt       ← Python 依赖
├── config.example.py      ← 配置模板
├── config.py              ← 实际配置（gitignore）
├── main.py                ← Gradio 调试入口（开发用，非正式 UI）
├── server.py              ← FastAPI 后端入口（正式 API，已创建）
│
├── src/
│   ├── __init__.py
│   ├── graph.py            ← LangGraph 编排图
│   ├── state.py            ← 全局状态定义
│   ├── auth.py             ← 邮箱验证码登录（CodeStore/SessionStore/UserStore）+ Resend 邮件
│   ├── logger.py           ← 结构化日志（终端彩色 + 文件）
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── template.py     ← 七条铁律 + 两段式输出 + 5 种 JSON Schema
│   │   ├── analyst.py      ← 基本面 Agent（5 tools，yfinance主→akshare备1→Tushare备2）
│   │   ├── technical.py    ← 技术面 Agent（3 tools，yfinance主→akshare备1→Tushare备2）
│   │   ├── valuation.py    ← 估值 Agent（6 tools，yfinance主→akshare备1→Tushare备2）
│   │   ├── news.py         ← 新闻 Agent（5 tools，yfinance主→akshare备）
│   │   └── summary.py      ← Summary Agent（3 tools，ReAct）
│   │
│   └── mcp_tools/
│       ├── __init__.py
│       ├── yahoo_api.py    ← **yfinance 主力数据源（US-friendly，2026-05-19 新增）**
│       ├── tushare_api.py  ← Tushare Pro 封装
│       ├── news_api.py     ← akshare 新闻 + 财务/行情备选（15s 超时保护）
│       └── calculator.py   ← 财务计算函数
│
├── .github/workflows/
│   └── docker-build.yml    ← GitHub Actions CI/CD（2026-05-19 新增）
│   ├── README.md
│   ├── package.json
│   ├── vite.config.ts
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx          ← 页面路由（Landing → Login → Dashboard → Report）
│       ├── index.css        ← Tailwind + 设计令牌
│       ├── lib/api.ts       ← API 调用层（REST + SSE + Auth API，已接入后端）
│       ├── lib/
│       │   ├── api.ts        ← API 调用层（REST + SSE 解析 + Auth）
│       │   └── charts.tsx    ← SVG 图表组件（雷达图/柱状图，零依赖）
│       └── pages/
│           ├── Landing.tsx   ← 落地页（确定性K线+动态发光+Playfair Display）
│           ├── Login.tsx     ← 邮箱验证码登录（两步流程 + Resend 降级 + Nice Invest 品牌）
│           ├── Dashboard.tsx ← 分析工作台（始终 header 布局无空闲页；session鉴权+SSE+Agent网格+配置+历史+Modal+退出登录）
│           └── Report.tsx    ← 报告页（分析报告前置+综合评分紧跟+总分圆+内联评分条居中；无雷达图/柱状图）
│
├── tests/                   ← 测试脚本与报告
│   ├── README.md
│   ├── run_and_save.py
│   ├── test_structural.py
│   ├── full_result.json
│   └── 平安银行-000001-全量分析-20260515.md
│
├── logs/                   ← 推理日志
│
├── Dockerfile              ← Docker 多阶段构建（Node 20 前端 + Python 3.11 后端）
├── render.yaml             ← Render 部署 Blueprint（已停用，保留备用）
├── Procfile                ← Railway 入口（已停用，保留备用）
├── railway.toml            ← Railway 配置（已停用）
├── .dockerignore           ← Docker 构建排除规则
└── requirements.txt        ← Python 依赖
```

---

## 部署

| 项目 | 信息 |
|------|------|
| **平台** | Sealos 国内云 |
| **线上地址** | Sealos 分配域名（如 `xxx.sealos.run`） |
| **镜像仓库** | 阿里云 ACR（个人版免费，`registry.cn-hangzhou.aliyuncs.com/...`） |
| **构建方式** | GitHub Actions → Docker 多阶段构建 → 推送 ACR |
| **CI/CD** | Push master → Actions 自动构建 → Sealos 手动部署（从 ACR 拉取） |
| **启动命令** | `python server.py`（端口从 `$PORT` 环境变量读取，默认 8000） |
| **环境变量** | `DEMO_API_KEY`、`DEMO_BASE_URL`、`PORT`（Sealos 控制台配置） |
| **冷启动** | 无休眠，随时可用 |

### 体验 Key 最终逻辑

```
用户分析请求 → _apply_llm_config(llm_config)
  ├─ llm_config 有 api_key → 用户自备 Key（前端配置页填写）
  └─ llm_config 无 api_key → 五级兜底读取：
       ├─ os.environ.get("DEMO_API_KEY")        ← Sealos 环境变量（推荐）
       ├─ os.environ.get("OPENAI_API_KEY")       ← 兼容命名
       ├─ os.environ.get("DEEPSEEK_API_KEY")     ← 兼容命名
       ├─ config.DEMO_API_KEY                   ← 本地开发（gitignored）
       └─ 硬编码兜底 Key                         ← server.py 内置（终极保底）
```
无任何次数限制，登录页不变。已配置 `DEMO_API_KEY` 时诊断日志会打印 `SET:sk-xxx***`。

---

## 踩坑记录（避免重复犯错）

### 用户侧

**U1: Sealos 环境变量名写错（2026-05-19）**
- 错误：把 `DEMO_BASE_URL` 也设成了 `DEMO_API_KEY`，导致 `DEMO_API_KEY` 的值被 URL 覆盖
- 现象：前端配置页填同样的 Key 可以分析，但环境变量方式始终报 401
- 教训：**部署平台配环境变量时，逐个确认变量名拼写**。Name 和 Value 是一一对应的，不要两个变量用同一个 Name

### Claude 侧

**C1: `_apply_llm_config` 强制覆写环境变量（2026-05-19）**
- 错误：else 分支无论 `demo_key` 是否为空都执行 `os.environ["OPENAI_API_KEY"] = demo_key`
- 后果：如果用户在 Sealos 里设置了 `OPENAI_API_KEY` 而非 `DEMO_API_KEY`，会被空字符串覆盖
- 教训：**设置环境变量前必须检查值是否非空**。修后：`if demo_key:` 才设置

**C2: 只读单一环境变量名（2026-05-19）**
- 错误：`_apply_llm_config` 只读 `DEMO_API_KEY`，不认 `OPENAI_API_KEY` / `DEEPSEEK_API_KEY`
- 后果：用户按直觉设置了 `OPENAI_API_KEY`（OpenAI 兼容的通用命名），代码找不到
- 教训：**部署相关环境变量应兼容多种常见命名**。修后：五级 fallback 链

**C3: 数据源优先级的上下文盲区（2026-05-19）**
- 错误：Render 美国服务器阶段引入了 yfinance 主力数据源，迁移到 Sealos 国内云后忘记翻回来
- 后果：Sealos 国内部署后仍在用 yfinance（Yahoo Finance）作为主力，延迟高于国内源
- 教训：**部署环境变更后，数据源优先级应同步审视**。修后：akshare（国内主力）→ Tushare → yfinance（海外兜底）
