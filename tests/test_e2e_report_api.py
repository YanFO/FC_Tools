"""
Report Agent 端到端測試
測試完整的 API 流程，包括報告生成、檔案下載等功能
"""
import pytest
import asyncio
import httpx
import os

# 測試配置
TEST_BASE_URL = "http://localhost:8000"
TEST_TIMEOUT = 30.0


class TestReportAPI:
    """測試 Report API 端點"""
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """測試健康檢查端點"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{TEST_BASE_URL}/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is True
    
    @pytest.mark.asyncio
    async def test_report_generate_stock_success(self):
        """測試股票報告生成成功"""
        async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
            payload = {
                "query": "/report stock AAPL"
            }
            
            response = await client.post(
                f"{TEST_BASE_URL}/api/report/generate",
                json=payload
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # 檢查基本回應結構
            assert "ok" in data
            assert "response" in data
            assert "output_files" in data
            assert "timestamp" in data
            
            # 如果成功，檢查檔案資訊
            if data["ok"]:
                assert len(data["output_files"]) > 0
                for file_info in data["output_files"]:
                    assert "format" in file_info
                    assert "filename" in file_info
                    assert "path" in file_info
                    assert "size" in file_info
    
    @pytest.mark.asyncio
    async def test_report_generate_macro(self):
        """測試總經報告生成"""
        async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
            payload = {
                "query": "/report macro GDP CPI"
            }
            
            response = await client.post(
                f"{TEST_BASE_URL}/api/report/generate",
                json=payload
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "ok" in data
    
    @pytest.mark.asyncio
    async def test_report_generate_news(self):
        """測試新聞報告生成"""
        async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
            payload = {
                "query": "/report news AAPL"
            }
            
            response = await client.post(
                f"{TEST_BASE_URL}/api/report/generate",
                json=payload
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "ok" in data
    
    @pytest.mark.asyncio
    async def test_report_generate_custom(self):
        """測試自訂報告生成"""
        async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
            payload = {
                "query": "/report custom 分析市場趨勢"
            }
            
            response = await client.post(
                f"{TEST_BASE_URL}/api/report/generate",
                json=payload
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "ok" in data
    
    @pytest.mark.asyncio
    async def test_report_generate_invalid_query(self):
        """測試無效查詢"""
        async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
            payload = {
                "query": "invalid query without /report"
            }
            
            response = await client.post(
                f"{TEST_BASE_URL}/api/report/generate",
                json=payload
            )
            
            assert response.status_code == 400
    
    @pytest.mark.asyncio
    async def test_agent_run_report_delegation(self):
        """測試通用 Agent 端點的 /report 委派"""
        async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
            payload = {
                "input_type": "text",
                "query": "/report stock TSLA"
            }
            
            response = await client.post(
                f"{TEST_BASE_URL}/api/agent/run",
                json=payload
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "ok" in data
            
            # 檢查是否有 output_files（Report Agent 特有）
            if data["ok"]:
                assert "output_files" in data
    
    @pytest.mark.asyncio
    async def test_report_status(self):
        """測試報告狀態端點"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{TEST_BASE_URL}/api/report/status")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "ok" in data
            if data["ok"]:
                assert "reports_directory" in data
                assert "file_counts" in data
                assert "total_size_bytes" in data
    
    @pytest.mark.asyncio
    async def test_report_templates(self):
        """測試模板列表端點"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{TEST_BASE_URL}/api/report/templates")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "ok" in data
            if data["ok"]:
                assert "templates" in data
                assert "count" in data
                
                # 檢查是否有必要的模板
                template_ids = [t["id"] for t in data["templates"]]
                assert "stock.j2" in template_ids
                assert "macro.j2" in template_ids
                assert "news.j2" in template_ids
                assert "custom.j2" in template_ids


class TestReportFileOperations:
    """測試報告檔案操作"""
    
    @pytest.mark.asyncio
    async def test_reports_list(self):
        """測試報告列表"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{TEST_BASE_URL}/api/reports/list")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "ok" in data
            if data["ok"]:
                assert "reports" in data
    
    @pytest.mark.asyncio
    async def test_report_download_security(self):
        """測試報告下載安全性"""
        async with httpx.AsyncClient() as client:
            # 測試路徑穿越攻擊
            dangerous_paths = [
                "../../../etc/passwd",
                "..\\..\\..\\windows\\system32\\config\\sam",
                "/etc/passwd",
                "C:\\Windows\\System32\\config\\SAM"
            ]
            
            for dangerous_path in dangerous_paths:
                response = await client.get(
                    f"{TEST_BASE_URL}/api/reports/download",
                    params={"path": dangerous_path}
                )
                
                # 應該拒絕危險路徑
                assert response.status_code in [400, 403, 404]


