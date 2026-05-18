# LangGraph-financial-agent 项目进展

> 创建时间：2026-05-15
> 最后更新：2026-05-18（阶段九）
> 目标岗位：腾讯金融大模型评测实习生（项目制）

---

## 阶段一：项目骨架

| # | 任务 | 状态 | 备注 |
|---|------|------|------|
| 1.1 | 创建项目目录结构 | ✅ | `LangGraph-financial-agent/` |
| 1.2 | 编写 CLAUDE.md 项目架构 | ✅ | Agent 职责、工具链、评测设计 |
| 1.3 | 编写 PROGRESS.md 进度看板 | ✅ | 本文件 |
| 1.4 | 编写 README.md | ✅ | 安装运行说明 |
| 1.5 | 创建 requirements.txt | ✅ | 依赖列表 |
| 1.6 | 创建 config.example.py | ✅ | 配置模板 |

## 阶段二：MCP Server

| # | 任务 | 状态 | 备注 |
|---|------|------|------|
| 2.1 | Tushare Pro 工具封装 | ✅ | `src/mcp_tools/tushare_api.py`，5 个接口 |
| 2.2 | 财务计算函数 | ✅ | `src/mcp_tools/calculator.py`，杜邦/PEG/CAGR/比率 |

## 阶段三：ReAct Agent

| # | 任务 | 状态 | 备注 |
|---|------|------|------|
| 3.1 | 基本面 Agent | ✅ | `src/agents/analyst.py`，3 工具 |
| 3.2 | 技术面 Agent | ✅ | `src/agents/technical.py`，1 工具 |
| 3.3 | 估值 Agent | ✅ | `src/agents/valuation.py`，4 工具 |
| 3.4 | 新闻 Agent | ✅ | `src/agents/news.py`，2 工具 |

## 阶段四：LangGraph 编排

| # | 任务 | 状态 | 备注 |
|---|------|------|------|
| 4.1 | State 定义 | ✅ | `src/state.py` |
| 4.2 | Router 节点 | ✅ | 路由判断 + 代码预处理 |
| 4.3 | 并行 Agent 调用 | ✅ | 4 Agent 并行执行 |
| 4.4 | Summary 节点 | ✅ | 汇总 + 投资倾向 |
| 4.5 | Graph 完整串联 | ✅ | `src/graph.py` |

## 阶段五：评判 Agent 与评测

| # | 任务 | 状态 | 备注 |
|---|------|------|------|
| 5.1 | 评判 Agent 实现 | ✅ | 4 维度打分逻辑 |
| 5.2 | 多模型对比模式 | ✅ | GPT-4o / DeepSeek / Qwen |
| 5.3 | 雷达图可视化 | ✅ | matplotlib 生成 |
| 5.4 | 幻觉检测对照 | ✅ | 对照 Tushare 真实数据 |

## 阶段六：Gradio Web UI

| # | 任务 | 状态 | 备注 |
|---|------|------|------|
| 6.1 | Gradio 主界面 | ✅ | `main.py`，双 Tab |
| 6.2 | 深色主题 | ✅ | 金融专业风格 |
| 6.3 | 评判模式界面 | ✅ | 多模型对比展示 |
| 6.4 | 集成测试与 Demo | ✅ | Gradio 6.0 兼容，验证通过 |

---

## 当前状态

✅ 阶段一至六：全部完成（2026-05-15）
✅ 阶段五优化 Step 1-5：全部完成（2026-05-15）
✅ 首轮全量测试：000001.SZ 平安银行 PASS（2026-05-15）
✅ 结构回归测试：62 PASS, 0 FAIL（2026-05-15）
✅ GitHub 上传准备：LICENSE + .gitignore + requirements.txt 加固（2026-05-16）
✅ 前端 web/：Gemini 生成 Landing + Dashboard 框架（2026-05-17）
✅ UI 设计文档 v2：已定稿（2026-05-17）
✅ **阶段七：前后端整合全部完成（2026-05-17）**
✅ **tushare_api.py 动态 token 支持（_get_pro 函数）**
✅ **Server.py：FastAPI + SSE 流式推送 + 4 个 API 端点**
✅ **前端：api.ts 重写 + Dashboard SSE 改造 + Report 研报页 + 图表组件 + PDF 导出**

