# 项目进度 — LangGraph-financial-agent (Nice Invest)

> 最后更新：2026-05-19（阶段十一完成：数据源架构升级 + Sealos 部署 + 优先级翻转 + API Key 修复）

---

## 阶段一~六：核心链路（已完成）

| # | 任务 | 状态 | 备注 |
|---|------|------|------|
| 1.x | 项目骨架 + CLAUDE.md + README | ✅ | |
| 2.x | MCP/FunctionCall 工具链（Tushare + 财务计算） | ✅ | |
| 3.x | 4 个 ReAct Agent（基本面/技术面/估值/新闻） | ✅ | |
| 4.x | LangGraph 编排（Router → 并行 Agent → Summary） | ✅ | Send API + add reducer |
| 5.x | 评判 Agent + 多模型对比 + 雷达图 | ✅ | 4 维度打分 |
| 6.x | Gradio Web UI | ✅ | 已降级为调试入口 |

**测试**：000001.SZ 平安银行全量分析 PASS / 结构回归 62 PASS 0 FAIL

## 阶段七：前后端整合（已完成）

| # | 任务 | 状态 | 备注 |
|---|------|------|------|
| 7.1 | FastAPI + SSE 流式推送 | ✅ | 5 个 API 端点 |
| 7.2 | React 19 + TypeScript SPA | ✅ | Landing → Login → Dashboard → Report |
| 7.3 | Agent 两段式输出（Markdown + JSON） | ✅ | 5 种 JSON Schema |
| 7.4 | 邮箱验证码登录 | ✅ | Resend + 游客模式 |
| 7.5 | 日志系统 | ✅ | 终端 + 文件双输出 |

## 阶段八：UI 精修 + 部署准备（已完成）

| # | 任务 | 状态 | 备注 |
|---|------|------|------|
| 8.x | 落地页确定性 K 线 + Playfair Display | ✅ | |
| 8.x | Dashboard 布局优化 + LLM-only 配置 | ✅ | |
| 8.x | 报告页研报风格（暖调色板） | ✅ | |
| 8.x | B1-B3 修复（花括号/游客模式/CORS） | ✅ | |

## 阶段九：输出清洗 + 数据源翻转 + A 股护栏（已完成）

| # | 任务 | 状态 | 备注 |
|---|------|------|------|
| 9.x | 服务端/客户端双重输出清洗 | ✅ | B5 |
| 9.x | 数据源 akshare 优先翻转 | ✅ | B6 |
| 9.x | 前端结构化展示 + Markdown 渲染 | ✅ | B7/B8 |
| 9.x | A 股注册表 + 安全护栏 | ✅ | 5517 只全量 |
| 9.x | B4-B8 全量修复 | ✅ | 13 文件改动 |

## 阶段十：GitHub 发布 + Railway → Render 部署（已完成）

| # | 任务 | 状态 | 备注 |
|---|------|------|------|
| 10.x | 前后端合一部署（StaticFiles） | ✅ | |
| 10.x | config 导入修复（5 模块 try/except） | ✅ | B9 |
| 10.x | Gradio 6.0 兼容 + Procfile | ✅ | B10 |
| 10.x | B9-B15 全量修复 | ✅ | |
| 10.x | Render Docker 部署成功 | ✅ | |

## 阶段十一：数据源架构升级 + Sealos 国内部署（已完成）

| # | 任务 | 状态 | 备注 |
|---|------|------|------|
| 11.1 | yahoo_api.py（yfinance 封装） | ✅ | 5 个数据函数 |
| 11.2-11.5 | 4 Agent yfinance 工具集成 | ✅ | 三阶段降级 |
| 11.6 | akshare 15s 超时保护 | ✅ | `_ak_call` wrapper |
| 11.7 | GitHub Actions CI/CD + 阿里云 ACR | ✅ | |
| 11.8 | Sealos 国内云部署 | ✅ | ACR 拉镜像 |
| 11.9 | 数据源优先级翻转（akshare 主力） | ✅ | B16/C3 |
| 11.10 | B17 API Key 401 修复 | ✅ | 五级 fallback |

---

## 当前状态

**部署**：Sealos 国内云，阿里云 ACR 镜像，GitHub Actions 自动构建
**数据源**：akshare（国内主力）→ Tushare Pro（备选）→ yfinance（海外兜底）
**核心链路**：4 Agent 并行 + Summary 全量跑通
**UI**：React 19 + FastAPI + SSE，3 页 SPA + 邮箱登录
**下一步**：评测 Agent 真实评测（多模型横向对比）

## 2026-05-26 - Landing Page Polish

| # | 任务 | 状态 | 备注 |
|---|------|------|------|
| L1 | 根路径先展示 Landing | 完成 | session 检查移动到点击入口后执行 |
| L2 | Landing 首屏无整体翻转 | 完成 | `mouse/smoothMouse` 初始居中，鼠标移动后才启用视差 |
| L3 | 粒子背景无时间驱动入场闪烁 | 完成 | 移除 `uTime` 和 `THREE.Clock` |
| L4 | K 线图稳定围绕标题中心 | 完成 | 生成后用 `kCenter` 对 OHLC 整体归一 |
| L5 | Gaussian mist 交互柔化 | 初步完成 | 去除固定硬光圈，改为高斯衰减；当前可继续微调参数 |

**本地检查点**：`7d927d3 Stabilize landing page entry`

**注意**：L5 的 mist 柔化改动目前尚未提交，便于继续调参或回退到检查点。

## 2026-05-27 - Report Page Interaction Polish

| # | 任务 | 状态 | 备注 |
|---|------|------|------|
| R1 | 报告标题状态行去掉方向箭头图标 | 完成 | 只保留文字判断，不再显示趋势 icon |
| R2 | 移除报告页底部独立风险清单模块 | 完成 | 风险内容保留在正文五段结构中，避免重复 |
| R3 | 从报告页返回分析工作台时保留完成态 | 完成 | Dashboard 在 Report 页面期间保持挂载，仅隐藏 |

**原则**：报告详情页的正文是主信息源，结构化评分可辅助展示；不要额外重复渲染已在正文中出现的段落模块。
