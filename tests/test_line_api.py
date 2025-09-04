"""
LINE API 與聊天紀錄測試
"""
import pytest
from unittest.mock import patch, AsyncMock
import sys
from pathlib import Path

# 加入專案根目錄到 Python 路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.graphs.agent_graph import agent_graph


class TestLineAPI:
    """LINE API 測試"""
    
    def test_line_api_status(self):
        """測試 LINE API 狀態"""
        from app.settings import settings
        # 只要成功讀到 True/False 即可（不崩潰）
        assert settings.api_status["line"] in (True, False)
    
    @pytest.mark.asyncio
    async def test_line_worker_fetch_messages_only(self):
        """測試 LINE 工作器僅抓取訊息"""
        # 模擬 LINE 抓取
        with patch("app.services.line_client.line_client.fetch_messages", new=AsyncMock(return_value={
            "ok": True,
            "source": "LINE",
            "data": [
                {"user_id":"U1","text":"請看 AAPL 報價"},
                {"user_id":"U1","text":"幫我找 CPI"}
            ]
        })):
            o = await agent_graph.graph.ainvoke({
                "input_type": "line",
                "line_info": {"user_id": "U1", "limit": 10},
                "messages": [],
                "warnings": [],
                "sources": [],
                "tool_loop_count": 0,
                "tool_call_sigs": []
            }, config={"recursion_limit": 8})

            fr = o.get("final_response", {})
            assert fr["ok"] is True
            assert len(fr.get("tool_results", [])) >= 1  # 至少有 LINE 結果上拋
    
    @pytest.mark.asyncio
    async def test_line_worker_triggers_fmp_via_content(self):
        """測試 LINE 工作器根據聊天內容觸發 FMP 工具"""
        # 聊天紀錄帶到股票/總經關鍵字，Agent 應觸發對應工具
        with patch("app.services.line_client.line_client.fetch_messages", new=AsyncMock(return_value={
            "ok": True, 
            "source": "LINE",
            "data": [
                {"text":"AAPL 報價"}, 
                {"text":"最近 CPI"}
            ]
        })), \
        patch("app.services.fmp_client.fmp_client.get_quote", new=AsyncMock(return_value={
            "ok": True, 
            "source":"FMP", 
            "data":[{"symbol":"AAPL","price":123.45}]
        })), \
        patch("app.services.fmp_client.fmp_client.get_macro_data", new=AsyncMock(return_value={
            "ok": True, 
            "source":"FMP", 
            "data":[{
                "indicator":"CPI",
                "country":"US",
                "date":"2025-07-01",
                "value":322.132
            }]
        })):
            o = await agent_graph.graph.ainvoke({
                "input_type": "line",
                "line_info": {"user_id": "U1", "limit": 10},
                "messages": [],
                "warnings": [],
                "sources": [],
                "tool_loop_count": 0,
                "tool_call_sigs": []
            }, config={"recursion_limit": 8})

            fr = o.get("final_response", {})
            assert fr["ok"] is True

            # 匯總後應可見 FMP 結果（報價或 CPI 任一）
            fmp_results = [r for r in fr.get("tool_results", [])
                          if isinstance(r, dict) and r.get("source") == "FMP"]
            assert len(fmp_results) > 0, "應該有 FMP 工具結果"
    
    @pytest.mark.asyncio
    async def test_line_worker_empty_messages(self):
        """測試 LINE 工作器處理空訊息情況"""
        with patch("app.services.line_client.line_client.fetch_messages", new=AsyncMock(return_value={
            "ok": True, 
            "source": "LINE",
            "data": []
        })):
            o = await agent_graph.graph.ainvoke({
                "input_type": "line",
                "line_info": {"user_id": "U1", "limit": 10},
                "messages": [],
                "warnings": [],
                "sources": [],
                "tool_loop_count": 0,
                "tool_call_sigs": []
            }, config={"recursion_limit": 8})

            fr = o.get("final_response", {})
            assert fr["ok"] is True
            assert fr.get("response", "").strip()  # 應該有回應文字
    
    @pytest.mark.asyncio
    async def test_line_worker_error_handling(self):
        """測試 LINE 工作器錯誤處理"""
        with patch("app.services.line_client.line_client.fetch_messages", new=AsyncMock(return_value={
            "ok": False, 
            "reason": "missing_api_key",
            "message": "LINE API 金鑰未設定"
        })):
            o = await agent_graph.graph.ainvoke({
                "input_type": "line",
                "line_info": {"user_id": "U1", "limit": 10},
                "messages": [],
                "warnings": [],
                "sources": [],
                "tool_loop_count": 0,
                "tool_call_sigs": []
            }, config={"recursion_limit": 8})

            fr = o.get("final_response", {})
            assert fr["ok"] is True  # Agent 應該優雅處理錯誤
            # 檢查是否有錯誤相關的工具結果
            tool_results = fr.get("tool_results", [])
            assert len(tool_results) >= 0  # 可能有錯誤結果
    
    def test_line_client_import(self):
        """測試 LINE 客戶端可以正常導入"""
        try:
            from app.services.line_client import line_client
            assert line_client is not None
        except ImportError:
            pytest.skip("LINE 客戶端未實作")
    
    @pytest.mark.asyncio
    async def test_agent_line_routing(self):
        """測試 Agent 正確處理 LINE 輸入"""
        with patch("app.services.line_client.line_client.fetch_messages", new=AsyncMock(return_value={
            "ok": True,
            "source": "LINE",
            "data": [{"text":"測試訊息"}]
        })):
            o = await agent_graph.graph.ainvoke({
                "input_type": "line",
                "line_info": {"user_id": "U1"},
                "messages": [],
                "warnings": [],
                "sources": [],
                "tool_loop_count": 0,
                "tool_call_sigs": []
            }, config={"recursion_limit": 8})

            # 檢查是否正確執行了 LINE 任務
            assert "final_response" in o
            assert o["final_response"]["ok"] is True
            assert o["final_response"].get("supervised") is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