✅ **UI 精修（2026-05-17）**：落地页 K 线固定化/字体/Hover 优化、Dashboard 空闲页删除+布局调整、API 配置简化为 LLM-only+体验 Key、报告页评分/雷达图/错误处理修复
✅ **阶段八（2026-05-17）**：前后端打通 + 邮箱验证码登录 + 日志系统 + 测试连接修复 + 体验 Key 后端化管理
✅ **Bug 修复（2026-05-17 晚）**：template.py 花括号转义修复 + 游客模式跳过登录 + CORS 端口扩展
✅ **阶段九（2026-05-18）**：输出格式清洗 + 数据源优先级反转 + 前端结构化展示 + 历史缓存修复 + 股票名称显示修复 + Markdown符号去除 + 报告UI修复 + 报告页布局重排/####清洗/仿宋二级标题/字号升级/关键指标颜色加深
✅ **搜索重构 + A股安全护栏（2026-05-18）**：A股注册表（akshare 5517只）+ 搜索框确认按钮 + /api/validate-stock 校验端点 + LLM 模糊识别兜底 + 非A股警告弹窗
✅ **阶段十：GitHub 发布 + Railway 部署（2026-05-18）**：前后端合一部署、config 导入修复、Gradio 6.0 兼容、页面标题修复、黑屏修复
⬜ 下一步：体验 Key 问题排查
⬜ 下一步：面试资产整理

### 阶段十：GitHub 发布 + Railway 部署（2026-05-18）

| # | 任务 | 状态 | 备注 |
|---|------|------|------|
| 10.1 | 前端 API_BASE 相对路径化 | ✅ | `api.ts` 改为 `""`，前后端同域 |
| 10.2 | server.py 静态文件 serve | ✅ | `StaticFiles(directory="web/dist", html=True)` |
| 10.3 | .gitignore 加固 | ✅ | 排除 `config.py`、`.codebuddy/`、`.claude/`、`.workbuddy/`；保留 `!web/dist/` |
| 10.4 | GitHub 仓库创建与推送 | ✅ | `https://github.com/wang-zilei/Nice_Invest` |
| 10.5 | config 导入全量修复 | ✅ | 5 个模块 6 处 `import config` → try/except + env fallback |
| 10.6 | Gradio 6.0 兼容修复 | ✅ | `css` 参数从 `Blocks()` 移至 `launch()` |
| 10.7 | Procfile 入口指定 | ✅ | `web: python server.py`，防止 Railway 误用 main.py |
| 10.8 | 页面标题修改 | ✅ | `index.html` 标题 "My Google AI Studio App" → "Nice Invest" |
| 10.9 | 黑屏修复（landing.html 缺失） | ✅ | 重新构建，Vite 从 `public/` 复制 `landing.html` 到 `dist/` |
| 10.10 | 体验 Key 线上不生效 | ⬜ | 待排查：疑似 DeepSeek API Key 余额耗尽（402），需查看 Railway 日志确认 |

**部署 Bug 汇总**：

| Bug | 现象 | 根因 | 修复 |
|-----|------|------|------|
| B9: ModuleNotFoundError | Railway 启动崩溃 | `config.py` 被 gitignore，线上无此文件，`import config` 直接抛异常 | 5 模块全部 try/except + os.environ 兜底 |
| B10: Gradio 6.0 IndexError | 持续重启循环 | Railway 自动检测 `main.py` 为入口，Gradio 6.0 Blocks() 不接受 css 参数 | ① css 移至 launch() ② 新增 Procfile 指定 `server.py` |
| B11: Landing 黑屏 | 页面全黑，仅能盲点进入 | `web/dist/landing.html` 被清理后未重新构建（iframe 加载 404） | 清理 dist 后完整 rebuild，Vite 从 public/ 复制 |
| B12: 体验 Key 不生效 | 免费体验 2 次无法使用 | 待确认：疑似 DeepSeek 体验 Key 余额耗尽（402 Insufficient Balance） | 待排查 |
| B13: 页面标题错误 | 标签页显示 "My Google AI Studio App" | index.html title 未修改 | 改为 "Nice Invest" |

### 阶段九补充：Markdown 符号去除与 UI 修复（2026-05-18 本会话）

6 大问题 × 5 个文件改动：

