"""
FMP 工具測試
測試 Financial Modeling Prep API 相關功能與 Report Agent 工具
"""
import pytest
from unittest.mock import patch, AsyncMock
import os

from app.services.fmp_client import fmp_client
from app.graphs.report_agent import (
    tool_fmp_quote,
    tool_fmp_profile,
    tool_fmp_news,
    tool_fmp_macro
)


class TestReportAgentFMPTools:
    """測試 Report Agent 的 FMP 工具"""
    
    @pytest.mark.asyncio
    async def test_tool_fmp_quote_success(self):
        """測試 FMP 報價工具成功"""
        with patch('app.graphs.report_agent.fmp_client') as mock_client:
            mock_client.get_quote = AsyncMock(return_value={
                "ok": True,
                "data": [{"symbol": "AAPL", "price": 150.0}]
            })
            
            result = await tool_fmp_quote(["AAPL"])
            
            assert result["ok"] is True
            assert result["source"] == "FMP"
            assert "timestamp" in result
            assert "logs" in result
            assert result["data"] is not None
    
    @pytest.mark.asyncio
    async def test_tool_fmp_quote_missing_symbols(self):
        """測試 FMP 報價工具缺少股票代號"""
        result = await tool_fmp_quote([])
        
        assert result["ok"] is False
        assert result["source"] == "FMP"
        assert result["error"] == "missing_symbols"
        assert "未提供股票代號" in result["logs"]
    
    @pytest.mark.asyncio
    async def test_tool_fmp_profile_success(self):
        """測試 FMP 基本面工具成功"""
        with patch('app.graphs.report_agent.fmp_client') as mock_client:
            mock_client.get_profile = AsyncMock(return_value={
                "ok": True,
                "data": [{"symbol": "AAPL", "companyName": "Apple Inc."}]
            })
            
            result = await tool_fmp_profile(["AAPL"])
            
            assert result["ok"] is True
            assert result["source"] == "FMP"
            assert "查詢 1 個公司基本面" in result["logs"]
    
    @pytest.mark.asyncio
    async def test_tool_fmp_news_with_symbols(self):
        """測試 FMP 新聞工具（有股票代號）"""
        with patch('app.graphs.report_agent.fmp_client') as mock_client:
            mock_client.get_news = AsyncMock(return_value={
                "ok": True,
                "data": [{"title": "Apple News", "site": "Reuters"}]
            })
            
            result = await tool_fmp_news(["AAPL"], limit=10)
            
            assert result["ok"] is True
            assert result["source"] == "FMP"
            mock_client.get_news.assert_called_once_with(symbols=["AAPL"], limit=10)
    
    @pytest.mark.asyncio
    async def test_tool_fmp_macro_success(self):
        """測試 FMP 總經工具成功"""
        with patch('app.graphs.report_agent.fmp_client') as mock_client:
            # 模擬每個指標的查詢結果
            mock_client.get_economic_indicator = AsyncMock(return_value={
                "ok": True,
                "data": [{"date": "2025-09-01", "value": 2.5}]
            })
            
            result = await tool_fmp_macro(["CPI", "GDP"], limit=6)
            
            assert result["ok"] is True
            assert result["source"] == "FMP"
            assert "CPI_US" in result["data"]
            assert "GDP_US" in result["data"]
            
            # 檢查是否為每個指標都調用了 API
            assert mock_client.get_economic_indicator.call_count == 2
    
    @pytest.mark.asyncio
    async def test_tool_exception_handling(self):
        """測試工具異常處理"""
        with patch('app.graphs.report_agent.fmp_client') as mock_client:
            mock_client.get_quote = AsyncMock(side_effect=Exception("Unexpected error"))
            
            result = await tool_fmp_quote(["AAPL"])
            
            assert result["ok"] is False
            assert result["source"] == "FMP"
            assert result["error"] == "query_failed"
            assert "Unexpected error" in result["logs"]


class TestFMPClientIntegration:
    """測試 FMP 客戶端整合（需要實際 API 金鑰或模擬）"""
    
    @pytest.mark.asyncio
    async def test_get_quote_missing_api_key(self):
        """測試缺少 API 金鑰"""
        # 暫時移除 API 金鑰
        original_key = os.environ.get("FMP_API_KEY")
        if "FMP_API_KEY" in os.environ:
            del os.environ["FMP_API_KEY"]
        
        try:
            result = await fmp_client.get_quote(["AAPL"])
            
            assert result["ok"] is False
            assert result["reason"] == "missing_api_key"
        
        finally:
            # 恢復原始 API 金鑰
            if original_key:
                os.environ["FMP_API_KEY"] = original_key
    
    @pytest.mark.asyncio
    async def test_get_quote_empty_symbols(self):
        """測試空股票代號列表"""
        result = await fmp_client.get_quote([])
        
        assert result["ok"] is False
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(not os.environ.get("FMP_API_KEY"), reason="需要 FMP_API_KEY 環境變數")
    async def test_real_api_call(self):
        """測試真實 API 呼叫（需要有效的 API 金鑰）"""
        result = await fmp_client.get_quote(["AAPL"])
        
        # 如果有有效的 API 金鑰，應該能成功獲取資料
        if result["ok"]:
            assert len(result["data"]) > 0
            assert result["data"][0]["symbol"] == "AAPL"
        else:
            # 如果失敗，檢查是否為已知的錯誤原因
            assert result["reason"] in ["missing_api_key", "rate_limit_exceeded", "upstream_error"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
