/**
 * CustomerForm 客戶表單組件
 * 用於新增和編輯客戶資料，包含表單驗證
 */

'use client';

import React, { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useCustomers } from '@/lib/hooks/useCustomers';
import { useClientOnly } from '@/lib/hooks/useClientOnly';
import { Customer } from '@/lib/types';
import { fmtPhone } from '@/lib/formatters';

interface CustomerFormProps {
  editingCustomer?: Customer | null;
  onCustomerSelect?: (customer: Customer) => void;
  onFormSubmit?: (customer: Customer) => void;
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

export function CustomerForm({ 
  editingCustomer, 
  onCustomerSelect, 
  onFormSubmit,
  className = '' 
}: CustomerFormProps) {
  const { create, update, error: customerError } = useCustomers();
  
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
  const isClient = useClientOnly();

  // 當編輯客戶變更時更新表單
  useEffect(() => {
    if (editingCustomer) {
      setFormData({
        lineId: editingCustomer.lineId,
        name: editingCustomer.name,
        phone: editingCustomer.phone || '',
        annualIncome: editingCustomer.annualIncome?.toString() || '',
        riskProfile: editingCustomer.riskProfile || '',
        note: editingCustomer.note || '',
      });
      setErrors({});
    }
  }, [editingCustomer]);

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
    
    if (!validateForm()) return;

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

      let savedCustomer: Customer;

      if (editingCustomer) {
        // 更新現有客戶
        const updated = update(editingCustomer.id, customerData);
        if (!updated) {
          throw new Error('更新客戶失敗');
        }
        savedCustomer = updated;
      } else {
        // 新增客戶
        savedCustomer = create(customerData);
      }

      // 通知父組件
      onFormSubmit?.(savedCustomer);
      
      // 如果是新增，清空表單
      if (!editingCustomer) {
        handleClear();
      }
    } catch (err) {
      console.error('Form submission error:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  // 清空表單
  const handleClear = () => {
    setFormData({
      lineId: '',
      name: '',
      phone: '',
      annualIncome: '',
      riskProfile: '',
      note: '',
    });
    setErrors({});
    onCustomerSelect?.(null as any);
  };

  return (
    <Card className={`p-6 ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">
          {editingCustomer ? '編輯客戶' : '新增客戶'}
        </h3>
        {editingCustomer && (
          <Button variant="outline" size="sm" onClick={handleClear} suppressHydrationWarning={true}>
            取消編輯
          </Button>
        )}
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* LINE ID */}
        <div>
          <label className="text-sm font-medium mb-2 block">
            LINE ID <span className="text-destructive">*</span>
          </label>
          <Input
            value={formData.lineId}
            onChange={(e) => handleInputChange('lineId', e.target.value)}
            placeholder="請輸入 LINE ID"
            className={errors.lineId ? 'border-destructive' : ''}
            suppressHydrationWarning={true}
          />
          {errors.lineId && (
            <p className="text-sm text-destructive mt-1">{errors.lineId}</p>
          )}
        </div>

        {/* 姓名 */}
        <div>
          <label className="text-sm font-medium mb-2 block">
            姓名 <span className="text-destructive">*</span>
          </label>
          <Input
            value={formData.name}
            onChange={(e) => handleInputChange('name', e.target.value)}
            placeholder="請輸入客戶姓名"
            className={errors.name ? 'border-destructive' : ''}
            suppressHydrationWarning={true}
          />
          {errors.name && (
            <p className="text-sm text-destructive mt-1">{errors.name}</p>
          )}
        </div>

        {/* 電話 */}
        <div>
          <label className="text-sm font-medium mb-2 block">電話</label>
          <Input
            value={formData.phone}
            onChange={(e) => handleInputChange('phone', e.target.value)}
            placeholder="請輸入電話號碼"
            className={errors.phone ? 'border-destructive' : ''}
            suppressHydrationWarning={true}
          />
          {errors.phone && (
            <p className="text-sm text-destructive mt-1">{errors.phone}</p>
          )}
          {formData.phone && !errors.phone && (
            <p className="text-sm text-muted-foreground mt-1">
              格式化: {fmtPhone(formData.phone)}
            </p>
          )}
        </div>

        {/* 年收入 */}
        <div>
          <label className="text-sm font-medium mb-2 block">年收入 (新台幣)</label>
          <Input
            type="number"
            value={formData.annualIncome}
            onChange={(e) => handleInputChange('annualIncome', e.target.value)}
            placeholder="請輸入年收入"
            className={errors.annualIncome ? 'border-destructive' : ''}
            suppressHydrationWarning={true}
          />
          {errors.annualIncome && (
            <p className="text-sm text-destructive mt-1">{errors.annualIncome}</p>
          )}
        </div>

        {/* 風險偏好 */}
        <div>
          <label className="text-sm font-medium mb-2 block">投資風險偏好</label>
          <Select value={formData.riskProfile} onValueChange={(value) => handleInputChange('riskProfile', value)}>
            <SelectTrigger>
              <SelectValue placeholder="請選擇風險偏好" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="保守">保守型</SelectItem>
              <SelectItem value="平衡">平衡型</SelectItem>
              <SelectItem value="積極">積極型</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* 備註 */}
        <div>
          <label className="text-sm font-medium mb-2 block">備註</label>
          <Textarea
            value={formData.note}
            onChange={(e) => handleInputChange('note', e.target.value)}
            placeholder="請輸入備註資訊"
            rows={3}
            suppressHydrationWarning={true}
          />
        </div>

        {/* 錯誤訊息 */}
        {customerError && (
          <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-md">
            <p className="text-sm text-destructive">{customerError}</p>
          </div>
        )}

        {/* 按鈕組 */}
        <div className="flex space-x-2 pt-4">
          <Button
            type="submit"
            disabled={isSubmitting}
            className="flex-1"
            suppressHydrationWarning={true}
          >
            {isSubmitting ? '處理中...' : (editingCustomer ? '更新' : '新增')}
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={handleClear}
            disabled={isSubmitting}
            suppressHydrationWarning={true}
          >
            清空
          </Button>
        </div>
      </form>
    </Card>
  );
}
