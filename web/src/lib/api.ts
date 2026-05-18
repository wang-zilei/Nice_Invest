// API 调用层 — 与 FastAPI 后端通信

const API_BASE = "";

// ============================================================
// 客户端输出清洗（兜底，服务器端已做一次清洗）
// ============================================================
export function cleanAnalysisText(text: string): string {
  if (!text) return text;
  let cleaned = text;
  // 去除 DeepSeek 思考标签
  cleaned = cleaned.replace(/思考[\s\S]*?思考/g, '');
  cleaned = cleaned.replace(/响应[\s\S]*?响应/g, '');
  // 去除常见过渡/思考句式开头的行
  const patterns = [
    /^好的[，,].*$/m, /^现在我来.*$/m, /^下面给出.*$/m, /^让我.*$/m,
    /^我手动.*$/m, /^看起来.*$/m, /^根据获取.*$/m, /^首先[，,].*$/m,
    /^接下来.*$/m, /^最后[，,].*$/m, /^基于以上.*$/m, /^我们已经.*$/m,
    /^让我先.*$/m, /^综合来看.*$/m,
  ];
  for (const p of patterns) {
    cleaned = cleaned.replace(p, '');
  }
  // 去除 Markdown 水平分隔线
  cleaned = cleaned.replace(/^[\-*_]{3,}\s*$/gm, '');
  // 去除残留的 Markdown 标题标记符（保留标题文字）
  cleaned = cleaned.replace(/^####\s+/gm, '');
  cleaned = cleaned.replace(/^###\s+/gm, '');
  cleaned = cleaned.replace(/^##\s+/gm, '');
  cleaned = cleaned.replace(/^#\s+/gm, '');
  // 去除粗体/斜体标记（保留内部文字）
  cleaned = cleaned.replace(/\*\*(.+?)\*\*/g, '$1');
  cleaned = cleaned.replace(/__(.+?)__/g, '$1');
  cleaned = cleaned.replace(/\*(.+?)\*/g, '$1');

  // 清理多余空行
  cleaned = cleaned.replace(/\n{4,}/g, '\n\n\n');
  cleaned = cleaned.replace(/^\n+/, '');
  return cleaned.trim();
}

/**
 * 从分析文本中提取 JSON 数据块（客户端兜底解析）
 */
export function parseJsonFromText(text: string): Record<string, unknown> | null {
  if (!text) return null;
  const jsonMatch = text.match(/```json\s*\n([\s\S]*?)\n```/);
  if (jsonMatch) {
    try { return JSON.parse(jsonMatch[1]); } catch { /* ignore */ }
  }
  // 兜底：找裸 JSON 对象
  const start = text.indexOf('{');
  const end = text.lastIndexOf('}');
  if (start >= 0 && end > start) {
    try { return JSON.parse(text.slice(start, end + 1)); } catch { /* ignore */ }
  }
  return null;
}

// ============================================================
// Auth 相关类型
// ============================================================
export interface SendCodeResponse {
  ok: boolean;
  message: string;
  fallback?: boolean;
  dev_code?: string;
}

export interface VerifyCodeResponse {
  ok: boolean;
  session_token: string;
  email: string;
}

export interface SessionCheckResponse {
  valid: boolean;
  reason?: string;
  email?: string;
  is_guest?: boolean;
}

export interface UsageResponse {
  email: string;
  is_guest?: boolean;
}

// ============================================================
// Auth API
// ============================================================
export async function sendVerificationCode(email: string): Promise<SendCodeResponse> {
  const res = await fetch(`${API_BASE}/api/auth/send-code`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: "发送失败" }));
    throw new Error((detail as any).detail || "发送失败");
  }
  return res.json();
}

export async function verifyCode(email: string, code: string): Promise<VerifyCodeResponse> {
  const res = await fetch(`${API_BASE}/api/auth/verify-code`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, code }),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: "验证码错误或已过期" }));
    throw new Error((detail as any).detail || "验证失败");
  }
  return res.json();
}