| # | 问题 | 改动文件 | 说明 |
|---|------|---------|------|
| 9.6.1 | **去除 Markdown 符号** | template.py, summary.py, server.py, api.ts | 后端铁律新增"禁止Markdown符号"规则；`_clean_agent_output()`/`cleanAnalysisText()` 双重清洗 `#`/`---`/`**` 等符号；前后端 `FormattedMarkdown`/`ReportMarkdown` 兜底 |
| 9.6.2 | **关键指标中文映射** | Dashboard.tsx | 新增 `METRIC_NAME_MAP`（18个指标英文→中文）；中文标签用 serif 字体，数值用 tech 字体 |
| 9.6.3 | **表格对齐修复** | Dashboard.tsx, Report.tsx | CSS grid `auto` 列 → HTML `<table>` 实现列对齐；内容超出自动换行 |
| 9.6.4 | **标题层级样式** | Dashboard.tsx, Report.tsx | 中文编号（一、二、三）→ serif bold 一级标题；数字子编号（1.1）→ sans-serif 二级标题；短行"XXX："→ sub-heading |
| 9.6.5 | **Summary 报告头部块移除** | summary.py | 输出格式改为直接从"一、投资倾向"开始，禁止 `---`/`# 标题` 等头部 |
| 9.6.6 | **报告页全宽布局** | Report.tsx | `max-w-[820px]` → `w-full px-8 lg:px-12`；去除分析报告白框卡片包裹 |

### 阶段九补充3：搜索重构 + A股安全护栏（2026-05-18 本会话）

**问题**：
1. 搜索仅覆盖 20 只本地硬编码股票（Tushare 限流时回退）
2. 点击推荐公司直接触发分析，缺少"确认"步骤
3. 无 A 股合法性输入校验，用户可随意输入任意文本

**改动**（5 文件）：

| # | 改动 | 文件 | 说明 |
|---|------|------|------|
| 9.8.1 | **新建 A 股注册表** | `src/stock_registry.py` | akshare `stock_info_a_code_name()` 获取全量 5517 只 A 股（代码+名称），缓存到 `data/a_share_registry.json`，每日刷新；提供 3 个函数：`load_registry()` / `search_registry()` / `validate_stock()` |
| 9.8.2 | **改造 /api/search** | server.py | 废弃 Tushare+20 只硬编码逻辑，改用 stock_registry.search_registry() 搜索全量 A 股 |
| 9.8.3 | **新增 /api/validate-stock** | server.py | 安全护栏端点：①本地注册表精确匹配 ②LLM 模糊识别兜底（处理简称/别名） ③二次确认 LLM 返回结果在注册表中存在 |
| 9.8.4 | **新增前端校验 API** | api.ts | `validateStockInput()` 函数，调用 /api/validate-stock |
| 9.8.5 | **搜索交互重构** | Dashboard.tsx | ①点击建议→填充输入框（不触发分析）②新增"确认分析"按钮 ③确认→校验→分析/警告 ④警告 Modal（AlertTriangle 图标）⑤支持 Enter 快捷键 |

**搜索优先级逻辑**（stock_registry.py）：
1. 代码精确匹配（000001 = 000001.SZ）
2. 名称精确匹配（平安银行）
3. 名称包含关键词（茅台 → 贵州茅台）
4. 代码包含关键词

**校验双层机制**（server.py）：
- 第一层：本地注册表精确/模糊匹配（毫秒级，零 LLM 调用）
- 第二层：LLM 辅助识别（仅本地匹配失败时触发，处理简称/别名的模糊输入）

### 阶段九补充2：报告页 UI 精修与 Markdown 层级修复（2026-05-18）

5 项改动 × 3 个文件：

| # | 改动 | 文件 | 说明 |
|---|------|------|------|
| 9.7.1 | **报告页布局重排** | Report.tsx | ①移除雷达图（仅保留总分圆+内联评分条）②报告正文移至综合评分上方 ③权重分布 `flex-1` → `max-w-[380px]` 居中不拉伸 |
| 9.7.2 | **`####` 四级标题清洗** | api.ts, Report.tsx, Dashboard.tsx | `cleanAnalysisText()`/`ReportMarkdown`/`FormattedMarkdown` 三处新增 `####` 清洗规则；清洗后 `3.4 文本` 自动识别为二级标题 |
| 9.7.3 | **全文字号+2 + 字间距** | Report.tsx, Dashboard.tsx | 报告标题/正文/评分/表格标题行全部 +2 号；正文添加 `tracking-wide` 加大字间距 |
| 9.7.4 | **二级标题/表格说明 → 仿宋** | Report.tsx, Dashboard.tsx | 数字子编号（1.1、3.2）→ 仿宋 bold；表格前说明文字 → 预扫描检测 + 仿宋加粗渲染 |
| 9.7.5 | **关键指标颜色加深** | Dashboard.tsx | 标题 `text-[#403d39]/60` → `text-[#252422]`；指标名称 `text-[#403d39]/60` → `text-[#252422] font-semibold` |

