#!/bin/bash
# Agent 環境修復腳本
# 自動檢查與修復 Agent 執行所需的環境變數設定

set -e

echo "=== Agent 環境檢查/修復工具 ==="
echo "檢查時間: $(date)"
echo ""

# 確保 .env 檔案存在
if [ ! -f .env ]; then
    echo "⚠️  .env 檔案不存在，正在建立..."
    touch .env
    echo "✅ 已建立 .env 檔案"
else
    echo "✅ .env 檔案存在"
fi

echo ""
echo "=== 檢查 Agent 執行控制變數 ==="

# 檢查並設定 EXECUTE_TOOLS
if ! grep -q "^EXECUTE_TOOLS=" .env 2>/dev/null; then
    echo "⚠️  EXECUTE_TOOLS 未設定，將寫入預設值 1"
    echo "EXECUTE_TOOLS=1" >> .env
    echo "✅ 已設定 EXECUTE_TOOLS=1"
else
    current_value=$(grep "^EXECUTE_TOOLS=" .env | cut -d'=' -f2)
    echo "✅ EXECUTE_TOOLS 已設定: $current_value"
fi

# 檢查並設定 COLLOQUIAL_ENABLED
if ! grep -q "^COLLOQUIAL_ENABLED=" .env 2>/dev/null; then
    echo "⚠️  COLLOQUIAL_ENABLED 未設定，將寫入預設值 1"
    echo "COLLOQUIAL_ENABLED=1" >> .env
    echo "✅ 已設定 COLLOQUIAL_ENABLED=1"
else
    current_value=$(grep "^COLLOQUIAL_ENABLED=" .env | cut -d'=' -f2)
    echo "✅ COLLOQUIAL_ENABLED 已設定: $current_value"
fi

# 檢查並設定 MAX_TOOL_LOOPS
if ! grep -q "^MAX_TOOL_LOOPS=" .env 2>/dev/null; then
    echo "⚠️  MAX_TOOL_LOOPS 未設定，將寫入預設值 3"
    echo "MAX_TOOL_LOOPS=3" >> .env
    echo "✅ 已設定 MAX_TOOL_LOOPS=3"
else
    current_value=$(grep "^MAX_TOOL_LOOPS=" .env | cut -d'=' -f2)
    echo "✅ MAX_TOOL_LOOPS 已設定: $current_value"
fi

# 檢查並設定 LLM_REPORT_ENHANCEMENT
if ! grep -q "^LLM_REPORT_ENHANCEMENT=" .env 2>/dev/null; then
    echo "⚠️  LLM_REPORT_ENHANCEMENT 未設定，將寫入預設值 1"
    echo "LLM_REPORT_ENHANCEMENT=1" >> .env
    echo "✅ 已設定 LLM_REPORT_ENHANCEMENT=1"
else
    current_value=$(grep "^LLM_REPORT_ENHANCEMENT=" .env | cut -d'=' -f2)
    echo "✅ LLM_REPORT_ENHANCEMENT 已設定: $current_value"
fi

echo ""
echo "=== 檢查 API 金鑰設定 ==="

# 檢查 OpenAI API 金鑰
if ! grep -q "^OPENAI_API_KEY=" .env 2>/dev/null || [ -z "$(grep "^OPENAI_API_KEY=" .env | cut -d'=' -f2)" ]; then
    echo "⚠️  OPENAI_API_KEY 未設定或為空"
    echo "   請手動設定: OPENAI_API_KEY=your_api_key"
    if ! grep -q "^OPENAI_API_KEY=" .env 2>/dev/null; then
        echo "OPENAI_API_KEY=" >> .env
    fi
else
    echo "✅ OPENAI_API_KEY 已設定"
fi

# 檢查 FMP API 金鑰
if ! grep -q "^FMP_API_KEY=" .env 2>/dev/null || [ -z "$(grep "^FMP_API_KEY=" .env | cut -d'=' -f2)" ]; then
    echo "⚠️  FMP_API_KEY 未設定或為空"
    echo "   無 FMP 金鑰時將顯示空狀態，不會報錯"
    if ! grep -q "^FMP_API_KEY=" .env 2>/dev/null; then
        echo "FMP_API_KEY=" >> .env
    fi
else
    echo "✅ FMP_API_KEY 已設定"
fi

echo ""
echo "=== 檢查輸出目錄設定 ==="

# 檢查並設定 OUTPUT_DIR
if ! grep -q "^OUTPUT_DIR=" .env 2>/dev/null; then
    echo "⚠️  OUTPUT_DIR 未設定，將寫入預設值 ./outputs"
    echo "OUTPUT_DIR=./outputs" >> .env
    echo "✅ 已設定 OUTPUT_DIR=./outputs"
