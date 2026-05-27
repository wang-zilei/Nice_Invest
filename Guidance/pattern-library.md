# 解决范式库 — Nice Invest

> 从 PROGRESS.md 和 CLAUDE.md 中提取的架构模式和解决思路
> 新增范式追加到顶部

---

## P12: 数据源三级降级策略

- **场景**：单一数据源不稳定（Tushare 频率限制 1次/分钟，美国 IP 被墙国内 API，yfinance 延迟高）
- **方案**：按部署环境动态调整优先级
  - 国内部署：akshare（东方财富/同花顺）→ Tushare Pro → yfinance（Yahoo Finance）
  - 海外部署：yfinance → Tushare → akshare（需 HTTP 代理）
- **实现要点**：
  - 每个 Agent 工具列表按优先级排列，LLM 通过工具描述引导按顺序选择
  - akshare 调用包裹 15s 超时保护（`_ak_call` + `concurrent.futures`）
  - 数据源切换不改变 Agent 的 prompt 结构
- **适用**：任何依赖外部 API 的 Agent 项目
- **来源**：B6 + B16 + 阶段十一
- **教训**：部署环境变更后，数据源优先级应同步审视

## P11: 输出清洗双重保障（前馈 + 反馈）

- **场景**：模型输出混入推理链/思考过程（"好的"、"现在我来..."），影响用户体验
- **方案**：三层防御
  1. **前馈（模板铁律）**：prompt 中明确禁止 12 种过渡句式 + Markdown 符号
  2. **服务端清洗**：`_clean_agent_output()` 正则匹配，SSE 推送前去除推理标签/过渡句/Markdown 符号
  3. **客户端兜底**：`cleanAnalysisText()` 同一套清洗规则在前端再执行一次
- **适用**：任何面向用户的 LLM 输出场景
- **来源**：B5 + 阶段九
- **教训**：光靠 prompt 约束不够，必须有服务端清洗作为反馈护栏

## P10: 输出模板铁律 + 两段式输出

- **场景**：Agent 输出格式不稳定，前端无法可靠解析结构化数据
- **方案**：
  - 7 条铁律（禁止思考过程、禁止 Markdown 符号、数据来源标注、失败兜底、量化优于定性、不确定性标注、完整输出 ≥200字）
  - 两段式输出：纯文本正文（人读）+ JSON 代码块（前端渲染）
  - 五段式模板：元信息 → 核心结论 → 详细分析 → 关键指标表 → 风险提示
- **适用**：需要前端解析 Agent 输出的多 Agent 系统
- **来源**：template.py + 阶段七
- **注意**：JSON Schema 中的花括号必须转义为 `{{` `}}`（B1 教训）

## P9: LangGraph Send API 并行分发

- **场景**：4 个 Agent 互不依赖，需要并行执行而非串行
- **方案**：
  - `_route_agents()` 返回 `[Send(agent, state) for agent in agents]` 列表
  - `agent_results` 使用 `Annotated[list, add]` reducer 实现并行写入
  - 每个 Agent 独立 ReAct 循环，互不阻塞
- **适用**：多 Agent 并行执行场景
- **来源**：graph.py:491 + state.py
- **优势**：相比串行，4 Agent 并行可将总耗时从串行累加降为最长单个

## P8: A股安全护栏（双层校验）

- **场景**：用户可随意输入非 A 股文本，导致 Agent 无意义执行
- **方案**：
  1. 第一层：本地注册表精确/模糊匹配（毫秒级，零 LLM 调用）
     - akshare `stock_info_a_code_name()` 全量 5517 只 A 股，缓存到本地 JSON 每日刷新
  2. 第二层：LLM 辅助识别（处理简称/别名，返回后二次确认注册表是否存在）
- **适用**：需要验证用户输入合法性的场景
- **来源**：stock_registry.py + server.py `/api/validate-stock`

## P7: 体验 Key 多级环境变量兜底

- **场景**：不同平台/用户习惯下 API Key 环境变量命名不一致
- **方案**：五级 fallback 读取
  ```
  DEMO_API_KEY → OPENAI_API_KEY → DEEPSEEK_API_KEY → config.py → 硬编码兜底
  ```
- **关键细节**：
  - 必须同时设置 OPENAI/DEEPSEEK/QWEN 三组环境变量（不同模型分支读不同的 env var）
  - 只在找到非空 Key 时才设置环境变量，防止空值覆盖已有配置
  - Base URL 同样四级 fallback
- **适用**：需要支持多模型多端点的 LLM 配置管理
- **来源**：server.py:762 + C1/C2 踩坑
- **教训**：设置环境变量前必须检查值是否非空（C1）；环境变量名应兼容多种常见命名（C2）

