"""
Supervisor Agent 端點測試
測試 Supervisor Agent 的 API 端點，包括問答與簡報製作功能
"""
import pytest
import httpx
import asyncio
import os

# 測試配置
TEST_TIMEOUT = 30.0
TEST_BASE_URL = "http://localhost:8000"

async def _server_ready():
    """檢查服務是否就緒"""
    try:
        async with httpx.AsyncClient(timeout=2) as c:
            r = await c.get("http://localhost:8000/health")
            return r.status_code == 200
    except Exception:
        return False

pytestmark = pytest.mark.asyncio

@pytest.fixture(scope="session", autouse=True)
def _skip_if_server_not_running():
    """如果服務未運行則跳過所有測試"""
    import asyncio
    if not asyncio.run(_server_ready()):
        pytest.skip("測試若需要服務運行，請自行啟動服務", allow_module_level=True)


class TestSupervisorEndpoints:
    """測試 Supervisor Agent API 端點"""

    async def test_health_check(self):
        """測試健康檢查端點"""
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/health")

            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is True

    async def test_supervisor_text_query_stock(self):
        """測試 Supervisor 文字查詢 - 股票"""
        async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
            payload = {
                "input_type": "text",
                "query": "AAPL股價多少？"
            }
            
            response = await client.post(
                f"{TEST_BASE_URL}/api/agent/run",
                json=payload
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # 檢查基本回應結構
            assert "ok" in data
            assert "response" in data
            assert "tool_results" in data
            assert "sources" in data
            assert "nlg" in data
            
            # 檢查工具執行結果
            if data["ok"] and data.get("tool_results"):
                # 應該有 FMP 來源
                sources = data.get("sources", [])
                assert "FMP" in sources
                
                # 檢查 NLG 結構
                nlg = data.get("nlg", {})
                assert "raw" in nlg
                # 如果 COLLOQUIAL_ENABLED=1，應該有 colloquial
                if os.environ.get("COLLOQUIAL_ENABLED", "1") == "1":
                    assert "colloquial" in nlg
    
    async def test_supervisor_text_query_macro(self):
        """測試 Supervisor 文字查詢 - 總經"""
        async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
            payload = {
                "input_type": "text",
                "query": "美國CPI最新是多少？"
            }
            
            response = await client.post(
                f"{TEST_BASE_URL}/api/agent/run",
                json=payload
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert "ok" in data
            assert "tool_results" in data
            
            # 如果有工具結果，檢查來源
            if data.get("tool_results"):
                sources = data.get("sources", [])
                assert "FMP" in sources
    
    async def test_supervisor_report_generation_stock(self):
        """測試 Supervisor 簡報生成 - 股票報告"""
        async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
            payload = {
                "input_type": "text",
                "query": "/report stock AAPL TSLA"
            }
            
            response = await client.post(
                f"{TEST_BASE_URL}/api/agent/run",
                json=payload
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert "ok" in data
            assert "tool_results" in data
            
            # 檢查是否有報告輸出
            if data["ok"]:
                # 應該有 output_files（Report Agent 特有）
                assert "output_files" in data
                
                # 檢查檔案資訊
                output_files = data.get("output_files", [])
                if output_files:
                    for file_info in output_files:
                        assert "format" in file_info
                        assert "filename" in file_info
                        assert "path" in file_info
    
    async def test_supervisor_report_generation_macro(self):
        """測試 Supervisor 簡報生成 - 總經報告"""
        async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
            payload = {
                "input_type": "text",
                "query": "/report macro GDP CPI"
            }
            
            response = await client.post(
                f"{TEST_BASE_URL}/api/agent/run",
                json=payload
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert "ok" in data
            assert "tool_results" in data
    
    async def test_supervisor_report_generation_news(self):
        """測試 Supervisor 簡報生成 - 新聞報告"""
        async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
            payload = {
                "input_type": "text",
                "query": "/report news AAPL"
            }
            
            response = await client.post(
                f"{TEST_BASE_URL}/api/agent/run",
                json=payload
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert "ok" in data
            assert "tool_results" in data
    
    async def test_supervisor_report_generation_custom(self):
        """測試 Supervisor 簡報生成 - 自訂報告"""
        async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
            payload = {
                "input_type": "text",
                "query": "/report custom 分析市場趨勢"
            }
            
            response = await client.post(
                f"{TEST_BASE_URL}/api/agent/run",
                json=payload
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert "ok" in data
    
    async def test_supervisor_file_query(self):
        """測試 Supervisor 檔案查詢"""
        async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
            payload = {
                "input_type": "file",
                "file_info": {
                    "path": "Data/Cathay_Q3.pdf",
                    "task": "qa"
                },
                "query": "這份檔案的主要內容是什麼？"
            }
            
            response = await client.post(
                f"{TEST_BASE_URL}/api/agent/run",
                json=payload
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert "ok" in data
            assert "tool_results" in data
    
    async def test_supervisor_invalid_query(self):
        """測試 Supervisor 無效查詢"""
        async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
            payload = {
                "input_type": "text",
                "query": ""
            }
            
            response = await client.post(
                f"{TEST_BASE_URL}/api/agent/run",
                json=payload
            )
            
            # 應該優雅處理空查詢
            assert response.status_code in [200, 400]
    
    async def test_supervisor_malformed_request(self):
        """測試 Supervisor 格式錯誤的請求"""
        async with httpx.AsyncClient() as client:
            # 缺少必要欄位
            response = await client.post(
                f"{TEST_BASE_URL}/api/agent/run",
                json={}
            )
            
            assert response.status_code == 422  # Validation error


class TestSupervisorExecuteToolsControl:
    """測試 Supervisor 工具執行控制"""
    
    async def test_execute_tools_disabled(self):
        """測試 EXECUTE_TOOLS=0 的行為"""
        # 暫時設定 EXECUTE_TOOLS=0
        original_value = os.environ.get("EXECUTE_TOOLS")
        os.environ["EXECUTE_TOOLS"] = "0"
        
        try:
            async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
                payload = {
                    "input_type": "text",
                    "query": "AAPL股價多少？"
                }
                
                response = await client.post(
                    f"{TEST_BASE_URL}/api/agent/run",
                    json=payload
                )
                
                assert response.status_code == 200
                data = response.json()
                
                # 應該有警告或錯誤說明
                warnings = data.get("warnings", [])
                assert any("execute_tools_disabled" in str(w) for w in warnings)
        
        finally:
            # 恢復原始值
            if original_value:
                os.environ["EXECUTE_TOOLS"] = original_value
            elif "EXECUTE_TOOLS" in os.environ:
                del os.environ["EXECUTE_TOOLS"]
    
    async def test_max_tool_loops_exceeded(self):
        """測試達到最大工具循環次數"""
        # 暫時設定較小的循環次數
        original_value = os.environ.get("MAX_TOOL_LOOPS")
        os.environ["MAX_TOOL_LOOPS"] = "1"
        
        try:
            async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
                payload = {
                    "input_type": "text",
                    "query": "AAPL股價和基本面資料"  # 可能需要多次工具調用
                }
                
                response = await client.post(
                    f"{TEST_BASE_URL}/api/agent/run",
                    json=payload
                )
                
                assert response.status_code == 200
                data = response.json()
                
                # 檢查是否有循環上限警告
                warnings = data.get("warnings", [])
                # 可能會有 tool_loops_exceeded 警告
        
        finally:
            # 恢復原始值
            if original_value:
                os.environ["MAX_TOOL_LOOPS"] = original_value
            elif "MAX_TOOL_LOOPS" in os.environ:
                del os.environ["MAX_TOOL_LOOPS"]


class TestSupervisorEmptyStateHandling:
    """測試 Supervisor 空狀態處理"""
    
    async def test_missing_fmp_api_key(self):
        """測試缺少 FMP API 金鑰的情況"""
        # 暫時移除 FMP_API_KEY
        original_key = os.environ.get("FMP_API_KEY")
        if "FMP_API_KEY" in os.environ:
            del os.environ["FMP_API_KEY"]
        
        try:
            async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
                payload = {
                    "input_type": "text",
                    "query": "AAPL股價多少？"
                }
                
                response = await client.post(
                    f"{TEST_BASE_URL}/api/agent/run",
                    json=payload
                )
                
                assert response.status_code == 200
                data = response.json()
                
                # 應該仍然成功，但可能包含空狀態說明
                assert "ok" in data
                
                # 檢查是否有適當的錯誤或警告說明
                if not data.get("ok"):
                    # 應該有明確的錯誤說明，不是杜撰的資料
                    assert "response" in data
                    response_text = data["response"].lower()
                    assert any(keyword in response_text for keyword in 
                              ["api", "金鑰", "key", "無法", "錯誤"])
        
        finally:
            # 恢復原始 API 金鑰
            if original_key:
                os.environ["FMP_API_KEY"] = original_key


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
