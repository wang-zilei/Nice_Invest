# 测试记录

> 项目：LangGraph 金融分析 Multi-Agent 系统
> 测试框架终版确认：2026-05-15

## 测试脚本

| 脚本 | 用途 |
|------|------|
| `test_structural.py` | 结构回归测试（62 项，无需 API Key） |
| `run_and_save.py` | 全量 4 Agent 并行分析 + JSON 保存 |

## 最近一次全量测试

- **日期**：2026-05-15
- **股票**：000001.SZ（平安银行）
- **结果**：PASS — 4 Agent 并行执行成功，Summary 正常生成
- **投资倾向**：中性

### 4 Agent 输出概览

| Agent | 输出长度 | 置信度 | 数据来源 |
|-------|---------|--------|---------|
| 基本面 | 1155 字符 | 0.8 | 部分 Tushare + LLM |
| 技术面 | 2065 字符 | 0.65 | Tushare daily（真实） |
| 估值 | 2368 字符 | 0.8 | 部分 Tushare + LLM |
| 新闻舆情 | 2116 字符 | 0.8 | LLM 知识兜底 |

### 已知限制

1. Tushare `stock_basic` 频率限制（免费用户 1次/分钟），高频调用回退 LLM 知识
2. Tushare `news` 接口需要更高积分（>=120），新闻分析依赖 LLM 知识
3. 技术面 Agent 因 daily 接口稳定，输出质量最高

## 修复记录

### 2026-05-15 首轮测试修复（5 个 Bug）

1. **DeepSeek 协议错误**：`ChatAnthropic` → `ChatOpenAI`（DeepSeek 是 OpenAI 兼容协议）
2. **valuation.py 语法错误**：`@tool` 装饰器误放在赋值语句
3. **全量分析路由 BUG**：`full` 类型被路由到 `summary` 而非 4 个 Agent
4. **ReAct 多 tool_call 顺序错误**：多个 tool 的 AIMessage 被拆分，违反 API 协议
5. **并行状态冲突**：Agent 返回 `**state` 导致 `stock_code` 等多写冲突 + `agent_results` 翻倍
