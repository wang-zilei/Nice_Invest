"""
main.py — Gradio Web UI 入口
启动命令: python main.py
默认端口: http://localhost:7860
"""
import gradio as gr
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
from datetime import datetime

from src.graph import build_graph
from src.state import AnalysisState
from config import DEFAULT_MODEL


# 初始化 LangGraph 图
graph = build_graph()


# ============================================================
# UI 主题与样式
# ============================================================
CUSTOM_CSS = """
.gradio-container {
    max-width: 1200px !important;
    padding: 0 !important;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans SC', sans-serif !important;
}
footer { display: none !important; }

/* 英雄区 */
.hero {
    background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 50%, #0f172a 100%);
    padding: 80px 60px 64px;
    text-align: center;
    border-radius: 0 0 32px 32px;
    position: relative;
    overflow: hidden;
}
.hero::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    background: radial-gradient(circle at 30% 50%, rgba(59, 130, 246, 0.08) 0%, transparent 50%),
                radial-gradient(circle at 70% 30%, rgba(16, 185, 129, 0.06) 0%, transparent 50%);
    pointer-events: none;
}
.hero-badge {
    display: inline-block;
    background: rgba(59, 130, 246, 0.15);
    color: #60a5fa;
    font-size: 13px;
    font-weight: 500;
    padding: 6px 16px;
    border-radius: 20px;
    margin-bottom: 24px;
    letter-spacing: 0.5px;
}
.hero h1 {
    color: #f1f5f9 !important;
    font-size: 42px !important;
    font-weight: 700 !important;
    letter-spacing: -0.5px !important;
    margin: 0 0 16px 0 !important;
    line-height: 1.2 !important;
}
.hero-subtitle {
    color: #94a3b8 !important;
    font-size: 17px !important;
    max-width: 640px;
    margin: 0 auto !important;
    line-height: 1.7 !important;
}

/* 四大分析师卡片 */
.analysts-section {
    padding: 64px 48px 48px;
    text-align: center;
}
.section-title {
    font-size: 28px !important;
    font-weight: 700 !important;
    color: #0f172a !important;
    margin: 0 0 8px 0 !important;
}
.section-desc {
    color: #64748b !important;
    font-size: 15px !important;
    margin: 0 0 48px 0 !important;
}
.analysts-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 24px;
    max-width: 1060px;
    margin: 0 auto;
}
@media (max-width: 900px) {
    .analysts-grid { grid-template-columns: repeat(2, 1fr); }
}
.analyst-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 20px;
    padding: 32px 24px;
    text-align: left;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.analyst-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 32px rgba(0,0,0,0.08);
}
.analyst-icon {
    width: 48px;
    height: 48px;
    border-radius: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 22px;
    margin-bottom: 20px;
}
.analyst-card h3 {
    color: #0f172a !important;
    font-size: 17px !important;
    font-weight: 600 !important;
    margin: 0 0 10px 0 !important;
}
.analyst-card p {
    color: #64748b !important;
    font-size: 13.5px !important;
    line-height: 1.7 !important;
    margin: 0 0 16px 0 !important;
}
.analyst-metrics {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
}
.analyst-metrics span {
    background: #f8fafc;
    color: #475569;
    font-size: 12px;
    padding: 4px 10px;
    border-radius: 6px;
    font-weight: 500;
}

/* 数据来源区 */
.data-source-section {
    padding: 48px;
    background: #f8fafc;
    margin: 0 48px;
    border-radius: 20px;
}
.source-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 32px;
    max-width: 800px;
    margin: 0 auto;
}
.source-item {
    text-align: left;
}
.source-item h4 {
    color: #0f172a !important;
    font-size: 15px !important;
    font-weight: 600 !important;
    margin: 0 0 8px 0 !important;
    display: flex;
    align-items: center;
    gap: 8px;
}
.source-item p {
    color: #64748b !important;
    font-size: 13.5px !important;
    line-height: 1.7 !important;
    margin: 0 !important;
}

/* 工作台区域 */
.workspace-section {
    padding: 64px 48px;
}
.workspace-container {
    max-width: 900px;
    margin: 0 auto;
}
.input-row {
    display: flex;
    gap: 16px;
    align-items: flex-end;
    margin-bottom: 0;
}
.input-field {
    flex: 1;
}
.input-field select,
.input-field input {
    width: 100% !important;
    background: #f8fafc !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 12px !important;
    padding: 14px 16px !important;
    font-size: 14px !important;
    color: #0f172a !important;
    transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
}
.input-field select:focus,
.input-field input:focus {
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1) !important;
    outline: none !important;
}
.input-field label {
    display: block;
    font-size: 13px;
    font-weight: 600;
    color: #374151;
    margin-bottom: 6px;
}
.run-btn {
    background: linear-gradient(135deg, #3b82f6, #1d4ed8) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 14px 36px !important;
    font-size: 15px !important;
    font-weight: 600 !important;
    cursor: pointer;
    transition: transform 0.15s ease, box-shadow 0.15s ease !important;
    min-width: 160px !important;
    white-space: nowrap;
}
.run-btn:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(59, 130, 246, 0.3) !important;
}
.run-btn:active {
    transform: translateY(0) !important;
}

/* 结果区 */
.result-section {
    margin-top: 32px;
    display: none;
}
.result-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 20px;
    padding: 32px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.result-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 24px;
    padding-bottom: 20px;
    border-bottom: 1px solid #f1f5f9;
}
.result-header h3 {
    color: #0f172a !important;
    font-size: 17px !important;
    font-weight: 600 !important;
    margin: 0 !important;
}
.verdict-badge {
    padding: 6px 16px;
    border-radius: 20px;
    font-size: 13px;
    font-weight: 600;
}
.verdict-bullish { background: #ecfdf5; color: #059669; }
.verdict-neutral { background: #f1f5f9; color: #475569; }
.verdict-bearish { background: #fef2f2; color: #dc2626; }
.result-content {
    color: #334155 !important;
    font-size: 14px !important;
    line-height: 1.8 !important;
}

/* 评测区 */
.eval-section {
    padding: 64px 48px;
    background: #f8fafc;
}
.eval-container {
    max-width: 900px;
    margin: 0 auto;
}
.eval-form {
    display: flex;
    gap: 16px;
    align-items: flex-end;
    margin-bottom: 32px;
    flex-wrap: wrap;
}
.eval-form .input-field {
    flex: 1;
    min-width: 140px;
}
.eval-result {
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 20px;
    padding: 32px;
}
.eval-result h3 {
    color: #0f172a !important;
    font-size: 17px !important;
    font-weight: 600 !important;
    margin: 0 0 20px 0 !important;
}
.eval-result .prose {
    color: #334155 !important;
    font-size: 14px !important;
    line-height: 1.8 !important;
}

/* Markdown 全局 */
.prose, .markdown {
    color: #0f172a !important;
}
.prose table, .markdown table {
    border-collapse: collapse;
    width: 100%;
    margin: 16px 0;
}
.prose th, .markdown th,
.prose td, .markdown td {
    border: 1px solid #e2e8f0;
    padding: 10px 14px;
    text-align: left;
}
.prose th, .markdown th {
    background: #f8fafc;
    font-weight: 600;
}
"""


