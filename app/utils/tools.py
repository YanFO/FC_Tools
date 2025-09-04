"""
Tool Definitions and Management Utilities

This module contains all tool function definitions, tool binding and configuration logic,
tool validation and parameter handling, and tool result processing functions.
"""

import logging
import json
from typing import Dict, Any, List, Optional
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# Tool to source mapping
TOOL_TO_SOURCE = {
    "tool_fmp_quote": "FMP",
    "tool_fmp_profile": "FMP", 
    "tool_fmp_news": "FMP",
    "tool_fmp_macro": "FMP",
    "tool_file_load": "FILE",
    "tool_rag_query": "RAG",
    "tool_report_generate": "REPORT",
    "tool_line_fetch": "LINE"
}

# Context tokens for query analysis
CONTEXT_TOKENS = {"股價", "報價", "行情", "股票", "代號", "price", "quote", "ticker", "查", "查詢", "quotes", "新聞", "news", "重點", "headlines", "stock", "stocks", "data", "show", "get"}
MACRO_KWS = {"CPI", "PPI", "GDP", "UNEMPLOYMENT", "NFP", "FED", "RATE", "利率", "通膨", "失業率"}


# =============================================================================
# FMP Tools
# =============================================================================

@tool
async def tool_fmp_quote(symbols: List[str]) -> Dict[str, Any]:
    """
    取得股票報價資訊
    
    Args:
        symbols: 股票代號列表，例如 ["AAPL", "TSLA", "GOOGL"]
        
    Returns:
        包含股票報價資訊的字典
    """
    logger.info(f"呼叫 FMP 報價工具: {symbols}")
    try:
        from app.services.fmp_client import fmp_client
        return await fmp_client.get_quote(symbols)
    except Exception as e:
        logger.error(f"FMP 報價工具執行失敗: {str(e)}")
        return {"ok": False, "reason": str(e), "source": "FMP"}


@tool
async def tool_fmp_profile(symbols: List[str]) -> Dict[str, Any]:
    """
    取得公司基本資料和簡介
    
    Args:
        symbols: 股票代號列表，例如 ["AAPL", "TSLA", "GOOGL"]
        
    Returns:
        包含公司基本資料的字典
    """
    logger.info(f"呼叫 FMP 公司資料工具: {symbols}")
    try:
        from app.services.fmp_client import fmp_client
        return await fmp_client.get_profile(symbols)
    except Exception as e:
        logger.error(f"FMP 公司資料工具執行失敗: {str(e)}")
        return {"ok": False, "reason": str(e), "source": "FMP"}


@tool
async def tool_fmp_news(symbols: Optional[List[str]] = None, 
                       query: Optional[str] = None,
                       limit: int = 10) -> Dict[str, Any]:
    """
    取得新聞資料
    
    Args:
        symbols: 可選的股票代號列表，用於篩選特定公司新聞
        query: 可選的查詢關鍵字
        limit: 新聞數量限制，預設 10 條
        
    Returns:
        包含新聞資料的字典
    """
    logger.info(f"呼叫 FMP 新聞工具: symbols={symbols}, query={query}")
    try:
        from app.services.fmp_client import fmp_client
        return await fmp_client.get_news(symbols=symbols, query=query, limit=limit)
    except Exception as e:
        logger.error(f"FMP 新聞工具執行失敗: {str(e)}")
        return {"ok": False, "reason": str(e), "source": "FMP"}


@tool
async def tool_fmp_macro(indicator: str, country: str = "US") -> Dict[str, Any]:
    """
    取得總體經濟數據
    
    Args:
        indicator: 經濟指標名稱，如 "GDP", "CPI", "UNEMPLOYMENT" 等
        country: 國家代碼，預設為 "US"
        
    Returns:
        包含經濟數據的字典
    """
    logger.info(f"呼叫 FMP 總經工具: {indicator}, {country}")
    try:
        from app.services.fmp_client import fmp_client
        return await fmp_client.get_macro_data(indicator, country)
    except Exception as e:
        logger.error(f"FMP 總經工具執行失敗: {str(e)}")
        return {"ok": False, "reason": str(e), "source": "FMP"}


# =============================================================================
# File Processing Tools
# =============================================================================