export async function checkSession(token: string): Promise<SessionCheckResponse> {
  const res = await fetch(`${API_BASE}/api/auth/session`, {
    headers: { "X-Session-Token": token },
  });
  if (!res.ok) return { valid: false };
  return res.json();
}

export async function getUsage(token: string): Promise<UsageResponse> {
  const res = await fetch(`${API_BASE}/api/auth/usage`, {
    headers: { "X-Session-Token": token },
  });
  if (!res.ok) throw new Error("获取用量信息失败");
  return res.json();
}

export function getSessionToken(): string | null {
  try {
    const raw = localStorage.getItem("nice_invest_session");
    if (!raw) return null;
    const data = JSON.parse(raw);
    return data.session_token || null;
  } catch {
    return null;
  }
}

export function getSessionEmail(): string | null {
  try {
    const raw = localStorage.getItem("nice_invest_session");
    if (!raw) return null;
    const data = JSON.parse(raw);
    return data.email || null;
  } catch {
    return null;
  }
}

export function clearSession() {
  localStorage.removeItem("nice_invest_session");
}

const COMMON_STOCKS: StockMatch[] = [
  { ts_code: "000001.SZ", name: "平安银行", industry: "银行" },
  { ts_code: "600519.SH", name: "贵州茅台", industry: "白酒" },
  { ts_code: "000858.SZ", name: "五粮液", industry: "白酒" },
  { ts_code: "600036.SH", name: "招商银行", industry: "银行" },
  { ts_code: "000333.SZ", name: "美的集团", industry: "家电" },
  { ts_code: "002415.SZ", name: "海康威视", industry: "安防" },
  { ts_code: "600900.SH", name: "长江电力", industry: "电力" },
  { ts_code: "000651.SZ", name: "格力电器", industry: "家电" },
  { ts_code: "002594.SZ", name: "比亚迪", industry: "汽车" },
  { ts_code: "601318.SH", name: "中国平安", industry: "保险" },
  { ts_code: "600276.SH", name: "恒瑞医药", industry: "医药" },
  { ts_code: "000568.SZ", name: "泸州老窖", industry: "白酒" },
  { ts_code: "601899.SH", name: "紫金矿业", industry: "矿业" },
  { ts_code: "300750.SZ", name: "宁德时代", industry: "电池" },
  { ts_code: "600030.SH", name: "中信证券", industry: "证券" },
  { ts_code: "000002.SZ", name: "万科A", industry: "房地产" },
  { ts_code: "600585.SH", name: "海螺水泥", industry: "建材" },
  { ts_code: "601166.SH", name: "兴业银行", industry: "银行" },
  { ts_code: "000063.SZ", name: "中兴通讯", industry: "通信" },
  { ts_code: "002475.SZ", name: "立讯精密", industry: "电子" },
];

/**
 * 根据股票代码查找名称（本地兜底）
 */
export function lookupStockName(code: string): string {
  if (!code) return "";
  const match = COMMON_STOCKS.find(s => s.ts_code === code);
  return match?.name || "";
}

/**
 * 安全获取股票显示名称（名称 + 代码），确保代码不替代名称
 */
export function stockDisplayName(name: string, code: string): { name: string; code: string } {
  const resolvedName = name && name !== code ? name : lookupStockName(code) || code;
  return { name: resolvedName, code };
}

function fallbackSearch(keyword: string): StockMatch[] {
  const kw = keyword.trim().toLowerCase();
  if (!kw) return [];
  return COMMON_STOCKS.filter(
    (s) => s.ts_code.toLowerCase().includes(kw) || s.name.includes(keyword.trim())
  )
    .sort((a, b) => {
      const aCode = a.ts_code.toLowerCase().startsWith(kw) ? 0 : 1;
      const bCode = b.ts_code.toLowerCase().startsWith(kw) ? 0 : 1;
      return aCode - bCode || a.ts_code.length - b.ts_code.length;
    })
    .slice(0, 5);
}