## 阶段七 UI 精修（2026-05-17 完成）

| # | 任务 | 状态 | 备注 |
|---|------|------|------|
| 7.0 | **Agent prompt 结构化输出改造**（5 个 Agent + template + Summary） | ✅ | 两段式输出（Markdown + JSON），5 种 JSON Schema |
| 7.1 | FastAPI 后端框架 + `/api/search` | ✅ | server.py，含 Tushare 搜索 + 本地兜底 20 只股票 |
| 7.2 | `/api/analyze` SSE + Agent 进度回调 | ✅ | SSE 事件：init/router_done/agent_start/agent_complete/done |
| 7.3 | 前端 api.ts 接入真实 API | ✅ | 替换 mock，添加 SSE 解析、搜索、历史、校验接口 |
| 7.4 | 搜索框 Top-5 匹配 | ✅ | 防抖搜索，下拉选择，支持 Tushare + 本地兜底 |
| 7.5 | Agent 卡片 SSE 动态绑定 | ✅ | Dashboard 实时更新 agent card 状态/进度 |
| 7.6 | 用户配置 Panel | ✅ | localStorage 持久化，Tushare + LLM 校验 |
| 7.7 | 历史记录 Panel | ✅ | 50 条内存存储，点击可回查 |
| 7.8 | 子 Agent 报告 Modal | ✅ | 点击卡片查看分析摘要 + JSON 结构化数据 |
| 7.9 | Page 3 Report 完整页面（研报风格） | ✅ | 综合评分 → 交叉分析 → 情景分析 → 风险清单 |
| 7.10 | 图表组件（雷达图/柱状图） | ✅ | SVG 纯实现（零依赖）：RadarChart + BarChart |
| 7.11 | 报告导出 PDF | ✅ | window.print() + @media print 样式 |

## 阶段七 UI 精修（2026-05-17 完成）

| # | 任务 | 状态 | 备注 |
|---|------|------|------|
| 8.1 | 落地页 K 线固定化（确定性种子） | ✅ | 160 根 K 线 + 2 条 MA 均线，固定模式，右端上升趋势 |
| 8.2 | 落地页亮度提升 | ✅ | 背景 #0A0C10 → #1A1D24 |
| 8.3 | 落地页 K 线动态效果 | ✅ | 发光脉冲 + 均线透明度波动 + 环境粒子 |
| 8.4 | Nice Invest 字体替换 | ✅ | Playfair Display（意大利斜体）+ 副标题 DM Sans |
| 8.5 | 副标题文案修改 | ✅ | "Based on Multi-agent" |
| 8.6 | Hover 效果减弱 | ✅ | 移除颜色变化，仅保留 scale(1.015) 微呼吸 |
| 8.7 | 删除 Dashboard 空闲状态页 | ✅ | Dashboard 始终显示 header+搜索+Agent 网格布局 |
| 8.8 | 搜索区扩展 + 新闻 Agent 上移 | ✅ | header min-height 100px，搜索框 50px 高，新闻 row 3 → 0.85fr |
| 8.9 | API 配置简化为 LLM-only | ✅ | 移除 Tushare，统一 api_key + base_url，支持任意兼容 OpenAI 协议的端点 |
| 8.10 | 公开体验 Key + 2 次限额 | ✅ | DeepSeek 体验 Key（sk-322...），localStorage 计数，超限弹窗提示配置 |
| 8.11 | 报告页评分模块缩小 | ✅ | 总分圆 140px→100px，紧凑内联评分条 |
| 8.12 | 雷达图修复 | ✅ | 缩小半径 + 增加 margin + 限制 ratio 0-1 |
| 8.13 | 去除各维度评分对比柱状图 | ✅ | 删除重复的 BarChart 模块 |
| 8.14 | 数据缺失时默认 5 分修复 | ✅ | extractScores 无数据时返回 0 + DataUnavailable 提示组件 |

## Bug 修复（2026-05-17 晚）

### B1: template.py 花括号导致 5 个 Agent 全部初始化崩溃