@tool
async def tool_file_load(file_path: str) -> Dict[str, Any]:
    """
    載入檔案內容進行處理
    
    Args:
        file_path: 檔案路徑
        
    Returns:
        包含檔案處理結果的字典
    """
    logger.info(f"呼叫檔案載入工具: {file_path}")
    try:
        from app.services.file_ingest import file_ingest_service
        return await file_ingest_service.process_file(file_path)
    except Exception as e:
        logger.error(f"檔案載入工具執行失敗: {str(e)}")
        return {"ok": False, "reason": str(e), "source": "FILE"}


# =============================================================================
# RAG Tools
# =============================================================================

@tool
async def tool_rag_query(question: str, top_k: int = 5) -> Dict[str, Any]:
    """
    執行 RAG 查詢以獲取相關文檔資訊
    
    Args:
        question: 查詢問題
        top_k: 返回最相關的文檔數量，預設 5
        
    Returns:
        包含 RAG 查詢結果的字典
    """
    logger.info(f"呼叫 RAG 查詢工具: {question}")
    try:
        from app.services.rag import rag_service
        query_result = await rag_service.query_documents(question, top_k)
        if query_result["ok"] and query_result["data"]["relevant_chunks"]:
            return await rag_service.answer_question(question, query_result["data"]["relevant_chunks"])
        else:
            return query_result
    except Exception as e:
        logger.error(f"RAG 查詢工具執行失敗: {str(e)}")
        return {"ok": False, "reason": str(e), "source": "RAG"}


# =============================================================================
# Report Generation Tools
# =============================================================================

@tool
async def tool_report_generate(template_id: str, context: Dict[str, Any], output_formats: List[str] = None) -> Dict[str, Any]:
    """
    生成報告 - 支援 LLM 先分析再產出報告
    
    Args:
        template_id: 報告模板 ID
        context: 報告上下文資料
        output_formats: 輸出格式列表，預設 ["markdown", "pdf"]
        
    Returns:
        包含報告生成結果的字典
    """
    logger.info(f"呼叫報告生成工具: {template_id}")
    output_formats = output_formats or ["markdown", "pdf"]
    
    try:
        from app.services.report import report_service
        from app.settings import settings
        
        # 1) 先讓 LLM 分析（可關）
        if settings.llm_report_enhancement:
            try:
                from app.graphs.agent_graph import agent_graph
                enhanced_context = await _enhance_context_with_llm(context, template_id)
                context.update(enhanced_context)
            except Exception as e:
                logger.warning(f"LLM 增強失敗，使用原始 context: {e}")
        
        # 2) 生成報告
        result = await report_service.generate_report(
            template_id=template_id,
            context=context,
            output_formats=output_formats
        )
        
        if result.get("ok"):
            files = result.get("files", [])
            return {
                "ok": True,
                "source": "REPORT",
                "data": {
                    "files": files,
                    "template_id": template_id,
                    "output_formats": output_formats
                },
                "logs": f"生成 {len(files)} 個檔案，LLM增強={'已啟用' if settings.llm_report_enhancement else '已停用'}"
            }
        else:
            return result
            
    except Exception as e:
        logger.error(f"報告生成工具執行失敗: {str(e)}")
        return {"ok": False, "reason": str(e), "source": "REPORT"}


async def _enhance_context_with_llm(context: Dict[str, Any], template_id: str) -> Dict[str, Any]:
    """使用 LLM 增強報告上下文"""
    # 這裡可以實現 LLM 增強邏輯
    # 為了避免循環導入，暫時返回空字典
    return {}


# =============================================================================
# LINE Tools
# =============================================================================

