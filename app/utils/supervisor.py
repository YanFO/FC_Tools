"""
Supervised Agent Decision-Making Utilities

This module contains functions for supervised agent architecture including
decision-making logic, tool result evaluation, and conversation analysis.
"""

import logging
from typing import Dict, Any, List
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

logger = logging.getLogger(__name__)


def supervisor_copywriting(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    監督式 Agent 決策節點：分析當前狀態並決定下一步行動
    實現完整的監督式架構，包括工具協調、對話管理和終止決策
    
    Args:
        state: Agent state dictionary
        
    Returns:
        Updated state with supervisor decisions
    """
    query = (state.get("query") or "").strip()
    tools = state.get("tool_results") or []
    messages = state.get("messages", [])
    tool_loop_count = state.get("tool_loop_count", 0)
    
    logger.info(f"監督節點分析：查詢='{query}', 工具結果數={len(tools)}, 循環次數={tool_loop_count}")
    
    # 1. 分析當前對話狀態
    conversation_analysis = analyze_conversation_state(state)
    
    # 2. 評估工具執行結果
    tool_effectiveness = evaluate_tool_results(tools, query)
    
    # 3. 監督式決策邏輯
    supervisor_decision = make_supervisor_decision(
        query=query,
        tools=tools,
        messages=messages,
        tool_loop_count=tool_loop_count,
        conversation_analysis=conversation_analysis,
        tool_effectiveness=tool_effectiveness
    )
    
    # 4. 記錄監督決策
    state["supervisor_decision"] = supervisor_decision["decision"]
    state["supervisor_reasoning"] = supervisor_decision["reasoning"]
    state["next_action"] = supervisor_decision["next_action"]
    
    logger.info(f"監督決策：{supervisor_decision['decision']} - {supervisor_decision['reasoning']}")
    
    # 5. 根據決策設置 NLG 參數
    nlg_payload = prepare_nlg_payload(query, tools, supervisor_decision)
    state["nlg_payload"] = nlg_payload
    
    # 6. 處理對話歷史（如果需要）
    if supervisor_decision["decision"] == "end_conversation":
        from app.utils.conversation import prepare_conversation_storage
        prepare_conversation_storage(state)
    
    return state


def analyze_conversation_state(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    分析當前對話狀態
    
    Args:
        state: Agent state dictionary
        
    Returns:
        Dictionary with conversation analysis results
    """
    messages = state.get("messages", [])
    query = state.get("query", "")
    
    # 分析對話複雜度
    user_messages = [msg for msg in messages if isinstance(msg, HumanMessage)]
    ai_messages = [msg for msg in messages if isinstance(msg, AIMessage)]
    
    analysis = {
        "user_message_count": len(user_messages),
        "ai_message_count": len(ai_messages),
        "conversation_turns": len(user_messages),
        "query_complexity": assess_query_complexity(query),
        "requires_multi_step": requires_multi_step_processing(query),
        "has_context_dependency": bool(state.get("parent_session_id"))
    }
    
    return analysis


def evaluate_tool_results(tools: List[Dict[str, Any]], query: str) -> Dict[str, Any]:
    """
    評估工具執行結果的有效性
    
    Args:
        tools: List of tool execution results
        query: Original query string
        
    Returns:
        Dictionary with tool effectiveness metrics
    """
    if not tools:
        return {
            "effectiveness": "no_tools", 
            "completeness": 0.0, 
            "quality": "unknown",
            "query_satisfaction": False,
            "successful_tools": 0,
            "total_tools": 0
        }
    
    # 計算結果完整性
    successful_tools = [t for t in tools if t.get("ok", False)]
    completeness = len(successful_tools) / len(tools) if tools else 0.0
    
    # 評估結果品質
    quality = "high"
    if completeness < 0.5:
        quality = "low"
    elif completeness < 0.8:
        quality = "medium"
    
    # 檢查是否滿足查詢需求
    query_satisfaction = check_query_satisfaction(tools, query)
    
    return {
        "effectiveness": "good" if completeness > 0.7 else "partial" if completeness > 0.3 else "poor",
        "completeness": completeness,
        "quality": quality,
        "query_satisfaction": query_satisfaction,
        "successful_tools": len(successful_tools),
        "total_tools": len(tools)
    }


def make_supervisor_decision(query: str, tools: List[Dict[str, Any]], messages: List[BaseMessage], 
                           tool_loop_count: int, conversation_analysis: Dict[str, Any], 
                           tool_effectiveness: Dict[str, Any]) -> Dict[str, Any]:
    """
    監督式決策邏輯
    
    Args:
        query: User query
        tools: Tool execution results
        messages: Conversation messages
        tool_loop_count: Number of tool execution loops
        conversation_analysis: Conversation state analysis
        tool_effectiveness: Tool effectiveness metrics
        
    Returns:
        Dictionary with supervisor decision and reasoning
    """
    # Import settings here to avoid circular imports
    try:
        from app.settings import settings
        max_loops = getattr(settings, 'max_tool_loops', 3)
    except ImportError:
        max_loops = 3
    
    # 決策因子
    has_sufficient_data = tool_effectiveness["completeness"] > 0.6
    query_satisfied = tool_effectiveness["query_satisfaction"]
    
    # 決策邏輯
    if tool_loop_count >= max_loops:
        return {
            "decision": "end_conversation",
            "reasoning": f"已達到最大工具循環次數 ({max_loops})",
            "next_action": "generate_response"
        }
    
    if not tools and not requires_tools(query):
        return {
            "decision": "end_conversation", 
            "reasoning": "查詢不需要工具支援，可直接回應",
            "next_action": "generate_direct_response"
        }
    
    if has_sufficient_data and query_satisfied:
        return {
            "decision": "end_conversation",
            "reasoning": "已獲得足夠資料且滿足查詢需求",
            "next_action": "generate_response"
        }
    
    if tools and not has_sufficient_data and tool_loop_count < max_loops:
        return {
            "decision": "continue_tools",
            "reasoning": "資料不足，需要更多工具支援",
            "next_action": "retry_tools"
        }
    
    # 預設決策
    return {
        "decision": "end_conversation",
        "reasoning": "基於當前狀態，結束對話並生成回應",
        "next_action": "generate_response"
    }


def prepare_nlg_payload(query: str, tools: List[Dict[str, Any]], supervisor_decision: Dict[str, Any]) -> Dict[str, Any]:
    """
    準備 NLG 處理參數
    
    Args:
        query: User query
        tools: Tool execution results
        supervisor_decision: Supervisor decision dictionary
        
    Returns:
        NLG payload dictionary
    """
    # 判斷任務類型
    is_news = any(k in query for k in ["新聞", "news", "headline", "headlines"])
    is_macro = any(k in query for k in ["CPI", "通膨", "GDP", "失業", "UNEMPLOYMENT", "利率", "FED", "FFR", "總經", "宏觀", "macro", "經濟數據", "經濟指標"])
    is_quote = any(k in query for k in ["股價", "報價", "price", "quote", "ticker"]) or any(
        tool.get("source") == "FMP" and "price" in str(tool) for tool in tools
    )

    return {
        "is_news": is_news, 
        "is_macro": is_macro, 
        "is_quote": is_quote,
        "query": query, 
        "tools": tools,
        "supervisor_decision": supervisor_decision["decision"],
        "supervisor_reasoning": supervisor_decision["reasoning"],
        "response_strategy": supervisor_decision["next_action"]
    }


def assess_query_complexity(query: str) -> str:
    """
    評估查詢複雜度
    
    Args:
        query: User query string
        
    Returns:
        Complexity level: "simple", "medium", or "complex"
    """
    if not query:
        return "simple"
    
    complexity_indicators = ["和", "以及", "還有", "比較", "分析", "趨勢", "預測"]
    if any(indicator in query for indicator in complexity_indicators):
        return "complex"
    elif len(query.split()) > 10:
        return "medium"
    else:
        return "simple"


def requires_multi_step_processing(query: str) -> bool:
    """
    判斷是否需要多步驟處理
    
    Args:
        query: User query string
        
    Returns:
        True if multi-step processing is required
    """
    multi_step_keywords = ["分析", "比較", "報告", "總結", "預測", "建議"]
    return any(keyword in query for keyword in multi_step_keywords)


def check_query_satisfaction(tools: List[Dict[str, Any]], query: str) -> bool:
    """
    檢查工具結果是否滿足查詢需求
    
    Args:
        tools: Tool execution results
        query: User query string
        
    Returns:
        True if query requirements are satisfied
    """
    if not tools:
        return False
    
    # 簡單的滿足度檢查
    successful_tools = [t for t in tools if t.get("ok", False)]
    return len(successful_tools) > 0


def requires_tools(query: str) -> bool:
    """
    判斷查詢是否需要工具支援
    
    Args:
        query: User query string
        
    Returns:
        True if tools are required for the query
    """
    tool_keywords = ["股價", "報價", "新聞", "CPI", "GDP", "price", "quote", "news"]
    return any(keyword in query for keyword in tool_keywords)
