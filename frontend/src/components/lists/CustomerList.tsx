/**
 * CustomerList 客戶列表組件
 * 顯示客戶列表，支援點擊編輯、刪除等操作
 */

'use client';

import React, { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { useCustomers } from '@/lib/hooks/useCustomers';
import { useClientOnly } from '@/lib/hooks/useClientOnly';
import { Customer } from '@/lib/types';
import { fmtDate, fmtCurrency, fmtPhone, fmtLineId } from '@/lib/formatters';
import { Empty, UsersIcon } from '@/components/common/Empty';
import { ErrorState } from '@/components/common/ErrorState';
import { Loading } from '@/components/common/Loading';

interface CustomerListProps {
  onCustomerSelect?: (customer: Customer) => void;
  selectedCustomer?: Customer | null;
  className?: string;
}

export function CustomerList({ 
  onCustomerSelect, 
  selectedCustomer,
  className = '' 
}: CustomerListProps) {
  const { customers, loading, error, remove, clearError } = useCustomers();
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const isClient = useClientOnly();

  // 處理客戶選擇
  const handleCustomerClick = (customer: Customer) => {
    onCustomerSelect?.(customer);
  };

  // 處理刪除客戶
  const handleDelete = async (customer: Customer, e: React.MouseEvent) => {
    e.stopPropagation(); // 防止觸發行點擊事件
    
    if (!confirm(`確定要刪除客戶「${customer.name}」嗎？此操作無法復原。`)) {
      return;
    }

    setDeletingId(customer.id);
    
    try {
      const success = remove(customer.id);
      if (success && selectedCustomer?.id === customer.id) {
        // 如果刪除的是當前選中的客戶，清除選擇
        onCustomerSelect?.(null as any);
      }
    } catch (err) {
      console.error('Delete customer error:', err);
    } finally {
      setDeletingId(null);
    }
  };

  // 取得風險偏好的顯示樣式
  const getRiskProfileBadge = (riskProfile?: string) => {
    if (!riskProfile) return null;
    
    const variants = {
      '保守': 'secondary' as const,
      '平衡': 'default' as const,
      '積極': 'destructive' as const,
    };
    
    return (
      <Badge variant={variants[riskProfile as keyof typeof variants] || 'outline'}>
        {riskProfile}
      </Badge>
    );
  };

  if (loading) {
    return (
      <Card className={`p-6 ${className}`}>
        <h3 className="text-lg font-semibold mb-4">客戶列表</h3>
        <Loading text="載入客戶資料中..." />
      </Card>
    );
  }

  if (error) {
    return (
      <Card className={`p-6 ${className}`}>
        <h3 className="text-lg font-semibold mb-4">客戶列表</h3>
        <ErrorState
          title="載入失敗"
          message={error}
          onRetry={clearError}
          retryText="重試"
        />
      </Card>
    );
  }

  if (customers.length === 0) {
    return (
      <Card className={`p-6 ${className}`}>
        <h3 className="text-lg font-semibold mb-4">客戶列表</h3>
        <Empty
          icon={<UsersIcon />}
          title="暫無客戶資料"
          description="尚未新增任何客戶，請使用上方表單新增客戶資料"
        />
      </Card>
    );
  }

  return (
    <Card className={`p-6 ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold">客戶列表</h3>
          <p className="text-sm text-muted-foreground">
            共 {customers.length} 位客戶
          </p>
        </div>
      </div>

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>姓名</TableHead>
              <TableHead>LINE ID</TableHead>
              <TableHead>電話</TableHead>
              <TableHead>風險偏好</TableHead>
              <TableHead>年收入</TableHead>
              <TableHead>建立時間</TableHead>
              <TableHead className="text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {customers.map((customer) => (
              <TableRow
                key={customer.id}
                className={`cursor-pointer hover:bg-muted/50 ${
                  selectedCustomer?.id === customer.id ? 'bg-muted' : ''
                }`}
                onClick={() => handleCustomerClick(customer)}
              >
                <TableCell className="font-medium">
                  {customer.name}
                </TableCell>
                <TableCell>
                  <code className="text-xs bg-muted px-2 py-1 rounded">
                    {fmtLineId(customer.lineId)}
                  </code>
                </TableCell>
                <TableCell>
                  {customer.phone ? (
                    <span className="text-sm">{fmtPhone(customer.phone)}</span>
                  ) : (
                    <span className="text-sm text-muted-foreground">未提供</span>
                  )}
                </TableCell>
                <TableCell>
                  {getRiskProfileBadge(customer.riskProfile) || (
                    <span className="text-sm text-muted-foreground">未設定</span>
                  )}
                </TableCell>
                <TableCell>
                  {customer.annualIncome ? (
                    <span className="text-sm">
                      {fmtCurrency(customer.annualIncome)}
                    </span>
                  ) : (
                    <span className="text-sm text-muted-foreground">未提供</span>
                  )}
                </TableCell>
                <TableCell>
                  <span className="text-sm text-muted-foreground">
                    {fmtDate(customer.createdAt, { includeTime: false })}
                  </span>
                </TableCell>
                <TableCell className="text-right">
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={(e) => handleDelete(customer, e)}
                    disabled={deletingId === customer.id}
                    className="text-xs"
                    suppressHydrationWarning={true}
                  >
                    {deletingId === customer.id ? '刪除中...' : '刪除'}
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>


    </Card>
  );
}
