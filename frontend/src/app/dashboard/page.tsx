/**
 * Dashboard 主儀表板頁面
 * 包含 AgentToolResults 和 StreamingChat 的兩欄式佈局
 */

'use client';

import React from 'react';
import { AgentToolResults } from '@/components/dashboard/AgentToolResults';
import { AgentChat } from '@/components/chat/AgentChat';

export default function DashboardPage() {
  return (
    <div className="container mx-auto p-6 h-screen flex flex-col">
      {/* 頁面標題 */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-foreground">投資助理儀表板</h1>
        <p className="text-muted-foreground mt-2">
          與智能助理對話，獲取即時股票報價、新聞資訊和總經數據分析
        </p>
      </div>

      {/* 主要內容區域 */}
      <div className="flex-1 flex gap-6 min-h-0">
        {/* 左側工具結果顯示區域 (70%) */}
        <div className="flex-1 lg:w-[70%]">
          <AgentToolResults className="h-full" />
        </div>

        {/* 右側聊天區域 (30%) */}
        <div className="w-full lg:w-[30%] min-w-[320px]">
          <AgentChat className="h-full" />
        </div>
      </div>

      {/* 移動端佈局 */}
      <style jsx>{`
        @media (max-width: 1024px) {
          .container {
            flex-direction: column;
          }
          
          .flex {
            flex-direction: column;
          }
          
          .lg\\:w-\\[70\\%\\] {
            width: 100%;
            margin-bottom: 1.5rem;
          }
          
          .lg\\:w-\\[30\\%\\] {
            width: 100%;
            min-width: auto;
            height: 400px;
          }
        }
      `}</style>
    </div>
  );
}
