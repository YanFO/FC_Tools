# 投資助理前端應用程式

基於 Next.js 14 的智能投資助理前端應用程式，提供股票查詢、新聞分析、總經數據和客戶管理功能。

## 功能特色

### 🎯 核心功能
- **智能聊天助理**: 支援股票、新聞、總經數據查詢
- **股票報價查詢**: 即時股價和相關資訊
- **新聞資訊**: 關鍵字和股票相關新聞
- **總經數據**: 各國 CPI、GDP、失業率、利率等指標
- **報告管理**: PDF 報告列表和下載功能
- **客戶管理**: LINE 客戶資料 CRUD 操作

### 🛠 技術特色
- **Next.js 14** + App Router + TypeScript
- **TailwindCSS** + shadcn/ui 組件庫
- **響應式設計**: 支援桌面和移動端
- **狀態管理**: 自定義 Hooks + localStorage 持久化
- **錯誤處理**: 統一的錯誤處理和用戶友好提示
- **Traditional Chinese (zh-TW)**: 全繁體中文介面

## 快速開始

### 環境需求
- Node.js 18+
- npm 或 yarn
- 後端服務運行在 `http://localhost:8000`

### 安裝步驟

1. **安裝依賴**
   ```bash
   npm install
   ```

2. **環境變數設定**
   ```bash
   # .env.local 檔案已包含以下設定
   NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
   ```

3. **啟動開發伺服器**
   ```bash
   npm run dev
   ```

4. **開啟瀏覽器**
   ```
   http://localhost:3000
   ```

### 生產環境部署

```bash
# 建置應用程式
npm run build

# 啟動生產伺服器
npm start
```
