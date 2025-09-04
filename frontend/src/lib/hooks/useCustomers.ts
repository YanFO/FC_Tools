/**
 * useCustomers Hook
 * 前端狀態管理的客戶 CRUD 操作，使用 localStorage 持久化
 */

import { useState, useCallback, useEffect } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { Customer } from '../types';

const STORAGE_KEY = 'customers_v1';

interface UseCustomersReturn {
  customers: Customer[];
  loading: boolean;
  error: string | null;
  list: () => Customer[];
  create: (customerData: Omit<Customer, 'id' | 'createdAt' | 'updatedAt'>) => Customer;
  update: (id: string, customerData: Partial<Omit<Customer, 'id' | 'createdAt' | 'updatedAt'>>) => Customer | null;
  remove: (id: string) => boolean;
  findById: (id: string) => Customer | null;
  findByLineId: (lineId: string) => Customer | null;
  clearError: () => void;
  exportData: () => string;
  importData: (jsonData: string) => boolean;
}

function loadCustomersFromStorage(): Customer[] {
  try {
    if (typeof window === 'undefined') return [];
    
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return [];
    
    const parsed = JSON.parse(stored);
    return Array.isArray(parsed) ? parsed : [];
  } catch (error) {
    console.error('Failed to load customers from localStorage:', error);
    return [];
  }
}

function saveCustomersToStorage(customers: Customer[]): void {
  try {
    if (typeof window === 'undefined') return;
    
    localStorage.setItem(STORAGE_KEY, JSON.stringify(customers));
  } catch (error) {
    console.error('Failed to save customers to localStorage:', error);
  }
}

export function useCustomers(): UseCustomersReturn {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 初始化載入
  useEffect(() => {
    setLoading(true);
    try {
      const loadedCustomers = loadCustomersFromStorage();
      setCustomers(loadedCustomers);
    } catch (err) {
      setError('載入客戶資料失敗');
      console.error('Customer initialization error:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  // 自動儲存到 localStorage
  useEffect(() => {
    if (customers.length > 0 || customers.length === 0) {
      saveCustomersToStorage(customers);
    }
  }, [customers]);

  const list = useCallback((): Customer[] => {
    return [...customers];
  }, [customers]);

  const create = useCallback((customerData: Omit<Customer, 'id' | 'createdAt' | 'updatedAt'>): Customer => {
    const now = new Date().toISOString();
    const newCustomer: Customer = {
      ...customerData,
      id: uuidv4(),
      createdAt: now,
      updatedAt: now,
    };

    setCustomers(prev => [...prev, newCustomer]);
    setError(null);
    
    return newCustomer;
  }, []);

  const update = useCallback((
    id: string, 
    customerData: Partial<Omit<Customer, 'id' | 'createdAt' | 'updatedAt'>>
  ): Customer | null => {
    let updatedCustomer: Customer | null = null;

    setCustomers(prev => {
      const index = prev.findIndex(c => c.id === id);
      if (index === -1) {
        setError(`找不到 ID 為 ${id} 的客戶`);
        return prev;
      }

      const now = new Date().toISOString();
      updatedCustomer = {
        ...prev[index],
        ...customerData,
        updatedAt: now,
      };

      const newCustomers = [...prev];
      newCustomers[index] = updatedCustomer;
      setError(null);
      
      return newCustomers;
    });

    return updatedCustomer;
  }, []);

  const remove = useCallback((id: string): boolean => {
    let removed = false;

    setCustomers(prev => {
      const index = prev.findIndex(c => c.id === id);
      if (index === -1) {
        setError(`找不到 ID 為 ${id} 的客戶`);
        return prev;
      }

      removed = true;
      setError(null);
      return prev.filter(c => c.id !== id);
    });

    return removed;
  }, []);

  const findById = useCallback((id: string): Customer | null => {
    return customers.find(c => c.id === id) || null;
  }, [customers]);

  const findByLineId = useCallback((lineId: string): Customer | null => {
    return customers.find(c => c.lineId === lineId) || null;
  }, [customers]);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const exportData = useCallback((): string => {
    return JSON.stringify(customers, null, 2);
  }, [customers]);

  const importData = useCallback((jsonData: string): boolean => {
    try {
      const parsed = JSON.parse(jsonData);
      if (!Array.isArray(parsed)) {
        setError('匯入資料格式錯誤：必須是陣列');
        return false;
      }

      // 驗證資料結構
      const validCustomers = parsed.filter(item => {
        return (
          typeof item === 'object' &&
          typeof item.id === 'string' &&
          typeof item.lineId === 'string' &&
          typeof item.name === 'string' &&
          typeof item.createdAt === 'string' &&
          typeof item.updatedAt === 'string'
        );
      });

      if (validCustomers.length !== parsed.length) {
        setError(`匯入資料中有 ${parsed.length - validCustomers.length} 筆格式錯誤的記錄`);
      }

      setCustomers(validCustomers);
      setError(null);
      return true;
    } catch (err) {
      setError('匯入資料解析失敗');
      console.error('Import data error:', err);
      return false;
    }
  }, []);

  return {
    customers,
    loading,
    error,
    list,
    create,
    update,
    remove,
    findById,
    findByLineId,
    clearError,
    exportData,
    importData,
  };
}
