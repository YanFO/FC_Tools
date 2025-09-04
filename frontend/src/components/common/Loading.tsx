/**
 * Loading 載入狀態組件
 * 提供各種載入動畫和骨架屏
 */

import React from 'react';
import { Card } from '@/components/ui/card';

interface LoadingProps {
  text?: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function Loading({ 
  text = '載入中...', 
  size = 'md', 
  className = '' 
}: LoadingProps) {
  const getSizeClasses = () => {
    switch (size) {
      case 'sm':
        return 'p-4';
      case 'lg':
        return 'p-12';
      default:
        return 'p-8';
    }
  };

  return (
    <Card className={`flex flex-col items-center justify-center text-center ${getSizeClasses()} ${className}`}>
      <Spinner size={size} />
      {text && (
        <p className="mt-4 text-sm text-muted-foreground">
          {text}
        </p>
      )}
    </Card>
  );
}

// 旋轉載入器
export function Spinner({ size = 'md' }: { size?: 'sm' | 'md' | 'lg' }) {
  const getSizeValue = () => {
    switch (size) {
      case 'sm':
        return 16;
      case 'lg':
        return 32;
      default:
        return 24;
    }
  };

  const spinnerSize = getSizeValue();

  return (
    <div className="animate-spin">
      <svg
        width={spinnerSize}
        height={spinnerSize}
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="text-primary"
      >
        <path d="M21 12a9 9 0 1 1-6.219-8.56" />
      </svg>
    </div>
  );
}

// 內聯載入器 (用於按鈕等)
export function InlineLoading({ text }: { text?: string }) {
  return (
    <div className="flex items-center space-x-2">
      <Spinner size="sm" />
      {text && <span className="text-sm">{text}</span>}
    </div>
  );
}

// 骨架屏組件
export function Skeleton({ 
  className = '', 
  width, 
  height 
}: { 
  className?: string; 
  width?: string | number; 
  height?: string | number; 
}) {
  const style = {
    width: typeof width === 'number' ? `${width}px` : width,
    height: typeof height === 'number' ? `${height}px` : height,
  };

  return (
    <div 
      className={`animate-pulse bg-muted rounded ${className}`}
      style={style}
    />
  );
}

// 表格骨架屏
export function TableSkeleton({ rows = 5, columns = 4 }: { rows?: number; columns?: number }) {
  return (
    <div className="space-y-3">
      {/* 表頭 */}
      <div className="flex space-x-4">
        {Array.from({ length: columns }).map((_, i) => (
          <Skeleton key={i} className="h-4 flex-1" />
        ))}
      </div>
      
      {/* 表格行 */}
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div key={rowIndex} className="flex space-x-4">
          {Array.from({ length: columns }).map((_, colIndex) => (
            <Skeleton key={colIndex} className="h-4 flex-1" />
          ))}
        </div>
      ))}
    </div>
  );
}

// 卡片骨架屏
export function CardSkeleton() {
  return (
    <Card className="p-6">
      <div className="space-y-4">
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-4 w-1/2" />
        <div className="space-y-2">
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-2/3" />
        </div>
      </div>
    </Card>
  );
}

// 聊天訊息骨架屏
export function ChatMessageSkeleton() {
  return (
    <div className="space-y-4">
      {/* 用戶訊息 */}
      <div className="flex justify-end">
        <div className="max-w-xs">
          <Skeleton className="h-10 w-32 rounded-lg" />
        </div>
      </div>
      
      {/* AI 回應 */}
      <div className="flex justify-start">
        <div className="max-w-md space-y-2">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-4 w-1/2" />
        </div>
      </div>
    </div>
  );
}

// 列表項目骨架屏
export function ListItemSkeleton() {
  return (
    <div className="flex items-center space-x-4 p-4">
      <Skeleton className="h-10 w-10 rounded-full" />
      <div className="flex-1 space-y-2">
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-3 w-1/2" />
      </div>
      <Skeleton className="h-8 w-16" />
    </div>
  );
}
