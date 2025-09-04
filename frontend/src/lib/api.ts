/**
 * API 包裝器
 * 統一處理 API 請求、錯誤處理和健康檢查
 */

import { 
  AgentRunRequest, 
  AgentRunResponse, 
  ReportListResponse, 
  HealthCheckResponse,
  ApiError 
} from './types';

// 從環境變數取得 API 基礎 URL
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

/**
 * 建立完整的 API URL
 */
function buildApiUrl(path: string): string {
  // 確保路徑以 / 開頭
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${API_BASE_URL}${normalizedPath}`;
}

/**
 * 通用錯誤處理
 */
function handleApiError(error: any, context: string): ApiError {
  const timestamp = new Date().toISOString();
  
  if (error instanceof TypeError && error.message.includes('fetch')) {
    return {
      message: '無法連接到後端服務，請檢查服務是否正常運行',
      code: 'NETWORK_ERROR',
      timestamp
    };
  }
  
  if (error.status) {
    return {
      message: error.message || `API 請求失敗 (${error.status})`,
      status: error.status,
      code: 'HTTP_ERROR',
      timestamp
    };
  }
  
  return {
    message: error.message || `${context} 時發生未知錯誤`,
    code: 'UNKNOWN_ERROR',
    timestamp
  };
}

/**
 * 通用 GET 請求
 */
export async function apiGet<T = any>(path: string): Promise<T> {
  try {
    const url = buildApiUrl(path);
    console.log(`API GET: ${url}`);
    
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    if (!response.ok) {
      throw {
        status: response.status,
        message: `HTTP ${response.status}: ${response.statusText}`
      };
    }
    
    const data = await response.json();
    return data;
  } catch (error) {
    console.error(`API GET Error (${path}):`, error);
    throw handleApiError(error, `GET ${path}`);
  }
}

/**
 * 通用 POST 請求
 */
export async function apiPost<T = any>(path: string, body: any): Promise<T> {
  try {
    const url = buildApiUrl(path);
    console.log(`API POST: ${url}`, body);
    
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });
    
    if (!response.ok) {
      throw {
        status: response.status,
        message: `HTTP ${response.status}: ${response.statusText}`
      };
    }
    
    const data = await response.json();
    return data;
  } catch (error) {
    console.error(`API POST Error (${path}):`, error);
    throw handleApiError(error, `POST ${path}`);
  }
}

/**
 * 健康檢查
 */
export async function healthCheck(): Promise<HealthCheckResponse> {
  return apiGet<HealthCheckResponse>('/health');
}

/**
 * 執行 Agent 查詢
 */
export async function runAgent(request: AgentRunRequest): Promise<AgentRunResponse> {
  return apiPost<AgentRunResponse>('/api/agent/run', request);
}

/**
 * 取得報告列表
 */
export async function getReportsList(limit: number = 20): Promise<ReportListResponse> {
  return apiGet<ReportListResponse>(`/api/reports/list?limit=${limit}`);
}

/**
 * 建立報告下載 URL
 */
export function buildReportDownloadUrl(path: string): string {
  const encodedPath = encodeURIComponent(path);
  return buildApiUrl(`/api/reports/download?path=${encodedPath}`);
}

/**
 * 檢查後端服務狀態
 */
export async function checkBackendStatus(): Promise<{ available: boolean; error?: string }> {
  try {
    const health = await healthCheck();
    return { 
      available: health.ok,
      error: health.ok ? undefined : '後端服務回報異常狀態'
    };
  } catch (error) {
    const apiError = error as ApiError;
    return { 
      available: false, 
      error: apiError.message 
    };
  }
}

/**
 * API 客戶端類別 (可選的物件導向介面)
 */
export class ApiClient {
  private baseUrl: string;
  
  constructor(baseUrl?: string) {
    this.baseUrl = baseUrl || API_BASE_URL;
  }
  
  async get<T>(path: string): Promise<T> {
    return apiGet<T>(path);
  }
  
  async post<T>(path: string, body: any): Promise<T> {
    return apiPost<T>(path, body);
  }
  
  async health(): Promise<HealthCheckResponse> {
    return healthCheck();
  }
  
  async agent(request: AgentRunRequest): Promise<AgentRunResponse> {
    return runAgent(request);
  }
  
  async reports(limit?: number): Promise<ReportListResponse> {
    return getReportsList(limit);
  }
  
  downloadUrl(path: string): string {
    return buildReportDownloadUrl(path);
  }
}

// 預設 API 客戶端實例
export const api = new ApiClient();
