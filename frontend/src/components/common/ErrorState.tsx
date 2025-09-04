/**
 * ErrorState 錯誤狀態組件
 * 用於顯示錯誤訊息和重試操作
 */

import React from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

interface ErrorStateProps {
  title?: string;
  message: string;
  code?: string;
  onRetry?: () => void;
  retryText?: string;
  className?: string;
  variant?: 'default' | 'destructive' | 'warning';
}

export function ErrorState({
  title = '發生錯誤',
  message,
  code,
  onRetry,
  retryText = '重試',
  className = '',
  variant = 'destructive'
}: ErrorStateProps) {
  const getVariantStyles = () => {
    switch (variant) {
      case 'warning':
        return 'border-yellow-200 bg-yellow-50';
      case 'destructive':
        return 'border-red-200 bg-red-50';
      default:
        return 'border-gray-200 bg-gray-50';
    }
  };

  const getIconColor = () => {
    switch (variant) {
      case 'warning':
        return 'text-yellow-600';
      case 'destructive':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

  return (
    <Card className={`flex flex-col items-center justify-center p-8 text-center ${getVariantStyles()} ${className}`}>
      <div className={`mb-4 ${getIconColor()}`}>
        <ErrorIcon />
      </div>
      
      <h3 className="mb-2 text-lg font-semibold text-foreground">
        {title}
      </h3>
      
      <p className="mb-4 text-sm text-muted-foreground max-w-md">
        {message}
      </p>
      
      {code && (
        <Badge variant="outline" className="mb-4 text-xs">
          錯誤代碼: {code}
        </Badge>
      )}
      
      {onRetry && (
        <Button 
          onClick={onRetry}
          variant={variant === 'destructive' ? 'destructive' : 'default'}
          size="sm"
        >
          {retryText}
        </Button>
      )}
    </Card>
  );
}

// 錯誤圖示
function ErrorIcon({ size = 48 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="12" cy="12" r="10" />
      <line x1="15" y1="9" x2="9" y2="15" />
      <line x1="9" y1="9" x2="15" y2="15" />
    </svg>
  );
}

// 警告圖示
export function WarningIcon({ size = 48 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  );
}

// 網路錯誤組件
export function NetworkError({ onRetry }: { onRetry?: () => void }) {
  return (
    <ErrorState
      title="連線失敗"
      message="無法連接到後端服務，請檢查網路連線或服務狀態"
      code="NETWORK_ERROR"
      onRetry={onRetry}
      variant="warning"
    />
  );
}

// API 錯誤組件
export function ApiError({ 
  message, 
  status, 
  onRetry 
}: { 
  message: string; 
  status?: number; 
  onRetry?: () => void; 
}) {
  return (
    <ErrorState
      title={`API 錯誤 ${status ? `(${status})` : ''}`}
      message={message}
      code={status ? `HTTP_${status}` : 'API_ERROR'}
      onRetry={onRetry}
      variant="destructive"
    />
  );
}
