"""
Response Building and Formatting Utilities

This module contains functions for response building, NLG processing,
tool result aggregation, and output formatting.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from langchain_core.messages import BaseMessage, AIMessage

logger = logging.getLogger(__name__)


def collect_tool_results_and_sources(state: Dict[str, Any]) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    收集所有工具結果和來源資訊（支援複雜的工具訊息解析）

    Args:
        state: Agent state dictionary

    Returns:
        Tuple of (tool_results, sources)
    """
    tool_results = []
    sources = []

    # 定義工具名稱到來源的映射
    TOOL_TO_SOURCE = {
        "tool_fmp": "FMP",
        "tool_file": "FILE",
        "tool_line": "LINE",
        "tool_rag": "RAG",
        "tool_report": "REPORT"
    }

    # 從訊息中解析工具結果
    from langchain_core.messages import ToolMessage

    for m in state.get("messages", []):
        if isinstance(m, ToolMessage):
            result = _parse_tool_content(m.content)
            tool_results.append(result)

            # 補充來源資訊
            tool_name = getattr(m, "name", "unknown")
            source = result.get("source") if isinstance(result, dict) else None

            # 檢查是否為報告生成結果
            if source == "REPORT" or "tool_report_generate" in tool_name:
                source = "REPORT"

            # 如果沒有來源，根據工具名稱推斷
            if not source:
                for tool_prefix, src in TOOL_TO_SOURCE.items():
                    if tool_name.startswith(tool_prefix):
                        source = src
                        break
                if not source:
                    source = "UNKNOWN"

            if source:
                sources.append({
                    "source": source,
                    "timestamp": result.get("timestamp") if isinstance(result, dict) else None,
                    "tool": tool_name
                })

    # 也檢查舊的狀態欄位（向後相容）
    if state.get("fmp_results"):
        tool_results.extend(state["fmp_results"])
        sources.append({"name": "FMP", "type": "financial_data"})

    if state.get("file_results"):
        tool_results.append(state["file_results"])
        sources.append({"name": "File", "type": "document"})

    if state.get("line_results"):
        tool_results.append(state["line_results"])
        sources.append({"name": "LINE", "type": "messaging"})

    if state.get("rag_results"):
        tool_results.append(state["rag_results"])
        sources.append({"name": "RAG", "type": "knowledge_base"})

    if state.get("report_results"):
        tool_results.append(state["report_results"])
        sources.append({"name": "Report", "type": "generated_report"})

    return tool_results, sources


def _parse_tool_content(content: str) -> Dict[str, Any]:
    """
    解析工具訊息內容

    Args:
        content: Tool message content

    Returns:
        Parsed tool result dictionary
    """
    try:
        import json
        if isinstance(content, str):
            return json.loads(content)
        else:
            return content if isinstance(content, dict) else {"content": str(content)}
    except (json.JSONDecodeError, TypeError):
        return {"content": str(content), "ok": False, "reason": "parse_error"}


def build_final_response(state: Dict[str, Any], tool_results: List[Dict[str, Any]], 
                        sources: List[Dict[str, Any]], warnings: List[str]) -> Dict[str, Any]:
    """
    建構最終回應字典
    
    Args:
        state: Agent state dictionary
        tool_results: List of tool execution results
        sources: List of data sources
        warnings: List of warning messages
        
    Returns:
        Final response dictionary
    """
    session_id = state.get("session_id")
    
    return {
        "ok": True,
        "response": state.get("final_response_text", ""),
        "input_type": state["input_type"],
        "tool_results": tool_results,
        "sources": sources,
        "warnings": list(set(warnings)),  # 去重警告
        "tool_call_sigs": state.get("tool_call_sigs", []),
        "timestamp": datetime.now().isoformat(),
        "supervised": True,  # 標記為 supervised 模式
        "session_id": session_id,
        "conversation_stored": bool(session_id),
        "supervisor_decision": state.get("supervisor_decision"),
        "supervisor_reasoning": state.get("supervisor_reasoning"),
        "nlg": {
            "raw": state.get("nlg_raw"),
            "colloquial": state.get("nlg_colloquial"),
            "system_prompt": get_colloquial_system_prompt()
        }
    }


def get_colloquial_system_prompt() -> Optional[str]:
    """
    取得口語化系統提示
    
    Returns:
        Colloquial system prompt or None
    """
    try:
        from app.settings import settings
        return settings.colloquial_system_prompt if settings.colloquial_enabled else None
    except (ImportError, AttributeError):
        return None


