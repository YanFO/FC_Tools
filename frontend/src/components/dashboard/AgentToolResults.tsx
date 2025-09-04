/**
 * AgentToolResults 智能代理工具結果顯示組件
 * 顯示來自後端 Agent 工具調用的實時結果，包括結構化數據、圖表和格式化內容
 */

'use client';

import React, { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useAgentChat } from '@/lib/hooks/useAgentChat';
import { fmtDate, fmtCurrency, fmtNumber } from '@/lib/formatters';
import { Empty, MessageIcon } from '@/components/common/Empty';
import { Loading } from '@/components/common/Loading';

interface AgentToolResultsProps {
  className?: string;
}

interface ToolResult {
  id: string;
  type: string;
  title: string;
  data: any;
  timestamp: string;
  sources?: Array<{ source: string; timestamp?: string; tool?: string }>;
}

export function AgentToolResults({ className = '' }: AgentToolResultsProps) {
  const { messages, loading } = useAgentChat();
  const [toolResults, setToolResults] = useState<ToolResult[]>([]);

  // 從聊天訊息中提取工具結果
  useEffect(() => {
    const results: ToolResult[] = [];
    
    messages.forEach((message) => {
      if (message.type === 'assistant' && message.tool_results) {
        message.tool_results.forEach((toolResult, index) => {
          results.push({
            id: `${message.id}-${index}`,
            type: toolResult.tool || 'unknown',
            title: getToolResultTitle(toolResult),
            data: toolResult,
            timestamp: message.timestamp,
            sources: message.sources,
          });
        });
      }
    });

    setToolResults(results.reverse()); // 最新的在前面
  }, [messages]);

  // 根據工具結果類型生成標題
  const getToolResultTitle = (toolResult: any): string => {
    if (toolResult.tool === 'stock_price') {
      return `股票報價 - ${toolResult.symbol || '未知'}`;
    }
    if (toolResult.tool === 'news_search') {
      return `新聞搜尋 - ${toolResult.query || '未知'}`;
    }
    if (toolResult.tool === 'economic_data') {
      return `總經數據 - ${toolResult.indicator || '未知'}`;
    }
    if (toolResult.content) {
      return '分析結果';
    }
    return '工具結果';
  };

  // 渲染工具結果內容
  const renderToolResult = (result: ToolResult) => {
    const { data } = result;

    // 股票數據
    if (result.type === 'stock_price' && data.price) {
      return (
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <span className="text-sm text-muted-foreground">當前價格</span>
              <p className="text-lg font-semibold text-green-600">
                ${fmtNumber(data.price, { decimals: 2 })}
              </p>
            </div>
            <div>
              <span className="text-sm text-muted-foreground">變動</span>
              <p className={`text-lg font-semibold ${data.change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {data.change >= 0 ? '+' : ''}{fmtNumber(data.change, { decimals: 2 })}
                ({data.change_percent >= 0 ? '+' : ''}{fmtNumber(data.change_percent, { decimals: 2 })}%)
              </p>
            </div>
          </div>
          {data.volume && (
            <div>
              <span className="text-sm text-muted-foreground">成交量</span>
              <p className="text-sm">{fmtNumber(data.volume)}</p>
            </div>
          )}
        </div>
      );
    }

    // 新聞數據
    if (result.type === 'news_search' && data.articles) {
      return (
        <div className="space-y-3">
          {data.articles.slice(0, 5).map((article: any, index: number) => (
            <div key={index} className="border-l-2 border-primary/20 pl-3">
              <h4 className="text-sm font-medium line-clamp-2">{article.title}</h4>
              <p className="text-xs text-muted-foreground mt-1">
                {article.source} • {fmtDate(article.published_at, { includeTime: false })}
              </p>
              {article.summary && (
                <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                  {article.summary}
                </p>
              )}
            </div>
          ))}
        </div>
      );
    }

    // 總經數據
    if (result.type === 'economic_data' && data.data_points) {
      return (
        <div className="space-y-3">
          <div className="grid grid-cols-3 gap-2 text-xs">
            <span className="font-medium">日期</span>
            <span className="font-medium">數值</span>
            <span className="font-medium">變動</span>
          </div>
          {data.data_points.slice(0, 6).map((point: any, index: number) => (
            <div key={index} className="grid grid-cols-3 gap-2 text-sm">
              <span className="text-muted-foreground">
                {fmtDate(point.date, { includeTime: false })}
              </span>
              <span className="font-medium">{fmtNumber(point.value, { decimals: 2 })}</span>
              <span className={`text-xs ${point.change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {point.change >= 0 ? '+' : ''}{fmtNumber(point.change, { decimals: 2 })}%
              </span>
            </div>
          ))}
        </div>
      );
    }

    // 通用文本內容
    if (data.content || data.result) {
      return (
        <div className="prose prose-sm max-w-none">
          <p className="text-sm text-muted-foreground whitespace-pre-wrap">
            {data.content || data.result}
          </p>
        </div>
      );
    }

    // JSON 數據回退
    return (
      <div className="bg-muted/30 p-3 rounded-md">
        <pre className="text-xs text-muted-foreground overflow-x-auto">
          {JSON.stringify(data, null, 2)}
        </pre>
      </div>
    );
  };

  if (toolResults.length === 0 && !loading) {
    return (
      <Card className={`p-6 h-full flex items-center justify-center ${className}`}>
        <Empty
          icon={<MessageIcon />}
          title="等待分析結果"
          description="在右側聊天區域提出問題，分析結果將在此處顯示"
          action={
            <div className="mt-4 space-y-2">
              <p className="text-xs text-muted-foreground">您可以詢問：</p>
              <div className="flex flex-wrap gap-2">
                <Badge variant="outline" className="text-xs">AAPL 股價</Badge>
                <Badge variant="outline" className="text-xs">科技新聞</Badge>
                <Badge variant="outline" className="text-xs">美國 CPI</Badge>
              </div>
            </div>
          }
        />
      </Card>
    );
  }

  return (
    <Card className={`p-6 h-full flex flex-col ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">分析結果</h3>
        <Badge variant="secondary" className="text-xs">
          {toolResults.length} 個結果
        </Badge>
      </div>

      <ScrollArea className="flex-1">
        <div className="space-y-4">
          {loading && (
            <Card className="p-4">
              <Loading text="正在分析中..." size="sm" />
            </Card>
          )}

          {toolResults.map((result) => (
            <Card key={result.id} className="p-4">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <h4 className="text-sm font-medium">{result.title}</h4>
                  <p className="text-xs text-muted-foreground">
                    {fmtDate(result.timestamp)}
                  </p>
                </div>
                <Badge variant="outline" className="text-xs">
                  {result.type}
                </Badge>
              </div>

              {renderToolResult(result)}

              {result.sources && result.sources.length > 0 && (
                <div className="mt-3 pt-3 border-t">
                  <p className="text-xs text-muted-foreground mb-1">資料來源：</p>
                  <div className="space-y-1">
                    {result.sources.map((source, index) => (
                      <div key={index} className="text-xs text-muted-foreground">
                        {source.source} {source.tool && `(${source.tool})`}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </Card>
          ))}
        </div>
      </ScrollArea>
    </Card>
  );
}