**现象**：前端分析请求一律失败（`ValueError: Invalid format specifier in f-string template`），错误发生在 Agent 初始化阶段，未到 LLM 调用。

**根因**：`ChatPromptTemplate.from_messages()` 使用 Python f-string 格式解析模板，`template.py` 中 5 个 JSON Schema + TWO_PART_OUTPUT + OUTPUT_TEMPLATE 包含大量 JSON 花括号 `{}`，LangChain 误解析为嵌套模板变量。

**修复**：重写 `src/agents/template.py`，所有非模板变量的花括号转义为 `{{` / `}}`。覆盖 FUNDAMENTAL / TECHNICAL / VALUATION / NEWS / SUMMARY 5 个 JSON Schema + 输出模板示例 + `{stock_code}` 占位符。

**验证**：终端直连 DeepSeek API PASS → 比亚迪 002594.SZ 基本面 Agent 全链路 PASS（35s 完成分析）→ 5 个 Agent 全部初始化 PASS。

### B2: 邮箱登录卡住用户 — 增加游客模式

**现象**：Resend 邮件无法送达（`niceinvest.dev` 域名未验证），降级 `dev_code` 展示标注"开发模式"用户不理解，强制邮箱验证阻塞用户体验。

**修复**（4 文件）：
- `Login.tsx`：新增「跳过登录，直接体验」按钮，写入 `__guest__` session token
- `server.py`：3 个端点（`/api/auth/session`、`/api/auth/usage`、`/api/analyze`）支持 `__guest__` 游客 token 放行
- `Dashboard.tsx`：游客模式下显示"游客模式"而非 guest 邮箱

### B3: CORS 端口扩展

**现象**：Vite 启动时默认端口被占用（3000→3001→3002），不在 CORS 白名单中导致前端请求被拦截。

**修复**：`server.py` CORS `allow_origins` 新增 3001/3002 端口。

## 阶段九：输出格式 & 数据源 & 前端展示修复（2026-05-18 完成）

6 大问题 × 13 个文件改动：

### 9.1 输出清洗（禁止思考过程泄漏）
| # | 任务 | 状态 | 备注 |
|---|------|------|------|
| 9.1.1 | 服务端输出清洗 `_clean_agent_output()` | ✅ | server.py，SSE 推送前自动去除 DeepSeek 思考标签 + 12 种过渡句式 |
| 9.1.2 | 客户端兜底清洗 `cleanAnalysisText()` | ✅ | api.ts，双重保障 |
| 9.1.3 | 铁律强化（4→6条） | ✅ | template.py，新增"禁止暴露思考过程"详细约束 + "完整输出≥200字" |
| 9.1.4 | max_steps 8→12 | ✅ | graph.py，防止复杂分析被截断 |
| 9.1.5 | preview 200→400 字符 | ✅ | server.py，在句子边界截断 |

### 9.2 数据源优先级反转（akshare 优先）
| # | 任务 | 状态 | 备注 |
|---|------|------|------|
| 9.2.1 | 基本面 Agent 工作流改为 akshare 优先 | ✅ | analyst.py，先调 get_fundamental_backup 再调 get_fundamental_data |
| 9.2.2 | 估值 Agent 工作流改为 akshare 优先 | ✅ | valuation.py，先调 get_valuation_backup 再调 get_valuation_metrics |
| 9.2.3 | 技术面 Agent 新增 akshare backup 工具 | ✅ | technical.py，新增 get_technical_data_backup（60日OHLCV+MA） |
| 9.2.4 | akshare 日线行情函数 | ✅ | news_api.py，新增 get_daily_quote_ak()，前复权数据+统计摘要 |

### 9.3 前端结构化展示
| # | 任务 | 状态 | 备注 |
|---|------|------|------|
| 9.3.1 | AgentModal 重构 | ✅ | Dashboard.tsx，评分数字+置信度条+数据完整度标签+FormattedMarkdown渲染 |
| 9.3.2 | Report 页 JSON 兜底解析 | ✅ | Report.tsx，parseJsonFromText() 客户端二次提取 |
| 9.3.3 | Report 页文本清洗 | ✅ | Report.tsx，cleanAnalysisText() + ReportMarkdown 组件替代裸文本 |
| 9.3.4 | Summary SSE 补字段 | ✅ | server.py，agent_complete 事件补充 analysis/preview 字段 |

