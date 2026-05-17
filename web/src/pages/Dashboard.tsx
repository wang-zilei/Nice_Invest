import React, { useEffect, useState, useRef, useCallback } from "react";
import {
  Search, Clock, FileText, TrendingUp, PieChart, Radio, Loader2,
  BookOpen, Settings, X, CheckCircle, AlertCircle, AlertTriangle,
  ChevronRight, RefreshCw, LogOut,
} from "lucide-react";
import { motion } from "motion/react";
import {
  searchStocks, analyzeStock, getHistory, getHistoryDetail, validateConfig,
  createInitialAnalysis,
  getUsage, getSessionToken, getSessionEmail, clearSession,
  cleanAnalysisText, parseJsonFromText, lookupStockName, stockDisplayName,
  validateStockInput,
  type AnalysisData, type AgentTask, type StockMatch,
  type LLMConfig, type SSEEvent, type HistoryEntry, type ReportData,
  type UsageResponse,
} from "@/src/lib/api";
import type { AnalysisResult } from "@/src/App";

// ============================================================
// 常量
// ============================================================
const iconMap: Record<string, React.ReactNode> = {
  FileText: <FileText className="w-5 h-5" />,
  TrendingUp: <TrendingUp className="w-5 h-5" />,
  PieChart: <PieChart className="w-5 h-5" />,
  Radio: <Radio className="w-5 h-5" />,
  BrainCircuit: <BookOpen className="w-5 h-5" />,
};

const STORAGE_KEY = "nice_invest_config";

function loadConfig(): { llm: LLMConfig } {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch { /* ignore */ }
  return { llm: {} };
}

function saveConfig(cfg: { llm: LLMConfig }) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(cfg));
}

// ============================================================
// Props
// ============================================================
interface DashboardProps {
  onViewReport: (result: AnalysisResult) => void;
  onLogout?: () => void;
}