# ============================================================
# 工具函数
# ============================================================
def format_verdict_badge(verdict: str) -> str:
    v = verdict.strip().lower()
    if "看" in v and "好" in v or "bull" in v or "buy" in v:
        return f'<span class="verdict-badge verdict-bullish">看好</span>'
    elif "看" in v and "空" in v or "bear" in v or "sell" in v:
        return f'<span class="verdict-badge verdict-bearish">看空</span>'
    else:
        return f'<span class="verdict-badge verdict-neutral">中性</span>'


# ============================================================
# 分析逻辑
# ============================================================
def run_analysis(stock_code: str, analysis_type: str) -> tuple:
    """执行股票分析"""
    if not stock_code or not stock_code.strip():
        return '<p style="color:#94a3b8;">请输入股票代码开始分析</p>', ''

    stock_code = stock_code.strip()
    type_map = {
        "全量分析": "full",
        "基本面分析": "fundamental",
        "技术面分析": "technical",
        "估值分析": "valuation",
        "新闻舆情": "news"
    }
    analysis_internal = type_map.get(analysis_type, "full")

    initial_state: AnalysisState = {
        "stock_code": stock_code,
        "analysis_type": analysis_internal,
        "eval_mode": False,
        "eval_models": ["gpt-4o"],
        "raw_data": {},
        "agent_results": [],
        "evaluation_results": [],
        "messages": [],
        "summary": "",
        "final_verdict": "",
    }

    try:
        result = graph.invoke(initial_state)
        summary = result.get("summary", "分析完成，无摘要生成")
        verdict = result.get("final_verdict", "中性")
        return summary.replace('\n', '<br>'), format_verdict_badge(verdict)
    except Exception as e:
        return f'<p style="color:#dc2626;">分析失败：{str(e)}</p>', ''


