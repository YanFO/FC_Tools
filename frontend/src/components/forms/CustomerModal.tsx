/**
 * CustomerModal 客戶新增模態框組件
 * 用於在模態框中新增客戶資料，包含表單驗證
 */

'use client';

import React, { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useCustomers } from '@/lib/hooks/useCustomers';
import { useClientOnly } from '@/lib/hooks/useClientOnly';
import { Customer } from '@/lib/types';
import { fmtPhone } from '@/lib/formatters';

interface CustomerModalProps {
  onCustomerCreated?: (customer: Customer) => void;
  children: React.ReactNode; // Trigger button
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

export function CustomerModal({ 
  onCustomerCreated,
  children
}: CustomerModalProps) {
  const { create, error: customerError } = useCustomers();
  const isClient = useClientOnly();
  
  const [open, setOpen] = useState(false);
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

  // 重置表單當模態框關閉時
  useEffect(() => {
    if (!open) {
      setFormData({
        lineId: '',
        name: '',
        phone: '',
        annualIncome: '',
        riskProfile: '',
        note: '',
      });
      setErrors({});
      setIsSubmitting(false);
    }
  }, [open]);

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

      const newCustomer = create(customerData);
      
      // 通知父組件
      onCustomerCreated?.(newCustomer);
      
      // 關閉模態框
      setOpen(false);
    } catch (err) {
      console.error('Form submission error:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {children}
      </DialogTrigger>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>新增客戶</DialogTitle>
        </DialogHeader>

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
          <div className="flex justify-end space-x-2 pt-4">
            <Button
              type="button"
              variant="outline"
              onClick={() => setOpen(false)}
              disabled={isSubmitting}
              suppressHydrationWarning={true}
            >
              取消
            </Button>
            <Button
              type="submit"
              disabled={isSubmitting}
              suppressHydrationWarning={true}
            >
              {isSubmitting ? '處理中...' : '新增'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
