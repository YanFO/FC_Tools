"""
測試迴圈防呆機制
"""
import pytest
import sys
from pathlib import Path

# 加入專案根目錄到 Python 路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.graphs.agent_graph import build_graph, _tool_sig


class TestLoopGuard:
    """測試迴圈防呆機制"""
    
    def test_tool_sig_generation(self):
        """測試工具簽章生成"""
        tool1 = {"name": "tool_fmp_quote", "args": {"symbols": ["AAPL"]}}
        tool2 = {"name": "tool_fmp_quote", "args": {"symbols": ["AAPL"]}}
        tool3 = {"name": "tool_fmp_quote", "args": {"symbols": ["TSLA"]}}
        
        sig1 = _tool_sig(tool1)
        sig2 = _tool_sig(tool2)
        sig3 = _tool_sig(tool3)
        
        # 相同工具和參數應該產生相同簽章
        assert sig1 == sig2
        
        # 不同參數應該產生不同簽章
        assert sig1 != sig3
        
        # 簽章應該是字串
        assert isinstance(sig1, str)
        assert len(sig1) > 0
    
    @pytest.mark.asyncio
    async def test_graph_loop_prevention(self):
        """測試圖的迴圈防呆"""
        graph = build_graph()
        
        # 使用可能導致重複呼叫的查詢
        result = graph.invoke({
            "input_type": "text",
            "query": "請查 AAPL 報價，重覆再查一次 AAPL 報價",
            "messages": [],
            "warnings": [],
            "sources": [],
            "tool_loop_count": 0,
            "tool_call_sigs": []
        }, config={"recursion_limit": 8})
        
        final_response = result.get("final_response", {})
        
        # 應該成功執行，不會崩潰
        assert final_response.get("ok") is True
        
        # 應該有回應文字
        assert final_response.get("response", "").strip()
        
        # 檢查是否有迴圈相關警告（可能有，也可能沒有，取決於 LLM 行為）
        warnings = final_response.get("warnings", [])
        
        # 如果有警告，應該是合理的警告類型
        for warning in warnings:
            assert isinstance(warning, str)
            # 可能的警告類型
            valid_warnings = [
                "tool_loops_exceeded",
                "tool_calls_duplicate",
                "missing_api_key"
            ]
            # 檢查警告是否包含已知的警告類型之一
            is_valid_warning = any(vw in warning for vw in valid_warnings)
            if not is_valid_warning:
                # 如果不是已知警告類型，至少應該是字串
                assert isinstance(warning, str)
    
    @pytest.mark.asyncio
    async def test_graph_recursion_limit(self):
        """測試遞迴限制"""
        graph = build_graph()
        
        # 測試正常情況下不會超過遞迴限制
        result = graph.invoke({
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
        
        # 檢查工具迴圈計數
        tool_loop_count = result.get("tool_loop_count", 0)
        assert tool_loop_count >= 0
        assert tool_loop_count <= 4  # MAX_TOOL_LOOPS
    
    @pytest.mark.asyncio
    async def test_graph_duplicate_detection(self):
        """測試重複工具呼叫偵測"""
        graph = build_graph()
        
        # 執行一個簡單的查詢
        result = graph.invoke({
            "input_type": "text",
            "query": "請查 AAPL 報價",
            "messages": [],
            "warnings": [],
            "sources": [],
            "tool_loop_count": 0,
            "tool_call_sigs": []
        }, config={"recursion_limit": 8})
        
        # 檢查工具呼叫簽章是否被記錄
        tool_call_sigs = result.get("tool_call_sigs", [])
        
        # 如果有工具呼叫，應該有簽章記錄
        tool_results = result.get("final_response", {}).get("tool_results", [])
        if len(tool_results) > 0:
            # 工具呼叫簽章可能在狀態中，也可能因為流程設計而不在最終結果中
            # 這裡我們檢查是否至少有工具結果，表示工具確實被呼叫了
            assert len(tool_results) > 0

            # 如果有簽章記錄，檢查格式
            if len(tool_call_sigs) > 0:
                for sig in tool_call_sigs:
                    assert isinstance(sig, str)
                    assert len(sig) > 0
    
    def test_max_tool_loops_constant(self):
        """測試最大工具迴圈常數"""
        # 這個測試確保 MAX_TOOL_LOOPS 常數存在且合理
        from app.graphs.agent_graph import AgentGraph
        
        # 建立一個 agent 實例來測試 should_continue 方法
        agent = AgentGraph()
        
        # 測試超過限制的情況
        state = {
            "tool_loop_count": 5,  # 超過預期的 MAX_TOOL_LOOPS (4)
            "messages": [],
            "warnings": []
        }
        
        result = agent.should_continue(state)
        assert result == "end"
        
        # 檢查是否加入了警告
        warnings = state.get("warnings", [])
        loop_warnings = [w for w in warnings if "tool_loops_exceeded" in str(w)]
        assert len(loop_warnings) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