# ============================================================
# 评判逻辑
# ============================================================
def run_evaluation(stock_code: str, model_a: str, model_b: str) -> tuple:
    """执行多模型对比评测"""
    if not stock_code or not stock_code.strip():
        return '<p style="color:#94a3b8;">请输入股票代码</p>', None

    stock_code = stock_code.strip()
    eval_models = [model_a, model_b]

    initial_state: AnalysisState = {
        "stock_code": stock_code,
        "analysis_type": "full",
        "eval_mode": True,
        "eval_models": eval_models,
        "raw_data": {},
        "agent_results": [],
        "evaluation_results": [],
        "messages": [],
        "summary": "",
        "final_verdict": "",
    }

    try:
        result = graph.invoke(initial_state)
        eval_results = result.get("evaluation_results", [])

        report = ""
        for er in eval_results:
            report += f"### {er['model']}\n"
            report += f"| 维度 | 得分 |\n|------|------|\n"
            report += f"| 幻觉检测 | {er['hallucination_score']}/10 |\n"
            report += f"| 推理质量 | {er['reasoning_score']}/10 |\n"
            report += f"| 风险敏感度 | {er['risk_sensitivity']}/10 |\n"
            report += f"| 工具调用准确率 | {er['tool_accuracy']}/10 |\n"
            report += f"| **综合得分** | **{er['overall_score']}/10** |\n\n"

        chart_path = generate_radar_chart(eval_results)
        return report, chart_path
    except Exception as e:
        return f'<p style="color:#dc2626;">评测失败：{str(e)}</p>', None


