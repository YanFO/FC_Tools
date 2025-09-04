"""
Conversation History and Session Management Utilities

This module contains functions for managing conversation history, session storage,
and context injection for the supervised agent architecture.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from langchain_core.messages import BaseMessage, AIMessage

logger = logging.getLogger(__name__)


def init_conversation_store():
    """
    Initialize conversation history storage service
    
    Returns:
        session_service instance or None if unavailable
    """
    try:
        from app.services.session import session_service
        return session_service
    except ImportError:
        logger.warning("無法導入 session_service，對話歷史功能將受限")
        return None


async def load_conversation_history(conversation_store, session_id: str, parent_session_id: Optional[str] = None) -> Dict[str, Any]:
    """
    載入對話歷史並準備上下文
    
    Args:
        conversation_store: Session service instance
        session_id: Current session ID
        parent_session_id: Parent session ID for context retrieval
        
    Returns:
        Dictionary containing conversation history and context
    """
    history_context = {
        "current_session_history": [],
        "parent_session_context": None,
        "conversation_summary": None
    }
    
    if not conversation_store:
        logger.warning("對話儲存服務未可用")
        return history_context
    
    try:
        # 載入父會話上下文
        if parent_session_id:
            parent_context = await conversation_store.get_parent_session_context(parent_session_id)
            if parent_context:
                history_context["parent_session_context"] = parent_context
                logger.info(f"已載入父會話 {parent_session_id} 的上下文")
        
        # 載入當前會話歷史（如果存在）
        session_info = await conversation_store.get_session_info(session_id)
        if session_info:
            history_context["conversation_summary"] = session_info.get("summary")
            logger.info(f"已載入會話 {session_id} 的摘要")
        
        return history_context
        
    except Exception as e:
        logger.error(f"載入對話歷史失敗: {str(e)}")
        return history_context


async def save_conversation_history(conversation_store, session_id: str, messages: List[BaseMessage]) -> bool:
    """
    儲存對話歷史
    
    Args:
        conversation_store: Session service instance
        session_id: Session ID to save to
        messages: List of conversation messages
        
    Returns:
        True if successful, False otherwise
    """
    if not conversation_store or not messages:
        return False
    
    try:
        # 轉換訊息格式
        message_dicts = []
        for msg in messages:
            if hasattr(msg, 'content') and msg.content:
                message_dicts.append({
                    'type': type(msg).__name__.lower().replace('message', ''),
                    'content': msg.content,
                    'timestamp': datetime.now().isoformat()
                })
        
        # 儲存會話摘要
        success = await conversation_store.save_session_summary(session_id, message_dicts)
        if success:
            logger.info(f"已儲存會話 {session_id} 的對話歷史")
        
        return success
        
    except Exception as e:
        logger.error(f"儲存對話歷史失敗: {str(e)}")
        return False


def inject_conversation_context(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    將對話上下文注入到系統提示中
    
    Args:
        state: Agent state dictionary
        
    Returns:
        Updated state with injected conversation context
    """
    try:
        conversation_context = state.get("conversation_context")
        parent_context = state.get("conversation_history", {}).get("parent_session_context")
        
        if not conversation_context and not parent_context:
            return state
        
        # 建構上下文區塊
        context_blocks = []
        
        if parent_context:
            context_blocks.append(f"""
[對話歷史上下文]
基於之前的對話，以下是相關的背景資訊：
{parent_context}
[/對話歷史上下文]
""")
        
        if conversation_context:
            context_blocks.append(f"""
[當前會話上下文]
{conversation_context}
[/當前會話上下文]
""")
        
        if context_blocks:
            # 更新系統提示
            current_system_prompt = state.get("_system_prompt", "")
            enhanced_prompt = "\n".join(context_blocks) + "\n" + current_system_prompt
            state["_system_prompt"] = enhanced_prompt
            
            logger.info("已注入對話上下文到系統提示")
        
        return state
        
    except Exception as e:
        logger.error(f"注入對話上下文失敗: {str(e)}")
        return state


def prepare_conversation_storage(state: Dict[str, Any]) -> None:
    """
    準備對話歷史儲存
    
    Args:
        state: Agent state dictionary
    """
    session_id = state.get("session_id")
    if not session_id:
        return
    
    messages = state.get("messages", [])
    if not messages:
        return
    
    # 標記需要儲存對話歷史
    state["_save_conversation"] = True
    state["_conversation_messages"] = messages


def build_conversation_system_prompt(conversation_context: Optional[str]) -> str:
    """
    建構包含對話歷史的系統提示區塊
    
    Args:
        conversation_context: Conversation context string
        
    Returns:
        System prompt block with conversation context
    """
    if not conversation_context:
        return ""
    
    return f"""
[對話歷史上下文]
基於之前的對話，以下是相關的背景資訊：
{conversation_context}

請在回應時考慮這些歷史上下文，保持對話的連貫性和一致性。
[/對話歷史上下文]
"""


def prepare_conversation_messages_for_storage(messages: List[BaseMessage], final_response: str) -> List[BaseMessage]:
    """
    準備要儲存的對話訊息，包含最終回應
    
    Args:
        messages: Original message list
        final_response: Final AI response to add
        
    Returns:
        Messages list with final response added
    """
    try:
        final_ai_message = AIMessage(content=final_response)
        return messages + [final_ai_message]
    except Exception as e:
        logger.error(f"準備對話訊息儲存失敗: {str(e)}")
        return messages