// ============================================================
// Types
// ============================================================
export interface StockMatch {
  ts_code: string;
  name: string;
  industry: string;
}

export interface SearchResult {
  matches: StockMatch[];
}

export interface LLMConfig {
  model?: string;
  api_key?: string;
  base_url?: string;
}

export interface AgentTask {
  id: string;
  name: string;
  description: string;
  shortDesc: string;
  icon: string;
  status: "pending" | "analyzing" | "completed" | "error";
  progress: number;
  message: string;
  preview?: string;
  analysis?: string;
  jsonData?: Record<string, unknown>;
  confidence?: number;
}

export interface AnalysisData {
  analysisId: string;
  symbol: string;
  name: string;
  estimatedTime: string;
  totalProgress: number;
  agents: AgentTask[];
  reportAgent: AgentTask;
}

export interface ReportData {
  meta: { stock_code: string; stock_name: string; analysis_time: string };
  verdict: {
    direction: string;
    confidence: string;
    weighted_score: number;
    recommendation_level: string;
  };
  scores: {
    fundamental: number;
    technical: number;
    valuation: number;
    news: number;
    weighted_total: number;
  };
  cross_analysis: Array<{
    agent_pair: string;
    consistent: boolean;
    detail: string;
  }>;
  scenarios: {
    bull: { trigger: string; expected_return: string };
    base: { description: string };
    bear: { trigger: string; downside_risk: string };
  };
  risks: Array<{
    description: string;
    impact: string;
    probability: string;
    mitigation: string;
  }>;
}

export interface HistoryEntry {
  id: string;
  stock_code: string;
  stock_name: string;
  analysis_type: string;
  verdict: string;
  elapsed: number;
  created_at: string;
}

export interface HistoryDetail {
  found: boolean;
  record: {
    id: string;
    stock_code: string;
    stock_name: string;
    analysis_type: string;
    verdict: string;
    elapsed: number;
    created_at: string;
    agent_results: Array<{
      agent_name: string;
      analysis: string;
      confidence: number;
    }>;
    summary_text: string;
    summary_json: ReportData | null;
  } | null;
}

// ============================================================
// API 函数
// ============================================================
export async function searchStocks(keyword: string): Promise<StockMatch[]> {
  const localMatches = fallbackSearch(keyword);
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), 2500);

  try {
    const res = await fetch(`${API_BASE}/api/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ keyword }),
      signal: controller.signal,
    });
    if (!res.ok) return localMatches;
    const data: SearchResult = await res.json();
    return data.matches?.length ? data.matches : localMatches;
  } catch {
    return localMatches;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

export async function getHistory(limit = 20): Promise<HistoryEntry[]> {
  const res = await fetch(`${API_BASE}/api/history?limit=${limit}`);
  if (!res.ok) return [];
  const data = await res.json();
  return data.history;
}

export async function getHistoryDetail(analysisId: string): Promise<HistoryDetail | null> {
  const res = await fetch(`${API_BASE}/api/history/${analysisId}`);
  if (!res.ok) return null;
  return res.json();
}

export async function validateConfig(config: {
  model?: string;
  api_key?: string;
  base_url?: string;
}): Promise<Record<string, string>> {
  const res = await fetch(`${API_BASE}/api/config/validate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  });
  if (!res.ok) return {};
  const data = await res.json();
  return data.results;
}

// ============================================================
// A 股安全护栏：校验用户输入是否为有效 A 股公司
// ============================================================
export interface ValidateStockResponse {
  valid: boolean;
  ts_code?: string;
  name?: string;
  source?: string;      // "registry" | "llm"
  message?: string;     // 校验失败时的提示信息
}

export async function validateStockInput(input: string): Promise<ValidateStockResponse> {
  const res = await fetch(`${API_BASE}/api/validate-stock`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ input }),
  });
  if (!res.ok) {
    return { valid: false, message: "校验服务异常，请稍后重试" };
  }
  return res.json();
}

