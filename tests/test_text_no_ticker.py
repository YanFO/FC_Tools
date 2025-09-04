"""
測試文字輸入不會錯誤識別為股票代號
"""
import pytest
import sys
from pathlib import Path

# 加入專案根目錄到 Python 路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.graphs.agent_graph import build_graph, extract_tickers, needs_data


class TestTextNoTicker:
    """測試文字不會被錯誤識別為股票代號"""
    
    def test_extract_tickers_no_context(self):
        """測試沒有語境詞時不抽取股票代號"""
        # "hi" 沒有股票相關語境詞，不應該被識別
        result = extract_tickers("hi")
        assert result == []
        
        # "ok" 也不應該被識別
        result = extract_tickers("ok")
        assert result == []
        
        # "AI" 也不應該被識別
        result = extract_tickers("AI")
        assert result == []
    
    def test_extract_tickers_with_context(self):
        """測試有語境詞時才抽取股票代號"""
        # 有 "報價" 語境詞，應該識別 AAPL
        result = extract_tickers("請查 AAPL 報價")
        assert "AAPL" in result
        
        # 有 "股價" 語境詞，應該識別 TSLA
        result = extract_tickers("TSLA 股價如何")
        assert "TSLA" in result
    
    def test_needs_data_no_requirement(self):
        """測試一般問候語不需要資料"""
        result = needs_data("hi")
        assert result["require"] is False
        assert result["tools"] == []
        
        result = needs_data("hello")
        assert result["require"] is False
        assert result["tools"] == []
        
        result = needs_data("你好")
        assert result["require"] is False
        assert result["tools"] == []
    
    def test_needs_data_with_requirement(self):
        """測試有股票查詢需求時需要資料"""
        result = needs_data("請查 AAPL 報價")
        assert result["require"] is True
        assert len(result["tools"]) > 0
        
        # 檢查是否包含報價工具
        tool_names = [tool["name"] for tool in result["tools"]]
        assert "tool_fmp_quote" in tool_names
    
    @pytest.mark.asyncio
    async def test_graph_no_ticker_execution(self):
        """測試圖執行時不會錯誤觸發工具"""
        graph = build_graph()
        
        result = graph.invoke({
            "input_type": "text",
            "query": "hi",
            "messages": [],
            "warnings": [],
            "sources": [],
            "tool_loop_count": 0,
            "tool_call_sigs": []
        }, config={"recursion_limit": 8})
        
        final_response = result.get("final_response", {})
        
        # 應該成功執行
        assert final_response.get("ok") is True
        
        # 不應該有工具結果（因為沒有股票查詢需求）
        tool_results = final_response.get("tool_results", [])
        # 允許空的工具結果或者沒有 FMP 相關的結果
        fmp_results = [tr for tr in tool_results if isinstance(tr, dict) and tr.get("source") == "FMP"]
        assert len(fmp_results) == 0
        
        # 應該有回應文字
        assert final_response.get("response", "").strip()
        
        # 不應該有重複工具呼叫警告
        warnings = final_response.get("warnings", [])
        duplicate_warnings = [w for w in warnings if "duplicate" in str(w)]
        assert len(duplicate_warnings) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
