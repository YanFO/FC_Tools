/**
 * ReportList 報告列表組件
 * 顯示可下載的報告列表，包含表格、下載功能和空狀態
 */

'use client';

import React from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { useReports } from '@/lib/hooks/useReports';
import { useClientOnly } from '@/lib/hooks/useClientOnly';
import { fmtDate, fmtBytes } from '@/lib/formatters';
import { Empty, FileIcon } from '@/components/common/Empty';
import { ErrorState } from '@/components/common/ErrorState';
import { Loading, TableSkeleton } from '@/components/common/Loading';

interface ReportListProps {
  limit?: number;
  className?: string;
}

export function ReportList({ limit = 20, className = '' }: ReportListProps) {
  const { reports, loading, error, list, buildDownloadUrl, refresh, clearError } = useReports();
  const isClient = useClientOnly();

  // 處理下載
  const handleDownload = (path: string, filename: string) => {
    try {
      const downloadUrl = buildDownloadUrl(path);
      
      // 創建隱藏的下載連結
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = filename;
      link.target = '_blank';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err) {
      console.error('Download error:', err);
    }
  };

  // 取得渲染模式的顯示文字和樣式
  const getRenderModeDisplay = (mode: string) => {
    switch (mode) {
      case 'overlay':
        return { text: '覆蓋', variant: 'default' as const };
      case 'acroform':
        return { text: '表單', variant: 'secondary' as const };
      case 'auto':
        return { text: '自動', variant: 'outline' as const };
      default:
        return { text: '未知', variant: 'destructive' as const };
    }
  };

  if (loading && reports.length === 0) {
    return (
      <Card className={`p-6 ${className}`}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">報告列表</h3>
          <Button variant="outline" size="sm" disabled suppressHydrationWarning={true}>
            重新整理
          </Button>
        </div>
        <TableSkeleton rows={5} columns={5} />
      </Card>
    );
  }

  if (error) {
    return (
      <Card className={`p-6 ${className}`}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">報告列表</h3>
          <Button variant="outline" size="sm" onClick={refresh} suppressHydrationWarning={true}>
            重新整理
          </Button>
        </div>
        <ErrorState
          title="載入報告失敗"
          message={error}
          onRetry={() => {
            clearError();
            list(limit);
          }}
          retryText="重試"
        />
      </Card>
    );
  }

  if (reports.length === 0) {
    return (
      <Card className={`p-6 ${className}`}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">報告列表</h3>
          <Button variant="outline" size="sm" onClick={refresh} disabled={loading} suppressHydrationWarning={true}>
            {loading ? '載入中...' : '重新整理'}
          </Button>
        </div>
        <Empty
          icon={<FileIcon />}
          title="暫無報告"
          description="目前沒有可下載的報告，請稍後再試或聯繫管理員"
          action={
            <Button variant="outline" onClick={refresh} disabled={loading} suppressHydrationWarning={true}>
              重新整理
            </Button>
          }
        />
      </Card>
    );
  }

  return (
    <Card className={`p-6 ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold">報告列表</h3>
          <p className="text-sm text-muted-foreground">
            共 {reports.length} 個報告
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={refresh} disabled={loading} suppressHydrationWarning={true}>
          {loading ? '載入中...' : '重新整理'}
        </Button>
      </div>

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>檔案名稱</TableHead>
              <TableHead>大小</TableHead>
              <TableHead>生成時間</TableHead>
              <TableHead>渲染模式</TableHead>
              <TableHead className="text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {reports.map((report) => {
              const renderMode = getRenderModeDisplay(report.render_mode);
              
              return (
                <TableRow key={report.path}>
                  <TableCell className="font-medium">
                    <div className="flex items-center space-x-2">
                      <FileIcon size={16} />
                      <span className="truncate max-w-xs" title={report.name}>
                        {report.name}
                      </span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <span className="text-sm text-muted-foreground">
                      {fmtBytes(report.size)}
                    </span>
                  </TableCell>
                  <TableCell>
                    <span className="text-sm text-muted-foreground">
                      {fmtDate(report.generated_at)}
                    </span>
                  </TableCell>
                  <TableCell>
                    <Badge variant={renderMode.variant} className="text-xs">
                      {renderMode.text}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDownload(report.path, report.name)}
                      className="text-xs"
                      suppressHydrationWarning={true}
                    >
                      下載
                    </Button>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>

      {/* 浮水印資訊 */}
      {reports.length > 0 && reports[0].watermark && (
        <div className="mt-4 text-xs text-muted-foreground text-center">
          報告浮水印: {reports[0].watermark}
        </div>
      )}

      {/* 載入更多 */}
      {loading && reports.length > 0 && (
        <div className="mt-4 text-center">
          <Loading text="載入中..." size="sm" />
        </div>
      )}
    </Card>
  );
}