def generate_radar_chart(eval_results: list) -> str:
    fig, ax = plt.subplots(figsize=(7, 5), subplot_kw=dict(projection='polar'))

    categories = ['幻觉检测', '推理质量', '风险敏感度', '工具调用准确率']
    num_vars = len(categories)
    angles = [n / float(num_vars) * 2 * 3.14159 for n in range(num_vars)]
    angles += angles[:1]

    colors = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6']

    for i, er in enumerate(eval_results):
        values = [
            er.get('hallucination_score', 0),
            er.get('reasoning_score', 0),
            er.get('risk_sensitivity', 0),
            er.get('tool_accuracy', 0),
        ]
        values += values[:1]
        ax.plot(angles, values, 'o-', linewidth=2, color=colors[i % len(colors)],
                label=er['model'], markersize=5)
        ax.fill(angles, values, alpha=0.12, color=colors[i % len(colors)])

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, fontsize=11)
    ax.set_ylim(0, 10)
    ax.set_yticks([2, 4, 6, 8, 10])
    ax.set_yticklabels(['2', '4', '6', '8', '10'], fontsize=9, color='#64748b')
    ax.spines['polar'].set_color('#e2e8f0')
    ax.grid(color='#e2e8f0', linewidth=0.5)
    ax.legend(loc='upper right', bbox_to_anchor=(1.25, 1.05), fontsize=11, frameon=False)

    fig.patch.set_facecolor('white')
    plt.tight_layout()
    chart_path = 'logs/radar_chart.png'
    plt.savefig(chart_path, dpi=120, bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.close()
    return chart_path


# ============================================================
# Hero + 分析师卡片 HTML
# ============================================================
HERO_HTML = """
<div class="hero">
    <div class="hero-badge"> Multi-Agent 金融分析系统</div>
    <h1>智能金融分析平台</h1>
    <p class="hero-subtitle">
        四大专业分析 Agent 协同工作，覆盖基本面、技术面、估值模型与新闻舆情，
        基于 Tushare Pro 官方数据源，提供结构化投资分析建议。
    </p>
</div>
"""

ANALYSTS_HTML = """
<div class="analysts-section">
    <h2 class="section-title">四大分析师</h2>
    <p class="section-desc">每个分析师专注于一个投资分析维度，独立完成数据采集、计算与推理</p>
    <div class="analysts-grid">
        <!-- 基本面 -->
        <div class="analyst-card">
            <div class="analyst-icon" style="background: #eff6ff; color: #3b82f6;">📊</div>
            <h3>基本面分析师</h3>
            <p>深度解读企业财务健康状况，分析盈利能力、偿债能力与成长性，为投资决策提供核心数据支撑。</p>
            <div class="analyst-metrics">
                <span>ROE</span><span>净利率</span><span>营收增速</span><span>资产负债率</span><span>杜邦分析</span>
            </div>
        </div>
        <!-- 技术面 -->
        <div class="analyst-card">
            <div class="analyst-icon" style="background: #f0fdf4; color: #10b981;"></div>
            <h3>技术面分析师</h3>
            <p>追踪量价关系与技术指标变化，识别支撑位与压力位，把握短期趋势信号与交易时机。</p>
            <div class="analyst-metrics">
                <span>MA均线</span><span>MACD</span><span>KDJ</span><span>量价关系</span><span>支撑压力位</span>
            </div>
        </div>
        <!-- 估值 -->
        <div class="analyst-card">
            <div class="analyst-icon" style="background: #fefce8; color: #eab308;">💰</div>
            <h3>估值分析师</h3>
            <p>运用 PE/PB/PS 等估值模型，结合 PEG 与同行对比，评估股票当前价格是否合理或被低估。</p>
            <div class="analyst-metrics">
                <span>PE/PB/PS</span><span>PEG</span><span>同行对比</span><span>CAGR</span>
            </div>
        </div>
        <!-- 舆情 -->
        <div class="analyst-card">
            <div class="analyst-icon" style="background: #fdf2f8; color: #ec4899;">📰</div>
            <h3>舆情分析师</h3>
            <p>监控企业相关新闻与公告，提取重大事件信息，评估市场情绪对股价的潜在影响。</p>
            <div class="analyst-metrics">
                <span>新闻资讯</span><span>公告事件</span><span>情感分析</span><span>重大事件</span>
            </div>
        </div>
    </div>
</div>
"""

DATA_SOURCE_HTML = """
<div class="data-source-section">
    <div style="text-align: center; margin-bottom: 40px;">
        <h2 class="section-title" style="margin-bottom: 8px;">数据来源与质量保障</h2>
        <p class="section-desc" style="margin: 0;">所有分析结论均基于官方数据源，并通过交叉验证确保准确性</p>
    </div>
    <div class="source-grid">
        <div class="source-item">
            <h4>🏛️ Tushare Pro 官方数据</h4>
            <p>接入 Tushare Pro 金融数据平台，获取股票基本信息、财务报表、日线行情、新闻资讯等全维度真实数据。</p>
        </div>
        <div class="source-item">
            <h4> 多维度交叉验证</h4>
            <p>独立评判 Agent 对分析结果进行幻觉检测、推理质量评估、风险敏感度检验与工具调用准确率审核，确保输出可靠。</p>
        </div>
    </div>
</div>
"""

WORKSPACE_HTML = """
<div class="workspace-section">
    <div style="text-align: center; margin-bottom: 40px;">
        <h2 class="section-title">开始分析</h2>
        <p class="section-desc">输入股票代码，选择分析维度，即刻获取结构化投资建议</p>
    </div>
    <div class="workspace-container">
"""


# ============================================================
# 评测区 HTML
# ============================================================
EVAL_WORKSPACE_HTML = """
<div class="eval-section">
    <div style="text-align: center; margin-bottom: 40px;">
        <h2 class="section-title">多模型对比评测</h2>
        <p class="section-desc">使用不同模型对同一股票进行分析，对比输出质量与可靠性</p>
    </div>
    <div class="eval-container">
"""

WORKSPACE_CLOSE = "</div></div>"


# ============================================================
# Gradio 界面
# ============================================================
with gr.Blocks(title="智能金融分析平台", css=CUSTOM_CSS) as app:

    # ---- Hero ----
    gr.HTML(HERO_HTML)

    # ---- 四大分析师 ----
    gr.HTML(ANALYSTS_HTML)

    # ---- 数据来源 ----
    gr.HTML(DATA_SOURCE_HTML)

    # ---- 分析工作台 ----
    gr.HTML(WORKSPACE_HTML)

    with gr.Row():
        with gr.Column(scale=3):
            stock_input = gr.Textbox(
                placeholder="输入股票代码，如 600519.SH",
                show_label=False,
                lines=1,
                elem_classes="input-field"
            )
        with gr.Column(scale=2):
            analysis_type = gr.Dropdown(
                choices=["全量分析", "基本面分析", "技术面分析", "估值分析", "新闻舆情"],
                value="全量分析",
                show_label=False,
                elem_classes="input-field"
            )
        with gr.Column(scale=1, min_width=160):
            analyze_btn = gr.Button("开始分析", elem_classes="run-btn")

    gr.HTML(WORKSPACE_CLOSE)

    # ---- 分析结果 ----
    with gr.Row():
        summary_output = gr.Markdown()
    with gr.Row():
        verdict_output = gr.HTML()

    gr.HTML('<div style="height: 24px;"></div>')

    # ---- 多模型评测 ----
    gr.HTML(EVAL_WORKSPACE_HTML)

    with gr.Row():
        with gr.Column(scale=3):
            eval_stock = gr.Textbox(
                placeholder="输入股票代码",
                show_label=False,
                lines=1,
                elem_classes="input-field"
            )
        with gr.Column(scale=2):
            model_a = gr.Dropdown(
                choices=["gpt-4o", "deepseek-chat", "qwen-plus"],
                value="gpt-4o",
                show_label=False,
                elem_classes="input-field"
            )
        with gr.Column(scale=2):
            model_b = gr.Dropdown(
                choices=["gpt-4o", "deepseek-chat", "qwen-plus"],
                value="deepseek-chat",
                show_label=False,
                elem_classes="input-field"
            )
        with gr.Column(scale=1, min_width=160):
            eval_btn = gr.Button("开始评测", elem_classes="run-btn")

    gr.HTML(WORKSPACE_CLOSE)

    # ---- 评测结果 ----
    with gr.Row():
        with gr.Column():
            eval_report = gr.Markdown(elem_classes="eval-result")
        with gr.Column():
            radar_chart = gr.Image(show_label=False)

    # 事件绑定
    analyze_btn.click(
        fn=run_analysis,
        inputs=[stock_input, analysis_type],
        outputs=[summary_output, verdict_output]
    )

    eval_btn.click(
        fn=run_evaluation,
        inputs=[eval_stock, model_a, model_b],
        outputs=[eval_report, radar_chart]
    )


if __name__ == "__main__":
    import os
    os.makedirs("logs", exist_ok=True)

    print("=" * 60)
    print("  智能金融分析平台")
    print("  http://localhost:7860")
    print("=" * 60)
    app.launch(server_port=7860, share=False)