// ============================================================
// Dashboard
// ============================================================
export default function Dashboard({ onViewReport, onLogout }: DashboardProps) {
  // 搜索状态
  const [searchText, setSearchText] = useState("");
  const [searchResults, setSearchResults] = useState<StockMatch[]>([]);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searching, setSearching] = useState(false);
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [selectedStock, setSelectedStock] = useState<StockMatch | null>(null);  // 用户选中的股票

  // 分析状态
  const [data, setData] = useState<AnalysisData | null>(null);
  const [phase, setPhase] = useState<"idle" | "searching" | "analyzing" | "done" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState("");
  const [elapsed, setElapsed] = useState("");
  const [verdict, setVerdict] = useState("");
  const controllerRef = useRef<AbortController | null>(null);
  const [validatingInput, setValidatingInput] = useState(false);  // 正在校验用户输入

  // 面板状态
  const [configOpen, setConfigOpen] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [modalAgent, setModalAgent] = useState<AgentTask | null>(null);

  // 警告弹窗
  const [showWarning, setShowWarning] = useState(false);
  const [warningMessage, setWarningMessage] = useState("");

  // 配置
  const [config, setConfig] = useState(loadConfig);
  const [configDraft, setConfigDraft] = useState(config);
  const [validating, setValidating] = useState(false);
  const [validResults, setValidResults] = useState<Record<string, string>>({});

  // 历史
  const [history, setHistory] = useState<HistoryEntry[]>([]);

  // 用量（从后端获取）
  const [usageInfo, setUsageInfo] = useState<{ remaining: number; max: number } | null>(null);
  const userEmail = getSessionEmail();

  // 加载历史和用量
  useEffect(() => {
    getHistory(10).then(setHistory);
    const token = getSessionToken();
    if (token) {
      getUsage(token)
        .then((info) => setUsageInfo({ remaining: info.remaining_uses, max: info.max_uses }))
        .catch(() => {/* ignore */});
    }
  }, []);

  // ============================================================
  // 获取实际使用的 LLM 配置（用户自备 Key 优先，否则由后端注入体验 Key）
  // ============================================================
  const getEffectiveLLMConfig = useCallback((): LLMConfig => {
    if (config.llm?.api_key) {
      return config.llm; // 用户已配置自己的 Key
    }
    return {}; // 后端根据 session 决定是否注入体验 Key
  }, [config.llm]);

  // ============================================================
  // 搜索
  // ============================================================
  const doSearch = useCallback(async (kw: string) => {
    if (kw.length < 1) {
      setSearchResults([]);
      setSearchOpen(false);
      setSearching(false);
      return;
    }
    setSearching(true);
    try {
      const matches = await searchStocks(kw);
      setSearchResults(matches);
      setSearchOpen(matches.length > 0);
    } catch {
      setSearchResults([]);
      setSearchOpen(false);
    } finally {
      setSearching(false);
    }
  }, []);

  const handleSearchInput = (v: string) => {
    setSearchText(v);
    setSelectedStock(null);  // 手动输入时清除已选股票
    if (searchTimer.current) clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(() => doSearch(v), 300);
  };

  // ============================================================
  // 确认分析（含安全护栏校验）
  // ============================================================
  const handleConfirmAnalysis = async () => {
    const sessionToken = getSessionToken();
    if (!sessionToken) {
      onLogout?.();
      return;
    }

    // 如果用户从建议列表点击选中了股票，直接开始分析
    if (selectedStock) {
      startAnalysis(selectedStock);
      return;
    }

    // 用户手动输入，需要经过安全护栏校验
    const input = searchText.trim();
    if (!input) {
      setWarningMessage("请输入公司名称或股票代码后再确认分析");
      setShowWarning(true);
      return;
    }

    setValidatingInput(true);
    try {
      const result = await validateStockInput(input);
      if (result.valid && result.ts_code && result.name) {
        // 校验通过，构建 StockMatch 并开始分析
        const matched: StockMatch = {
          ts_code: result.ts_code,
          name: result.name,
          industry: "",
        };
        setSelectedStock(matched);
        startAnalysis(matched);
      } else {
        // 校验失败，显示警告
        setWarningMessage(result.message || "未识别为有效的 A 股公司，请检查公司名称或代码是否正确");
        setShowWarning(true);
      }
    } catch {
      setWarningMessage("校验服务异常，请稍后重试");
      setShowWarning(true);
    } finally {
      setValidatingInput(false);
    }
  };

  // ============================================================
  // 开始分析
  // ============================================================
  const startAnalysis = (match: StockMatch) => {
    // 检查 session 有效性
    const sessionToken = getSessionToken();
    if (!sessionToken) {
      onLogout?.();
      return;
    }

    setSearchOpen(false);
    setSearchText(`${match.name} (${match.ts_code})`);
    setErrorMessage("");

    const initialData = createInitialAnalysis(match.ts_code, match.name);
    setData(initialData);
    setPhase("analyzing");
    setVerdict("");

    let summaryJson: ReportData | null = null;
    let finalVerdict = "";

    const updateAgent = (id: string, update: Partial<AgentTask>) => {
      setData((prev) => {
        if (!prev) return prev;
        const agents = prev.agents.map((a) =>
          a.id === id ? { ...a, ...update } : a
        );
        const reportAgent =
          id === "agent_summary"
            ? { ...prev.reportAgent, ...update }
            : prev.reportAgent;
        return { ...prev, agents, reportAgent };
      });
    };

    const effectiveLLM = getEffectiveLLMConfig();

    const ctrl = analyzeStock(
      match.ts_code,
      match.name,
      "full",
      effectiveLLM,
      (e: SSEEvent) => {
        const { event, data: d } = e;
        switch (event) {
          case "init":
            setData((prev) =>
              prev ? { ...prev, analysisId: d.analysis_id as string } : prev
            );
            break;
          case "router_done":
            setData((prev) => {
              if (!prev) return prev;
              const agentList = d.agents as string[];
              const nameMap: Record<string, string> = {
                fundamental: "基本面分析",
                technical: "技术面分析",
                valuation: "估值分析",
                news: "新闻舆情分析",
              };
              const agents = prev.agents.map((a) => {
                const agentType = a.id.replace("agent_", "");
                if (agentList.includes(agentType)) {
                  return {
                    ...a,
                    status: "analyzing" as AgentTask["status"],
                    shortDesc: `初始化${nameMap[agentType] || agentType}Agent...`,
                    message: "环境就绪",
                    progress: 5,
                  };
                }
                return a;
              });
              return { ...prev, agents };
            });
            break;
          case "agent_start": {
            const agentType = d.agent as string;
            const cnName = (d.name as string) || agentType;
            const id = agentType === "summary" ? "agent_summary" : `agent_${agentType}`;
            updateAgent(id, {
              status: "analyzing",
              shortDesc: `${cnName}分析中...`,
              message: "正在调用数据接口",
              progress: 10,
            });
            break;
          }
          case "agent_complete": {
            const agentType = d.agent as string;
            const cnName = (d.name as string) || agentType;
            const id = agentType === "summary" ? "agent_summary" : `agent_${agentType}`;
            const confidence = d.confidence as number;
            const jsonData = d.json_data as Record<string, unknown> | undefined;
            const preview = d.preview as string;
            const analysis = d.analysis as string;

            if (agentType === "summary") {
              finalVerdict = (d.verdict as string) || "中性";
              summaryJson = (d.json_data as ReportData) || null;
              setVerdict(finalVerdict);
              updateAgent(id, {
                status: "completed",
                shortDesc: `综合评分完成 — ${finalVerdict}`,
                message: "报告生成完毕",
                progress: 100,
                confidence,
                jsonData,
                analysis,
              });
              setData((prev) => {
                if (!prev) return prev;
                const agents = prev.agents.map((a) =>
                  a.status === "analyzing"
                    ? { ...a, status: "completed" as AgentTask["status"], progress: 100 }
                    : a
                );
                return { ...prev, agents };
              });
            } else {
              updateAgent(id, {
                status: "completed",
                shortDesc: `${cnName}报告完成`,
                message: preview || "分析完成",
                progress: 100,
                confidence,
                jsonData,
                preview,
                analysis,
              });
            }
            break;
          }
          case "agent_error": {
            const agentType = d.agent as string;
            const id = agentType === "summary" ? "agent_summary" : `agent_${agentType}`;
            updateAgent(id, {
              status: "error",
              shortDesc: `分析出错: ${(d.error as string)?.slice(0, 30)}`,
              message: "",
              progress: 0,
            });
            break;
          }
          case "progress": {
            const agent = d.agent as string;
            if (agent !== "system") {
              const id = agent === "summary" ? "agent_summary" : `agent_${agent}`;
              updateAgent(id, {
                message: d.message as string,
                progress: 65,
              });
            }
            break;
          }
          case "done":
            setElapsed(`${d.elapsed as number}s`);
            finalVerdict = (d.verdict as string) || finalVerdict;
            setVerdict(finalVerdict);
            if ((d.summary_json as ReportData) && !summaryJson) {
              summaryJson = d.summary_json as ReportData;
            }
            // 同步 stock_name 到 AnalysisData，确保名称不为空
            const doneStockName = (d.stock_name as string) || match.name;
            const resolved = stockDisplayName(doneStockName, match.ts_code);
            setData((prev) => prev ? { ...prev, name: resolved.name } : prev);
            setPhase("done");
            getHistory(10).then(setHistory);
            break;
          case "error":
            setErrorMessage((d.message as string) || "分析过程中发生未知错误");
            setPhase("error");
            break;
        }
      },
      (error: string) => {
        console.error("SSE error:", error);
        // 401 → session 过期，退回登录
        if (error.includes("401") || error.includes("登录")) {
          onLogout?.();
          return;
        }
        setErrorMessage(error || "网络连接异常，请确认后端服务（server.py）已启动");
        setPhase("error");
      },
      () => {}
    );
    controllerRef.current = ctrl;
  };

  // ============================================================
  // 查看报告
  // ============================================================
  const handleViewReport = () => {
    if (!data) return;
    const summaryAgent = data.reportAgent;
    const reportData: ReportData | null =
      (summaryAgent?.jsonData as unknown as ReportData) || null;

    const display = stockDisplayName(data.name, data.symbol);

    onViewReport({
      analysisId: data.analysisId,
      stockCode: data.symbol,
      stockName: display.name,
      verdict: verdict || data.reportAgent?.shortDesc || "中性",
      summaryText: data.reportAgent?.analysis || data.reportAgent?.preview || "",
      reportData,
      agents: data.agents,
    });
  };

  // ============================================================
  // 从历史记录加载缓存结果
  // ============================================================
  const handleHistorySelect = async (h: HistoryEntry) => {
    setHistoryOpen(false);
    if (controllerRef.current) controllerRef.current.abort();

    // 尝试从历史记录获取完整结果
    const detail = await getHistoryDetail(h.id);
    if (detail?.found && detail.record) {
      const rec = detail.record;
      // 构建 AgentTask 列表
      const nameToType: Record<string, string> = {
        "基本面": "fundamental",
        "技术面": "technical",
        "估值": "valuation",
        "新闻舆情": "news",
      };
      const typeToConfig: Record<string, { name: string; description: string; icon: string }> = {
        fundamental: { name: "1. 基本面分析", description: "扫描财务报表，分析盈利能力、偿债能力、运营效率和成长性，评估公司内在价值与竞争优势。", icon: "FileText" },
        technical: { name: "2. 技术面分析", description: "分析价格趋势、交易量、技术指标和图表形态，识别市场趋势与关键支撑阻力位。", icon: "TrendingUp" },
        valuation: { name: "3. 估值分析", description: "运行估值模型，对比行业与历史数据，评估当前价格的合理性与安全边际。", icon: "PieChart" },
        news: { name: "4. 新闻与市场情绪", description: "扫描新闻资讯，分析市场情绪、舆论趋势和事件影响，捕捉潜在风险与机会。", icon: "Radio" },
      };

      const agents: AgentTask[] = (rec.agent_results || []).map((r: any) => {
        const type = nameToType[r.agent_name] || "fundamental";
        const cfg = typeToConfig[type];
        return {
          id: `agent_${type}`,
          name: cfg.name,
          description: cfg.description,
          shortDesc: `${r.agent_name}报告完成`,
          icon: cfg.icon,
          status: "completed" as AgentTask["status"],
          progress: 100,
          message: "分析完成",
          analysis: r.analysis,
          confidence: r.confidence,
        };
      });

      // 补齐可能缺失的 agent
      const existingTypes = new Set(agents.map((a) => a.id));
      for (const [type, cfg] of Object.entries(typeToConfig)) {
        if (!existingTypes.has(`agent_${type}`)) {
          agents.push({
            id: `agent_${type}`,
            name: cfg.name,
            description: cfg.description,
            shortDesc: "数据缺失",
            icon: cfg.icon,
            status: "error" as AgentTask["status"],
            progress: 0,
            message: "",
          });
        }
      }

      // Summary agent
      const reportAgent: AgentTask = {
        id: "agent_summary",
        name: "投资决策引擎",
        description: "系统将自动整合所有分析结果，生成专业投资报告与操作建议。",
        shortDesc: `综合评分完成 — ${rec.verdict}`,
        icon: "BrainCircuit",
        status: "completed" as AgentTask["status"],
        progress: 100,
        message: "报告生成完毕",
        analysis: rec.summary_text,
        jsonData: rec.summary_json as unknown as Record<string, unknown> | undefined,
      };

      const display = stockDisplayName(rec.stock_name, rec.stock_code);

      const analysisData: AnalysisData = {
        analysisId: rec.id,
        symbol: rec.stock_code,
        name: display.name,
        estimatedTime: `${rec.elapsed}s`,
        totalProgress: 100,
        agents,
        reportAgent,
      };

      setSearchText(`${display.name} (${display.code})`);
      setData(analysisData);
      setVerdict(rec.verdict);
      setElapsed(`${rec.elapsed}s`);
      setPhase("done");
      return;
    }

    // 降级：重新分析
    const fallbackDisplay = stockDisplayName(h.stock_name, h.stock_code);
    setSearchText(`${fallbackDisplay.name} (${fallbackDisplay.code})`);
    startAnalysis({ ts_code: h.stock_code, name: fallbackDisplay.name, industry: "" });
  };

  // ============================================================
  // 配置校验
  // ============================================================
  const handleValidate = async () => {
    setValidating(true);
    const results = await validateConfig({
      model: configDraft.llm?.model || "deepseek-chat",
      api_key: configDraft.llm?.api_key || "",
      base_url: configDraft.llm?.base_url || "",
    });
    setValidResults(results);
    setValidating(false);
  };

  const handleSaveConfig = () => {
    setConfig(configDraft);
    saveConfig(configDraft);
    setConfigOpen(false);
  };

  // ============================================================
  // 构建初始数据（未分析时的占位状态）
  // ============================================================
  const displayData: AnalysisData = data || {
    analysisId: "",
    symbol: "",
    name: "输入股票代码或名称，开始多维度投资分析",
    estimatedTime: "--:--",
    totalProgress: 0,
    agents: [
      {
        id: "agent_fundamental", name: "1. 基本面分析",
        description: "扫描财务报表，分析盈利能力、偿债能力、运营效率和成长性。",
        shortDesc: "等待分析启动...", icon: "FileText",
        status: "pending" as AgentTask["status"], progress: 0, message: "",
      },
      {
        id: "agent_technical", name: "2. 技术面分析",
        description: "分析价格趋势、交易量、技术指标和图表形态，识别市场趋势与关键支撑阻力位。",
        shortDesc: "等待分析启动...", icon: "TrendingUp",
        status: "pending" as AgentTask["status"], progress: 0, message: "",
      },
      {
        id: "agent_valuation", name: "3. 估值分析",
        description: "运行估值模型，对比行业与历史数据，评估当前价格的合理性与安全边际。",
        shortDesc: "等待分析启动...", icon: "PieChart",
        status: "pending" as AgentTask["status"], progress: 0, message: "",
      },
      {
        id: "agent_news", name: "4. 新闻与市场情绪",
        description: "扫描新闻资讯，分析市场情绪、舆论趋势和事件影响，捕捉潜在风险与机会。",
        shortDesc: "等待分析启动...", icon: "Radio",
        status: "pending" as AgentTask["status"], progress: 0, message: "",
      },
    ],
    reportAgent: {
      id: "agent_summary", name: "投资决策引擎",
      description: "系统将自动整合所有分析结果，生成专业投资报告。",
      shortDesc: "等待各节点数据流输入...", icon: "BrainCircuit",
      status: "pending" as AgentTask["status"], progress: 0, message: "等待前置节点完成",
    },
  };

  const isPlaceholder = !data;

  // ============================================================
  // 渲染
  // ============================================================
  return (
    <div className="flex flex-col h-screen w-full bg-[#fffcf2] text-[#252422] font-sans overflow-hidden">
      {/* Header — 搜索入口区域 */}
      <header className="shrink-0 bg-[#fffcf2] border-b border-[#ccc5b9]/40 flex items-center justify-between px-6 lg:px-10 relative z-20"
        style={{ minHeight: "100px", paddingTop: "14px", paddingBottom: "14px" }}
      >
        <div className="flex items-center gap-2.5 shrink-0">
          <BookOpen className="w-5 h-5 text-[#403d39]" />
          <span className="text-[22px] font-serif font-bold tracking-wide italic text-[#252422]">
            Nice Invest
          </span>
        </div>

        {/* 搜索框 + 确认按钮 */}
        <div className="flex-1 max-w-[660px] mx-8 relative flex items-center gap-2">
          <div className="flex-1 relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-[20px] h-[20px] text-[#ccc5b9]" />
            <input
              type="text"
              placeholder="输入公司名称、股票代码..."
              value={searchText}
              onChange={(e) => handleSearchInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") handleConfirmAnalysis(); }}
              className="w-full h-[50px] pl-11 pr-4 bg-white border border-[#ccc5b9] rounded-lg text-[15px] text-[#252422] focus:outline-none focus:ring-1 focus:ring-[#403d39] focus:border-[#403d39] transition-all placeholder-[#ccc5b9] shadow-sm"
            />
            {searching && (
              <Loader2 className="absolute right-4 top-1/2 -translate-y-1/2 w-4 h-4 animate-spin text-[#403d39]" />
            )}
            {searchOpen && searchResults.length > 0 && (
              <div className="absolute top-full mt-1.5 w-full bg-white border border-[#ccc5b9] rounded-lg shadow-lg z-50 max-h-[320px] overflow-auto">
                {searchResults.map((m) => (
                  <button
                    key={m.ts_code}
                    className="w-full text-left px-4 py-3.5 hover:bg-[#fffcf2] flex items-center justify-between group border-b border-[#ccc5b9]/10 last:border-b-0"
                    onClick={() => {
                      if (controllerRef.current) controllerRef.current.abort();
                      setSearchText(`${m.name} (${m.ts_code})`);
                      setSelectedStock(m);
                      setSearchOpen(false);
                    }}
                  >
                    <div>
                      <span className="text-[14px] font-medium text-[#252422]">{m.name}</span>
                      <span className="text-[12px] text-[#403d39]/50 ml-2">{m.ts_code}</span>
                    </div>
                    <span className="text-[12px] text-[#403d39]/40 group-hover:text-[#eb5e28] transition-colors">
                      {m.industry}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>
          {/* 确认分析按钮 */}
          <button
            onClick={handleConfirmAnalysis}
            disabled={phase === "analyzing" || validatingInput || !searchText.trim()}
            className="shrink-0 h-[50px] px-6 bg-[#252422] text-white rounded-lg text-[14px] font-medium hover:bg-[#403d39] transition-colors flex items-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {validatingInput ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <ChevronRight className="w-4 h-4" />
            )}
            确认分析
          </button>
        </div>

        <div className="flex items-center gap-5 text-[#403d39] shrink-0">
          <button
            onClick={() => { getHistory(20).then(setHistory); setHistoryOpen(true); }}
            className="flex items-center gap-2 hover:text-[#252422] transition-colors"
          >
            <Clock className="w-[18px] h-[18px]" />
            <span className="text-[14px] font-medium">历史记录</span>
          </button>
          <button
            onClick={() => { setConfigDraft(config); setConfigOpen(true); }}
            className="w-9 h-9 rounded-full bg-white border border-[#ccc5b9] flex items-center justify-center text-[#403d39] hover:bg-[#fffcf2] hover:text-[#252422] transition-colors"
          >
            <Settings className="w-4 h-4" />
          </button>
          {onLogout && (
            <button
              onClick={onLogout}
              className="w-9 h-9 rounded-full bg-white border border-[#ccc5b9] flex items-center justify-center text-[#403d39] hover:bg-[#fffcf2] hover:text-[#eb5e28] transition-colors"
              title="退出登录"
            >
              <LogOut className="w-4 h-4" />
            </button>
          )}
        </div>
      </header>

      {/* Main — 股票信息 + Agent 网格 */}
      <div className="flex-1 flex flex-col overflow-hidden px-10 pb-10 pt-6">
        {/* 股票信息区 / 欢迎语 */}
        <div className="shrink-0 mb-6 w-full max-w-[1200px] mx-auto text-left px-4 lg:px-8">
          {isPlaceholder ? (
            <div>
              <span className="text-[13px] font-serif font-semibold text-[#403d39]/60 tracking-wider uppercase mb-2 block">
                欢迎使用
              </span>
              <div className="flex items-center justify-between">
                <div>
                  <h1 className="text-[36px] font-tech font-extrabold text-[#252422] leading-tight mb-1 tracking-tight">
                    {displayData.name}
                  </h1>
                  {!config.llm?.api_key && usageInfo && (
                    <p className="text-[13px] text-[#403d39]/50">
                      体验模式 · 剩余 {usageInfo.remaining} / {usageInfo.max} 次免费分析
                    </p>
                  )}
                  {userEmail && userEmail !== "guest@niceinvest.dev" && (
                    <p className="text-[12px] text-[#403d39]/30 mt-0.5">{userEmail}</p>
                  )}
                  {userEmail === "guest@niceinvest.dev" && (
                    <p className="text-[12px] text-[#403d39]/30 mt-0.5">游客模式</p>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div>
              <span className="text-[13px] font-serif font-semibold text-[#403d39]/60 tracking-wider uppercase mb-2 block">
                当前分析对象
              </span>
              <div className="flex items-center justify-between">
                <div>
                  <h1 className="text-[36px] font-tech font-extrabold text-[#252422] leading-tight mb-1 tracking-tight">
                    {displayData.name}{" "}
                    <span className="font-medium text-[#403d39]/40">({displayData.symbol})</span>
                  </h1>
                  <div className="flex items-center gap-4 text-[14px] text-[#403d39]/60">
                    {phase === "analyzing" ? (
                      <span className="flex items-center gap-2">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        正在生成多维度投资分析...
                      </span>
                    ) : phase === "error" ? (
                      <span className="flex items-center gap-2 text-red-500">
                        <AlertCircle className="w-4 h-4" />
                        分析失败
                      </span>
                    ) : phase === "done" ? (
                      <span className="flex items-center gap-4">
                        <span className="flex items-center gap-1.5">
                          <CheckCircle className="w-4 h-4 text-[#eb5e28]" />
                          分析完成
                        </span>
                        <span className="text-[13px]">耗时 {elapsed}</span>
                        {verdict && (
                          <span className="text-[14px] font-semibold text-[#252422]">
                            投资倾向：{verdict}
                          </span>
                        )}
                        <button
                          onClick={handleViewReport}
                          className="ml-2 px-4 py-1.5 bg-[#252422] text-white text-[13px] rounded-lg hover:bg-[#403d39] transition-colors flex items-center gap-1.5"
                        >
                          查看完整报告 <ChevronRight className="w-3.5 h-3.5" />
                        </button>
                      </span>
                    ) : null}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* 错误提示横幅 */}
        {phase === "error" && errorMessage && (
          <div className="shrink-0 w-full max-w-[1200px] mx-auto mb-4 p-4 bg-red-50 border border-red-200 rounded-xl flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <p className="text-[14px] font-medium text-red-700 mb-1">分析异常</p>
              <p className="text-[13px] text-red-600/80 whitespace-pre-wrap leading-relaxed">{errorMessage}</p>
            </div>
            <button
              onClick={() => setPhase("idle")}
              className="shrink-0 text-red-400 hover:text-red-600 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Agent Grid — 紧凑布局，防止底部 Agent 顶到边缘 */}
        <div className="flex-1 w-full mx-auto relative flex items-center justify-center max-w-[1400px]" style={{ minHeight: 0 }}>
          {/* 装饰光晕 */}
          <div className="absolute top-[15%] left-[20%] w-[300px] h-[300px] bg-[#ccc5b9]/8 rounded-full blur-[120px] pointer-events-none" />
          <div className="absolute bottom-[15%] right-[20%] w-[400px] h-[400px] bg-[#403d39]/4 rounded-full blur-[120px] pointer-events-none" />

          <div className="w-full h-full relative grid grid-cols-[1fr_auto_1fr] gap-x-10 gap-y-0 items-center justify-items-center"
            style={{ gridTemplateRows: "1fr auto 0.85fr" }}
          >
            {/* SVG 连线 */}
            <svg className="absolute inset-0 w-full h-full pointer-events-none z-0">
              <path d="M 50% 26% V 36% H 46% V 50%" stroke="#ccc5b9" strokeWidth="1.5" fill="none" strokeLinecap="square" />
              <path d="M 18% 50% H 32% V 38% H 50%" stroke="#ccc5b9" strokeWidth="1.5" fill="none" strokeLinecap="square" />
              <path d="M 82% 50% H 68% V 38% H 50%" stroke="#ccc5b9" strokeWidth="1.5" fill="none" strokeLinecap="square" />
              <path d="M 50% 68% V 62% H 46% V 50%" stroke="#ccc5b9" strokeWidth="1.5" fill="none" strokeLinecap="square" />
            </svg>

            {/* Row 1: 基本面 */}
            <div className="col-start-2 row-start-1 z-10 w-full flex justify-center translate-y-6">
              <AgentCard agent={displayData.agents[0]} onClick={() => setModalAgent(displayData.agents[0])} />
            </div>

            {/* Row 2: 技术面 · 核心 · 估值 */}
            <div className="col-start-1 row-start-2 z-10 w-full flex justify-end translate-x-4">
              <AgentCard agent={displayData.agents[1]} onClick={() => setModalAgent(displayData.agents[1])} />
            </div>
            <div className="col-start-2 row-start-2 z-20 relative">
              <CenterCore reportAgent={displayData.reportAgent} phase={phase} onClick={() => setModalAgent(displayData.reportAgent)} />
            </div>
            <div className="col-start-3 row-start-2 z-10 w-full flex justify-start -translate-x-4">
              <AgentCard agent={displayData.agents[2]} onClick={() => setModalAgent(displayData.agents[2])} />
            </div>

            {/* Row 3: 新闻（原来是 row 3 1fr 撑到底部，现在设为 0.85fr，位置上移） */}
            <div className="col-start-2 row-start-3 z-10 w-full flex justify-center -translate-y-2">
              <AgentCard agent={displayData.agents[3]} onClick={() => setModalAgent(displayData.agents[3])} />
            </div>
          </div>
        </div>
      </div>

      {/* 配置面板 */}
      <ConfigPanel
        open={configOpen}
        draft={configDraft}
        onDraftChange={setConfigDraft}
        onValidate={handleValidate}
        onSave={handleSaveConfig}
        onClose={() => setConfigOpen(false)}
        validating={validating}
        validResults={validResults}
        usageCount={usageInfo ? (usageInfo.max - usageInfo.remaining) : 0}
        demoMaxUses={usageInfo?.max || 2}
        demoModel="deepseek-chat"
      />

      {/* 历史面板 */}
      <HistoryPanel
        open={historyOpen}
        history={history}
        onClose={() => setHistoryOpen(false)}
        onSelect={handleHistorySelect}
      />

      {/* Agent 报告 Modal */}
      <AgentModal agent={modalAgent} onClose={() => setModalAgent(null)} />

      {/* 安全护栏警告 Modal */}
      <WarnModal
        open={showWarning}
        message={warningMessage}
        onClose={() => setShowWarning(false)}
      />
    </div>
  );
}

// ============================================================
// AgentCard
// ============================================================
function AgentCard({ agent, onClick }: { agent: AgentTask; onClick?: () => void }) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.4 }}
      className="bg-white rounded-2xl p-5 md:p-7 border border-[#ccc5b9]/40 shadow-[0_4px_24px_rgba(37,36,34,0.04)] w-full max-w-[420px] relative group cursor-pointer"
      onClick={onClick}
    >
      <div className="flex items-start gap-4">
        <div className="shrink-0 w-11 h-11 bg-[#fffcf2] border border-[#ccc5b9]/40 rounded-2xl flex items-center justify-center text-[#403d39]">
          {iconMap[agent.icon] || <FileText className="w-5 h-5" />}
        </div>
        <div className="flex-1 min-w-0 pt-0.5">
          <h3 className="text-[17px] font-tech font-bold text-[#252422] mb-2 break-words">
            {agent.name}
          </h3>
          <p className="text-[13px] text-[#403d39]/60 font-serif leading-relaxed mb-5">
            {agent.description}
          </p>
        </div>
      </div>
      <div className="flex items-center justify-between pt-3 border-t border-[#ccc5b9]/20">
        <div className="flex items-center gap-2">
          {agent.status === "analyzing" ? (
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
            >
              <Loader2 className="w-4 h-4 text-[#403d39]" />
            </motion.div>
          ) : agent.status === "completed" ? (
            <CheckCircle className="w-4 h-4 text-[#eb5e28]" />
          ) : agent.status === "error" ? (
            <AlertCircle className="w-4 h-4 text-red-500" />
          ) : null}
          <span
            className={`text-[13px] font-medium font-tech ${
              agent.status === "completed"
                ? "text-[#403d39]"
                : agent.status === "error"
                ? "text-red-500"
                : "text-[#403d39]/60"
            }`}
          >
            {agent.shortDesc}
          </span>
        </div>
        {agent.confidence && agent.status === "completed" && (
          <span className="text-[12px] text-[#403d39]/40">
            置信度 {(agent.confidence * 100).toFixed(0)}%
          </span>
        )}
      </div>
    </motion.div>
  );
}

// ============================================================
// CenterCore
// ============================================================
function CenterCore({
  reportAgent,
  phase,
  onClick,
}: {
  reportAgent: AgentTask;
  phase: string;
  onClick?: () => void;
}) {
  return (
    <div className="relative flex flex-col items-center justify-center cursor-pointer" onClick={onClick}>
      <div className="absolute inset-[-30px] border border-[#ccc5b9]/30 rounded-full drop-shadow-sm opacity-50" />
      <div className="absolute inset-[-60px] border border-[#ccc5b9]/15 rounded-full opacity-30" />

      <div className="relative w-[110px] h-[130px] bg-[#252422] border border-[#403d39] rounded-2xl shadow-[0_8px_30px_rgba(37,36,34,0.2)] flex flex-col items-center pt-5 pb-3 px-5 z-10 overflow-hidden">
        <div className="w-full flex items-center justify-between mb-4 px-1">
          <BookOpen className="w-5 h-5 text-[#fffcf2]" />
          <div className="flex gap-1">
            {[0, 0.2, 0.4].map((delay, i) => (
              <motion.div
                key={i}
                className="w-1.5 h-1.5 rounded-full bg-[#403d39]"
                animate={{ opacity: [0.3, 1, 0.3] }}
                transition={{ duration: 1.2, repeat: Infinity, delay }}
              />
            ))}
          </div>
        </div>

        <div className="w-full flex flex-col gap-2.5 px-1 flex-1">
          {[0, 0.3, 0.6].map((delay, i) => (
            <motion.div
              key={i}
              className={`h-[3px] bg-[#403d39] rounded-full relative overflow-hidden ${
                i === 0 ? "w-full" : i === 1 ? "w-[85%]" : "w-[60%]"
              }`}
            >
              {phase === "analyzing" && (
                <motion.div
                  className="absolute inset-y-0 left-0 bg-[#ccc5b9] rounded-full"
                  animate={{ width: ["0%", "100%", "100%"] }}
                  transition={{ duration: 2, repeat: Infinity, ease: "circInOut", delay }}
                />
              )}
            </motion.div>
          ))}
        </div>

        <div className="w-full mt-auto flex items-center justify-center">
          <span className="text-[10px] font-bold tracking-[0.15em] text-[#ccc5b9] uppercase">
            {reportAgent.status === "completed" ? "报告就绪" : "撰写总结中"}
          </span>
        </div>
      </div>
    </div>
  );
}

// ============================================================
// ConfigPanel（简化版：仅 LLM 配置，无 Tushare）
// ============================================================
function ConfigPanel({
  open,
  draft,
  onDraftChange,
  onValidate,
  onSave,
  onClose,
  validating,
  validResults,
  usageCount,
  demoMaxUses,
  demoModel,
}: {
  open: boolean;
  draft: { llm: LLMConfig };
  onDraftChange: (d: { llm: LLMConfig }) => void;
  onValidate: () => void;
  onSave: () => void;
  onClose: () => void;
  validating: boolean;
  validResults: Record<string, string>;
  usageCount: number;
  demoMaxUses: number;
  demoModel: string;
}) {
  if (!open) return null;

  const hasCustomKey = !!draft.llm?.api_key;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/20" onClick={onClose}>
      <div
        className="bg-white rounded-2xl p-8 w-[460px] max-h-[80vh] overflow-auto shadow-xl border border-[#ccc5b9]/40"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-[18px] font-bold text-[#252422]">大模型 API 配置</h3>
          <button onClick={onClose} className="text-[#403d39]/40 hover:text-[#252422]">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* 体验模式提示 */}
        {!hasCustomKey && (
          <div className="mb-5 p-3 bg-[#fffcf2] border border-[#ccc5b9]/30 rounded-lg">
            <p className="text-[13px] text-[#403d39]/70 leading-relaxed">
              当前使用<b>公开体验 API</b>（{demoModel}），剩余 <b>{demoMaxUses - usageCount}</b> 次。
              配置自己的大模型 API 可不限次数使用。
            </p>
          </div>
        )}

        <div className="space-y-4">
          <div>
            <label className="block text-[13px] font-medium text-[#403d39] mb-1">模型</label>
            <select
              value={draft.llm?.model || demoModel}
              onChange={(e) =>
                onDraftChange({ ...draft, llm: { ...draft.llm, model: e.target.value } })
              }
              className="w-full h-[38px] px-3 border border-[#ccc5b9] rounded-lg text-[13px] bg-white"
            >
              <option value="deepseek-chat">DeepSeek Chat</option>
              <option value="gpt-4o">GPT-4o</option>
              <option value="gpt-4.1">GPT-4.1</option>
              <option value="qwen-plus">Qwen Plus</option>
              <option value="qwen-max">Qwen Max</option>
              <option value="claude-sonnet-4-6">Claude Sonnet 4.6</option>
            </select>
          </div>

          <div>
            <label className="block text-[13px] font-medium text-[#403d39] mb-1">API Key</label>
            <input
              type="password"
              value={draft.llm?.api_key || ""}
              onChange={(e) =>
                onDraftChange({ ...draft, llm: { ...draft.llm, api_key: e.target.value } })
              }
              className="w-full h-[38px] px-3 border border-[#ccc5b9] rounded-lg text-[13px] focus:outline-none focus:ring-1 focus:ring-[#403d39]"
              placeholder="sk-..."
            />
          </div>

          <div>
            <label className="block text-[13px] font-medium text-[#403d39] mb-1">Base URL</label>
            <input
              type="text"
              value={draft.llm?.base_url || ""}
              onChange={(e) =>
                onDraftChange({ ...draft, llm: { ...draft.llm, base_url: e.target.value } })
              }
              className="w-full h-[38px] px-3 border border-[#ccc5b9] rounded-lg text-[13px] focus:outline-none focus:ring-1 focus:ring-[#403d39]"
              placeholder="https://api.openai.com/v1"
            />
            <p className="text-[11px] text-[#403d39]/40 mt-1">
              支持任何兼容 OpenAI 协议的 API 端点（DeepSeek / OpenAI / Qwen / 第三方代理等）
            </p>
          </div>

          {validResults.llm && (
            <p className={`text-[12px] ${validResults.llm === "valid" ? "text-green-600" : "text-red-500"}`}>
              {validResults.llm === "valid" ? "连接成功" : validResults.llm}
            </p>
          )}
        </div>

        <div className="flex gap-3 mt-6">
          <button
            onClick={onValidate}
            disabled={validating}
            className="flex-1 h-[40px] border border-[#ccc5b9] rounded-lg text-[13px] font-medium text-[#403d39] hover:bg-[#fffcf2] transition-colors flex items-center justify-center gap-2"
          >
            {validating ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
            校验连接
          </button>
          <button
            onClick={onSave}
            className="flex-1 h-[40px] bg-[#252422] text-white rounded-lg text-[13px] font-medium hover:bg-[#403d39] transition-colors"
          >
            保存配置
          </button>
        </div>
      </div>
    </div>
  );
}

// ============================================================
// HistoryPanel
// ============================================================
function HistoryPanel({
  open,
  history,
  onClose,
  onSelect,
}: {
  open: boolean;
  history: HistoryEntry[];
  onClose: () => void;
  onSelect: (h: HistoryEntry) => void;
}) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/20" onClick={onClose}>
      <div
        className="bg-white rounded-2xl p-8 w-[520px] max-h-[70vh] overflow-auto shadow-xl border border-[#ccc5b9]/40"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-[18px] font-bold text-[#252422]">历史分析记录</h3>
          <button onClick={onClose} className="text-[#403d39]/40 hover:text-[#252422]">
            <X className="w-5 h-5" />
          </button>
        </div>

        {history.length === 0 ? (
          <p className="text-[14px] text-[#403d39]/60 text-center py-8">暂无记录</p>
        ) : (
          <div className="space-y-2">
            {history.map((h) => {
              const hDisplay = stockDisplayName(h.stock_name, h.stock_code);
              return (
              <button
                key={h.id}
                onClick={() => onSelect(h)}
                className="w-full text-left px-4 py-3 rounded-lg hover:bg-[#fffcf2] flex items-center justify-between group transition-colors border border-transparent hover:border-[#ccc5b9]/40"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-[14px] font-medium text-[#252422]">
                      {hDisplay.name}
                    </span>
                    <span className="text-[12px] text-[#403d39]/50 font-mono">{hDisplay.code}</span>
                    <span className="text-[12px] text-[#403d39]/40">
                      {h.analysis_type === "full" ? "全量分析" : h.analysis_type}
                    </span>
                  </div>
                  <span className="text-[12px] text-[#403d39]/40">
                    {h.created_at?.slice(0, 16)?.replace("T", " ")}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[13px] font-medium text-[#252422]">{h.verdict}</span>
                  <span className="text-[12px] text-[#403d39]/40">{h.elapsed}s</span>
                  <ChevronRight className="w-4 h-4 text-[#ccc5b9] group-hover:text-[#eb5e28] transition-colors" />
                </div>
              </button>
            );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================================
// AgentModal — 结构化展示 Agent 分析结果
// ============================================================

// 指标英文 key → 中文名称映射（用于关键指标展示）
const METRIC_NAME_MAP: Record<string, string> = {
  // 基本面
  roe: "净资产收益率(ROE)",
  net_profit_margin: "净利率",
  gross_margin: "毛利率",
  revenue_growth: "营收增速",
  net_profit_growth: "净利润增速",
  debt_ratio: "资产负债率",
  current_ratio: "流动比率",
  asset_turnover: "资产周转率",
  // 技术面
  latest_price: "最新价",
  ma_5: "5日均线",
  ma_20: "20日均线",
  ma_60: "60日均线",
  volatility_20d: "20日波动率",
  volume_ratio: "量比",
  // 估值
  pe_ttm: "市盈率(PE-TTM)",
  pb: "市净率(PB)",
  ps_ttm: "市销率(PS-TTM)",
  peg: "市盈增长比(PEG)",
  dividend_yield: "股息率",
  // 新闻
  total_news_count: "新闻总数",
  positive_count: "正面新闻数",
  negative_count: "负面新闻数",
  neutral_count: "中性新闻数",
};

function formatMetricKey(key: string): string {
  return METRIC_NAME_MAP[key] || key;
}

function AgentModal({ agent, onClose }: { agent: AgentTask | null; onClose: () => void }) {
  if (!agent) return null;

  // 清洗并分离 Markdown 正文（去 JSON 块 + 思考过程）
  const rawText = agent.analysis || agent.preview || "";
  const cleaned = cleanAnalysisText(rawText);
  const markdownText = cleaned.replace(/```json\s*\n[\s\S]*?\n```/g, "").trim();

  // 尝试解析 JSON 结构化数据（优先用 agent.jsonData，否则从文本中提取）
  const jsonData = (agent.jsonData as Record<string, Record<string, unknown>> | undefined)
    || parseJsonFromText(rawText);

  // 提取 report 内的 score 和 key_metrics
  const reportKey = Object.keys(jsonData || {}).find(k => k.includes("_report") || k === "ReportData");
  const innerData = reportKey ? (jsonData?.[reportKey] as Record<string, unknown> | undefined) : undefined;
  const score = typeof innerData?.score === "number" ? innerData.score : null;
  const dataCompleteness = typeof innerData?.data_completeness === "string" ? innerData.data_completeness : null;

  // 是否为 Summary Agent（报告生成器）
  const isSummary = agent.id === "agent_summary";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/20" onClick={onClose}>
      <div
        className="bg-white rounded-2xl p-8 w-[780px] max-h-[90vh] overflow-auto shadow-xl border border-[#ccc5b9]/40"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-[22px] font-bold text-[#252422]">{agent.name}</h3>
          <button onClick={onClose} className="text-[#403d39]/40 hover:text-[#252422]">
            <X className="w-5 h-5" />
          </button>
        </div>
        <p className="text-[16px] text-[#403d39]/50 mb-5">{agent.description}</p>

        {/* 评分 & 置信度条 */}
        <div className="flex items-center gap-6 mb-5">
          {score !== null && (
            <div className="flex items-center gap-2">
              <span className="text-[14px] text-[#403d39]/50">综合评分</span>
              <span className="text-[24px] font-bold font-tech text-[#eb5e28]">{score}/10</span>
            </div>
          )}
          {agent.confidence && (
            <div className="flex items-center gap-2">
              <span className="text-[14px] text-[#403d39]/50">置信度</span>
              <div className="w-20 h-1.5 bg-[#ccc5b9]/20 rounded-full overflow-hidden">
                <div
                  className="h-full bg-[#403d39] rounded-full"
                  style={{ width: `${(agent.confidence * 100).toFixed(0)}%` }}
                />
              </div>
              <span className="text-[14px] text-[#403d39]/60">{(agent.confidence * 100).toFixed(0)}%</span>
            </div>
          )}
          {dataCompleteness && (
            <span className={`text-[13px] px-2 py-0.5 rounded-full ${
              dataCompleteness === "complete" ? "bg-green-50 text-green-700" :
              dataCompleteness === "partial" ? "bg-amber-50 text-amber-700" :
              "bg-red-50 text-red-700"
            }`}>
              数据{dataCompleteness === "complete" ? "完整" : dataCompleteness === "partial" ? "部分缺失" : "严重缺失"}
            </span>
          )}
        </div>

        {/* 报告正文（清洗后） */}
        {markdownText ? (
          <div className="p-5 bg-[#fffcf2] rounded-lg border border-[#ccc5b9]/20">
            <h4 className="text-[15px] font-semibold text-[#403d39] mb-3">
              {isSummary ? "完整投资报告" : "分析报告"}
            </h4>
            <div className="text-[16px] text-[#252422] leading-relaxed tracking-wide">
              <FormattedMarkdown text={markdownText} />
            </div>
          </div>
        ) : (
          <div className="p-4 bg-[#fffcf2] rounded-lg border border-[#ccc5b9]/20">
            <p className="text-[16px] text-[#403d39]/60">分析结果尚未生成或数据不可用</p>
          </div>
        )}

        {/* 指标明细（如果有 JSON 结构化数据） */}
        {innerData && !isSummary && (innerData as any).key_metrics && (
          <div className="mt-4 p-4 bg-white border border-[#ccc5b9]/20 rounded-lg">
            <h4 className="text-[14px] font-semibold text-[#252422] uppercase tracking-wider mb-3">关键指标</h4>
            <div className="grid grid-cols-2 gap-x-6 gap-y-2">
              {Object.entries((innerData as any).key_metrics as Record<string, unknown>).map(([k, v]) => (
                <div key={k} className="flex justify-between text-[15px] items-baseline">
                  <span className="text-[#252422] font-serif font-semibold" style={{ fontFamily: '"Noto Serif SC", SimSun, serif' }}>
                    {formatMetricKey(k)}
                  </span>
                  <span className="font-tech font-medium text-[#252422]" style={{ fontFamily: '"Space Grotesk", "Times New Roman", monospace' }}>
                    {String(v ?? "--")}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================================
// FormattedMarkdown — 纯文本报告渲染（不引入额外依赖）
// 支持：中文编号标题（一、二、三...）、Markdown表格、列表、段落
// 所有 Markdown 格式符号已在后端清洗，此处做前端兜底处理
// ============================================================
function FormattedMarkdown({ text }: { text: string }) {
  if (!text) return null;

  // 预处理：兜底清洗残留的 Markdown 符号
  let cleanText = text;
  // 去除水平分隔线
  cleanText = cleanText.replace(/^[\-*_]{3,}\s*$/gm, "");
  // 去除残留的 Markdown 标题标记符（保留标题文字，包含 #### 四级标题）
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
        <h2 key={i} className="text-[21px] font-bold text-[#252422] mt-6 mb-3 font-serif leading-tight">
          {line.trim()}
        </h2>
      );
      i++; continue;
    }

    // 数字子编号标题：1.1 XXX / 3.2 XXX（二级标题，兼容 #### 清洗后的编号，仿宋）
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
        // 开始收集所有表格行
        const tableRows: string[][] = [cells];
        let j = i + 2; // skip separator line
        while (j < lines.length && lines[j].startsWith("|") && lines[j].endsWith("|")) {
          const rowCells = lines[j].split("|").filter(c => c.trim()).map(c => c.trim());
          if (rowCells.length > 0) tableRows.push(rowCells);
          j++;
        }
        // 最大列数
        const colCount = Math.max(...tableRows.map(r => r.length));
        elements.push(
          <div key={i} className="my-2 overflow-x-auto">
            <table className="w-full border-collapse text-[15px]">
              <thead>
                <tr>
                  {tableRows[0].map((c, ci) => (
                    <th key={ci} className="text-left px-3 py-1.5 bg-[#ccc5b9]/10 text-[#403d39]/80 font-semibold border-b border-[#ccc5b9]/30 whitespace-nowrap">
                      {c}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {tableRows.slice(1).map((row, ri) => (
                  <tr key={ri} className="border-b border-[#ccc5b9]/10">
                    {Array.from({ length: colCount }).map((_, ci) => (
                      <td key={ci} className="px-3 py-1.5 text-[#403d39] text-[15px] whitespace-normal break-words">
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
      // 独立的表格行（没有 header 分隔线的情况，当做普通行）
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
        <li key={i} className="text-[15px] text-[#403d39] ml-4 leading-relaxed tracking-wide">
          {line.replace(/^[\s]*[-*]\s+/, "")}
        </li>
      );
      i++; continue;
    }

    // "标题："或"标题:"结尾的行（小标题/字段行）
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
          className="text-[15px] text-[#252422] mt-3 mb-1 leading-relaxed"
          style={{ fontFamily: '"FangSong", "仿宋", "STFangsong", serif', fontWeight: 700 }}
        >
          {line.trim()}
        </p>
      );
      i++; continue;
    }

    // 普通文本行
    if (line.trim()) {
      elements.push(
        <p key={i} className="text-[15px] text-[#403d39] leading-relaxed whitespace-pre-wrap tracking-wide">
          {line.trim()}
        </p>
      );
    }
    i++;
  }

  return <div>{elements.length > 0 ? elements : <p className="text-[16px] text-[#403d39] whitespace-pre-wrap tracking-wide">{text}</p>}</div>;
}

// ============================================================
// WarnModal — 安全护栏警告弹窗（非 A 股输入时显示）
// ============================================================
function WarnModal({
  open,
  message,
  onClose,
}: {
  open: boolean;
  message: string;
  onClose: () => void;
}) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/20" onClick={onClose}>
      <div
        className="bg-white rounded-2xl p-8 w-[440px] shadow-xl border border-[#ccc5b9]/40"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex flex-col items-center text-center">
          <div className="w-14 h-14 bg-amber-50 border border-amber-200 rounded-full flex items-center justify-center mb-5">
            <AlertTriangle className="w-7 h-7 text-amber-600" />
          </div>
          <h3 className="text-[18px] font-bold text-[#252422] mb-3">无法识别该股票</h3>
          <p className="text-[14px] text-[#403d39]/70 leading-relaxed mb-6">
            {message}
          </p>
          <button
            onClick={onClose}
            className="px-8 py-2.5 bg-[#252422] text-white rounded-lg text-[14px] font-medium hover:bg-[#403d39] transition-colors"
          >
            知道了
          </button>
        </div>
      </div>
    </div>
  );
}
