"""
Supervisor Agent 工具測試
測試 Supervisor Agent 的工具執行、fallback 機制與口語化功能
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
import os

from app.graphs.agent_graph import (
    node_colloquialize,
    node_nlg_compose,
    tool_fmp_quote,
    tool_fmp_news,
    tool_fmp_macro,
    tool_rag_query,
    tool_report_generate
)
from app.settings import settings


class TestSupervisorTools:
    """測試 Supervisor Agent 的工具功能"""
    
    @pytest.mark.asyncio
    async def test_fmp_quote_tool_success(self):
        """測試 FMP 報價工具成功執行"""
        with patch('app.graphs.agent_graph.fmp_client') as mock_client:
            mock_client.get_quote = AsyncMock(return_value={
                "ok": True,
                "data": [{"symbol": "AAPL", "price": 150.0, "change": 2.5}],
                "source": "FMP",
                "timestamp": "2025-09-03T12:00:00"
            })

            result = await tool_fmp_quote.ainvoke({"symbols": ["AAPL"]})

            assert isinstance(result, dict)
            assert result["ok"] is True
            assert result["source"] == "FMP"
            assert "timestamp" in result
            assert result["data"] is not None
            mock_client.get_quote.assert_called_once_with(["AAPL"])

    @pytest.mark.asyncio
    async def test_fmp_quote_tool_empty_symbols(self):
        """測試 FMP 報價工具空股票代號"""
        with patch('app.graphs.agent_graph.fmp_client') as mock_client:
            mock_client.get_quote = AsyncMock(return_value={
                "ok": False,
                "source": "FMP",
                "error": "missing_symbols",
                "logs": "未提供股票代號"
            })

            result = await tool_fmp_quote.ainvoke({"symbols": []})

            assert result["ok"] is False
            assert result["source"] == "FMP"
            assert result["error"] == "missing_symbols"
    
    @pytest.mark.asyncio
    async def test_fmp_news_tool_with_symbols(self):
        """測試 FMP 新聞工具（有股票代號）"""
        with patch('app.graphs.agent_graph.fmp_client') as mock_client:
            mock_client.get_news = AsyncMock(return_value={
                "ok": True,
                "data": [{"title": "Apple News", "site": "Reuters"}],
                "source": "FMP",
                "timestamp": "2025-09-03T12:00:00"
            })

            result = await tool_fmp_news.ainvoke({"symbols": ["AAPL"], "limit": 5})

            assert "ok" in result
            assert result["source"] == "FMP"
            assert result["data"] is not None
            mock_client.get_news.assert_called_once_with(symbols=["AAPL"], query=None, limit=5)

    @pytest.mark.asyncio
    async def test_fmp_news_tool_without_symbols(self):
        """測試 FMP 新聞工具（無股票代號）"""
        with patch('app.graphs.agent_graph.fmp_client') as mock_client:
            mock_client.get_news = AsyncMock(return_value={
                "ok": True,
                "data": [{"title": "Market News", "site": "Reuters"}],
                "source": "FMP",
                "timestamp": "2025-09-03T12:00:00"
            })

            result = await tool_fmp_news.ainvoke({"symbols": None, "limit": 5})

            assert "ok" in result
            assert result["source"] == "FMP"
            assert result["data"] is not None
            mock_client.get_news.assert_called_once_with(symbols=None, query=None, limit=5)

    @pytest.mark.asyncio
    async def test_fmp_macro_tool_success(self):
        """測試 FMP 總經工具成功"""
        with patch('app.graphs.agent_graph.fmp_client') as mock_client:
            mock_client.get_macro_data = AsyncMock(return_value={
                "ok": True,
                "data": [{"date": "2025-09-01", "value": 2.5}],
                "source": "FMP",
                "timestamp": "2025-09-03T12:00:00"
            })

            result = await tool_fmp_macro.ainvoke({"indicator": "CPI", "country": "US"})

            assert "ok" in result
            assert result["source"] == "FMP"
            assert result["data"] is not None
            mock_client.get_macro_data.assert_called_once_with("CPI", "US")
    
    @pytest.mark.asyncio
    async def test_rag_query_tool_success(self):
        """測試 RAG 查詢工具成功"""
        with patch('app.graphs.agent_graph.rag_service') as mock_rag:
            mock_rag.query_documents = AsyncMock(return_value={
                "ok": True,
                "data": {"relevant_chunks": ["chunk1", "chunk2"]}
            })
            mock_rag.answer_question = AsyncMock(return_value={
                "ok": True,
                "data": {"answer": "Test answer", "sources": ["doc1.pdf"]}
            })

            result = await tool_rag_query.ainvoke({"question": "test query", "top_k": 5})

            assert "ok" in result
            assert result["data"] is not None
            mock_rag.query_documents.assert_called_once_with("test query", 5)
            mock_rag.answer_question.assert_called_once_with("test query", ["chunk1", "chunk2"])

    @pytest.mark.asyncio
    async def test_rag_query_tool_empty_query(self):
        """測試 RAG 查詢工具空查詢"""
        with patch('app.graphs.agent_graph.rag_service') as mock_rag:
            mock_rag.query_documents = AsyncMock(return_value={
                "ok": False,
                "data": {"relevant_chunks": []}
            })

            result = await tool_rag_query.ainvoke({"question": "", "top_k": 5})

            assert result["ok"] is False

    @pytest.mark.asyncio
    async def test_report_generate_tool_success(self):
        """測試報告生成工具成功"""
        with patch('app.graphs.agent_graph.report_service') as mock_report:
            mock_report.generate_report = AsyncMock(return_value={
                "ok": True,
                "data": {
                    "format": "markdown",
                    "filename": "test.md",
                    "path": "outputs/reports/test.md",
                    "generated_at": "2025-09-03T12:00:00"
                }
            })

            context = {"symbols": ["AAPL"], "quotes": [], "profiles": [], "news": []}
            result = await tool_report_generate.ainvoke({
                "template_id": "stock",
                "context": context,
                "output_formats": ["markdown"]
            })

            assert result["ok"] is True
            assert result["source"] == "REPORT"


class TestColloquializeNode:
    """測試口語化節點"""
    
    def test_colloquialize_enabled(self):
        """測試口語化功能啟用"""
        # 模擬啟用狀態
        with patch.object(settings, 'colloquial_enabled', 1):
            with patch('app.graphs.agent_graph.agent_graph') as mock_agent:
                mock_llm = Mock()
                mock_llm.invoke.return_value = Mock(content="口語化回覆")
                mock_agent.llm = mock_llm
                
                state = {
                    "nlg_raw": "正式的資料摘要",
                    "query": "AAPL股價"
                }
                
                result = node_colloquialize(state)
                
                assert result["nlg_colloquial"] == "口語化回覆"
    
    def test_colloquialize_disabled(self):
        """測試口語化功能停用"""
        # 模擬停用狀態
        with patch.object(settings, 'colloquial_enabled', 0):
            state = {
                "nlg_raw": "正式的資料摘要",
                "query": "AAPL股價"
            }
            
            result = node_colloquialize(state)
            
            assert result["nlg_colloquial"] is None
    
    def test_colloquialize_fallback_no_llm(self):
        """測試口語化回退機制（無 LLM）"""
        with patch.object(settings, 'colloquial_enabled', 1):
            with patch('app.graphs.agent_graph.agent_graph') as mock_agent:
                mock_agent.llm = None
                
                state = {
                    "nlg_raw": "股價資料摘要",
                    "query": "AAPL股價"
                }
                
                result = node_colloquialize(state)
                
                assert "我將為您查詢股價資訊" in result["nlg_colloquial"]
    
    def test_colloquialize_macro_fallback(self):
        """測試總經查詢的口語化回退"""
        with patch.object(settings, 'colloquial_enabled', 1):
            with patch('app.graphs.agent_graph.agent_graph') as mock_agent:
                mock_agent.llm = None
                
                state = {
                    "nlg_raw": "總經數據摘要",
                    "query": "美國CPI"
                }
                
                result = node_colloquialize(state)
                
                assert "我將為您查詢相關的總經數據" in result["nlg_colloquial"]


class TestNLGComposeNode:
    """測試 NLG 組合節點"""
    
    def test_nlg_compose_with_tool_results(self):
        """測試有工具結果的 NLG 組合"""
        state = {
            "tool_results": [
                {
                    "ok": True,
                    "source": "FMP",
                    "data": [{"symbol": "AAPL", "price": 150.0}]
                }
            ],
            "query": "AAPL股價"
        }
        
        result = node_nlg_compose(state)
        
        assert "nlg_raw" in result
        assert result["nlg_raw"] is not None
    
    def test_nlg_compose_empty_results(self):
        """測試無工具結果的 NLG 組合"""
        state = {
            "tool_results": [],
            "query": "測試查詢"
        }
        
        result = node_nlg_compose(state)
        
        assert "nlg_raw" in result
        # 應該有基本的回應，不是空的


class TestToolErrorHandling:
    """測試工具錯誤處理"""
    
    @pytest.mark.asyncio
    async def test_tool_network_error(self):
        """測試工具網路錯誤處理"""
        with patch('app.graphs.agent_graph.fmp_client') as mock_client:
            mock_client.get_quote = AsyncMock(return_value={
                "ok": False,
                "reason": "request_failed",
                "message": "Network error",
                "data": None
            })

            result = await tool_fmp_quote.ainvoke({"symbols": ["AAPL"]})

            assert result["ok"] is False
            assert result["reason"] == "request_failed"
            assert result["message"] == "Network error"
    
    @pytest.mark.asyncio
    async def test_tool_missing_api_key(self):
        """測試工具缺少 API 金鑰"""
        # 暫時移除 API 金鑰
        original_key = os.environ.get("FMP_API_KEY")
        if "FMP_API_KEY" in os.environ:
            del os.environ["FMP_API_KEY"]
        
        try:
            with patch('app.graphs.agent_graph.fmp_client') as mock_client:
                mock_client.get_quote = AsyncMock(return_value={
                    "ok": False,
                    "reason": "missing_api_key"
                })

                result = await tool_fmp_quote.ainvoke({"symbols": ["AAPL"]})

                assert result["ok"] is False
                assert result["reason"] == "missing_api_key"
        
        finally:
            # 恢復原始 API 金鑰
            if original_key:
                os.environ["FMP_API_KEY"] = original_key


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
