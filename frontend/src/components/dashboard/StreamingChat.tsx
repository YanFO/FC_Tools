/**
 * StreamingChat 流式聊天組件
 * 增強版的 AgentChat，支持實時流式響應和更好的用戶體驗
 */

'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { useAgentChat } from '@/lib/hooks/useAgentChat';
import { useClientOnly } from '@/lib/hooks/useClientOnly';
import { ChatMessage } from '@/lib/types';
import { fmtRelativeTime } from '@/lib/formatters';
import { ChatMessageSkeleton } from '@/components/common/Loading';
import { ErrorState } from '@/components/common/ErrorState';

interface StreamingChatProps {
  className?: string;
}

export function StreamingChat({ className = '' }: StreamingChatProps) {
  const {
    messages,
    loading,
    error,
    send,
    reset,
    clearError,
  } = useAgentChat();

  const isClient = useClientOnly();
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // 自動滾動到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  // 處理發送消息
  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const message = input.trim();
    setInput('');
    setIsStreaming(true);

    try {
      await send(message);
    } finally {
      setIsStreaming(false);
    }
  };

  // 處理鍵盤事件
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // 快速建議按鈕
  const suggestions = [
    { text: 'AAPL 最新股價', query: '/report stock AAPL' },
    { text: '科技新聞', query: 'AAPL 最新新聞 5 則' },
    { text: '美國 CPI 數據', query: '查詢美國 CPI 最近 6 期' },
    { text: 'NVDA vs AAPL', query: '/report stock NVDA,AAPL' },
  ];

  const handleSuggestionClick = (query: string) => {
    setInput(query);
    inputRef.current?.focus();
  };

  if (!isClient) {
    return (
      <Card className={`p-6 h-full flex items-center justify-center ${className}`}>
        <div className="text-center text-muted-foreground">
          <p>載入中...</p>
        </div>
      </Card>
    );
  }

  return (
    <Card className={`h-full flex flex-col ${className}`}>
      {/* 標題欄 */}
      <div className="flex items-center justify-between p-4 border-b">
        <div>
          <h3 className="font-semibold text-sm">智能投資助理</h3>
          {isStreaming && (
            <div className="flex items-center mt-1">
              <div className="flex space-x-1">
                <div className="w-1 h-1 bg-primary rounded-full animate-bounce"></div>
                <div className="w-1 h-1 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                <div className="w-1 h-1 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
              </div>
              <span className="text-xs text-muted-foreground ml-2">正在思考中...</span>
            </div>
          )}
        </div>
        <div className="flex items-center space-x-2">
          {messages.length > 0 && (
            <Badge variant="secondary" className="text-xs">
              {messages.length} 條對話
            </Badge>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={reset}
            className="text-xs"
            suppressHydrationWarning={true}
          >
            清除
          </Button>
        </div>
      </div>

      {/* 訊息歷史區域 */}
      <ScrollArea className="flex-1 p-4">
        <div className="space-y-4">
          {messages.length === 0 && !loading && (
            <div className="text-center text-muted-foreground text-sm py-8">
              <div className="mb-4">
                <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-primary/10 flex items-center justify-center">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-primary">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                  </svg>
                </div>
                <p className="mb-2 font-medium">歡迎使用智能投資助理！</p>
                <p className="text-xs">我可以幫您查詢股票報價、新聞資訊和總經數據</p>
              </div>
            </div>
          )}

          {messages.map((message) => (
            <div key={message.id} className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[80%] rounded-lg p-3 ${
                message.type === 'user'
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted text-muted-foreground'
              }`}>
                <div className="text-sm whitespace-pre-wrap">{message.content}</div>
                <div className="text-xs opacity-70 mt-1">
                  {fmtRelativeTime(message.timestamp)}
                </div>
              </div>
            </div>
          ))}

          {(loading || isStreaming) && (
            <div className="space-y-2">
              <ChatMessageSkeleton />
              {isStreaming && (
                <div className="flex items-center text-xs text-muted-foreground">
                  <div className="flex space-x-1 mr-2">
                    <div className="w-1 h-1 bg-muted-foreground rounded-full animate-pulse"></div>
                    <div className="w-1 h-1 bg-muted-foreground rounded-full animate-pulse" style={{ animationDelay: '0.2s' }}></div>
                    <div className="w-1 h-1 bg-muted-foreground rounded-full animate-pulse" style={{ animationDelay: '0.4s' }}></div>
                  </div>
                  <span>正在生成回應...</span>
                </div>
              )}
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>
      </ScrollArea>

      {/* 錯誤顯示 */}
      {error && (
        <div className="p-4 border-t">
          <ErrorState
            title="發送失敗"
            message={error}
            onRetry={clearError}
            retryText="關閉"
            variant="destructive"
            className="p-3"
          />
        </div>
      )}

      {/* 建議按鈕 */}
      {messages.length === 0 && !loading && !isStreaming && (
        <div className="p-4 border-t">
          <div className="space-y-3">
            <p className="text-xs text-muted-foreground">快速開始：</p>
            <div className="grid grid-cols-2 gap-2">
              {suggestions.map((suggestion, index) => (
                <Button
                  key={index}
                  variant="outline"
                  size="sm"
                  onClick={() => handleSuggestionClick(suggestion.query)}
                  className="text-xs h-8 justify-start"
                  suppressHydrationWarning={true}
                >
                  {suggestion.text}
                </Button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* 輸入區域 */}
      <div className="p-4 border-t">
        <div className="flex space-x-2">
          <Input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="輸入您的問題..."
            className="flex-1"
            disabled={loading || isStreaming}
            suppressHydrationWarning={true}
          />
          <Button
            onClick={handleSend}
            disabled={!input.trim() || loading || isStreaming}
            size="sm"
            className="px-4"
            suppressHydrationWarning={true}
          >
            {loading || isStreaming ? (
              <div className="flex items-center">
                <div className="w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin mr-1"></div>
                <span>發送中</span>
              </div>
            ) : (
              '發送'
            )}
          </Button>
        </div>

        {/* 連接狀態指示器 */}
        <div className="flex items-center justify-between mt-2">
          <div className="flex items-center text-xs text-muted-foreground">
            <div className={`w-2 h-2 rounded-full mr-2 ${error ? 'bg-red-500' : 'bg-green-500'}`}></div>
            <span>{error ? '連接異常' : '已連接'}</span>
          </div>
          
          {(loading || isStreaming) && (
            <div className="text-xs text-muted-foreground">
              <span>處理中...</span>
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}