### 9.4 历史记录缓存修复
| # | 任务 | 状态 | 备注 |
|---|------|------|------|
| 9.4.1 | null→None 语法修复 | ✅ | server.py:635，历史详情端点查询不存在记录时不再抛异常 |
| 9.4.2 | 历史列表名称显示修复 | ✅ | Dashboard.tsx，stockDisplayName() 确保名称不缺失 |

### 9.5 股票名称显示修复
| # | 任务 | 状态 | 备注 |
|---|------|------|------|
| 9.5.1 | stockDisplayName + lookupStockName | ✅ | api.ts，代码→名称映射（20只本地兜底） |
| 9.5.2 | 5 处名称显示点统一修复 | ✅ | Dashboard头部/历史面板/查看报告/历史回放/搜索框 |

### Bug 修复明细

**B4: 历史记录查询 500 错误**
- 现象：点击历史记录后降级为重新分析
- 根因：`server.py:635` `return {"found": False, "record": null}` — `null` 在 Python 中未定义
- 修复：`null` → `None`

**B5: Agent 输出混入思考过程**
- 现象：分析结果中出现"好的，数据已获取"、"现在我来..."等过渡语
- 根因：铁律第1条不够强硬，DeepSeek 模型倾向输出推理链
- 修复：铁律重写 + 服务端/客户端双重清洗 + 前端格式化渲染

**B6: 数据源 Tushare 限流导致分析失败**
- 现象：Tushare "调用频次超限" 错误，部分 Agent 无数据可用
- 根因：所有 Agent 优先调 Tushare，限流后才回退 akshare
- 修复：4 个 Agent 全部改为 akshare 优先，Tushare 作为补充

**B7: 报告页非结构化显示**
- 现象："查看完整报告"展示裸 markdown，无层次结构
- 根因：前端仅 whitespace-pre-wrap + 去 JSON 块，无 markdown 渲染
- 修复：ReportMarkdown/FormattedMarkdown 组件（标题/表格/列表层次渲染）

**B8: 股票代码替代名称**
- 现象：多处显示纯代码（如"000001.SZ"）而非"平安银行（000001.SZ）"
- 根因：`stock_name || stock_code` 当 name 为空时直接显示代码
- 修复：stockDisplayName() 查本地表兜底，5 处显示点统一

---

## 关键决策记录

