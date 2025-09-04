"""
測試股價、新聞、總經三類查詢的工具執行
驗證 EXECUTE_TOOLS=1 時工具會被實際執行，並檢查錯誤處理
"""
import pytest
from unittest.mock import patch

from app.graphs.agent_graph import agent_graph
from app.settings import settings


class TestQuoteNewsMacro:
    """測試股價、新聞、總經查詢功能"""
    
    @pytest.mark.asyncio
    async def test_stock_quote_tool_execution(self):
        """測試股價查詢工具執行"""
        input_data = {
            "input_type": "text",
            "query": "請問 AAPL 股價？",
            "options": {"temperature": 0}
        }
        
        # 執行 Agent
        result = await agent_graph.run(input_data)
        
        assert result is not None, "Agent 執行應該成功"
        
        # 檢查是否有工具執行結果
        tool_results = result.get("tool_results", [])
        
        if settings.fmp_api_key:
            # 有 API 金鑰時，應該執行工具
            assert len(tool_results) > 0, "應該有工具執行結果"
            
            # 檢查工具結果中是否包含股價相關工具
            tool_names = [tr.get("tool", "") for tr in tool_results]
            assert any("quote" in tool_name.lower() for tool_name in tool_names), "應該執行股價查詢工具"
            
            # 檢查回應格式（應該是純文字）
            response = result.get("response", "")
            assert len(response) > 0, "應該有回應內容"
            assert "AAPL" in response, "回應應該包含股票代號"
            
            # 檢查不是 JSON 或 Markdown 格式
            assert not response.strip().startswith("{"), "回應不應該是 JSON 格式"
            assert not response.strip().startswith("|"), "回應不應該是表格格式"
            
        else:
            # 沒有 API 金鑰時，應該回傳錯誤
            response = result.get("response", "")
            assert "missing_api_key" in response.lower() or "api" in response.lower(), "應該提及 API 金鑰問題"
    
    @pytest.mark.asyncio
    async def test_stock_news_tool_execution(self):
        """測試股票新聞查詢工具執行"""
        input_data = {
            "input_type": "text",
            "query": "請給我 AAPL 最近的 5 則新聞重點",
            "options": {"temperature": 0}
        }
        
        # 執行 Agent
        result = await agent_graph.run(input_data)
        
        assert result is not None, "Agent 執行應該成功"
        
        # 檢查工具執行
        tool_results = result.get("tool_results", [])
        
        if settings.fmp_api_key:
            # 有 API 金鑰時，應該執行工具
            assert len(tool_results) > 0, "應該有工具執行結果"
            
            # 檢查工具結果中是否包含新聞相關工具
            tool_names = [tr.get("tool", "") for tr in tool_results]
            assert any("news" in tool_name.lower() for tool_name in tool_names), "應該執行新聞查詢工具"
            
            # 檢查回應內容
            response = result.get("response", "")
            assert len(response) > 0, "應該有回應內容"
            
            # 檢查回應格式（條列新聞）
            if "無新聞" not in response and "沒有" not in response:
                # 如果有新聞，應該是條列格式
                assert any(indicator in response for indicator in ["1.", "2.", "•", "-", "｜"]), "新聞應該以條列格式呈現"
        else:
            # 沒有 API 金鑰時，應該回傳錯誤
            response = result.get("response", "")
            assert "missing_api_key" in response.lower() or "api" in response.lower(), "應該提及 API 金鑰問題"
    
    @pytest.mark.asyncio
    async def test_macro_data_tool_execution(self):
        """測試總經數據查詢工具執行"""
        input_data = {
            "input_type": "text",
            "query": "美國最新失業率多少？",
            "options": {"temperature": 0}
        }
        
        # 執行 Agent
        result = await agent_graph.run(input_data)
        
        assert result is not None, "Agent 執行應該成功"
        
        # 檢查工具執行
        tool_results = result.get("tool_results", [])
        
        if settings.fmp_api_key:
            # 有 API 金鑰時，應該執行工具
            assert len(tool_results) > 0, "應該有工具執行結果"
            
            # 檢查工具結果中是否包含總經相關工具
            tool_names = [tr.get("tool", "") for tr in tool_results]
            assert any("macro" in tool_name.lower() or "economic" in tool_name.lower() for tool_name in tool_names), "應該執行總經查詢工具"
            
            # 檢查回應內容
            response = result.get("response", "")
            assert len(response) > 0, "應該有回應內容"
            
            # 檢查回應包含相關關鍵詞
            keywords = ["失業率", "unemployment", "%", "美國"]
            assert any(keyword in response for keyword in keywords), "回應應該包含相關關鍵詞"
        else:
            # 沒有 API 金鑰時，應該回傳錯誤
            response = result.get("response", "")
            assert "missing_api_key" in response.lower() or "api" in response.lower(), "應該提及 API 金鑰問題"
    
    @pytest.mark.asyncio
    async def test_execute_tools_setting_respected(self):
        """測試 EXECUTE_TOOLS 設定被正確遵循"""
        input_data = {
            "input_type": "text",
            "query": "請問 AAPL 股價？",
            "options": {"temperature": 0}
        }
        
        # 測試 EXECUTE_TOOLS=1（預設）
        with patch.object(settings, 'execute_tools', 1):
            result = await agent_graph.run(input_data)
            
            if settings.fmp_api_key:
                tool_results = result.get("tool_results", [])
                assert len(tool_results) > 0, "EXECUTE_TOOLS=1 時應該執行工具"
        
        # 測試 EXECUTE_TOOLS=0（僅規劃）
        with patch.object(settings, 'execute_tools', 0):
            result = await agent_graph.run(input_data)
            
            # 在僅規劃模式下，可能有工具規劃但不執行
            # 具體行為取決於 agent_graph 的實作
            assert result is not None, "EXECUTE_TOOLS=0 時 Agent 仍應正常回應"
    
    @pytest.mark.asyncio
    async def test_missing_api_key_error_handling(self):
        """測試缺少 API 金鑰時的錯誤處理"""
        input_data = {
            "input_type": "text",
            "query": "請問 TSLA 股價？",
            "options": {"temperature": 0}
        }
        
        # 模擬沒有 API 金鑰的情況
        with patch.object(settings, 'fmp_api_key', None):
            result = await agent_graph.run(input_data)
            
            assert result is not None, "即使沒有 API 金鑰也應該有回應"
            
            response = result.get("response", "")
            
            # 檢查錯誤處理
            error_indicators = ["missing_api_key", "API 金鑰", "設定", "環境變數"]
            assert any(indicator in response for indicator in error_indicators), f"應該提及 API 金鑰問題，實際回應: {response}"
            
            # 確保沒有捏造數據
            fabricated_indicators = ["$", "美元", "漲", "跌", "%"]
            assert not any(indicator in response for indicator in fabricated_indicators), "不應該包含捏造的價格資訊"
    
    @pytest.mark.asyncio
    async def test_upstream_error_handling(self):
        """測試上游服務錯誤處理"""
        input_data = {
            "input_type": "text",
            "query": "請問 NVDA 股價？",
            "options": {"temperature": 0}
        }
        
        # 模擬上游 API 錯誤
        with patch('app.services.fmp_client.fmp_client.get_quote') as mock_get_quote:
            mock_get_quote.return_value = {
                "ok": False,
                "reason": "upstream_error",
                "message": "FMP API 服務暫時不可用"
            }
            
            result = await agent_graph.run(input_data)
            
            assert result is not None, "即使上游錯誤也應該有回應"
            
            response = result.get("response", "")
            
            # 檢查錯誤處理
            error_indicators = ["upstream_error", "服務", "錯誤", "暫時", "不可用"]
            assert any(indicator in response for indicator in error_indicators), f"應該提及上游錯誤，實際回應: {response}"
            
            # 確保沒有捏造數據
            assert "$" not in response, "不應該包含捏造的價格資訊"
    
    @pytest.mark.asyncio
    async def test_tool_results_structure(self):
        """測試工具執行結果的結構"""
        input_data = {
            "input_type": "text",
            "query": "請問 MSFT 股價？",
            "options": {"temperature": 0}
        }
        
        result = await agent_graph.run(input_data)
        
        if settings.fmp_api_key:
            tool_results = result.get("tool_results", [])
            
            if len(tool_results) > 0:
                # 檢查工具結果結構
                for tool_result in tool_results:
                    assert isinstance(tool_result, dict), "工具結果應該是字典"
                    
                    # 檢查必要欄位
                    expected_fields = ["tool", "input", "output"]
                    for field in expected_fields:
                        assert field in tool_result, f"工具結果應該包含 {field} 欄位"
                    
                    # 檢查工具名稱
                    tool_name = tool_result.get("tool", "")
                    assert len(tool_name) > 0, "工具名稱不應為空"
    
    @pytest.mark.asyncio
    async def test_response_format_compliance(self):
        """測試回應格式合規性"""
        test_queries = [
            ("請問 AAPL 股價？", "quote"),
            ("TSLA 最近新聞", "news"),
            ("美國 GDP 數據", "macro")
        ]
        
        for query, expected_type in test_queries:
            input_data = {
                "input_type": "text",
                "query": query,
                "options": {"temperature": 0}
            }
            
            result = await agent_graph.run(input_data)
            response = result.get("response", "")
            
            # 檢查回應不是 JSON 格式
            assert not response.strip().startswith("{"), f"回應不應該是 JSON 格式: {query}"
            assert not response.strip().startswith("["), f"回應不應該是 JSON 陣列格式: {query}"
            
            # 檢查回應不是 Markdown 表格
            assert not response.strip().startswith("|"), f"回應不應該是 Markdown 表格: {query}"
            
            # 檢查回應是純文字且有意義
            assert len(response.strip()) > 10, f"回應應該有足夠內容: {query}"


if __name__ == "__main__":
    # 執行測試
    pytest.main([__file__, "-v"])
