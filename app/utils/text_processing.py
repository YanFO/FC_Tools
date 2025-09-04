"""
Text Processing Pipeline Utilities

This module contains functions for text processing, intent classification,
system prompt construction, and query analysis.
"""

import logging
from typing import Dict, Any, Optional, List
from langchain_core.messages import AIMessage

logger = logging.getLogger(__name__)


def process_text_pipeline(state: Dict[str, Any], rules_service, classify_intent, normalize_symbol, 
                         build_system_prompt, Intent) -> Dict[str, Any]:
    """
    執行文字處理管線 - 整合意圖路由、對話歷史和 System Prompt 建構
    
    Args:
        state: Agent state dictionary
        rules_service: Rules service instance
        classify_intent: Intent classification function
        normalize_symbol: Symbol normalization function
        build_system_prompt: System prompt building function
        Intent: Intent enum class
        
    Returns:
        Updated state with processed text pipeline results
    """
    logger.info("執行監督式文字處理管線")

    query = state.get("query", "")
    if not query:
        state["warnings"].append("查詢文字為空")
        return state

    # 1. 檢查對話歷史（已在 run 方法中載入）
    session_id = state.get("session_id")
    conversation_history = state.get("conversation_history")
    
    if conversation_history:
        logger.info(f"使用會話 {session_id} 的對話歷史上下文")
    else:
        logger.info("無對話歷史上下文")

    # 2. 檢查規則違規
    violation = rules_service.check_violation(query)
    if violation:
        logger.info(f"檢測到規則違規: {violation['rule_id']}")
        state["_violation"] = violation
        # 直接設置 AI 回應，不觸發工具
        state["messages"] = [AIMessage(content=violation["rule_explanation"])]
        return state

    # 3. 意圖分類和符號識別
    intent_str = state.get("_intent")
    symbol = state.get("_symbol")

    if intent_str:
        intent = Intent(intent_str)
    else:
        # 備用：在 Graph 內分類
        intent = classify_intent(query)
        symbol = normalize_symbol(query)

    state["_intent"] = intent
    state["_symbol"] = symbol
    logger.info(f"查詢意圖: {intent}, 符號: {symbol}")

    # 4. 建構 System Prompt（包含對話歷史）
    rules_block = rules_service.get_system_prompt_rules()
    session_block = build_conversation_system_prompt_block(state)

    system_prompt = build_system_prompt(intent, rules_block, session_block, symbol)
    state["_system_prompt"] = system_prompt
    
    # 5. 注入對話上下文（如果需要）
    from app.utils.conversation import inject_conversation_context
    state = inject_conversation_context(state)

    # 6. 處理查詢並建構初始訊息
    from langchain_core.messages import HumanMessage
    from app.utils.tools import create_comprehensive_tool_prompt

    # 使用綜合工具提示，讓 LLM 完全自主選擇工具
    tool_prompt = create_comprehensive_tool_prompt()

    messages = [HumanMessage(content=f"""
請分析以下查詢並決定需要呼叫哪些工具：

查詢內容：{query}

{tool_prompt}
""")]

    state["messages"] = messages
    return state


def build_conversation_system_prompt_block(state: Dict[str, Any]) -> Optional[str]:
    """
    建構包含對話歷史的系統提示區塊
    
    Args:
        state: Agent state dictionary
        
    Returns:
        System prompt block with conversation context or None
    """
    conversation_context = state.get("conversation_context")
    
    if not conversation_context:
        return None
    
    return f"""
[對話歷史上下文]
基於之前的對話，以下是相關的背景資訊：
{conversation_context}

請在回應時考慮這些歷史上下文，保持對話的連貫性和一致性。
[/對話歷史上下文]
"""


def analyze_query_intent(query: str, classify_intent, normalize_symbol, Intent):
    """
    分析查詢意圖和符號
    
    Args:
        query: User query string
        classify_intent: Intent classification function
        normalize_symbol: Symbol normalization function
        Intent: Intent enum class
        
    Returns:
        Tuple of (intent, symbol)
    """
    try:
        intent = classify_intent(query)
        symbol = normalize_symbol(query)
        return intent, symbol
    except Exception as e:
        logger.error(f"意圖分析失敗: {str(e)}")
        return Intent.AMBIGUOUS, None