// ============================================================
// SSE 分析（核心）
// ============================================================
export interface SSEEvent {
  event: string;
  data: Record<string, unknown>;
}

const SSE_TIMEOUT = 330_000; // 整体超时 330 秒（后端整体 300s + 30s 余量）

export function analyzeStock(
  stockCode: string,
  stockName: string,
  analysisType: string,
  llmConfig: LLMConfig,
  onEvent: (event: SSEEvent) => void,
  onError: (error: string) => void,
  onDone: () => void
): AbortController {
  const controller = new AbortController();

  // 整体超时兜底：超过 SSE_TIMEOUT 自动中断
  const timeoutId = window.setTimeout(() => {
    controller.abort();
    onError("分析超时（超过 5 分钟），已自动取消。请检查 API Key 是否正确配置、网络连接是否正常。");
  }, SSE_TIMEOUT);

  fetch(`${API_BASE}/api/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      stock_code: stockCode,
      stock_name: stockName,
      analysis_type: analysisType,
      llm_config: llmConfig,
      session_token: getSessionToken() || "",
    }),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        const errorText = await response.text().catch(() => "");
        onError(`服务器错误 (HTTP ${response.status})${errorText ? ": " + errorText : ""}`);
        return;
      }
      const reader = response.body?.getReader();
      if (!reader) {
        onError("无法读取响应流");
        return;
      }

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        let currentEvent = "";
        for (const line of lines) {
          if (line.startsWith("event: ")) {
            currentEvent = line.slice(7).trim();
          } else if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6));
              onEvent({ event: currentEvent, data });
            } catch {
              // 忽略解析失败的行
            }
          }
        }
      }
    })
    .catch((err) => {
      if (err.name !== "AbortError") {
        onError(err.message);
      }
    })
    .finally(() => {
      window.clearTimeout(timeoutId);
      onDone();
    });

  return controller;
}

// ============================================================
// 辅助：创建初始分析数据
// ============================================================
const AGENT_CONFIG: Record<string, { name: string; description: string; icon: string }> = {
  fundamental: {
    name: "1. 基本面分析",
    description: "扫描财务报表，分析盈利能力、偿债能力、运营效率和成长性，评估公司内在价值与竞争优势。",
    icon: "FileText",
  },
  technical: {
    name: "2. 技术面分析",
    description: "分析价格趋势、交易量、技术指标和图表形态，识别市场趋势与关键支撑阻力位。",
    icon: "TrendingUp",
  },
  valuation: {
    name: "3. 估值分析",
    description: "运行估值模型，对比行业与历史数据，评估当前价格的合理性与安全边际。",
    icon: "PieChart",
  },
  news: {
    name: "4. 新闻与市场情绪",
    description: "扫描新闻资讯，分析市场情绪、舆论趋势和事件影响，捕捉潜在风险与机会。",
    icon: "Radio",
  },
};

export function createInitialAnalysis(
  stockCode: string,
  stockName: string
): AnalysisData {
  const reportAgent: AgentTask = {
    id: "agent_summary",
    name: "投资决策引擎",
    description: "系统将自动整合所有分析结果，生成专业投资报告与操作建议。",
    shortDesc: "等待各节点数据流输入...",
    icon: "BrainCircuit",
    status: "pending",
    progress: 0,
    message: "等待前置节点完成",
  };

  const agents: AgentTask[] = Object.entries(AGENT_CONFIG).map(([key, cfg]) => ({
    id: `agent_${key}`,
    name: cfg.name,
    description: cfg.description,
    shortDesc: "等待分析启动...",
    icon: cfg.icon,
    status: "pending" as AgentTask["status"],
    progress: 0,
    message: "",
  }));

  return {
    analysisId: "",
    symbol: stockCode,
    name: stockName,
    estimatedTime: "--:--",
    totalProgress: 0,
    agents,
    reportAgent,
  };
}
