/**
 * 格式化工具函數
 * 提供日期、貨幣、百分比、檔案大小等格式化功能
 */

/**
 * 格式化日期時間
 */
export function fmtDate(dateString: string, options?: {
  includeTime?: boolean;
  locale?: string;
}): string {
  try {
    const date = new Date(dateString);
    const { includeTime = true, locale = 'zh-TW' } = options || {};
    
    if (includeTime) {
      return date.toLocaleString(locale, {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
    } else {
      return date.toLocaleDateString(locale, {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
      });
    }
  } catch (error) {
    console.error('Date formatting error:', error);
    return dateString;
  }
}

/**
 * 格式化相對時間 (例如: "2 分鐘前")
 */
export function fmtRelativeTime(dateString: string): string {
  try {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffSeconds = Math.floor(diffMs / 1000);
    const diffMinutes = Math.floor(diffSeconds / 60);
    const diffHours = Math.floor(diffMinutes / 60);
    const diffDays = Math.floor(diffHours / 24);
    
    if (diffSeconds < 60) {
      return '剛剛';
    } else if (diffMinutes < 60) {
      return `${diffMinutes} 分鐘前`;
    } else if (diffHours < 24) {
      return `${diffHours} 小時前`;
    } else if (diffDays < 7) {
      return `${diffDays} 天前`;
    } else {
      return fmtDate(dateString, { includeTime: false });
    }
  } catch (error) {
    console.error('Relative time formatting error:', error);
    return dateString;
  }
}

/**
 * 格式化檔案大小
 */
export function fmtBytes(bytes: number, decimals: number = 2): string {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

/**
 * 格式化數字 (千分位分隔符)
 */
export function fmtNumber(num: number, options?: {
  decimals?: number;
  locale?: string;
}): string {
  const { decimals, locale = 'zh-TW' } = options || {};
  
  return num.toLocaleString(locale, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

/**
 * 格式化貨幣
 */
export function fmtCurrency(amount: number, options?: {
  currency?: string;
  locale?: string;
}): string {
  const { currency = 'TWD', locale = 'zh-TW' } = options || {};
  
  return amount.toLocaleString(locale, {
    style: 'currency',
    currency: currency,
  });
}

/**
 * 格式化百分比
 */
export function fmtPercentage(value: number, decimals: number = 2): string {
  return (value * 100).toFixed(decimals) + '%';
}

/**
 * 格式化股票代號 (轉大寫並移除空格)
 */
export function fmtStockSymbol(symbol: string): string {
  return symbol.trim().toUpperCase();
}

/**
 * 格式化股票代號列表
 */
export function fmtStockSymbols(symbols: string): string[] {
  return symbols
    .split(',')
    .map(s => fmtStockSymbol(s))
    .filter(s => s.length > 0);
}

/**
 * 截斷文字並加上省略號
 */
export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength - 3) + '...';
}

/**
 * 格式化 LINE ID (遮蔽部分字符)
 */
export function fmtLineId(lineId: string): string {
  if (lineId.length <= 6) return lineId;
  const start = lineId.substring(0, 3);
  const end = lineId.substring(lineId.length - 3);
  return `${start}***${end}`;
}

/**
 * 格式化電話號碼
 */
export function fmtPhone(phone: string): string {
  // 移除所有非數字字符
  const cleaned = phone.replace(/\D/g, '');
  
  // 台灣手機號碼格式 (09XX-XXX-XXX)
  if (cleaned.length === 10 && cleaned.startsWith('09')) {
    return `${cleaned.substring(0, 4)}-${cleaned.substring(4, 7)}-${cleaned.substring(7)}`;
  }
  
  // 台灣市話格式 (0X-XXXX-XXXX)
  if (cleaned.length === 9 || cleaned.length === 10) {
    return cleaned.replace(/(\d{2})(\d{4})(\d+)/, '$1-$2-$3');
  }
  
  return phone; // 無法識別格式，返回原始值
}