else
    current_value=$(grep "^OUTPUT_DIR=" .env | cut -d'=' -f2)
    echo "✅ OUTPUT_DIR 已設定: $current_value"
fi

# 檢查並建立輸出目錄
output_dir=$(grep "^OUTPUT_DIR=" .env | cut -d'=' -f2 | sed 's/^"//' | sed 's/"$//')
if [ -z "$output_dir" ]; then
    output_dir="./outputs"
fi

if [ ! -d "$output_dir" ]; then
    echo "⚠️  輸出目錄不存在，正在建立: $output_dir"
    mkdir -p "$output_dir"
    mkdir -p "$output_dir/reports"
    echo "✅ 已建立輸出目錄"
else
    echo "✅ 輸出目錄存在: $output_dir"
fi

echo ""
echo "=== 檢查 PDF 生成設定 ==="

# 檢查並設定 PDF_ENGINE
if ! grep -q "^PDF_ENGINE=" .env 2>/dev/null; then
    echo "⚠️  PDF_ENGINE 未設定，將寫入預設值 weasyprint"
    echo "PDF_ENGINE=weasyprint" >> .env
    echo "✅ 已設定 PDF_ENGINE=weasyprint"
else
    current_value=$(grep "^PDF_ENGINE=" .env | cut -d'=' -f2)
    echo "✅ PDF_ENGINE 已設定: $current_value"
fi

# 檢查 WeasyPrint 是否可用
echo "🔍 檢查 WeasyPrint 可用性..."
if command -v python3 >/dev/null 2>&1; then
    if python3 -c "import weasyprint" 2>/dev/null; then
        echo "✅ WeasyPrint 可用"
    else
        echo "⚠️  WeasyPrint 不可用，PDF 生成可能失敗"
        echo "   安裝建議: uv pip install weasyprint"
    fi
else
    echo "⚠️  Python3 不可用"
fi

echo ""
echo "=== 檢查向量資料庫設定 ==="

# 檢查並設定 VECTORSTORE_DIR
if ! grep -q "^VECTORSTORE_DIR=" .env 2>/dev/null; then
    echo "⚠️  VECTORSTORE_DIR 未設定，將寫入預設值 ./vector_store"
    echo "VECTORSTORE_DIR=./vector_store" >> .env
    echo "✅ 已設定 VECTORSTORE_DIR=./vector_store"
else
    current_value=$(grep "^VECTORSTORE_DIR=" .env | cut -d'=' -f2)
    echo "✅ VECTORSTORE_DIR 已設定: $current_value"
fi

echo ""
echo "=== 目前 Agent 相關設定 ==="
echo "--- Agent 執行控制 ---"
grep -E "^(EXECUTE_TOOLS|COLLOQUIAL_ENABLED|MAX_TOOL_LOOPS)=" .env 2>/dev/null || echo "無相關設定"

echo ""
echo "--- API 金鑰狀態 ---"
if grep -q "^OPENAI_API_KEY=.+" .env 2>/dev/null; then
    echo "OPENAI_API_KEY: ✅ 已設定"
else
    echo "OPENAI_API_KEY: ❌ 未設定或為空"
fi

if grep -q "^FMP_API_KEY=.+" .env 2>/dev/null; then
    echo "FMP_API_KEY: ✅ 已設定"
else
    echo "FMP_API_KEY: ⚠️  未設定或為空（將顯示空狀態）"
fi

echo ""
echo "--- 目錄設定 ---"
grep -E "^(OUTPUT_DIR|VECTORSTORE_DIR|PDF_ENGINE)=" .env 2>/dev/null || echo "無相關設定"

echo ""
echo "=== 修復完成 ==="
echo "✅ Agent 環境檢查與修復完成"
echo ""
echo "🚀 下一步操作："
echo "1. 檢查並填入必要的 API 金鑰（特別是 OPENAI_API_KEY）"
echo "2. 啟動服務: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
echo "3. 測試 Supervisor Agent 問答: curl -X POST http://localhost:8000/api/agent/run -H 'Content-Type: application/json' -d '{\"input_type\":\"text\",\"query\":\"AAPL股價多少？\"}'"
echo "4. 測試 Supervisor Agent 簡報: curl -X POST http://localhost:8000/api/agent/run -H 'Content-Type: application/json' -d '{\"input_type\":\"text\",\"query\":\"/report stock AAPL TSLA\"}'"
echo ""
echo "📋 如有問題，請檢查日誌或聯絡技術支援"
