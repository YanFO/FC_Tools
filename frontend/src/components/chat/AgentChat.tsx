/**
 * AgentChat 智能代理聊天組件
 * 右側固定的聊天介面，支援訊息歷史、輸入處理、載入狀態等
 */

'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useAgentChat } from '@/lib/hooks/useAgentChat';
import { useClientOnly } from '@/lib/hooks/useClientOnly';
import { checkBackendStatus } from '@/lib/api';
import { ChatMessage } from '@/lib/types';
import { fmtRelativeTime } from '@/lib/formatters';
import { InlineLoading, ChatMessageSkeleton } from '@/components/common/Loading';
import { ErrorState } from '@/components/common/ErrorState';

interface AgentChatProps {
  className?: string;
}

export function AgentChat({ className = '' }: AgentChatProps) {
  const { messages, send, loading, error, sessionId, reset, clearError } = useAgentChat();
  const [input, setInput] = useState('');
  const [backendStatus, setBackendStatus] = useState<{ available: boolean; error?: string } | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const isClient = useClientOnly();

  // 檢查後端狀態
  useEffect(() => {
    const checkStatus = async () => {
      try {
        const status = await checkBackendStatus();
        setBackendStatus(status);
      } catch (err) {
        setBackendStatus({ available: false, error: '無法檢查後端狀態' });
      }
    };

    checkStatus();
    // 每 30 秒檢查一次
    const interval = setInterval(checkStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  // 自動滾動到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // 處理發送訊息
  const handleSend = async () => {
    if (!input.trim() || loading) return;
    
    const message = input.trim();
    setInput('');
    
    try {
      await send(message);
      // 發送成功後聚焦輸入框
      setTimeout(() => inputRef.current?.focus(), 100);
    } catch (err) {
      console.error('Send message error:', err);
    }
  };

  // 處理按鍵事件
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // 建議按鈕點擊
  const handleSuggestionClick = (suggestion: string) => {
    setInput(suggestion);
    inputRef.current?.focus();
  };

  return (
    <Card className={`flex flex-col h-full ${className}`}>
      {/* 系統狀態標題 */}
      <div className="flex items-center justify-between p-4 border-b">
        <h3 className="font-semibold text-sm">智能助理</h3>
        <div className="flex items-center space-x-2">
          {backendStatus && (
            <Badge 
              variant={backendStatus.available ? 'default' : 'destructive'}
              className="text-xs"
            >
              {backendStatus.available ? '線上' : '離線'}
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
          {messages.length === 0 && (
            <div className="text-center text-muted-foreground text-sm py-8">
              <p className="mb-4">歡迎使用智能投資助理！</p>
              <p className="text-xs">您可以詢問股票報價、新聞、經濟數據等資訊</p>
            </div>
          )}

          {messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))}

          {loading && <ChatMessageSkeleton />}
          
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
            className="p-4"
          />
        </div>
      )}

      {/* 建議按鈕 */}
      {messages.length === 0 && !loading && (
        <div className="p-4 border-t">
          <div className="space-y-2">
            <p className="text-xs text-muted-foreground mb-2">快速開始：</p>
            <div className="flex flex-wrap gap-2">
              <SuggestionButton
                text="/report stock NVDA,AAPL"
                onClick={handleSuggestionClick}
              />
              <SuggestionButton
                text="查詢美國 CPI 最近 6 期"
                onClick={handleSuggestionClick}
              />
              <SuggestionButton
                text="AAPL 最新新聞 5 則"
                onClick={handleSuggestionClick}
              />
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
            placeholder={
              backendStatus?.available === false
                ? '後端服務不可用'
                : '輸入您的問題...'
            }
            disabled={loading || backendStatus?.available === false}
            className="flex-1"
            suppressHydrationWarning={true}
          />
          <Button
            onClick={handleSend}
            disabled={!input.trim() || loading || backendStatus?.available === false}
            size="sm"
            suppressHydrationWarning={true}
          >
            {loading ? <InlineLoading /> : '發送'}
          </Button>
        </div>
        
        {backendStatus?.available === false && (
          <p className="text-xs text-destructive mt-2">
            {backendStatus.error || '後端服務暫時不可用'}
          </p>
        )}
      </div>
    </Card>
  );
}

// 訊息氣泡組件
function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.type === 'user';
  const isError = message.type === 'error';
  const isWarning = message.type === 'warning';
  const isSystem = message.type === 'system';

  const getBubbleStyles = () => {
    if (isUser) {
      return 'bg-primary text-primary-foreground ml-auto max-w-xs';
    }
    if (isError) {
      return 'bg-destructive/10 text-destructive border border-destructive/20 max-w-md';
    }
    if (isWarning) {
      return 'bg-yellow-50 text-yellow-800 border border-yellow-200 max-w-md';
    }
    if (isSystem) {
      return 'bg-muted text-muted-foreground text-center max-w-md mx-auto';
    }
    return 'bg-muted text-foreground max-w-md';
  };

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`rounded-lg p-3 ${getBubbleStyles()}`}>
        <div className="text-sm whitespace-pre-wrap">
          {message.content}
        </div>
        
        {/* 資料來源 */}
        {message.sources && message.sources.length > 0 && (
          <div className="mt-2 pt-2 border-t border-current/20">
            <p className="text-xs opacity-70 mb-1">資料來源：</p>
            <div className="space-y-1">
              {message.sources.map((source, index) => (
                <div key={index} className="text-xs opacity-70">
                  {source.source} {source.tool && `(${source.tool})`}
                </div>
              ))}
            </div>
          </div>
        )}
        
        {/* 時間戳 */}
        <div className="text-xs opacity-50 mt-1">
          {fmtRelativeTime(message.timestamp)}
        </div>
      </div>
    </div>
  );
}

// 建議按鈕組件
function SuggestionButton({
  text,
  onClick
}: {
  text: string;
  onClick: (text: string) => void;
}) {
  return (
    <Button
      variant="outline"
      size="sm"
      onClick={() => onClick(text)}
      className="text-xs h-7"
      suppressHydrationWarning={true}
    >
      {text}
    </Button>
  );
}
