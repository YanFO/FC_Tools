"""
Report Agent 單元測試
測試 Report Agent 的核心功能，包括查詢解析、資料收集、模板選擇和報告建構
"""
import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime

from app.graphs.report_agent import (
    ReportAgent,
    parse_report_query,
    generate_timestamp,
    generate_slug,
    tool_fmp_quote,
    tool_fmp_profile,
    tool_fmp_news,
    tool_fmp_macro,
    tool_select_template,
    tool_rag_query
)


class TestReportQueryParsing:
    """測試報告查詢解析功能"""
    
    def test_parse_stock_query(self):
        """測試股票查詢解析"""
        result = parse_report_query("/report stock AAPL TSLA")
        
        assert result["report_type"] == "stock"
        assert "AAPL" in result["symbols"]
        assert "TSLA" in result["symbols"]
        assert "STOCK" not in result["symbols"]  # 應該被過濾掉
    
    def test_parse_macro_query(self):
        """測試總經查詢解析"""
        result = parse_report_query("/report macro GDP CPI")
        
        assert result["report_type"] == "macro"
        assert "GDP" in result["indicators"]
        assert "CPI" in result["indicators"]
    
    def test_parse_news_query(self):
        """測試新聞查詢解析"""
        result = parse_report_query("/report news AAPL")
        
        assert result["report_type"] == "news"
        assert "AAPL" in result["symbols"]
    
    def test_parse_custom_query(self):
        """測試自訂查詢解析"""
        result = parse_report_query("/report custom 分析公司財務")
        
        assert result["report_type"] == "custom"
        assert result["symbols"] == []
    
    def test_symbol_filtering(self):
        """測試股票代號過濾功能"""
        result = parse_report_query("/report stock AAPL STOCK NEWS TSLA")
        
        # 應該只保留有效的股票代號
        assert "AAPL" in result["symbols"]
        assert "TSLA" in result["symbols"]
        # 應該過濾掉關鍵詞
        assert "STOCK" not in result["symbols"]
        assert "NEWS" not in result["symbols"]


class TestUtilityFunctions:
    """測試工具函數"""
    
    def test_generate_timestamp(self):
        """測試時間戳記生成"""
        timestamp = generate_timestamp()
        
        # 檢查格式 YYYYMMDD_HHMMSS
        assert len(timestamp) == 15
        assert "_" in timestamp
        
        # 檢查可以解析為日期
        datetime.strptime(timestamp, "%Y%m%d_%H%M%S")
    
    def test_generate_slug_with_symbols(self):
        """測試有股票代號的 slug 生成"""
        slug = generate_slug(["AAPL", "TSLA", "GOOGL"], "stock")
        assert slug == "AAPL_TSLA"  # 只取前兩個
    
    def test_generate_slug_without_symbols(self):
        """測試無股票代號的 slug 生成"""
        slug = generate_slug([], "custom")
        assert slug == "CUSTOM"
        
        slug = generate_slug([], "macro")
        assert slug == "MACRO"


