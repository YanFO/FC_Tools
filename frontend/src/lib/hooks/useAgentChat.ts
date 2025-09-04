/**
 * useAgentChat Hook
 * 管理 Agent 聊天功能，包括 session_id、訊息歷史、查詢提交等
 */

import { useState, useCallback, useRef } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { runAgent } from '../api';
import { ChatMessage, AgentRunRequest, AgentRunResponse, ApiError } from '../types';

interface UseAgentChatReturn {
  messages: ChatMessage[];
  send: (text: string) => Promise<void>;
  loading: boolean;
  error: string | null;
  sessionId: string;
  reset: () => void;
  clearError: () => void;
}

export function useAgentChat(): UseAgentChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const sessionIdRef = useRef<string>(uuidv4());

  const addMessage = useCallback((message: Omit<ChatMessage, 'id' | 'timestamp'>) => {
    const newMessage: ChatMessage = {
      ...message,
      id: uuidv4(),
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, newMessage]);
    return newMessage;
  }, []);

  const send = useCallback(async (text: string) => {
    if (!text.trim() || loading) return;

    setLoading(true);
    setError(null);

    // 添加用戶訊息
    addMessage({
      type: 'user',
      content: text.trim(),
    });

    try {
      // 準備請求
      const request: AgentRunRequest = {
        input_type: 'text',
        query: text.trim(),
        session_id: sessionIdRef.current,
        options: {
          lang: 'tw',
          include_sources: true,
          format: 'json',
        },
      };

      console.log('Sending agent request:', request);

      // 發送請求
      const response: AgentRunResponse = await runAgent(request);

      console.log('Agent response:', response);

      // 處理回應
      if (response.ok) {
        // 檢查是否有回應內容
        if (response.response && response.response.trim()) {
          addMessage({
            type: 'assistant',
            content: response.response,
            sources: response.sources,
            tool_results: response.tool_results,
          });
        }

        // 處理警告
        if (response.warnings && response.warnings.length > 0) {
          response.warnings.forEach(warning => {
            addMessage({
              type: 'warning',
              content: `警告: ${warning}`,
            });
          });
        }

        // 如果沒有回應內容但有警告，顯示警告氣泡
        if (!response.response?.trim() && response.warnings && response.warnings.length > 0) {
          addMessage({
            type: 'warning',
            content: response.warnings.join(', '),
          });
        }
      } else {
        // 處理 API 回傳的錯誤
        const errorMessage = response.error || '查詢處理失敗';
        addMessage({
          type: 'error',
          content: errorMessage,
        });
        setError(errorMessage);
      }
    } catch (err) {
      console.error('Agent chat error:', err);
      
      const apiError = err as ApiError;
      const errorMessage = apiError.message || '發送訊息時發生錯誤';
      
      addMessage({
        type: 'error',
        content: errorMessage,
      });
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [loading, addMessage]);

  const reset = useCallback(() => {
    setMessages([]);
    setError(null);
    setLoading(false);
    sessionIdRef.current = uuidv4();
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    messages,
    send,
    loading,
    error,
    sessionId: sessionIdRef.current,
    reset,
    clearError,
  };
}
