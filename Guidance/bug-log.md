# Bug 日志 — Nice Invest

> 从 `LangGraph-financial-agent/PROGRESS.md` 和 `CLAUDE.md` 中提取并整理
> 最新 Bug 在顶部

---

## B17: Sealos 部署 API Key 401（2026-05-19）

- **现象**：Sealos 配置了环境变量后仍报"API Key 无效（401）"
- **根因**：`_apply_llm_config()` 只读 `DEMO_API_KEY`，且 else 分支无论 demo_key 是否为空都执行 `os.environ["OPENAI_API_KEY"] = demo_key`，导致用户设了 `OPENAI_API_KEY` 反而被空字符串覆盖
- **修复**：Key 读取五级 fallback（DEMO_API_KEY → OPENAI_API_KEY → DEEPSEEK_API_KEY → config.py → 硬编码兜底），只在找到非空 Key 时才设置环境变量
- **影响文件**：`server.py` `_apply_llm_config()`
- **教训**：设置环境变量前必须检查值是否非空；部署相关环境变量应兼容多种常见命名

## B16: Render 数据源全部失效（2026-05-19）

- **现象**：网站可访问可分析，但评分全 0，前端显示"数据源不可用"
- **根因**：Render 美国 IP → akshare HTTP 调用东方财富/同花顺/财联社超时（被墙）；Tushare Token 未配置
- **修复**：①新增 yfinance 主力数据源 ②GitHub Actions + 阿里云 ACR 国内镜像仓库 ③Sealos 国内云部署 ④akshare 调用添加 15s 超时（`_ak_call` wrapper）
- **影响文件**：`src/mcp_tools/yahoo_api.py`（新建）+ 4 个 Agent 文件集成
- **教训**：部署环境变更后，数据源优先级应同步审视

## C3: 数据源优先级上下文盲区（2026-05-19，Claude 侧）

- **错误**：Render 美国服务器阶段引入 yfinance 主力数据源，迁移到 Sealos 国内云后忘记翻回来
- **后果**：Sealos 国内部署后仍在用 yfinance 作为主力，延迟高于国内源
- **修复**：翻回 akshare（国内主力）→ Tushare → yfinance（海外兜底）
- **教训**：部署环境变更后，数据源优先级应同步审视

## C2: 只读单一环境变量名（2026-05-19，Claude 侧）

- **错误**：`_apply_llm_config` 只读 `DEMO_API_KEY`，不认 `OPENAI_API_KEY` / `DEEPSEEK_API_KEY`
- **后果**：用户按直觉设置了 `OPENAI_API_KEY`（OpenAI 兼容的通用命名），代码找不到
- **教训**：部署相关环境变量应兼容多种常见命名

## C1: _apply_llm_config 强制覆写环境变量（2026-05-19，Claude 侧）

- **错误**：else 分支无论 demo_key 是否为空都执行 `os.environ["OPENAI_API_KEY"] = demo_key`
- **后果**：如果用户在 Sealos 里设置了 `OPENAI_API_KEY` 而非 `DEMO_API_KEY`，会被空字符串覆盖
- **教训**：设置环境变量前必须检查值是否非空

## U1: Sealos 环境变量名写错（2026-05-19，用户侧）

- **错误**：把 `DEMO_BASE_URL` 也设成了 `DEMO_API_KEY`，导致 `DEMO_API_KEY` 的值被 URL 覆盖
- **教训**：部署平台配环境变量时，逐个确认变量名拼写

## B15: Railway 构建失败（2026-05-18）

- **现象**："secret https not found"
- **根因**：Railway nixpacks 基础设施问题
- **修复**：添加 Dockerfile，切 Render Docker 部署

## B14: 体验 Key 不生效（第二轮，2026-05-18）

- **现象**：localhost 同样报"API Key 无效"
- **根因**：`e2c60f8` 简化时删了 config.py 兜底，`DEMO_API_KEY` 只从 os.environ 读
- **修复**：恢复 os.environ → config.py → 默认值 三级兜底

## B13: 页面标题错误（2026-05-18）

- **现象**：标签页显示 "My Google AI Studio App"
- **修复**：`index.html` title 改为 "Nice Invest"

## B12: 体验 Key 不生效（第一轮，2026-05-18）

- **现象**：Railway 上配置了 DEMO_API_KEY 但代码读不到
- **根因**：`_apply_llm_config` 漏设 `DEEPSEEK_BASE_URL`，`get_llm()` deepseek 分支读空 base_url
- **修复**：同时设置 OPENAI/DEEPSEEK/QWEN 三组 env var

## B11: Landing 黑屏（2026-05-18）

- **现象**：页面全黑
- **根因**：`web/dist/landing.html` 被清理后未重新构建
- **修复**：清理 dist 后完整 rebuild

## B10: Gradio 6.0 IndexError（2026-05-18）

- **现象**：持续重启循环
- **根因**：Railway 自动检测 `main.py` 为入口，Gradio 6.0 `Blocks()` 不接受 css 参数
- **修复**：① css 移至 `launch()` ② 新增 Procfile 指定 `server.py`

## B9: ModuleNotFoundError（2026-05-18）

- **现象**：Railway 启动崩溃
- **根因**：`config.py` 被 gitignore，线上无此文件
- **修复**：5 模块全部 try/except + os.environ 兜底

## B8: 股票代码替代名称（2026-05-18）

- **现象**：多处显示纯代码而非"平安银行（000001.SZ）"
- **修复**：`stockDisplayName()` 查本地表兜底，5 处显示点统一

## B7: 报告页非结构化显示（2026-05-18）

- **现象**："查看完整报告"展示裸 markdown，无层次结构
- **修复**：`FormattedMarkdown`/`ReportMarkdown` 组件（标题/表格/列表层次渲染）

## B6: Tushare 限流导致分析失败（2026-05-18）

- **现象**：Tushare "调用频次超限" 错误
- **根因**：所有 Agent 优先调 Tushare，限流后才回退 akshare
- **修复**：4 个 Agent 全部改为 akshare 优先

## B5: Agent 输出混入思考过程（2026-05-18）

- **现象**：分析结果中出现"好的，数据已获取"、"现在我来..."等过渡语
- **根因**：铁律不够强硬，DeepSeek 模型倾向输出推理链
- **修复**：铁律重写 + 服务端/客户端双重清洗 + 前端格式化渲染

## B4: 历史记录查询 500 错误（2026-05-18）

- **根因**：`server.py:635` `return {"found": False, "record": null}` — Python 中 null 未定义
- **修复**：`null` → `None`

## B3: CORS 端口扩展（2026-05-17 晚）

- **现象**：Vite 默认端口被占用（3000→3001→3002），不在 CORS 白名单中
- **修复**：`server.py` CORS `allow_origins` 新增 3001/3002 端口

## B2: 邮箱登录卡住用户（2026-05-17 晚）

- **现象**：Resend 邮件无法送达，降级提示用户不理解
- **修复**：新增"跳过登录，直接体验"游客模式

## B1: template.py 花括号导致 5 个 Agent 全部初始化崩溃（2026-05-17）

- **现象**：前端分析请求一律失败（`ValueError: Invalid format specifier in f-string template`）
- **根因**：`ChatPromptTemplate.from_messages()` 使用 Python f-string 格式解析模板，JSON Schema 花括号被误解析为嵌套模板变量
- **修复**：所有非模板变量的花括号转义为 `{{` / `}}`
- **验证**：终端直连 DeepSeek API PASS → 5 个 Agent 全部初始化 PASS
- **教训**：LangChain `ChatPromptTemplate.from_messages()` 内部走 f-string 解析，所有静态花括号必须转义
