#!/bin/bash
set -e

echo "=== Supervisor Agent 設定檢查與修復 ==="

# 建立 scripts 目錄（如果不存在）
mkdir -p scripts

# 檢查並建立 .env 檔案
if [ ! -f .env ]; then
    echo "建立 .env 檔案..."
    cp .env.example .env
fi

echo "=== 檢查必要環境變數 ==="

# 檢查並添加必要的環境變數
grep -q "^EXECUTE_TOOLS=" .env || echo "EXECUTE_TOOLS=1" >> .env
grep -q "^COLLOQUIAL_ENABLED=" .env || echo "COLLOQUIAL_ENABLED=1" >> .env
grep -q "^MAX_TOOL_LOOPS=" .env || echo "MAX_TOOL_LOOPS=3" >> .env
grep -q "^OUTPUT_DIR=" .env || echo "OUTPUT_DIR=./outputs" >> .env
grep -q "^PDF_ENGINE=" .env || echo "PDF_ENGINE=weasyprint" >> .env
grep -q "^VECTORSTORE_DIR=" .env || echo "VECTORSTORE_DIR=./vector_store" >> .env

echo "=== 目前 Supervisor 相關設定 ==="
echo "EXECUTE_TOOLS=$(grep '^EXECUTE_TOOLS=' .env | cut -d'=' -f2)"
echo "COLLOQUIAL_ENABLED=$(grep '^COLLOQUIAL_ENABLED=' .env | cut -d'=' -f2)"
echo "MAX_TOOL_LOOPS=$(grep '^MAX_TOOL_LOOPS=' .env | cut -d'=' -f2)"
echo "OUTPUT_DIR=$(grep '^OUTPUT_DIR=' .env | cut -d'=' -f2)"
echo "PDF_ENGINE=$(grep '^PDF_ENGINE=' .env | cut -d'=' -f2)"
echo "VECTORSTORE_DIR=$(grep '^VECTORSTORE_DIR=' .env | cut -d'=' -f2)"

echo ""
echo "=== 檢查 API 金鑰設定 ==="
if grep -q "^OPENAI_API_KEY=" .env && [ "$(grep '^OPENAI_API_KEY=' .env | cut -d'=' -f2)" != "your_openai_api_key" ]; then
    echo "✅ OpenAI API 金鑰已設定"
elif grep -q "^AZURE_OPENAI_API_KEY=" .env && [ "$(grep '^AZURE_OPENAI_API_KEY=' .env | cut -d'=' -f2)" != "your_azure_key" ]; then
    echo "✅ Azure OpenAI API 金鑰已設定"
else
    echo "⚠️  警告：未設定 LLM API 金鑰，口語化功能可能無法使用"
fi

if grep -q "^FMP_API_KEY=" .env && [ "$(grep '^FMP_API_KEY=' .env | cut -d'=' -f2)" != "your_fmp_api_key" ]; then
    echo "✅ FMP API 金鑰已設定"
else
    echo "⚠️  警告：未設定 FMP API 金鑰，將顯示空狀態"
fi

echo ""
echo "=== 建立必要目錄 ==="
mkdir -p outputs/reports
mkdir -p logs
mkdir -p vector_store
mkdir -p resources/fonts
mkdir -p resources/pdf

echo "✅ 目錄建立完成"

echo ""
echo "=== 檢查 Python 環境 ==="
if [ -d ".venv" ]; then
    echo "✅ 虛擬環境已存在"
else
    echo "⚠️  虛擬環境不存在，請執行：uv venv"
fi

echo ""
echo "=== 設定完成 ==="
echo "請執行以下指令啟動服務："
echo "source .venv/bin/activate"
echo "uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
echo ""
echo "或執行測試："
echo "source .venv/bin/activate"
echo "pytest tests/test_supervisor_*.py -v"