def prepare_conversation_for_storage(state: Dict[str, Any], final_response: str) -> None:
    """
    準備對話內容以供儲存
    
    Args:
        state: Agent state dictionary
        final_response: Final response text
    """
    session_id = state.get("session_id")
    if not session_id or not state.get("messages"):
        return
    
    try:
        from app.utils.conversation import prepare_conversation_messages_for_storage
        
        # 準備要儲存的訊息
        messages_to_save = prepare_conversation_messages_for_storage(
            state["messages"], final_response
        )
        
        # 標記需要儲存對話歷史
        state["_save_conversation"] = True
        state["_conversation_messages"] = messages_to_save
        logger.info(f"標記會話 {session_id} 需要儲存對話歷史")
        
    except Exception as e:
        logger.error(f"準備對話歷史儲存失敗: {str(e)}")
        warnings = state.get("warnings", [])
        warnings.append(f"conversation_save_prep_failed: {str(e)}")
        state["warnings"] = warnings


def extract_ai_response_text(messages: List[BaseMessage]) -> str:
    """
    從訊息列表中提取 AI 回應文字
    
    Args:
        messages: List of conversation messages
        
    Returns:
        AI response text
    """
    ai_messages = [msg for msg in messages if isinstance(msg, AIMessage)]
    return ai_messages[-1].content if ai_messages else ""


def format_tool_results_summary(tool_results: List[Dict[str, Any]]) -> str:
    """
    格式化工具結果摘要
    
    Args:
        tool_results: List of tool execution results
        
    Returns:
        Formatted summary string
    """
    if not tool_results:
        return "無工具執行結果"
    
    total_tools = len(tool_results)
    successful_tools = sum(1 for tr in tool_results if isinstance(tr, dict) and tr.get("ok", False))
    
    return f"已執行 {total_tools} 個工具查詢（{successful_tools} 個成功）"


def aggregate_warnings(state: Dict[str, Any], additional_warnings: List[str] = None) -> List[str]:
    """
    聚合所有警告訊息
    
    Args:
        state: Agent state dictionary
        additional_warnings: Additional warnings to include
        
    Returns:
        List of all warnings
    """
    warnings = list(state.get("warnings", []))
    
    if additional_warnings:
        warnings.extend(additional_warnings)
    
    # 去重並排序
    return sorted(list(set(warnings)))


def build_nlg_response(state: Dict[str, Any], ai_text: str) -> str:
    """
    建構 NLG 回應文字
    
    Args:
        state: Agent state dictionary
        ai_text: Original AI response text
        
    Returns:
        Final NLG response text
    """
    # 優先使用口語化回應，其次使用正式摘要
    nlg_colloquial = state.get("nlg_colloquial", "").strip()
    nlg_raw = state.get("nlg_raw", "").strip()
    
    if nlg_colloquial:
        return nlg_colloquial
    elif nlg_raw:
        return nlg_raw
    else:
        return ai_text


def format_response_for_display(response: Dict[str, Any]) -> str:
    """
    格式化回應用於顯示
    
    Args:
        response: Response dictionary
        
    Returns:
        Formatted response string
    """
    if not response:
        return "無回應內容"
    
    if isinstance(response, dict):
        return response.get("response", response.get("content", str(response)))
    else:
        return str(response)


def create_error_response(error_message: str, input_type: str = "unknown") -> Dict[str, Any]:
    """
    創建錯誤回應
    
    Args:
        error_message: Error message
        input_type: Input type for the request
        
    Returns:
        Error response dictionary
    """
    return {
        "ok": False,
        "error": error_message,
        "input_type": input_type,
        "timestamp": datetime.now().isoformat(),
        "supervised": True
    }


def validate_response_completeness(response: Dict[str, Any]) -> Dict[str, Any]:
    """
    驗證回應完整性
    
    Args:
        response: Response dictionary to validate
        
    Returns:
        Validation results dictionary
    """
    required_fields = ["ok", "response", "input_type", "timestamp"]
    missing_fields = [field for field in required_fields if field not in response]
    
    return {
        "is_complete": len(missing_fields) == 0,
        "missing_fields": missing_fields,
        "has_content": bool(response.get("response", "").strip()),
        "has_supervisor_info": bool(response.get("supervisor_decision"))
    }


def enrich_response_with_metadata(response: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
    """
    使用狀態資訊豐富回應
    
    Args:
        response: Base response dictionary
        state: Agent state dictionary
        
    Returns:
        Enriched response dictionary
    """
    # 添加監督式架構資訊
    response["supervised"] = True
    response["supervisor_decision"] = state.get("supervisor_decision")
    response["supervisor_reasoning"] = state.get("supervisor_reasoning")
    
    # 添加會話資訊
    response["session_id"] = state.get("session_id")
    response["conversation_stored"] = bool(state.get("session_id"))
    
    # 添加工具執行資訊
    response["tool_call_sigs"] = state.get("tool_call_sigs", [])
    
    return response
