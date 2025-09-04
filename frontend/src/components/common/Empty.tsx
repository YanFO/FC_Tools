/**
 * Empty 空狀態組件
 * 用於顯示無資料時的友好提示
 */

import React from 'react';
import { Card } from '@/components/ui/card';

interface EmptyProps {
  icon?: React.ReactNode;
  title?: string;
  description: string;
  action?: React.ReactNode;
  className?: string;
}

// 預設圖標組件
export function MessageIcon() {
  return (
    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
    </svg>
  );
}

export function Empty({
  icon,
  title,
  description,
  action,
  className = ''
}: EmptyProps) {
  return (
    <Card className={`flex flex-col items-center justify-center p-8 text-center ${className}`}>
      {icon && (
        <div className="mb-4 text-muted-foreground">
          {icon}
        </div>
      )}
      
      {title && (
        <h3 className="mb-2 text-lg font-semibold text-foreground">
          {title}
        </h3>
      )}
      
      <p className="mb-4 text-sm text-muted-foreground max-w-sm">
        {description}
      </p>
      
      {action && (
        <div className="mt-2">
          {action}
        </div>
      )}
    </Card>
  );
}

// 預設圖示組件
export function EmptyIcon({ size = 48 }: { size?: number }) {
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
      <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
      <circle cx="9" cy="9" r="2" />
      <path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21" />
    </svg>
  );
}

// 檔案圖示
export function FileIcon({ size = 48 }: { size?: number }) {
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
      <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
      <polyline points="14,2 14,8 20,8" />
    </svg>
  );
}

// 用戶圖示
export function UsersIcon({ size = 48 }: { size?: number }) {
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
      <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  );
}


