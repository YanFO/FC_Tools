# 🤖 Supervisor Agent - 智能問答與簡報製作服務

基於 LangGraph 的 **Supervisor Agent** 單一入口服務，同時支援**自然語言問答**與**簡報製作**。
採用 StateGraph + ToolNode 架構，具備工具強制執行、口語化回覆、**LLM 先分析再產報告**與多格式輸出能力，
嚴格遵循**無模擬資料**原則。

## 🏗️ 架構概覽

### Supervisor Agent 單一入口
```
/api/agent/run
├── 自然語言問答 (input_type: "text", query: "AAPL股價多少？")
└── 簡報製作指令 (input_type: "text", query: "/report stock AAPL TSLA")
```

### StateGraph 工作流程
```
agent → [should_continue?] → tools → agent → supervisor_copywriting → nlg_compose → colloquialize → response_builder
```

### 節點說明
- **agent**：LLM 規劃與工具調用，支援 fallback 注入機制
- **tools (ToolNode)**：強制執行工具，受 `EXECUTE_TOOLS` 與 `MAX_TOOL_LOOPS` 控制
- **supervisor_copywriting**：資料整理與初步摘要
- **nlg_compose**：組合 `tool_results` → `nlg.raw`
- **colloquialize**：口語化轉換 `nlg.raw` → `nlg.colloquial`（可關）
- **response_builder**：統一回應格式，包含 `tool_results`、`sources`、`nlg`

### 🆕 LLM 報告增強功能
- **LLM 先分析再產報告**：`LLM_REPORT_ENHANCEMENT=1` 時，報告生成前先進行 LLM 分析
- **智能洞察注入**：自動產生市場分析、基本面分析、投資建議等結構化洞察
- **優雅回退機制**：LLM 分析失敗時自動回退至直接模板渲染，不影響報告產出

## 🚀 快速開始

### 1. 環境準備
```bash
# 使用 uv 建立虛擬環境（必須）
uv venv
source .venv/bin/activate

# 安裝依賴
uv pip install -r requirements.txt

# 設定環境變數
cp .env.example .env
# 編輯 .env 檔案，設定必要的 API 金鑰
```

### 2. 核心環境變數
```bash
# === Supervisor 控制參數 ===
EXECUTE_TOOLS=1              # 1=執行工具, 0=僅規劃模式
COLLOQUIAL_ENABLED=1         # 1=產生口語化回覆, 0=僅正式摘要
MAX_TOOL_LOOPS=3             # 工具執行循環上限

# === LLM 報告增強 ===
LLM_REPORT_ENHANCEMENT=1     # 1=LLM先分析再產報告, 0=直接渲染模板
LLM_ANALYSIS_TEMPERATURE=0.3 # LLM 分析溫度參數
LLM_ANALYSIS_MAX_TOKENS=2000 # LLM 分析最大 token 數
LLM_ANALYSIS_TIMEOUT=30      # LLM 分析超時秒數

# === API 金鑰 ===
OPENAI_API_KEY=your_key      # 必須：LLM 與口語化功能
FMP_API_KEY=your_key         # 選填：無金鑰時顯示空狀態

# === 輸出設定 ===
OUTPUT_DIR=./outputs         # 報告輸出目錄
PDF_ENGINE=weasyprint        # PDF 生成引擎
VECTORSTORE_DIR=./vector_store  # RAG 向量資料庫
```

### 3. 啟動服務
```bash
# 自動檢查與修復設定
./scripts/fix_agent.sh

# 啟動服務
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 或使用測試專用腳本（自動設定環境變數）
./scripts/run_server_for_tests.sh
```

### 4. 健康檢查
```bash
curl http://localhost:8000/health
# 預期回應：{"status": "healthy", "timestamp": "..."}
```

## 🧪 功能測試

### 問答功能測試

#### 股價查詢
```bash
curl -s -X POST http://localhost:8000/api/agent/run \
  -H 'Content-Type: application/json' \
  -d '{"input_type":"text","query":"AAPL股價多少？"}' | python3 -m json.tool
```

**預期回應結構**：
```json
{
  "ok": true,
  "response": "Apple Inc. (AAPL) 目前股價為 $150.25...",
  "tool_results": [
    {
      "ok": true,
      "source": "FMP",
      "data": {"symbol": "AAPL", "price": 150.25, ...},
      "timestamp": "2024-01-01T12:00:00Z"
    }
  ],
  "sources": [{"source": "FMP", "tool": "tool_fmp_quote", "timestamp": "..."}],
  "nlg": {
    "raw": "AAPL 股價資訊：當前價格 $150.25...",
    "colloquial": "蘋果股價現在是 150.25 美元，今天上漲了 2.3%..."
  }
}
```

