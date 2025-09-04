/**
 * useReports Hook
 * 管理報告列表和下載功能
 */

import { useState, useCallback, useEffect } from 'react';
import { getReportsList, buildReportDownloadUrl } from '../api';
import { ReportInfo, ReportListResponse, ApiError } from '../types';

interface UseReportsReturn {
  reports: ReportInfo[];
  loading: boolean;
  error: string | null;
  list: (limit?: number) => Promise<void>;
  buildDownloadUrl: (path: string) => string;
  refresh: () => Promise<void>;
  clearError: () => void;
}

export function useReports(autoLoad: boolean = true): UseReportsReturn {
  const [reports, setReports] = useState<ReportInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastLimit, setLastLimit] = useState<number>(20);

  const list = useCallback(async (limit: number = 20) => {
    setLoading(true);
    setError(null);
    setLastLimit(limit);

    try {
      console.log(`Fetching reports list with limit: ${limit}`);
      
      const response: ReportListResponse = await getReportsList(limit);
      
      console.log('Reports response:', response);

      if (response.ok) {
        setReports(response.data || []);
      } else {
        const errorMessage = response.reason || '取得報告列表失敗';
        setError(errorMessage);
        setReports([]);
      }
    } catch (err) {
      console.error('Reports list error:', err);
      
      const apiError = err as ApiError;
      const errorMessage = apiError.message || '取得報告列表時發生錯誤';
      setError(errorMessage);
      setReports([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const buildDownloadUrl = useCallback((path: string): string => {
    return buildReportDownloadUrl(path);
  }, []);

  const refresh = useCallback(async () => {
    await list(lastLimit);
  }, [list, lastLimit]);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  // 自動載入報告列表
  useEffect(() => {
    if (autoLoad) {
      list();
    }
  }, [autoLoad, list]);

  return {
    reports,
    loading,
    error,
    list,
    buildDownloadUrl,
    refresh,
    clearError,
  };
}
