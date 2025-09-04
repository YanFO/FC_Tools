"""
Agent 流程測試
測試四種輸入類型的 Agent 執行流程
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import sys
from pathlib import Path

# 加入專案根目錄到 Python 路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.graphs.agent_graph import AgentGraph, agent_graph


class TestAgentGraph:
    """Agent Graph 測試類別"""
    
    @pytest.fixture
    def mock_agent_graph(self):
        """建立模擬的 Agent Graph"""
        with patch('app.graphs.agent_graph.ChatOpenAI') as mock_llm:
            mock_llm.return_value = MagicMock()
            graph = AgentGraph()
            return graph
    
    @pytest.fixture
    def sample_text_input(self):
        """範例文字輸入"""
        return {
            "input_type": "text",
            "query": "請給我 AAPL 的最新報價",
            "options": {
                "lang": "tw",
                "top_k": 5
            }
        }
    
    @pytest.fixture
    def sample_file_input(self):
        """範例檔案輸入"""
        return {
            "input_type": "file",
            "query": "這份文件的主要內容是什麼？",
            "file": {
                "path": "./test_document.pdf",
                "task": "qa"
            },
            "options": {
                "lang": "tw"
            }
        }
    
    @pytest.fixture
    def sample_line_input(self):
        """範例 LINE 輸入"""
        return {
            "input_type": "line",
            "line": {
                "user_id": "U1234567890",
                "start": "2025-08-01T00:00:00Z",
                "end": "2025-09-01T23:59:59Z"
            },
            "options": {
                "lang": "tw"
            }
        }
    
    @pytest.fixture
    def sample_rule_input(self):
        """範例規則輸入"""
        return {
            "input_type": "rule",
            "rule": {
                "symbols": ["AAPL", "GOOGL"],
                "conditions": {
                    "price_change": "> 5%",
                    "volume": "> 1000000"
                }
            },
            "options": {
                "lang": "tw"
            }
        }
    
    def test_agent_graph_initialization(self, mock_agent_graph):
        """測試 Agent Graph 初始化"""
        assert mock_agent_graph is not None
        assert mock_agent_graph.llm is not None
        assert mock_agent_graph.graph is not None
    
    def test_input_router_text(self, mock_agent_graph):
        """測試文字輸入路由"""
        state = {
            "input_type": "text",
            "query": "test query",
            "messages": [],
            "warnings": [],
            "sources": []
        }
        
        result_state = mock_agent_graph.input_router(state)
        
        assert result_state["input_type"] == "text"
        assert "warnings" in result_state
        assert "sources" in result_state
    
    def test_route_input_decision(self, mock_agent_graph):
        """測試路由決策函數"""
        test_cases = [
            {"input_type": "text", "expected": "text"},
            {"input_type": "file", "expected": "file"},
            {"input_type": "line", "expected": "line"},
            {"input_type": "rule", "expected": "rule"}
        ]
        
        for case in test_cases:
            state = {"input_type": case["input_type"]}
            result = mock_agent_graph.route_input(state)
            assert result == case["expected"]
    
    def test_text_pipeline(self, mock_agent_graph):
        """測試文字處理管線"""
        state = {
            "input_type": "text",
            "query": "AAPL 股價如何？",
            "warnings": []
        }
        
        result_state = mock_agent_graph.text_pipeline(state)
        
        assert "messages" in result_state
        assert len(result_state["messages"]) > 0
        assert "AAPL" in result_state["messages"][0].content
    
    def test_text_pipeline_empty_query(self, mock_agent_graph):
        """測試空查詢的文字處理管線"""
        state = {
            "input_type": "text",
            "query": "",
            "warnings": []
        }
        
        result_state = mock_agent_graph.text_pipeline(state)
        
        assert "查詢文字為空" in result_state["warnings"]
    
    def test_file_pipeline_qa(self, mock_agent_graph):
        """測試檔案 QA 管線"""
        state = {
            "input_type": "file",
            "query": "文件內容是什麼？",
            "file_info": {
                "path": "./test.pdf",
                "task": "qa"
            },
            "warnings": []
        }
        
        result_state = mock_agent_graph.file_pipeline(state)
        
        assert "messages" in result_state
        assert len(result_state["messages"]) > 0
        assert "tool_file_load" in result_state["messages"][0].content
        assert "tool_rag_query" in result_state["messages"][0].content
    
    def test_file_pipeline_report(self, mock_agent_graph):
        """測試檔案報告管線"""
        state = {
            "input_type": "file",
            "file_info": {
                "path": "./test.pdf",
                "task": "report",
                "template_id": "file_summary"
            },
            "warnings": []
        }
        
        result_state = mock_agent_graph.file_pipeline(state)
        
        assert "messages" in result_state
        assert "tool_report_generate" in result_state["messages"][0].content
    
    def test_file_pipeline_missing_path(self, mock_agent_graph):
        """測試缺少檔案路徑的情況"""
        state = {
            "input_type": "file",
            "file_info": {},
            "warnings": []
        }
        
        result_state = mock_agent_graph.file_pipeline(state)
        
        assert "檔案路徑未提供" in result_state["warnings"]
    
    def test_line_pipeline(self, mock_agent_graph):
        """測試 LINE 處理管線"""
        state = {
            "input_type": "line",
            "line_info": {
                "user_id": "U1234567890",
                "start": "2025-08-01",
                "end": "2025-09-01"
            },
            "warnings": []
        }
        
        result_state = mock_agent_graph.line_pipeline(state)
        
        assert "messages" in result_state
        assert "tool_line_fetch" in result_state["messages"][0].content
    
    def test_line_pipeline_missing_id(self, mock_agent_graph):
        """測試缺少 ID 的 LINE 管線"""
        state = {
            "input_type": "line",
            "line_info": {},
            "warnings": []
        }
        
        result_state = mock_agent_graph.line_pipeline(state)
        
        assert "需要提供 user_id 或 chat_id" in result_state["warnings"]
    
    def test_rule_pipeline(self, mock_agent_graph):
        """測試規則處理管線"""
        state = {
            "input_type": "rule",
            "rule_info": {
                "symbols": ["AAPL", "GOOGL"],
                "conditions": {"price_change": "> 5%"}
            },
            "warnings": []
        }
        
        result_state = mock_agent_graph.rule_pipeline(state)
        
        assert "messages" in result_state
        assert "AAPL" in result_state["messages"][0].content
    
    def test_should_continue_with_tool_calls(self, mock_agent_graph):
        """測試有工具呼叫時的繼續決策"""
        # 模擬有 tool_calls 的訊息
        mock_message = MagicMock()
        mock_message.tool_calls = [{"name": "tool_fmp_quote"}]
        
        state = {
            "messages": [mock_message]
        }
        
        result = mock_agent_graph.should_continue(state)
        assert result == "continue"
    
    def test_should_continue_without_tool_calls(self, mock_agent_graph):
        """測試沒有工具呼叫時的結束決策"""
        # 模擬沒有 tool_calls 的訊息
        mock_message = MagicMock()
        mock_message.tool_calls = None
        
        state = {
            "messages": [mock_message]
        }
        
        result = mock_agent_graph.should_continue(state)
        assert result == "end"
    
    def test_response_builder(self, mock_agent_graph):
        """測試回應建構器"""
        from langchain_core.messages import AIMessage, ToolMessage
        
        state = {
            "input_type": "text",
            "messages": [
                AIMessage(content="這是 AI 的回應"),
                ToolMessage(content='{"ok": true, "source": "FMP"}', name="tool_fmp_quote", tool_call_id="t_1")
            ],
            "warnings": ["測試警告"],
            "sources": [],
            "tool_call_sigs": []
        }
        
        result_state = mock_agent_graph.response_builder(state)
        
        assert "final_response" in result_state
        assert result_state["final_response"]["ok"] is True
        assert result_state["final_response"]["input_type"] == "text"
        assert len(result_state["final_response"]["warnings"]) > 0


class TestAgentExecution:
    """Agent 執行測試"""
    
    @pytest.mark.asyncio
    async def test_run_text_input_success(self, sample_text_input):
        """測試成功執行文字輸入"""
        with patch.object(agent_graph, 'graph') as mock_graph:
            # 模擬成功的執行結果
            mock_result = {
                "final_response": {
                    "ok": True,
                    "response": "AAPL 當前價格為 $150.25",
                    "input_type": "text",
                    "tool_results": [],
                    "sources": [],
                    "warnings": [],
                    "timestamp": "2025-09-01T12:00:00Z"
                }
            }
            
            mock_graph.ainvoke = AsyncMock(return_value=mock_result)
            
            result = await agent_graph.run(sample_text_input)
            
            assert result["ok"] is True
            assert "AAPL" in result["response"]
            assert result["input_type"] == "text"
    
    @pytest.mark.asyncio
    async def test_run_file_input_success(self, sample_file_input):
        """測試成功執行檔案輸入"""
        with patch.object(agent_graph, 'graph') as mock_graph:
            mock_result = {
                "final_response": {
                    "ok": True,
                    "response": "文件主要討論了市場分析...",
                    "input_type": "file",
                    "tool_results": [],
                    "sources": [],
                    "warnings": [],
                    "timestamp": "2025-09-01T12:00:00Z"
                }
            }
            
            mock_graph.ainvoke = AsyncMock(return_value=mock_result)
            
            result = await agent_graph.run(sample_file_input)
            
            assert result["ok"] is True
            assert result["input_type"] == "file"
    
    @pytest.mark.asyncio
    async def test_run_execution_error(self, sample_text_input):
        """測試執行錯誤情況"""
        with patch.object(agent_graph, 'graph') as mock_graph:
            # 模擬執行錯誤
            mock_graph.ainvoke = AsyncMock(side_effect=Exception("測試錯誤"))
            
            result = await agent_graph.run(sample_text_input)
            
            assert result["ok"] is False
            assert "測試錯誤" in result["error"]
            assert result["input_type"] == "text"
    
    @pytest.mark.asyncio
    async def test_run_invalid_input_type(self):
        """測試無效的輸入類型"""
        invalid_input = {
            "input_type": "invalid_type",
            "query": "test"
        }
        
        # 這應該在路由階段處理，但我們測試錯誤處理
        result = await agent_graph.run(invalid_input)
        
        # 應該回傳錯誤或處理無效輸入
        assert "ok" in result


class TestAgentIntegration:
    """Agent 整合測試"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_end_to_end_text_flow(self):
        """端到端文字流程測試"""
        # 這個測試需要真實的 API 金鑰才能完整執行
        input_data = {
            "input_type": "text",
            "query": "測試查詢",
            "options": {"lang": "tw"}
        }
        
        # 由於沒有真實 API 金鑰，我們主要測試結構
        try:
            result = await agent_graph.run(input_data)
            # 無論成功或失敗，都應該有結構化回應
            assert isinstance(result, dict)
            assert "ok" in result
            assert "input_type" in result
        except Exception as e:
            # 預期可能的錯誤（如缺少 API 金鑰）
            assert "API" in str(e) or "金鑰" in str(e)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
