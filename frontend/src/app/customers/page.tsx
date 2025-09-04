/**
 * Customers 客戶管理頁面
 * 包含客戶表單、客戶列表和聊天功能的三欄式佈局
 */

'use client';

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { CustomerModal } from '@/components/forms/CustomerModal';
import { CustomerDetails } from '@/components/forms/CustomerDetails';
import { CustomerList } from '@/components/lists/CustomerList';
import { AgentChat } from '@/components/chat/AgentChat';
import { Customer } from '@/lib/types';

export default function CustomersPage() {
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null);

  // 處理客戶選擇
  const handleCustomerSelect = (customer: Customer | null) => {
    setSelectedCustomer(customer);
  };

  // 處理客戶新增成功
  const handleCustomerCreated = (customer: Customer) => {
    setSelectedCustomer(customer);
  };

  // 處理客戶更新成功
  const handleCustomerUpdate = (customer: Customer) => {
    setSelectedCustomer(customer);
  };

  return (
    <div className="container mx-auto p-6 h-screen flex flex-col">
      {/* 頁面標題 */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-foreground">LINE 客戶管理</h1>
        <p className="text-muted-foreground mt-2">
          管理 LINE 客戶資料，包含基本資訊、風險偏好和投資需求
        </p>
      </div>

      {/* 主要內容區域 */}
      <div className="flex-1 flex gap-6 min-h-0">
        {/* 左側客戶管理區域 (60%) */}
        <div className="flex-1 lg:w-[60%] flex flex-col gap-6">
          {/* 客戶列表 - 移到頂部 */}
          <div className="flex-1 min-h-0">
            <div className="h-full flex flex-col">
              {/* 新增客戶按鈕 */}
              <div className="mb-4">
                <CustomerModal onCustomerCreated={handleCustomerCreated}>
                  <Button className="w-full sm:w-auto" suppressHydrationWarning={true}>
                    + 新增客戶
                  </Button>
                </CustomerModal>
              </div>

              {/* 客戶列表 */}
              <div className="flex-1 min-h-0">
                <CustomerList
                  onCustomerSelect={handleCustomerSelect}
                  selectedCustomer={selectedCustomer}
                  className="h-full"
                />
              </div>
            </div>
          </div>

          {/* 選中客戶詳細資訊 - 移到中間 */}
          <div className="flex-shrink-0">
            <CustomerDetails
              customer={selectedCustomer}
              onCustomerUpdate={handleCustomerUpdate}
            />
          </div>
        </div>

        {/* 右側聊天區域 (40%) */}
        <div className="w-full lg:w-[40%] min-w-[320px]">
          <div className="h-full">
            <AgentChat className="h-full" />
          </div>
        </div>
      </div>

      {/* 移動端佈局樣式 */}
      <style jsx>{`
        @media (max-width: 1024px) {
          .container {
            padding: 1rem;
          }

          .flex {
            flex-direction: column;
          }

          .lg\\:w-\\[60\\%\\] {
            width: 100%;
            margin-bottom: 1.5rem;
          }

          .lg\\:w-\\[40\\%\\] {
            width: 100%;
            min-width: auto;
            height: 400px;
          }

          .flex-1.min-h-0 {
            min-height: 400px;
          }
        }

        @media (max-width: 768px) {
          .container {
            padding: 0.5rem;
          }

          .gap-6 {
            gap: 1rem;
          }

          .mb-6 {
            margin-bottom: 1rem;
          }

          h1 {
            font-size: 1.5rem;
          }

          .flex-1.min-h-0 {
            min-height: 300px;
          }
        }
      `}</style>
    </div>
  );
}
