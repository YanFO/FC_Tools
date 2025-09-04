#!/usr/bin/env bash
set -e

echo "=== 啟動 Supervisor Agent 測試服務 ==="

# 檢查虛擬環境
if [ ! -d ".venv" ]; then
    echo "建立虛擬環境..."
    uv venv
fi

# 啟用虛擬環境並安裝依賴
echo "啟用虛擬環境並安裝依賴..."
source .venv/bin/activate
uv pip install -r requirements.txt

# 設定測試環境變數
export EXECUTE_TOOLS=1
export COLLOQUIAL_ENABLED=1
export MAX_TOOL_LOOPS=3
export LLM_REPORT_ENHANCEMENT=1

echo "=== 環境變數設定 ==="
echo "EXECUTE_TOOLS=$EXECUTE_TOOLS"
echo "COLLOQUIAL_ENABLED=$COLLOQUIAL_ENABLED"
echo "MAX_TOOL_LOOPS=$MAX_TOOL_LOOPS"
echo "LLM_REPORT_ENHANCEMENT=$LLM_REPORT_ENHANCEMENT"

# 檢查 .env 檔案
if [ ! -f ".env" ]; then
    echo "複製 .env.example 到 .env..."
    cp .env.example .env
fi

echo ""
echo "=== 啟動服務 ==="
echo "服務將在 http://127.0.0.1:8000 啟動"
echo "健康檢查：curl http://127.0.0.1:8000/health"
echo "停止服務：Ctrl+C"
echo ""

# 啟動服務
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
