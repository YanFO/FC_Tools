/**
 * TopTabs 頂部標籤組件
 * 包含 Stock/News/Economic/Reports 四個標籤頁
 */

'use client';

import React, { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { useAgentChat } from '@/lib/hooks/useAgentChat';
import { useClientOnly } from '@/lib/hooks/useClientOnly';
import { fmtStockSymbols } from '@/lib/formatters';
import { TabType, StockShortcut, Country, EconomicIndicator } from '@/lib/types';
import { ReportList } from '@/components/lists/ReportList';

interface TopTabsProps {
  className?: string;
}

export function TopTabs({ className = '' }: TopTabsProps) {
  const { send } = useAgentChat();
  const [activeTab, setActiveTab] = useState<TabType>('stock');

  return (
    <div className={className}>
      <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as TabType)}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="stock">股票</TabsTrigger>
          <TabsTrigger value="news">新聞</TabsTrigger>
          <TabsTrigger value="economic">總經</TabsTrigger>
          <TabsTrigger value="reports">報告</TabsTrigger>
        </TabsList>

        <TabsContent value="stock" className="mt-6">
          <StockTab onQuery={send} />
        </TabsContent>

        <TabsContent value="news" className="mt-6">
          <NewsTab onQuery={send} />
        </TabsContent>

        <TabsContent value="economic" className="mt-6">
          <EconomicTab onQuery={send} />
        </TabsContent>

        <TabsContent value="reports" className="mt-6">
          <ReportsTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}

// 股票標籤頁
function StockTab({ onQuery }: { onQuery: (query: string) => Promise<void> }) {
  const [symbols, setSymbols] = useState('');
  const [loading, setLoading] = useState(false);
  const isClient = useClientOnly();

  const stockShortcuts: StockShortcut[] = ['AAPL', 'NVDA', 'TSLA'];

  const handleSubmit = async () => {
    if (!symbols.trim()) return;

    setLoading(true);
    try {
      const formattedSymbols = fmtStockSymbols(symbols);
      const query = `查詢個股 ${formattedSymbols.join(', ')} 報價`;
      await onQuery(query);
    } catch (error) {
      console.error('Stock query error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleShortcut = (symbol: StockShortcut) => {
    setSymbols(symbol);
  };

  return (
    <Card className="p-6">
      <h3 className="text-lg font-semibold mb-4">股票查詢</h3>
      
      <div className="space-y-4">
        <div>
          <label className="text-sm font-medium mb-2 block">
            股票代號 (多個代號請用逗號分隔)
          </label>
          <Input
            value={symbols}
            onChange={(e) => setSymbols(e.target.value)}
            placeholder="例如: AAPL, NVDA, TSLA"
            onKeyPress={(e) => e.key === 'Enter' && handleSubmit()}
            suppressHydrationWarning={true}
          />
        </div>

        <div>
          <p className="text-sm text-muted-foreground mb-2">快速選擇：</p>
          <div className="flex space-x-2">
            {stockShortcuts.map((symbol) => (
              <Badge
                key={symbol}
                variant="outline"
                className="cursor-pointer hover:bg-primary hover:text-primary-foreground"
                onClick={() => handleShortcut(symbol)}
              >
                {symbol}
              </Badge>
            ))}
          </div>
        </div>

        <Button
          onClick={handleSubmit}
          disabled={!symbols.trim() || loading}
          className="w-full"
          suppressHydrationWarning={true}
        >
          {loading ? '查詢中...' : '查詢股價'}
        </Button>
      </div>
    </Card>
  );
}

// 新聞標籤頁
function NewsTab({ onQuery }: { onQuery: (query: string) => Promise<void> }) {
  const [keywords, setKeywords] = useState('');
  const [loading, setLoading] = useState(false);
  const isClient = useClientOnly();

  const handleSubmit = async () => {
    if (!keywords.trim()) return;

    setLoading(true);
    try {
      const query = `查詢新聞 ${keywords.trim()} 近 10 則`;
      await onQuery(query);
    } catch (error) {
      console.error('News query error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="p-6">
      <h3 className="text-lg font-semibold mb-4">新聞查詢</h3>
      
      <div className="space-y-4">
        <div>
          <label className="text-sm font-medium mb-2 block">
            關鍵字或股票代號
          </label>
          <Input
            value={keywords}
            onChange={(e) => setKeywords(e.target.value)}
            placeholder="例如: NVDA, 人工智慧, 聯準會"
            onKeyPress={(e) => e.key === 'Enter' && handleSubmit()}
            suppressHydrationWarning={true}
          />
        </div>

        <Button
          onClick={handleSubmit}
          disabled={!keywords.trim() || loading}
          className="w-full"
          suppressHydrationWarning={true}
        >
          {loading ? '查詢中...' : '查詢新聞'}
        </Button>
      </div>
    </Card>
  );
}

// 總經標籤頁
function EconomicTab({ onQuery }: { onQuery: (query: string) => Promise<void> }) {
  const [country, setCountry] = useState<Country>('US');
  const [indicator, setIndicator] = useState<EconomicIndicator>('CPI');
  const [loading, setLoading] = useState(false);
  const isClient = useClientOnly();

  const countries: { value: Country; label: string }[] = [
    { value: 'US', label: '美國' },
    { value: 'Japan', label: '日本' },
    { value: 'Taiwan', label: '台灣' },
    { value: 'EU', label: '歐盟' },
  ];

  const indicators: { value: EconomicIndicator; label: string }[] = [
    { value: 'CPI', label: 'CPI (消費者物價指數)' },
    { value: 'GDP', label: 'GDP (國內生產毛額)' },
    { value: 'Unemployment', label: '失業率' },
    { value: 'Interest Rate', label: '利率' },
  ];

  const handleSubmit = async () => {
    setLoading(true);
    try {
      const countryName = countries.find(c => c.value === country)?.label || country;
      const indicatorName = indicators.find(i => i.value === indicator)?.label || indicator;
      const query = `${countryName} ${indicatorName} 最近 6 期`;
      await onQuery(query);
    } catch (error) {
      console.error('Economic query error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="p-6">
      <h3 className="text-lg font-semibold mb-4">總經數據查詢</h3>
      
      <div className="space-y-4">
        <div>
          <label className="text-sm font-medium mb-2 block">國家/地區</label>
          <Select value={country} onValueChange={(value) => setCountry(value as Country)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {countries.map((c) => (
                <SelectItem key={c.value} value={c.value}>
                  {c.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div>
          <label className="text-sm font-medium mb-2 block">經濟指標</label>
          <Select value={indicator} onValueChange={(value) => setIndicator(value as EconomicIndicator)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {indicators.map((i) => (
                <SelectItem key={i.value} value={i.value}>
                  {i.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <Button
          onClick={handleSubmit}
          disabled={loading}
          className="w-full"
          suppressHydrationWarning={true}
        >
          {loading ? '查詢中...' : '查詢數據'}
        </Button>
      </div>
    </Card>
  );
}

// 報告標籤頁
function ReportsTab() {
  return (
    <div>
      <ReportList />
    </div>
  );
}