## P6: SSE 流式进度推送

- **场景**：Agent 执行耗时 30-120 秒，用户等待期间需要实时反馈
- **方案**：FastAPI `StreamingResponse` + SSE 事件流
  - 事件类型：`init` → `router_done` → `agent_start` × N → `agent_complete` × N → `done`/`error`
  - 每个事件携带分析进度、Agent 名称、预览文本
  - 前端 `EventSource` 解析并动态更新 Agent 卡片状态
- **适用**：需要向用户实时展示后台进度的场景
- **来源**：server.py `/api/analyze`

## P5: 邮箱验证码登录 + 降级机制

- **场景**：用户需要登录才能使用分析功能，但邮件服务可能不可用
- **方案**：
  - ResendAPI 发送 6 位验证码（免费 100 封/天）
  - 降级：发送失败时终端打印验证码 + 前端返回 `dev_code`
  - 游客模式：跳过登录直接体验（`__guest__` session token）
- **适用**：需要轻量认证的个人项目/开发环境
- **来源**：auth.py + server.py `/api/auth/*`

## P4: 前后端分离但同域部署

- **场景**：需要前后端分离开发体验，但部署时要避免跨域问题
- **方案**：
  - 开发：前端 Vite（localhost:3000）+ 后端 FastAPI（localhost:8000），CORS 放行
  - 生产：FastAPI `StaticFiles(html=True)` 直接 serve 前端 dist，单端口同域
  - 前端 API 调用用相对路径（`""`），开发时 Vite proxy 转发
- **适用**：单人全栈项目，不需要 Nginx
- **来源**：server.py + api.ts

## P3: Agent 结构化数据提取

- **场景**：前端需要从 Agent 文本输出中提取 JSON 渲染指标卡
- **方案**：正则匹配 ` ```json ... ``` ` 代码块，失败兜底匹配 `{ ... }`
- **两层提取**：服务端 `_extract_json_from_text()` + 前端 `parseJsonFromText()`
- **适用**：LLM 输出需要结构化解析的场景
- **来源**：server.py:850

## P2: 股票名称智能补全

- **场景**：多处只显示代码（如"000001.SZ"）而非"平安银行"
- **方案**：`stockDisplayName(code, name)` 函数，当 name 为空时自动查本地映射表
- **覆盖点**：Dashboard 头部、历史面板、查看报告、历史回放、搜索框
- **适用**：需要代码/名称成对显示的场景
- **来源**：B8 + api.ts

## P1: Gradio 6.0 兼容修复

- **场景**：Gradio 6.0 不再接受 `Blocks(css=...)` 参数
- **方案**：`css` 参数从 `Blocks()` 移至 `launch()` 方法
- **适用**：Gradio 升级到 6.0+ 的项目
- **来源**：B10

## P13: Three.js landing page stabilization

- **场景**：落地页使用 Three.js 粒子/K 线背景时，随机初始值和时间驱动动画容易造成首屏翻转、闪烁、主体偏移或硬边交互。
- **方案**：
  1. 根路径保持 Landing 为第一屏，点击入口后再做 session 检查。
  2. 鼠标/视差初始值使用中心点 `(0, 0)`，用 `hasPointer` 控制是否启用视差，避免首屏极端旋转。
  3. 粒子亮度避免从 `uTime = 0` 开始变化；需要稳定首屏时，用随机属性决定基础亮度。
  4. K 线随机生成后计算 `kCenter`，对 OHLC 整体归一，让视觉主体围绕标题中心。
  5. 鼠标影响迷雾时避免固定半径硬阈值，优先使用 `exp(-dist * dist * k)` 这类高斯衰减做柔和过渡。
- **适用**：沉浸式 landing、canvas/WebGL 背景、粒子雾效、鼠标视差交互。
- **来源**：2026-05-26 landing polish，`web/public/landing.html`。

## P14: Report detail page state preservation

- **场景**：用户从 Dashboard 查看完整报告后，点击返回工作台，希望回到刚才的分析完成态，而不是重新进入空白初始态。
- **方案**：
  1. 将报告页作为同一 SPA 流程中的覆盖页面处理。
  2. 进入 Report 时保持 Dashboard 组件挂载，只用容器 `hidden` 隐藏。
  3. 返回 Dashboard 时只切换页面状态，不重新创建 Dashboard 内部分析状态。
  4. 报告正文已经包含风险清单时，不再额外渲染独立风险清单模块，避免重复信息。
- **适用**：多步骤分析工作台、详情页、报告页、需要保留上下文的 SPA。
- **来源**：2026-05-27 report polish，`web/src/App.tsx` + `web/src/pages/Report.tsx`。
