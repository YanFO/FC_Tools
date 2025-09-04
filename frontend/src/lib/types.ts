/**
 * 共享類型定義
 * 基於後端 API 結構定義的 TypeScript 類型
 */

// Agent 相關類型
export type AgentRunRequest = {
  input_type: "text";
  query: string;
  session_id?: string;
  options?: { 
    lang?: "tw" | "en"; 
    top_k?: number; 
    include_sources?: boolean; 
    format?: "json" | "markdown" | "plain";
  };
};

export type SourceInfo = {
  source: string;
  timestamp?: string;
  tool?: string;
};

export type NLGInfo = {
  raw?: string;
  colloquial?: string;
  system_prompt?: string;
};

export type AgentRunResponse = {
  ok: boolean;
  response?: string;
  input_type: string;
  tool_results?: Array<Record<string, any>>;
  sources?: SourceInfo[];
  warnings?: string[];
  error?: string;
  timestamp: string;
  trace_id?: string;
  nlg?: NLGInfo;
};

// 報告相關類型
export type ReportInfo = {
  name: string;
  path: string;             // For /api/reports/download?path=...
  size: number;
  generated_at: string;
  render_mode: "auto" | "overlay" | "acroform" | "unknown";
  watermark: string;
};

export type ReportListResponse = {
  ok: boolean;
  data: ReportInfo[];
  count: number;
  reason?: string | null;
  timestamp: string;
};

// 健康檢查類型
export type HealthCheckResponse = {
  ok: boolean;
  service: string;
  version: string;
  environment: string;
  timestamp: string;
  api_status: string;
};

// 客戶管理類型 (前端狀態管理)
export type Customer = {
  id: string;               // UUID v4 (frontend generated)
  lineId: string;
  name: string;
  phone?: string;
  annualIncome?: number;
  riskProfile?: "保守" | "平衡" | "積極";
  note?: string;
  createdAt: string;
  updatedAt: string;
};

// 聊天訊息類型
export type ChatMessage = {
  id: string;
  type: "user" | "assistant" | "system" | "error" | "warning";
  content: string;
  timestamp: string;
  sources?: SourceInfo[];
  tool_results?: Array<Record<string, any>>;
};

// API 錯誤類型
export type ApiError = {
  message: string;
  status?: number;
  code?: string;
  timestamp: string;
};

// 通用 API 回應類型
export type ApiResponse<T = any> = {
  ok: boolean;
  data?: T;
  error?: string;
  message?: string;
  timestamp: string;
};

// 表單狀態類型
export type FormState = "idle" | "loading" | "success" | "error";

// 標籤頁類型
export type TabType = "stock" | "news" | "economic" | "reports";

// 經濟指標類型
export type EconomicIndicator = "CPI" | "GDP" | "Unemployment" | "Interest Rate";
export type Country = "US" | "Japan" | "Taiwan" | "EU";

// 股票快捷鍵類型
export type StockShortcut = "AAPL" | "NVDA" | "TSLA";
