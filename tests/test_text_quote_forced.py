"""
測試股票查詢強制工具呼叫
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import patch, AsyncMock

# 加入專案根目錄到 Python 路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.graphs.agent_graph import build_graph, needs_data


class TestTextQuoteForced:
    """測試股票查詢必須呼叫工具"""
    
    def test_needs_data_aapl_query(self):
        """測試 AAPL 查詢需求偵測"""
        result = needs_data("請查 AAPL 報價")
        
        assert result["require"] is True
        assert len(result["tools"]) > 0
        
        # 檢查工具名稱
        tool_names = [tool["name"] for tool in result["tools"]]
        assert "tool_fmp_quote" in tool_names
        
        # 檢查參數
        quote_tools = [tool for tool in result["tools"] if tool["name"] == "tool_fmp_quote"]
        assert len(quote_tools) > 0
        assert "AAPL" in quote_tools[0]["args"]["symbols"]
    
    def test_needs_data_multiple_symbols(self):
        """測試多個股票代號查詢"""
        result = needs_data("請查 AAPL 和 TSLA 的報價")
        
        assert result["require"] is True
        
        # 檢查是否包含兩個股票代號
        quote_tools = [tool for tool in result["tools"] if tool["name"] == "tool_fmp_quote"]
        assert len(quote_tools) > 0
        symbols = quote_tools[0]["args"]["symbols"]
        assert "AAPL" in symbols
        assert "TSLA" in symbols
    
    @pytest.mark.asyncio
    async def test_graph_forced_tool_execution(self):
        """測試圖強制執行工具"""
        # 添加 mock 來模擬 FMP API 響應
        with patch("app.graphs.agent_graph.fmp_client.get_quote", new=AsyncMock(return_value={
            "ok": True,
            "source": "FMP",
            "data": [{"symbol": "AAPL", "price": 150.25, "change": 2.15, "changesPercentage": 1.45}]
        })), \
        patch("app.graphs.agent_graph.fmp_client.get_profile", new=AsyncMock(return_value={
            "ok": True,
            "source": "FMP",
            "data": [{"symbol": "AAPL", "companyName": "Apple Inc.", "industry": "Technology"}]
        })), \
        patch("app.graphs.agent_graph.fmp_client.get_news", new=AsyncMock(return_value={
            "ok": True,
            "source": "FMP",
            "data": [{"title": "Apple News", "text": "Apple stock rises", "symbol": "AAPL"}]
        })):
            graph = build_graph()

            result = await graph.ainvoke({
                "input_type": "text",
                "query": "請查 AAPL 報價",
                "messages": [],
                "warnings": [],
                "sources": [],
                "tool_loop_count": 0,
                "tool_call_sigs": []
            }, config={"recursion_limit": 8})

            final_response = result.get("final_response", {})

            # 應該成功執行
            assert final_response.get("ok") is True

            # 應該有工具結果
            tool_results = final_response.get("tool_results", [])
            assert len(tool_results) > 0

            # 檢查工具結果是否包含實際數據
            # 工具結果應該包含字典格式的數據
            dict_results = [tr for tr in tool_results if isinstance(tr, dict)]
            assert len(dict_results) > 0

            # 檢查是否有實際的數據內容（不只是空字典）
            non_empty_results = [tr for tr in dict_results if tr and len(tr) > 0]
            assert len(non_empty_results) > 0

            # 應該有回應文字
            assert final_response.get("response", "").strip()
    
    @pytest.mark.asyncio
    async def test_graph_macro_data_forced(self):
        """測試總經數據查詢強制執行工具"""
        graph = build_graph()
        
        result = graph.invoke({
            "input_type": "text",
            "query": "請查詢最新的 CPI 數據",
            "messages": [],
            "warnings": [],
            "sources": [],
            "tool_loop_count": 0,
            "tool_call_sigs": []
        }, config={"recursion_limit": 8})
        
        final_response = result.get("final_response", {})
        
        # 應該成功執行
        assert final_response.get("ok") is True
        
        # 應該有工具結果
        tool_results = final_response.get("tool_results", [])
        assert len(tool_results) > 0
        
        # 應該有回應文字
        assert final_response.get("response", "").strip()
    
    def test_needs_data_cpi_query(self):
        """測試 CPI 查詢需求偵測"""
        result = needs_data("請查詢最新的 CPI 數據")
        
        assert result["require"] is True
        assert len(result["tools"]) > 0
        
        # 檢查工具名稱
        tool_names = [tool["name"] for tool in result["tools"]]
        assert "tool_fmp_macro" in tool_names
        
        # 檢查參數
        macro_tools = [tool for tool in result["tools"] if tool["name"] == "tool_fmp_macro"]
        assert len(macro_tools) > 0
        assert macro_tools[0]["args"]["indicator"] == "CPI"
        assert macro_tools[0]["args"]["country"] == "US"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