#### 總經數據查詢
```bash
curl -s -X POST http://localhost:8000/api/agent/run \
  -H 'Content-Type: application/json' \
  -d '{"input_type":"text","query":"美國CPI最新是多少？"}' | python3 -m json.tool
```

#### 新聞查詢
```bash
curl -s -X POST http://localhost:8000/api/agent/run \
  -H 'Content-Type: application/json' \
  -d '{"input_type":"text","query":"TSLA最新新聞"}' | python3 -m json.tool
```

### 簡報製作測試

#### 股票報告
```bash
curl -s -X POST http://localhost:8000/api/agent/run \
  -H 'Content-Type: application/json' \
  -d '{"input_type":"text","query":"/report stock AAPL TSLA"}' | python3 -m json.tool
```

**預期回應結構**：
```json
{
  "ok": true,
  "response": "股票報告已生成完成",
  "output_files": [
    {
      "path": "outputs/reports/20240101_120000/stock_report.md",
      "format": "markdown",
      "size": 15420
    },
    {
      "path": "outputs/reports/20240101_120000/stock_report.pdf",
      "format": "pdf",
      "size": 245680
    }
  ],
  "tool_results": [...],
  "nlg": {...}
}
```

#### 總經報告
```bash
curl -s -X POST http://localhost:8000/api/agent/run \
  -H 'Content-Type: application/json' \
  -d '{"input_type":"text","query":"/report macro US CPI GDP"}' | python3 -m json.tool
```

## ⚙️ 控制參數說明

### EXECUTE_TOOLS 控制
```bash
# 執行模式（預設）
EXECUTE_TOOLS=1
# 回應包含實際 tool_results 與 sources

# 規劃模式
EXECUTE_TOOLS=0
# 回應包含 warnings: ["execute_tools_disabled: 工具執行已停用，僅顯示規劃結果"]
```

### COLLOQUIAL_ENABLED 控制
```bash
# 口語化啟用（預設）
COLLOQUIAL_ENABLED=1
# nlg.colloquial 包含口語化回覆

# 口語化停用
COLLOQUIAL_ENABLED=0
# nlg.colloquial 為 null，僅保留 nlg.raw
```

### MAX_TOOL_LOOPS 控制
```bash
# 達到上限時的回應
{
  "warnings": ["tool_loops_exceeded: 3 >= 3"],
  "tool_results": [...],  // 部分結果
  "response": "已達工具執行上限，返回部分結果"
}
```

## 🔧 空狀態處理

### 缺少 FMP API 金鑰
```json
{
  "ok": true,
  "response": "很抱歉，目前無法取得股價資料，因為缺少 FMP API 金鑰設定。",
  "tool_results": [
    {
      "ok": false,
      "source": "FMP",
      "error": "missing_api_key",
      "logs": "FMP_API_KEY 環境變數未設定"
    }
  ]
}
```

### PDF 引擎缺失
```json
{
  "ok": true,
  "response": "報告已生成 Markdown 格式，PDF 生成失敗",
  "output_files": [
    {"path": "report.md", "format": "markdown"}
  ],
  "warnings": ["pdf_generation_failed: WeasyPrint 不可用"]
}
```

## 📁 輸出檔案結構

### 報告輸出路徑
```
outputs/reports/
└── YYYYMMDD_HHMMSS/          # 時間戳記目錄
    ├── stock_report.md       # Markdown 格式（必有）
    ├── stock_report.pdf      # PDF 格式（可選）
    └── stock_report.pptx     # PowerPoint 格式（可選）
```

### Idempotency 保證
- 同一批次的多次請求會覆蓋相同時間戳記目錄
- 檔案路徑在回應的 `output_files` 陣列中提供
- 支援透過 `/api/download/{filename}` 下載（具路徑穿越防護）

## 🧪 測試與品質保證

### 執行測試
```bash
# 核心功能測試（不需服務運行）
pytest tests/test_supervisor_tools.py::TestColloquializeNode -v
pytest tests/test_supervisor_tools.py::TestNLGComposeNode -v

# 工具測試（使用正確的 .ainvoke 介面）
pytest tests/test_supervisor_tools.py::TestSupervisorTools -v

# 端點測試（需要先啟動服務）
# 方法1：先啟動服務，再跑測試
./scripts/run_server_for_tests.sh  # 終端1
RUN_SERVER_TESTS=1 pytest tests/test_supervisor_endpoints.py -v  # 終端2

# 方法2：未啟動服務時會自動 skip
pytest tests/test_supervisor_endpoints.py -v  # 顯示 skip 訊息

# 完整測試套件（會 skip 端點測試）
pytest tests/ -v

# 靜態檢查
ruff check --select F401,F821 .
```