class TestFMPTools:
    """測試 FMP 工具函數"""
    
    @pytest.mark.asyncio
    async def test_fmp_quote_success(self):
        """測試 FMP 報價查詢成功"""
        with patch('app.graphs.report_agent.fmp_client') as mock_client:
            mock_client.get_quote = AsyncMock(return_value={
                "ok": True,
                "data": [{"symbol": "AAPL", "price": 150.0}]
            })
            
            result = await tool_fmp_quote(["AAPL"])
            
            assert result["ok"] is True
            assert result["source"] == "FMP"
            assert "data" in result
            assert "timestamp" in result
    
    @pytest.mark.asyncio
    async def test_fmp_quote_missing_symbols(self):
        """測試 FMP 報價查詢缺少股票代號"""
        result = await tool_fmp_quote([])
        
        assert result["ok"] is False
        assert result["error"] == "missing_symbols"
        assert result["source"] == "FMP"
    
    @pytest.mark.asyncio
    async def test_fmp_profile_success(self):
        """測試 FMP 基本面查詢成功"""
        with patch('app.graphs.report_agent.fmp_client') as mock_client:
            mock_client.get_profile = AsyncMock(return_value={
                "ok": True,
                "data": [{"symbol": "AAPL", "companyName": "Apple Inc."}]
            })
            
            result = await tool_fmp_profile(["AAPL"])
            
            assert result["ok"] is True
            assert result["source"] == "FMP"
    
    @pytest.mark.asyncio
    async def test_fmp_news_success(self):
        """測試 FMP 新聞查詢成功"""
        with patch('app.graphs.report_agent.fmp_client') as mock_client:
            mock_client.get_news = AsyncMock(return_value={
                "ok": True,
                "data": [{"title": "Apple News", "site": "Reuters"}]
            })
            
            result = await tool_fmp_news(["AAPL"], limit=5)
            
            assert result["ok"] is True
            assert result["source"] == "FMP"
    
    @pytest.mark.asyncio
    async def test_fmp_macro_success(self):
        """測試 FMP 總經查詢成功"""
        with patch('app.graphs.report_agent.fmp_client') as mock_client:
            mock_client.get_economic_indicator = AsyncMock(return_value={
                "ok": True,
                "data": [{"date": "2025-09-01", "value": 2.5}]
            })
            
            result = await tool_fmp_macro(["CPI"], limit=6)
            
            assert result["ok"] is True
            assert result["source"] == "FMP"
            assert "CPI_US" in result["data"]


class TestTemplateTools:
    """測試模板相關工具"""
    
    def test_select_template_stock(self):
        """測試股票模板選擇"""
        result = tool_select_template("stock", {})
        
        assert result["ok"] is True
        assert result["source"] == "TEMPLATE"
        assert result["data"]["template_id"] == "stock.j2"
    
    def test_select_template_macro(self):
        """測試總經模板選擇"""
        result = tool_select_template("macro", {})
        
        assert result["ok"] is True
        assert result["data"]["template_id"] == "macro.j2"
    
    def test_select_template_custom(self):
        """測試自訂模板選擇"""
        result = tool_select_template("custom", {})
        
        assert result["ok"] is True
        assert result["data"]["template_id"] == "custom.j2"


class TestRAGTools:
    """測試 RAG 工具"""
    
    @pytest.mark.asyncio
    async def test_rag_query_success(self):
        """測試 RAG 查詢成功"""
        with patch('app.graphs.report_agent.rag_service') as mock_rag:
            mock_rag.query = AsyncMock(return_value={
                "ok": True,
                "data": {"answer": "Test answer", "sources": ["doc1.pdf"]}
            })
            
            result = await tool_rag_query("test query", top_k=5)
            
            assert result["ok"] is True
            assert result["source"] == "RAG"
    
    @pytest.mark.asyncio
    async def test_rag_query_empty(self):
        """測試 RAG 查詢空字串"""
        result = await tool_rag_query("", top_k=5)
        
        assert result["ok"] is False
        assert result["error"] == "empty_query"


class TestReportAgent:
    """測試 Report Agent 主要功能"""
    
    def test_agent_initialization(self):
        """測試 Agent 初始化"""
        agent = ReportAgent()
        
        assert agent.graph is not None
        # 檢查圖中是否有必要的節點
        # 注意：這需要根據實際的 LangGraph 實作調整
    
    @pytest.mark.asyncio
    async def test_agent_run_stock_report(self):
        """測試執行股票報告生成"""
        agent = ReportAgent()
        
        input_data = {
            "input_type": "text",
            "query": "/report stock AAPL",
            "session_id": None,
            "trace_id": "test-123"
        }
        
        # 模擬各種依賴
        with patch.multiple(
            'app.graphs.report_agent',
            tool_fmp_quote=AsyncMock(return_value={"ok": True, "data": []}),
            tool_fmp_profile=AsyncMock(return_value={"ok": True, "data": []}),
            tool_fmp_news=AsyncMock(return_value={"ok": True, "data": []}),
            tool_build_report=AsyncMock(return_value={
                "ok": True,
                "data": {"files": [{"format": "markdown", "filename": "AAPL.md"}]}
            })
        ):
            result = await agent.run(input_data)
            
            assert result["ok"] is True
            assert "output_files" in result
            assert result["trace_id"] == "test-123"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
