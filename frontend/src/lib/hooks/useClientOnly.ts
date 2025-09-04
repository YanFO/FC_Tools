/**
 * useClientOnly Hook
 * 用於處理 React 水合錯誤，確保組件在客戶端渲染後才顯示
 */

import { useState, useEffect } from 'react';

export function useClientOnly(): boolean {
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
  }, []);

  return isClient;
}
