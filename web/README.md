# Nice Invest — 前端

基于 React 19 + TypeScript + Tailwind CSS 4 + Three.js 的金融分析 Multi-Agent 前端。

## 页面

| 页面 | 路由 | 功能 |
|------|------|------|
| Landing | `/` | 3D K 线背景，品牌入口 |
| Dashboard | `/dashboard` | 股票搜索（防抖 Top-5）+ Agent 卡片（SSE 实时进度）+ 配置面板 + 历史记录 + Agent 详情 Modal |
| Report | `/report` | 研报风格：综合评分 + 雷达图/柱状图 + 交叉分析 + 情景分析 + 风险清单 + PDF 导出 |

## 运行

```bash
npm install
npm run dev
# → http://localhost:3000
```

后端 API 需同时启动：`python server.py`（`http://localhost:8000`）

## 技术栈

- React 19 + TypeScript
- Tailwind CSS 4（暖调专业色设计令牌）
- Three.js（Landing 页 3D K 线背景）
- motion（动画库）
- lucide-react（图标）
- 纯 SVG 图表（雷达图 + 柱状图，零依赖）

## 设计约束

- 反 AI 元素：禁紫色/蓝色渐变、机器人图标、Sparkles/emoji、"AI-Powered"/"智能"/"赋能"等标签
- 研报风格：参考中金/中信/摩根士丹利专业研报视觉语言
- 配色：暖调专业色（floral-white/dust-grey/charcoal-brown/carbon-black/spicy-paprika）