- **框架选择**：LangGraph + ReAct（非 AutoGen）
- **数据源**：Tushare Pro（真实数据，非 mock）
- **UI 框架**：Gradio → React 19 + FastAPI（2026-05-17 决策，Gradio 降级为调试入口）
- **前端来源**：Gemini AI Studio 生成的 Landing + Dashboard 框架
- **Agent 数量**：4 个分析 Agent + 1 个 Summary Agent（ReAct 模式）+ 1 个评判 Agent（独立，不在 UI 展示）
- **模型支持**：GPT-4o / DeepSeek / Qwen 多模型对比
- **范围控制**：不做 Docker/K8s/监控，聚焦核心功能
- **邮箱登录**：Resend API 验证码 + Session 管理（2026-05-17 决策，`src/auth.py`）
- **日志系统**：Python logging 双输出（终端+文件），`src/logger.py`（2026-05-17 决策）
- **体验 Key 后端化**：Dashboard 删除硬编码 Key，后端根据 session 扣减配额（2026-05-17 决策）
- **Gradio 6.0 兼容**：theme/css 参数从 Blocks() 移至 launch()
- **输出模板**：统一五段式（元信息→核心结论→详细分析→关键指标→风险提示），四条铁律约束
- **Summary 升级**：从纯 LLM 汇总升级为 ReAct Agent，含交叉验证/数据一致性/加权评分工具
- **新闻数据源**：akshare（东方财富+财联社+全球财经）替代 Tushare 新闻，懒加载模式
- **备选数据**：akshare 为基本面/估值 Agent 提供 Tushare 限流备选
- **评判模块隔离**：前端不展示评判 Agent 任何内容（2026-05-17 决策）
- **品牌统一**：前端 "Nice Invest" = 后端展示名（2026-05-17 决策）
- **SSE 流式推送**：使用 SSE 而非 WebSocket，满足 Agent 进度实时推送需求（2026-05-17 决策）
- **反 AI 元素**：UI/UX 严格避免紫色/蓝色渐变、机器人图标、Sparkles、emoji 等常见 AI 产品痕迹（2026-05-17 决策）
- **研报风格**：报告页参考中金/中信/摩根士丹利专业研报视觉语言，结论先行+数据支撑+风险提示（2026-05-17 决策）
- **配色方案**：暖调专业色（floral-white/dust-grey/charcoal-brown/carbon-black/spicy-paprika），看好不用绿色、看空不用红色（2026-05-17 决策）
- **Agent 两段式输出**：Markdown（人读）+ JSON 代码块（前端渲染），Summary 输出完整 ReportData（2026-05-17 决策）
- **输出清洗**：服务端 `_clean_agent_output()` + 客户端 `cleanAnalysisText()` 双重保障，禁止思考过程泄漏（2026-05-18 决策）
- **数据源反转**：akshare 优先（免费不限流），Tushare 降级为补充数据源（2026-05-18 决策）
- **前端 Markdown 渲染**：零依赖自定义 FormattedMarkdown/ReportMarkdown 组件，支持标题/表格/列表层次（2026-05-18 决策）
- **股票名称兜底**：本地 20 只股票映射表，名称/代码始终成对显示（2026-05-18 决策）
- **Markdown 符号禁止**：Agent 输出禁止 `#`/`**`/`---` 等 Markdown 格式符号，模板铁律新增第2条，前后端双重清洗（2026-05-18 决策）
- **纯文本标题层级**：中文编号（一、二、三）区分层级，前端渲染为不同字体/字重，替代 Markdown `###` 标题（2026-05-18 决策）
- **表格 HTML 渲染**：CSS grid → HTML `<table>` 保证列对齐+自动换行，Markdown `|` 管道符仅作解析标记不显示（2026-05-18 决策）
- **报告页全宽**：去除 max-w 约束和白色卡片包裹，`w-full px-8` 全宽布局（2026-05-18 决策）
- **关键指标中文化**：18 个英文 key → 中文名称映射，中文 serif + 数值 tech 字体分层（2026-05-18 决策）
- **报告页布局重排**：分析报告正文前置、综合评分紧跟其后；移除雷达图仅保留总分圆+内联评分条；权重分布居中约束不拉伸（2026-05-18 决策）
- **`####` 四级标题清洗**：服务端+客户端双重清洗 `####`，清洗后数字子编号（3.4）自动识别为二级标题（2026-05-18 决策）
- **仿宋二级标题**：数字子编号标题（1.1、3.2）和表格前说明文字使用 FangSong/仿宋 bold，替代 sans-serif semibold（2026-05-18 决策）
- **全文字号升级**：报告页与子 Agent 报告的标题/正文/评分/表格标题行全部 +2 号，正文字间距加大 tracking-wide（2026-05-18 决策）
- **A 股注册表**：基于 akshare `stock_info_a_code_name()` 获取 5517 只 A 股（代码+名称），缓存到本地 JSON 每日刷新；替代原有 Tushare+20 只硬编码搜索方案（2026-05-18 决策）
- **安全护栏**：双层校验（本地注册表 + LLM 模糊识别），用户输入经 `POST /api/validate-stock` 校验后才进入分析；非 A 股输入弹窗警告，不触发 Agent（2026-05-18 决策）
- **搜索交互重构**：点击建议仅填充输入框不再自动分析，新增"确认分析"按钮触发校验→分析流程；支持 Enter 快捷键（2026-05-18 决策）
- **前后端合一部署**：FastAPI 用 `StaticFiles(html=True)` 直接 serve 前端 dist，无需 Nginx 或多服务（2026-05-18 决策）
- **Railway 部署**：Procfile 指定 `python server.py`，端口从 `$PORT` 环境变量读取（2026-05-18 决策）
- **配置外部化**：所有 `import config` 改为 try/except + `os.environ.get()` 兜底，线上依赖 Railway 环境变量（2026-05-18 决策）
- **Demo Key 后端化**：体验 Key 通过 Railway Variables 注入，前端不包含任何硬编码 Key（2026-05-18 决策）
- **GitHub Pages 不适合**：项目需要 Python 后端，GitHub Pages 仅支持静态文件，选择 Railway 免费托管（2026-05-18 决策）

## 注意事项

- 用户为非技术背景（经管+金融科技），代码需简洁、注释充分
- 所有分析结论必须标注数据来源，面试可解释
- 评判 Agent 打分逻辑需有明确检查清单，避免黑箱