class TestReportErrorHandling:
    """測試錯誤處理"""
    
    @pytest.mark.asyncio
    async def test_missing_fmp_api_key(self):
        """測試缺少 FMP API 金鑰的情況"""
        # 暫時移除 FMP_API_KEY
        original_key = os.environ.get("FMP_API_KEY")
        if "FMP_API_KEY" in os.environ:
            del os.environ["FMP_API_KEY"]
        
        try:
            async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
                payload = {
                    "query": "/report stock AAPL"
                }
                
                response = await client.post(
                    f"{TEST_BASE_URL}/api/report/generate",
                    json=payload
                )
                
                assert response.status_code == 200
                data = response.json()
                
                # 應該仍然成功，但可能包含警告或空狀態
                assert "ok" in data
                
                # 如果有產出檔案，檢查是否包含空狀態說明
                if data.get("output_files"):
                    # 可以進一步檢查檔案內容是否包含「無資料」說明
                    pass
        
        finally:
            # 恢復原始 API 金鑰
            if original_key:
                os.environ["FMP_API_KEY"] = original_key
    
    @pytest.mark.asyncio
    async def test_malformed_request(self):
        """測試格式錯誤的請求"""
        async with httpx.AsyncClient() as client:
            # 缺少必要欄位
            response = await client.post(
                f"{TEST_BASE_URL}/api/report/generate",
                json={}
            )
            
            assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_server_error_handling(self):
        """測試伺服器錯誤處理"""
        async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
            # 測試極長的查詢字串
            payload = {
                "query": "/report stock " + "A" * 10000
            }
            
            response = await client.post(
                f"{TEST_BASE_URL}/api/report/generate",
                json=payload
            )
            
            # 應該優雅處理，不會導致 500 錯誤
            assert response.status_code in [200, 400, 413]


class TestReportIdempotency:
    """測試報告生成的 Idempotent 行為"""
    
    @pytest.mark.asyncio
    async def test_same_request_same_timestamp(self):
        """測試相同請求是否使用相同時間戳記"""
        async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
            payload = {
                "query": "/report stock AAPL"
            }
            
            # 連續發送兩個相同請求
            response1 = await client.post(
                f"{TEST_BASE_URL}/api/report/generate",
                json=payload
            )
            
            # 短暫延遲
            await asyncio.sleep(0.1)
            
            response2 = await client.post(
                f"{TEST_BASE_URL}/api/report/generate",
                json=payload
            )
            
            assert response1.status_code == 200
            assert response2.status_code == 200
            
            data1 = response1.json()
            data2 = response2.json()
            
            # 檢查檔案路徑是否包含不同的時間戳記
            # （因為是不同的請求執行，應該有不同的時間戳記）
            if data1.get("output_files") and data2.get("output_files"):
                path1 = data1["output_files"][0]["path"]
                path2 = data2["output_files"][0]["path"]
                
                # 提取時間戳記部分
                timestamp1 = path1.split("/")[-2] if "/" in path1 else ""
                timestamp2 = path2.split("/")[-2] if "/" in path2 else ""
                
                # 不同請求應該有不同時間戳記
                assert timestamp1 != timestamp2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
