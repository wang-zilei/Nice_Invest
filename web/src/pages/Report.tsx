import React from "react";
import { ArrowLeft, TrendingUp, TrendingDown, Minus, Shield, AlertTriangle, Printer, AlertCircle } from "lucide-react";
import { cleanAnalysisText, parseJsonFromText } from "@/src/lib/api";
import type { AnalysisResult } from "@/src/App";
import type { ReportData } from "@/src/lib/api";

interface ReportProps {
  result: AnalysisResult | null;
  onBack: () => void;
}

export default function Report({ result, onBack }: ReportProps) {
  if (!result) {
    return (
      <div className="w-full h-screen flex items-center justify-center bg-[#fffcf2]">
        <p className="text-[#403d39]/60">没有可用的分析结果</p>
      </div>
    );
  }

  const { stockCode, stockName, verdict, reportData, agents, summaryText } = result;

  // 股票名称回退到代码
  const displayName = stockName || stockCode;

  // 清洗后的 summary 文本
  const cleanedSummary = cleanAnalysisText(summaryText || "");
  // 去除 JSON 块的纯文本
  const summaryMarkdown = cleanedSummary.replace(/```json\s*\n[\s\S]*?\n```/g, "").trim();

  // 从 summaryText 或 reportData 中提取结构化数据
  const parsedFromText = parseJsonFromText(summaryText || "");
  const effectiveReportData: ReportData | null = reportData || (parsedFromText as unknown as ReportData) || null;

  // 从 effectiveReportData 或 agents 中提取数据
  const scores = effectiveReportData?.scores || extractScores(agents);
  const risks = effectiveReportData?.risks || [];
  const scenarios = effectiveReportData?.scenarios;
  const crossAnalysis = effectiveReportData?.cross_analysis || [];
  const verdictData = effectiveReportData?.verdict || {
    direction: verdict,
    confidence: "medium",
    weighted_score: scores.weighted_total || 0,
    recommendation_level: "数据不足",
  };

  // 检测是否缺乏数据
  const hasAnyScore = scores.fundamental > 0 || scores.technical > 0 ||
    scores.valuation > 0 || scores.news > 0;

  const directionIcon =
    verdictData.direction === "看好" ? (
      <TrendingUp className="w-6 h-6 text-[#eb5e28]" />
    ) : verdictData.direction === "看空" ? (
      <TrendingDown className="w-6 h-6 text-[#8B4513]" />
    ) : (
      <Minus className="w-6 h-6 text-[#403d39]" />
    );

  return (
    <div className="w-full h-screen overflow-auto bg-[#fffcf2] text-[#252422] font-sans">
      {/* 顶部导航 */}
      <header className="sticky top-0 z-30 bg-[#fffcf2]/95 backdrop-blur border-b border-[#ccc5b9]/30">
        <div className="w-full px-8 lg:px-12 py-4 flex items-center justify-between">
          <button
            onClick={onBack}
            className="flex items-center gap-2 text-[16px] text-[#403d39]/60 hover:text-[#252422] transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            返回分析工作台
          </button>
          <div className="flex items-center gap-4">
            <button
              onClick={() => window.print()}
              className="flex items-center gap-1.5 text-[15px] text-[#403d39]/60 hover:text-[#252422] transition-colors no-print"
            >
              <Printer className="w-4 h-4" />
              导出 PDF
            </button>
            <span className="text-[15px] text-[#403d39]/40 font-serif">
              Nice Invest 研报
            </span>
          </div>
        </div>
      </header>

      {/* 报告主体 — 全宽布局 */}
      <main className="w-full px-8 lg:px-12 py-10">
        {/* 标题区 */}
        <section className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            {directionIcon}
            <span className="text-[16px] font-semibold text-[#403d39] tracking-wider uppercase">
              {verdictData.recommendation_level || "数据不足 · 无法评估"}
            </span>
          </div>
          <h1 className="text-[36px] font-serif font-bold text-[#252422] mb-2 leading-tight">
            {displayName}
          </h1>
          <p className="text-[17px] text-[#403d39]/60 font-mono">
            {stockCode} · 多维度投资分析报告
          </p>
        </section>

        <div className="h-px bg-[#ccc5b9]/30 my-7" />

        {/* 分析报告正文 — 先于综合评分展示 */}
        {summaryMarkdown && (
          <>
            <section className="mb-8">
              <h2 className="text-[15px] font-semibold text-[#403d39]/60 uppercase tracking-wider mb-5">
                分析报告
              </h2>
              <div className="text-[16px] text-[#252422] leading-relaxed tracking-wide">
                <ReportMarkdown text={summaryMarkdown} />
              </div>
            </section>
            <div className="h-px bg-[#ccc5b9]/30 my-7" />
          </>
        )}

        {/* 综合评分 — 紧跟报告主体，无雷达图，权重分布居中不拉伸 */}
        <section className="mb-8">
          <h2 className="text-[15px] font-semibold text-[#403d39]/60 uppercase tracking-wider mb-5">
            综合评分
          </h2>

          {!hasAnyScore && (
            <DataUnavailable />
          )}

          <div className="flex flex-wrap gap-8 items-center justify-center">
            {/* 总分圆 */}
            <div className="flex flex-col items-center justify-center w-[100px] h-[100px] rounded-full border-2 border-[#403d39] shrink-0">
              <span className="text-[36px] font-bold font-tech text-[#252422]">
                {hasAnyScore ? (scores.weighted_total?.toFixed(1) || "--") : "--"}
              </span>
              <span className="text-[13px] text-[#403d39]/40">
                {hasAnyScore ? "/ 10" : "无数据"}
              </span>
            </div>

            {/* 各维度得分 — 居中不拉伸 */}
            <div className="w-full max-w-[380px] space-y-2.5">
              <InlineScore label="基本面" score={scores.fundamental} weight="35%" />
              <InlineScore label="技术面" score={scores.technical} weight="20%" />
              <InlineScore label="估值" score={scores.valuation} weight="30%" />
              <InlineScore label="新闻舆情" score={scores.news} weight="15%" />
              {hasAnyScore && (
                <div className="pt-2 mt-1 border-t border-[#ccc5b9]/20">
                  <div className="flex justify-between text-[15px]">
                    <span className="font-semibold text-[#252422]">加权总分</span>
                    <span className="font-bold font-tech text-[#eb5e28] text-[18px]">
                      {scores.weighted_total?.toFixed(1)} / 10
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>
        </section>

        <div className="h-px bg-[#ccc5b9]/30 my-7" />

        {/* 交叉分析 */}
        {crossAnalysis.length > 0 && (
          <>
            <section className="mb-8">
              <h2 className="text-[15px] font-semibold text-[#403d39]/60 uppercase tracking-wider mb-5">
                交叉分析
              </h2>
              <div className="space-y-3">
                {crossAnalysis.map((ca, i) => (
                  <div
                    key={i}
                    className="p-4 bg-white border border-[#ccc5b9]/30 rounded-lg"
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-[15px] font-medium text-[#252422]">{ca.agent_pair}</span>
                      <span
                        className={`text-[14px] px-2 py-0.5 rounded-full ${
                          ca.consistent
                            ? "bg-[#403d39]/10 text-[#403d39]"
                            : "bg-[#eb5e28]/10 text-[#eb5e28]"
                        }`}
                      >
                        {ca.consistent ? "一致" : "矛盾"}
                      </span>
                    </div>
                    <p className="text-[15px] text-[#403d39]/70 leading-relaxed tracking-wide">{ca.detail}</p>
                  </div>
                ))}
              </div>
            </section>
            <div className="h-px bg-[#ccc5b9]/30 my-7" />
          </>
        )}

        {/* 情景分析 */}
        {scenarios && (
          <>
            <section className="mb-8">
              <h2 className="text-[15px] font-semibold text-[#403d39]/60 uppercase tracking-wider mb-5">
                情景分析
              </h2>
              <div className="grid grid-cols-3 gap-4">
                <ScenarioCard
                  title="乐观情景"
                  color="border-[#403d39]"
                  trigger={scenarios.bull?.trigger}
                  outcome={scenarios.bull?.expected_return}
                />
                <ScenarioCard
                  title="基准情景"
                  color="border-[#ccc5b9]"
                  trigger=""
                  outcome={scenarios.base?.description}
                />
                <ScenarioCard
                  title="悲观情景"
                  color="border-[#8B4513]"
                  trigger={scenarios.bear?.trigger}
                  outcome={scenarios.bear?.downside_risk}
                />
              </div>
            </section>
            <div className="h-px bg-[#ccc5b9]/30 my-7" />
          </>
        )}

        {/* 风险清单 */}
        {risks.length > 0 ? (
          <section className="mb-8">
            <h2 className="text-[15px] font-semibold text-[#403d39]/60 uppercase tracking-wider mb-5 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4" />
              风险清单
            </h2>
            <div className="space-y-3">
              {risks.map((r, i) => (
                <div
                  key={i}
                  className="p-4 bg-white border border-[#ccc5b9]/30 rounded-lg flex items-start gap-4"
                >
                  <span className="text-[14px] font-mono text-[#403d39]/40 mt-0.5">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-[16px] text-[#252422] font-medium mb-2">{r.description}</p>
                    <div className="flex gap-3">
                      <RiskBadge label="影响" value={r.impact} />
                      <RiskBadge label="概率" value={r.probability} />
                    </div>
                    {r.mitigation && (
                      <p className="mt-2 text-[15px] text-[#403d39]/60 flex items-center gap-1.5 tracking-wide">
                        <Shield className="w-3.5 h-3.5" />
                        {r.mitigation}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </section>
        ) : (
          <section className="mb-8">
            <h2 className="text-[15px] font-semibold text-[#403d39]/60 uppercase tracking-wider mb-5 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4" />
              风险清单
            </h2>
            <p className="text-[16px] text-[#403d39]/50 text-center py-6">
              暂无风险分析数据
            </p>
          </section>
        )}

        {/* 页脚 */}
        <footer className="mt-16 pt-8 border-t border-[#ccc5b9]/30 text-center">
          <p className="text-[14px] text-[#403d39]/30 font-serif">
            Nice Invest · 基于 Multi-Agent 架构的金融分析系统
          </p>
          <p className="text-[13px] text-[#403d39]/20 mt-1">
            本报告由 AI 生成，仅供参考，不构成投资建议
          </p>
        </footer>
      </main>
    </div>
  );
}

// ============================================================
// 数据不可用提示
// ============================================================
function DataUnavailable() {
  return (
    <div className="mb-6 p-4 bg-[#fffcf2] border border-[#ccc5b9]/30 rounded-lg flex items-start gap-3">
      <AlertCircle className="w-5 h-5 text-[#ccc5b9] shrink-0 mt-0.5" />
      <div>
        <p className="text-[16px] font-medium text-[#403d39] mb-1">数据源不可用</p>
        <p className="text-[15px] text-[#403d39]/60 leading-relaxed tracking-wide">
          当前分析未能获取到结构化数据，评分和图表可能无法正常展示。
          请检查后端数据接口连接，或尝试使用其他股票代码重新分析。
        </p>
      </div>
    </div>
  );
}

// ============================================================
// 内联得分条
// ============================================================
function InlineScore({
  label,
  score,
  weight,
}: {
  label: string;
  score: number;
  max?: number;
  weight: string;
}) {
  const maxVal = 10;
  const hasData = score > 0;
  const pct = hasData ? (score / maxVal) * 100 : 0;

  return (
    <div className="flex items-center gap-3">
      <span className="text-[15px] text-[#403d39]/70 w-[80px] shrink-0">{label}</span>
      <div className="flex-1 h-1.5 bg-[#ccc5b9]/15 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{
            width: `${Math.min(hasData ? pct : 0, 100)}%`,
            backgroundColor: hasData ? "#403d39" : "#ccc5b9",
          }}
        />
      </div>
      <span className="text-[14px] font-mono text-[#252422] w-[36px] text-right shrink-0">
        {hasData ? score.toFixed(1) : "--"}
      </span>
      <span className="text-[13px] text-[#403d39]/30 w-[30px] text-right shrink-0">
        {weight}
      </span>
    </div>
  );
}

// ============================================================
// 情景卡片
// ============================================================
function ScenarioCard({
  title,
  color,
  trigger,
  outcome,
}: {
  title: string;
  color: string;
  trigger?: string;
  outcome?: string;
}) {
  return (
    <div className={`p-4 bg-white border-l-2 ${color} rounded-r-lg`}>
      <h3 className="text-[16px] font-semibold text-[#252422] mb-2.5">{title}</h3>
      {trigger && (
        <div className="mb-2">
          <span className="text-[13px] text-[#403d39]/40 uppercase">触发条件</span>
          <p className="text-[14px] text-[#403d39]/80 mt-0.5 leading-relaxed tracking-wide">{trigger}</p>
        </div>
      )}
      {outcome && (
        <div>
          <span className="text-[13px] text-[#403d39]/40 uppercase">预期表现</span>
          <p className="text-[14px] text-[#403d39]/80 mt-0.5 leading-relaxed tracking-wide">{outcome}</p>
        </div>
      )}
    </div>
  );
}

// ============================================================
// 风险标签
// ============================================================
function RiskBadge({ label, value }: { label: string; value?: string }) {
  const tagStyle =
    value === "high"
      ? "bg-[#403d39]/10 text-[#403d39]"
      : value === "medium"
      ? "bg-[#ccc5b9]/20 text-[#403d39]/80"
      : "bg-[#ccc5b9]/10 text-[#403d39]/50";
  return (
    <span className={`text-[13px] px-2 py-0.5 rounded-full font-medium ${tagStyle}`}>
      {label}: {value || "?"}
    </span>
  );
}

// ============================================================
// ReportMarkdown — 纯文本研报渲染（不引入额外依赖）
// 支持：中文编号标题、Markdown 标题（####/###/##/# 兜底）、表格、列表、段落
// ============================================================
function ReportMarkdown({ text }: { text: string }) {
  if (!text) return null;

  // 预处理：兜底清洗残留的 Markdown 符号
  let cleanText = text;
  // 去除水平分隔线
  cleanText = cleanText.replace(/^[\-*_]{3,}\s*$/gm, "");
  // 去除残留的 Markdown 标题标记符（保留标题文字）
  cleanText = cleanText.replace(/^####\s+/gm, "");
  cleanText = cleanText.replace(/^###\s+/gm, "");
  cleanText = cleanText.replace(/^##\s+/gm, "");
  cleanText = cleanText.replace(/^#\s+/gm, "");
  // 去除粗体/斜体标记
  cleanText = cleanText.replace(/\*\*(.+?)\*\*/g, "$1");
  cleanText = cleanText.replace(/__(.+?)__/g, "$1");
  cleanText = cleanText.replace(/\*(.+?)\*/g, "$1");

  const lines = cleanText.split("\n");

  // 预扫描：标记表格描述行（紧接表格前的非空、非标题、非表格行）
  const tableDescLines = new Set<number>();
  for (let idx = 0; idx < lines.length - 1; idx++) {
    const curr = lines[idx].trim();
    const next = lines[idx + 1];
    if (
      curr &&
      next &&
      next.startsWith("|") && next.endsWith("|") &&
      !curr.startsWith("|") &&
      !curr.match(/^[一二三四五六七八九十]、/) &&
      !curr.match(/^\d+\.\d+\s/)
    ) {
      tableDescLines.add(idx);
    }
  }

  const elements: React.ReactNode[] = [];

  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    const isTableDesc = tableDescLines.has(i);

    // 中文编号标题：一、XXX / 二、XXX（一级标题）
    if (line.match(/^[一二三四五六七八九十]、/)) {
      elements.push(
        <h2 key={i} className="text-[22px] font-bold text-[#252422] mt-7 mb-3 font-serif leading-tight">
          {line.trim()}
        </h2>
      );
      i++; continue;
    }

    // 数字子编号标题：1.1 XXX / 3.2 XXX（二级标题，仿宋）
    if (line.match(/^\d+\.\d+\s/)) {
      elements.push(
        <h3
          key={i}
          className="text-[18px] font-bold text-[#252422] mt-4 mb-2"
          style={{ fontFamily: '"FangSong", "仿宋", "STFangsong", serif' }}
        >
          {line.trim()}
        </h3>
      );
      i++; continue;
    }

    // 表格行（|...|...|）— 使用 HTML table 保证列对齐
    if (line.startsWith("|") && line.endsWith("|")) {
      const cells = line.split("|").filter(c => c.trim()).map(c => c.trim());
      const isHeader = lines[i + 1]?.match(/^\|[\s\-:|]+\|$/);
      if (isHeader) {
        // 收集所有连续的表格行
        const tableRows: string[][] = [cells];
        let j = i + 2;
        while (j < lines.length && lines[j].startsWith("|") && lines[j].endsWith("|")) {
          const rowCells = lines[j].split("|").filter(c => c.trim()).map(c => c.trim());
          if (rowCells.length > 0) tableRows.push(rowCells);
          j++;
        }
        const colCount = Math.max(...tableRows.map(r => r.length));
        elements.push(
          <div key={i} className="my-3 overflow-x-auto">
            <table className="w-full border-collapse text-[15px]">
              <thead>
                <tr>
                  {tableRows[0].map((c, ci) => (
                    <th key={ci} className="text-left px-3 py-2 bg-[#ccc5b9]/10 text-[#403d39]/80 font-semibold border-b border-[#ccc5b9]/30 whitespace-nowrap">
                      {c}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {tableRows.slice(1).map((row, ri) => (
                  <tr key={ri} className="border-b border-[#ccc5b9]/10">
                    {Array.from({ length: colCount }).map((_, ci) => (
                      <td key={ci} className="px-3 py-2 text-[#403d39] text-[15px] whitespace-normal break-words">
                        {row[ci] || ""}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
        i = j;
        continue;
      }
      elements.push(
        <p key={i} className="text-[15px] text-[#403d39] leading-relaxed tracking-wide">
          {cells.join("  ")}
        </p>
      );
      i++; continue;
    }

    // 列表项（- 或 * 开头）
    if (line.match(/^[\s]*[-*]\s/)) {
      elements.push(
        <li key={i} className="text-[16px] text-[#403d39] ml-4 leading-relaxed tracking-wide">
          {line.replace(/^[\s]*[-*]\s+/, "")}
        </li>
      );
      i++; continue;
    }

    // "XXX："或"XXX:"结尾的短行（小标题/字段行）
    if (line.trim().match(/^.+[：:]$/) && line.trim().length < 40) {
      elements.push(
        <p key={i} className="text-[16px] text-[#252422] font-semibold mt-3 mb-1 font-sans">
          {line.trim()}
        </p>
      );
      i++; continue;
    }

    // 空行
    if (line.trim() === "") {
      elements.push(<div key={i} className="h-2" />);
      i++; continue;
    }

    // 表格描述行（紧接表格前的说明文字，仿宋加粗）
    if (isTableDesc) {
      elements.push(
        <p
          key={i}
          className="text-[16px] text-[#252422] mt-3 mb-1 leading-relaxed"
          style={{ fontFamily: '"FangSong", "仿宋", "STFangsong", serif', fontWeight: 700 }}
        >
          {line.trim()}
        </p>
      );
      i++; continue;
    }

    // 普通文本
    if (line.trim()) {
      elements.push(
        <p key={i} className="text-[16px] text-[#403d39] leading-relaxed whitespace-pre-wrap tracking-wide">
          {line.trim()}
        </p>
      );
    }
    i++;
  }

  return <div>{elements.length > 0 ? elements : <p className="text-[16px] text-[#403d39] whitespace-pre-wrap tracking-wide">{text}</p>}</div>;
}

// ============================================================
// 辅助：从 agents 提取评分（缺少数据时不默认给分）
// ============================================================
function extractScores(agents: AnalysisResult["agents"]): {
  fundamental: number;
  technical: number;
  valuation: number;
  news: number;
  weighted_total: number;
} {
  const scores: Record<string, number> = {};
  let hasAny = false;

  for (const a of agents) {
    const type = a.id.replace("agent_", "");
    const jsonData = a.jsonData as Record<string, Record<string, unknown>> | undefined;
    const reportKey = `${type}_report`;
    const inner = jsonData?.[reportKey];

    if (inner && typeof inner === "object" && "score" in inner && typeof inner.score === "number") {
      scores[type] = Number(inner.score);
      hasAny = true;
    } else if (a.status === "completed" && a.confidence) {
      scores[type] = a.confidence * 10;
      hasAny = true;
    } else {
      scores[type] = 0; // 无数据时给 0 而非默认 5
    }
  }

  const f = scores.fundamental || 0;
  const t = scores.technical || 0;
  const v = scores.valuation || 0;
  const n = scores.news || 0;
  const weighted = hasAny ? f * 0.35 + t * 0.2 + v * 0.3 + n * 0.15 : 0;

  return { fundamental: f, technical: t, valuation: v, news: n, weighted_total: weighted };
}