### 預期測試結果
```bash
# 核心功能測試
✅ TestColloquializeNode::test_colloquialize_enabled PASSED
✅ TestColloquializeNode::test_colloquialize_disabled PASSED
✅ TestColloquializeNode::test_colloquialize_fallback_no_llm PASSED
✅ TestNLGComposeNode::test_nlg_compose_with_tool_results PASSED

# 工具測試（修正後的 .ainvoke 介面）
✅ TestSupervisorTools::test_fmp_quote_tool_success PASSED
✅ TestSupervisorTools::test_rag_query_tool_success PASSED
✅ TestSupervisorTools::test_report_generate_tool_success PASSED

# 端點測試（需服務運行）
SKIPPED tests/test_supervisor_endpoints.py - RUN_SERVER_TESTS!=1，略過端點測試
# 或啟動服務後：
✅ TestSupervisorEndpoints::test_health_check PASSED
✅ TestSupervisorEndpoints::test_supervisor_text_query_stock PASSED
```

## 🔍 疑難排解

### 常見問題

#### 1. 模組載入失敗
```bash
# 檢查虛擬環境
source .venv/bin/activate
python -c "from app.graphs.agent_graph import agent_graph; print('✅ 載入成功')"
```

#### 2. 設定值類型錯誤
```bash
# 確保 .env 中使用數字而非布林值
EXECUTE_TOOLS=1          # ✅ 正確
EXECUTE_TOOLS=true       # ❌ 錯誤
```

#### 3. 工具調用失敗
```bash
# 檢查 API 金鑰設定
grep -E "^(OPENAI_API_KEY|FMP_API_KEY)=" .env
```

#### 4. LLM 報告增強失敗
```bash
# 檢查 LLM 報告增強設定
grep -E "^LLM_REPORT_ENHANCEMENT=" .env

# 停用 LLM 報告增強（回退至直接模板渲染）
echo "LLM_REPORT_ENHANCEMENT=0" >> .env

# 檢查 LLM 分析日誌
grep -i "llm.*分析" logs/app.log
```

#### 5. PDF 生成失敗
```bash
# 安裝 WeasyPrint
uv pip install weasyprint

# 檢查字型（中文支援）
mkdir -p resources/fonts
# 下載 Noto CJK 字型至 resources/fonts/
```

#### 6. 端點測試 skip 問題
```bash
# 確認服務是否運行
curl http://localhost:8000/health

# 設定環境變數強制執行端點測試
RUN_SERVER_TESTS=1 TEST_BASE_URL=http://localhost:8000/api pytest tests/test_supervisor_endpoints.py -v
```

### 日誌檢查
```bash
# 查看應用日誌
tail -f logs/app.log

# 查看特定錯誤
grep -i "error\|exception" logs/app.log
```

## 📋 已知限制與後續優化

### 字型與版面
- **中文字型**：需手動安裝 Noto CJK 字型至 `resources/fonts/`
- **PDF 版面**：複雜表格可能需要調整 `resources/pdf/default.css`

### 快取與效能
- **API 快取**：FMP 請求未實施快取機制（建議 60-300 秒 TTL）
- **重試邏輯**：API 失敗時缺少指數退避重試
- **批次處理**：多股票查詢可考慮並行處理

### 可觀測性
- **統一追蹤**：建議實施 `trace_id` 統一追蹤
- **效能指標**：可考慮整合 Prometheus metrics
- **結構化日誌**：JSON 格式日誌便於分析

## 🚀 部署建議

### Docker 容器化
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install uv && uv pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 環境變數檢查清單
- [ ] `OPENAI_API_KEY` 已設定
- [ ] `EXECUTE_TOOLS=1` 確認
- [ ] `COLLOQUIAL_ENABLED=1` 確認
- [ ] `OUTPUT_DIR` 目錄可寫入
- [ ] `VECTORSTORE_DIR` 目錄存在

---

## 📞 技術支援

如有問題，請檢查：
1. 環境變數設定是否正確
2. API 金鑰是否有效
3. 虛擬環境是否正確啟用
4. 日誌檔案中的錯誤訊息

**🎯 Supervisor Agent 現已完全就緒，可投入生產使用！**