def preprocess_query(query: str) -> Dict[str, Any]:
    """
    預處理查詢文字
    
    Args:
        query: Raw query string
        
    Returns:
        Dictionary with preprocessed query information
    """
    if not query:
        return {
            "processed_query": "",
            "is_empty": True,
            "length": 0,
            "word_count": 0
        }
    
    processed_query = query.strip()
    
    return {
        "processed_query": processed_query,
        "is_empty": False,
        "length": len(processed_query),
        "word_count": len(processed_query.split()),
        "has_special_commands": processed_query.startswith("/"),
        "contains_symbols": any(char in processed_query for char in ["$", "%", "@", "#"])
    }


def extract_symbols_from_query(query: str) -> List[str]:
    """
    從查詢中提取股票符號
    
    Args:
        query: User query string
        
    Returns:
        List of extracted symbols
    """
    import re
    
    # 常見股票符號模式
    symbol_patterns = [
        r'\b[A-Z]{1,5}\b',  # 1-5個大寫字母
        r'\$[A-Z]{1,5}\b',  # $開頭的符號
    ]
    
    symbols = []
    for pattern in symbol_patterns:
        matches = re.findall(pattern, query.upper())
        symbols.extend(matches)
    
    # 移除重複並過濾常見非股票詞彙
    common_words = {"THE", "AND", "OR", "FOR", "TO", "OF", "IN", "ON", "AT", "BY", "WITH"}
    symbols = list(set(symbol.replace("$", "") for symbol in symbols if symbol not in common_words))
    
    return symbols


def build_enhanced_system_prompt(base_prompt: str, conversation_context: Optional[str] = None,
                                rules_context: Optional[str] = None) -> str:
    """
    建構增強的系統提示，包含對話歷史和規則上下文
    
    Args:
        base_prompt: Base system prompt
        conversation_context: Conversation history context
        rules_context: Rules context
        
    Returns:
        Enhanced system prompt
    """
    prompt_parts = []
    
    # 添加對話歷史上下文
    if conversation_context:
        prompt_parts.append(f"""
[對話歷史上下文]
基於之前的對話，以下是相關的背景資訊：
{conversation_context}

請在回應時考慮這些歷史上下文，保持對話的連貫性和一致性。
[/對話歷史上下文]
""")
    
    # 添加規則上下文
    if rules_context:
        prompt_parts.append(rules_context)
    
    # 添加基礎提示
    prompt_parts.append(base_prompt)
    
    return "\n".join(prompt_parts)


def validate_query_safety(query: str) -> Dict[str, Any]:
    """
    驗證查詢安全性
    
    Args:
        query: User query string
        
    Returns:
        Dictionary with safety validation results
    """
    if not query:
        return {"is_safe": True, "warnings": []}
    
    warnings = []
    
    # 檢查潛在的惡意內容
    suspicious_patterns = [
        "javascript:",
        "<script",
        "eval(",
        "exec(",
        "system(",
        "rm -rf",
        "DROP TABLE"
    ]
    
    query_lower = query.lower()
    for pattern in suspicious_patterns:
        if pattern in query_lower:
            warnings.append(f"檢測到可疑模式: {pattern}")
    
    # 檢查查詢長度
    if len(query) > 10000:
        warnings.append("查詢過長，可能存在風險")
    
    return {
        "is_safe": len(warnings) == 0,
        "warnings": warnings,
        "query_length": len(query)
    }


def format_query_for_logging(query: str, max_length: int = 100) -> str:
    """
    格式化查詢用於日誌記錄
    
    Args:
        query: User query string
        max_length: Maximum length for logging
        
    Returns:
        Formatted query string for logging
    """
    if not query:
        return "(空查詢)"
    
    if len(query) <= max_length:
        return query
    
    return query[:max_length] + "..."
