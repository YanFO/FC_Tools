/**
 * CustomerDetails 客戶詳細資訊組件
 * 顯示選中客戶的詳細資訊，支援編輯功能
 */

'use client';

import React, { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { useCustomers } from '@/lib/hooks/useCustomers';
import { useClientOnly } from '@/lib/hooks/useClientOnly';
import { Customer } from '@/lib/types';
import { fmtDate, fmtCurrency, fmtPhone, fmtLineId } from '@/lib/formatters';

interface CustomerDetailsProps {
  customer: Customer | null;
  onCustomerUpdate?: (customer: Customer) => void;
  className?: string;
}

interface FormData {
  lineId: string;
  name: string;
  phone: string;
  annualIncome: string;
  riskProfile: string;
  note: string;
}

interface FormErrors {
  lineId?: string;
  name?: string;
  phone?: string;
  annualIncome?: string;
}

export function CustomerDetails({ 
  customer, 
  onCustomerUpdate,
  className = '' 
}: CustomerDetailsProps) {
  const { update, error: customerError } = useCustomers();
  const isClient = useClientOnly();
  
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState<FormData>({
    lineId: '',
    name: '',
    phone: '',
    annualIncome: '',
    riskProfile: '',
    note: '',
  });
  
  const [errors, setErrors] = useState<FormErrors>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  // 當客戶變更時更新表單
  useEffect(() => {
    if (customer) {
      setFormData({
        lineId: customer.lineId,
        name: customer.name,
        phone: customer.phone || '',
        annualIncome: customer.annualIncome?.toString() || '',
        riskProfile: customer.riskProfile || '',
        note: customer.note || '',
      });
      setErrors({});
      setIsEditing(false);
    }
  }, [customer]);

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

  // 表單驗證
  const validateForm = (): boolean => {
    const newErrors: FormErrors = {};

    if (!formData.lineId.trim()) {
      newErrors.lineId = 'LINE ID 為必填項目';
    }

    if (!formData.name.trim()) {
      newErrors.name = '姓名為必填項目';
    }

    if (formData.phone && !/^[0-9\-\s\+\(\)]+$/.test(formData.phone)) {
      newErrors.phone = '電話號碼格式不正確';
    }

    if (formData.annualIncome && isNaN(Number(formData.annualIncome))) {
      newErrors.annualIncome = '年收入必須為數字';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // 處理輸入變更
  const handleInputChange = (field: keyof FormData, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    
    // 清除該欄位的錯誤
    if (errors[field as keyof FormErrors]) {
      setErrors(prev => ({ ...prev, [field]: undefined }));
    }
  };

  // 處理表單提交
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!customer || !validateForm()) return;

    setIsSubmitting(true);
    
    try {
      const customerData = {
        lineId: formData.lineId.trim(),
        name: formData.name.trim(),
        phone: formData.phone.trim() || undefined,
        annualIncome: formData.annualIncome ? Number(formData.annualIncome) : undefined,
        riskProfile: formData.riskProfile as Customer['riskProfile'] || undefined,
        note: formData.note.trim() || undefined,
      };

      const updatedCustomer = update(customer.id, customerData);
      if (updatedCustomer) {
        onCustomerUpdate?.(updatedCustomer);
        setIsEditing(false);
      }
    } catch (err) {
      console.error('Form submission error:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  // 取消編輯
  const handleCancel = () => {
    if (customer) {
      setFormData({
        lineId: customer.lineId,
        name: customer.name,
        phone: customer.phone || '',
        annualIncome: customer.annualIncome?.toString() || '',
        riskProfile: customer.riskProfile || '',
        note: customer.note || '',
      });
      setErrors({});
    }
    setIsEditing(false);
  };

  if (!customer) {
    return (
      <Card className={`p-6 ${className}`}>
        <div className="text-center text-muted-foreground py-8">
          <p>請從上方列表選擇客戶以查看詳細資訊</p>
        </div>
      </Card>
    );
  }

  return (
    <Card className={`p-6 ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">客戶詳細資訊</h3>
        {!isEditing ? (
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsEditing(true)}
            suppressHydrationWarning={true}
          >
            編輯
          </Button>
        ) : (
          <div className="flex space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleCancel}
              disabled={isSubmitting}
              suppressHydrationWarning={true}
            >
              取消
            </Button>
            <Button
              size="sm"
              onClick={handleSubmit}
              disabled={isSubmitting}
              suppressHydrationWarning={true}
            >
              {isSubmitting ? '儲存中...' : '儲存'}
            </Button>
          </div>
        )}
      </div>

      {isEditing ? (
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* 編輯表單 */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium mb-1 block">
                LINE ID <span className="text-destructive">*</span>
              </label>
              <Input
                value={formData.lineId}
                onChange={(e) => handleInputChange('lineId', e.target.value)}
                className={errors.lineId ? 'border-destructive' : ''}
                suppressHydrationWarning={true}
              />
              {errors.lineId && (
                <p className="text-xs text-destructive mt-1">{errors.lineId}</p>
              )}
            </div>

            <div>
              <label className="text-sm font-medium mb-1 block">
                姓名 <span className="text-destructive">*</span>
              </label>
              <Input
                value={formData.name}
                onChange={(e) => handleInputChange('name', e.target.value)}
                className={errors.name ? 'border-destructive' : ''}
                suppressHydrationWarning={true}
              />
              {errors.name && (
                <p className="text-xs text-destructive mt-1">{errors.name}</p>
              )}
            </div>

            <div>
              <label className="text-sm font-medium mb-1 block">電話</label>
              <Input
                value={formData.phone}
                onChange={(e) => handleInputChange('phone', e.target.value)}
                className={errors.phone ? 'border-destructive' : ''}
                suppressHydrationWarning={true}
              />
              {errors.phone && (
                <p className="text-xs text-destructive mt-1">{errors.phone}</p>
              )}
            </div>

            <div>
              <label className="text-sm font-medium mb-1 block">年收入</label>
              <Input
                type="number"
                value={formData.annualIncome}
                onChange={(e) => handleInputChange('annualIncome', e.target.value)}
                className={errors.annualIncome ? 'border-destructive' : ''}
                suppressHydrationWarning={true}
              />
              {errors.annualIncome && (
                <p className="text-xs text-destructive mt-1">{errors.annualIncome}</p>
              )}
            </div>
          </div>

          <div>
            <label className="text-sm font-medium mb-1 block">投資風險偏好</label>
            <Select value={formData.riskProfile} onValueChange={(value) => handleInputChange('riskProfile', value)}>
              <SelectTrigger suppressHydrationWarning={true}>
                <SelectValue placeholder="請選擇風險偏好" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="保守">保守型</SelectItem>
                <SelectItem value="平衡">平衡型</SelectItem>
                <SelectItem value="積極">積極型</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div>
            <label className="text-sm font-medium mb-1 block">備註</label>
            <Textarea
              value={formData.note}
              onChange={(e) => handleInputChange('note', e.target.value)}
              rows={2}
              suppressHydrationWarning={true}
            />
          </div>

          {customerError && (
            <div className="p-2 bg-destructive/10 border border-destructive/20 rounded-md">
              <p className="text-xs text-destructive">{customerError}</p>
            </div>
          )}
        </form>
      ) : (
        <div className="space-y-3">
          {/* 顯示模式 */}
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-muted-foreground">姓名：</span>
              <span className="font-medium">{customer.name}</span>
            </div>
            <div>
              <span className="text-muted-foreground">LINE ID：</span>
              <code className="text-xs bg-muted px-1 py-0.5 rounded">
                {fmtLineId(customer.lineId)}
              </code>
            </div>
            {customer.phone && (
              <div>
                <span className="text-muted-foreground">電話：</span>
                <span>{fmtPhone(customer.phone)}</span>
              </div>
            )}
            {customer.annualIncome && (
              <div>
                <span className="text-muted-foreground">年收入：</span>
                <span>{fmtCurrency(customer.annualIncome)}</span>
              </div>
            )}
            {customer.riskProfile && (
              <div>
                <span className="text-muted-foreground">風險偏好：</span>
                {getRiskProfileBadge(customer.riskProfile)}
              </div>
            )}
            <div>
              <span className="text-muted-foreground">建立時間：</span>
              <span>{fmtDate(customer.createdAt, { includeTime: false })}</span>
            </div>
          </div>
          {customer.note && (
            <div>
              <span className="text-muted-foreground text-sm">備註：</span>
              <p className="mt-1 text-sm bg-muted/30 p-2 rounded">
                {customer.note}
              </p>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}