@tool
async def tool_line_fetch(user_id: Optional[str] = None,
                         chat_id: Optional[str] = None,
                         start_date: Optional[str] = None,
                         end_date: Optional[str] = None,
                         limit: int = 100) -> Dict[str, Any]:
    """
    抓取 LINE 訊息
    
    Args:
        user_id: 可選的用戶 ID
        chat_id: 可選的聊天 ID
        start_date: 開始日期
        end_date: 結束日期
        limit: 訊息數量限制，預設 100
        
    Returns:
        包含 LINE 訊息的字典
    """
    logger.info(f"呼叫 LINE 抓取工具: user_id={user_id}, chat_id={chat_id}")
    try:
        from app.services.line_client import line_client
        return await line_client.fetch_messages(
            user_id=user_id,
            chat_id=chat_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
    except Exception as e:
        logger.error(f"LINE 抓取工具執行失敗: {str(e)}")
        return {"ok": False, "reason": str(e), "source": "LINE"}


# =============================================================================
# Tool Management Functions
# =============================================================================

def get_all_tools() -> List:
    """
    取得所有可用工具的列表
    
    Returns:
        所有工具函數的列表
    """
    return [
        tool_fmp_quote,
        tool_fmp_profile,
        tool_fmp_news,
        tool_fmp_macro,
        tool_file_load,
        tool_rag_query,
        tool_report_generate,
        tool_line_fetch
    ]


def get_tool_descriptions() -> Dict[str, str]:
    """
    取得所有工具的描述

    Returns:
        工具名稱到描述的映射字典
    """
    tools = get_all_tools()
    descriptions = {}

    for tool_func in tools:
        tool_name = tool_func.name
        tool_desc = tool_func.description or "無描述"
        descriptions[tool_name] = tool_desc

    return descriptions


def dedup_tool_calls(tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    工具呼叫去重（名稱+參數 唯一）

    Args:
        tool_calls: 工具呼叫列表

    Returns:
        去重後的工具呼叫列表
    """
    seen = set()
    uniq = []
    for t in tool_calls:
        key = (t.get("name"), repr(sorted(t.get("args", {}).items())))
        if key not in seen:
            seen.add(key)
            uniq.append(t)
    return uniq


def parse_tool_content(content) -> Dict[str, Any]:
    """
    穩健解析工具內容

    Args:
        content: 工具返回的內容

    Returns:
        解析後的內容字典
    """
    if isinstance(content, (dict, list)):
        return content
    if content is None:
        return {}

    try:
        return json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return {"content": str(content)}


def validate_tool_parameters(tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    驗證工具參數

    Args:
        tool_name: 工具名稱
        parameters: 工具參數

    Returns:
        驗證結果字典
    """
    validation_result = {
        "valid": True,
        "errors": [],
        "warnings": []
    }

    # 基本參數驗證邏輯
    if tool_name.startswith("tool_fmp_"):
        if tool_name in ["tool_fmp_quote", "tool_fmp_profile"]:
            if not parameters.get("symbols"):
                validation_result["valid"] = False
                validation_result["errors"].append("symbols 參數為必需")
        elif tool_name == "tool_fmp_macro":
            if not parameters.get("indicator"):
                validation_result["valid"] = False
                validation_result["errors"].append("indicator 參數為必需")

    elif tool_name == "tool_file_load":
        if not parameters.get("file_path"):
            validation_result["valid"] = False
            validation_result["errors"].append("file_path 參數為必需")

    elif tool_name == "tool_rag_query":
        if not parameters.get("question"):
            validation_result["valid"] = False
            validation_result["errors"].append("question 參數為必需")

    return validation_result


def get_tool_source(tool_name: str) -> str:
    """
    根據工具名稱取得資料來源

    Args:
        tool_name: 工具名稱

    Returns:
        資料來源名稱
    """
    return TOOL_TO_SOURCE.get(tool_name, "UNKNOWN")


def create_comprehensive_tool_prompt() -> str:
    """
    創建包含所有工具描述的綜合提示

    Returns:
        包含所有工具資訊的提示字串
    """
    tools = get_all_tools()
    tool_descriptions = []

    for tool_func in tools:
        tool_name = tool_func.name
        tool_desc = tool_func.description or "無描述"

        # 取得工具參數資訊
        if hasattr(tool_func, 'args_schema') and tool_func.args_schema:
            schema = tool_func.args_schema.schema()
            properties = schema.get('properties', {})
            required = schema.get('required', [])

            param_info = []
            for param_name, param_schema in properties.items():
                param_type = param_schema.get('type', 'unknown')
                param_desc = param_schema.get('description', '')
                is_required = param_name in required

                param_str = f"  - {param_name} ({param_type})"
                if is_required:
                    param_str += " [必需]"
                if param_desc:
                    param_str += f": {param_desc}"
                param_info.append(param_str)

            if param_info:
                tool_descriptions.append(f"• {tool_name}: {tool_desc}\n" + "\n".join(param_info))
            else:
                tool_descriptions.append(f"• {tool_name}: {tool_desc}")
        else:
            tool_descriptions.append(f"• {tool_name}: {tool_desc}")

    return f"""
可用工具列表：

{chr(10).join(tool_descriptions)}

請根據用戶查詢的內容，自主選擇最適合的工具組合來提供幫助。你可以：
- 同時使用多個工具來獲取完整資訊
- 根據查詢內容靈活選擇工具
- 不受任何預設限制，完全基於查詢需求做決策
"""
