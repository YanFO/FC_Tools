"""
Session 管理服務
處理對話摘要、持久化和 parent_session_id 注入功能
"""
import logging
from typing import Dict, Any, Optional, List

from app.services.database import database_service
from app.settings import settings

logger = logging.getLogger(__name__)


class SessionService:
    """Session 管理服務類別"""
    
    def __init__(self):
        self.max_summary_tokens = getattr(settings, 'session_summary_max_tokens', 512)
        self.max_history_turns = getattr(settings, 'session_history_max_turns', 6)
    
    async def summarize_session(self, session_id: str, messages: List[Dict[str, Any]]) -> Optional[str]:
        """
        將對話摘要化
        
        Args:
            session_id: Session ID
            messages: 對話訊息列表
            
        Returns:
            摘要文字或 None（如果失敗）
        """
        if not messages:
            return None
        
        try:
            # 過濾出有意義的對話內容
            meaningful_messages = []
            for msg in messages:
                if isinstance(msg, dict):
                    content = msg.get('content', '')
                    msg_type = msg.get('type', 'human')
                elif hasattr(msg, 'content'):
                    content = msg.content
                    msg_type = type(msg).__name__.lower().replace('message', '')
                else:
                    continue
                
                # 跳過空內容或系統訊息
                if not content or content.strip() == '' or msg_type == 'system':
                    continue
                
                # 跳過工具調用相關訊息
                if 'tool_call' in content.lower() or msg_type == 'tool':
                    continue
                
                meaningful_messages.append({
                    'type': msg_type,
                    'content': content[:500]  # 限制長度
                })
            
            if not meaningful_messages:
                return None
            
            # 建立摘要提示
            conversation_text = "\n".join([
                f"{msg['type']}: {msg['content']}" 
                for msg in meaningful_messages[-self.max_history_turns:]  # 只取最近幾輪
            ])
            
            summary_prompt = f"""
請將以下對話摘要為簡潔的重點，重點關注：
1. 使用者的偏好和要求
2. 重要的設定或指示
3. 對話的主要主題

對話內容：
{conversation_text}

請用繁體中文回覆，限制在 {self.max_summary_tokens} 個字元內：
"""
            
            # 使用簡單摘要（暫時不使用 LLM）
            logger.info("使用簡單摘要生成")
            summary = self._simple_summary(meaningful_messages)
            
            # 清理和限制摘要長度
            summary = summary.strip()
            if len(summary) > self.max_summary_tokens:
                summary = summary[:self.max_summary_tokens] + "..."
            
            logger.info(f"Session {session_id} 摘要生成成功，長度: {len(summary)}")
            return summary
            
        except Exception as e:
            logger.error(f"摘要 Session {session_id} 失敗: {str(e)}")
            return self._simple_summary(meaningful_messages) if 'meaningful_messages' in locals() else None
    
    def _simple_summary(self, messages: List[Dict[str, Any]]) -> str:
        """簡單的摘要生成（當 LLM 不可用時）"""
        if not messages:
            return "空對話"
        
        # 統計訊息類型
        user_messages = [msg for msg in messages if msg.get('type') == 'human']
        ai_messages = [msg for msg in messages if msg.get('type') == 'ai']
        
        # 提取關鍵詞
        all_content = " ".join([msg.get('content', '') for msg in messages])
        keywords = []
        
        # 檢查常見主題
        if any(word in all_content.upper() for word in ['AAPL', 'TSLA', 'NVDA', 'MSFT']):
            keywords.append("股票查詢")
        if "繁體中文" in all_content or "中文" in all_content:
            keywords.append("語言偏好")
        if "報告" in all_content or "report" in all_content.lower():
            keywords.append("報告生成")
        if "簡短" in all_content or "重點" in all_content:
            keywords.append("簡潔回覆偏好")
        
        summary_parts = [
            f"對話輪數: {len(user_messages)} 輪",
            f"主要主題: {', '.join(keywords) if keywords else '一般對話'}"
        ]
        
        return " | ".join(summary_parts)
    
    async def save_session_summary(self, session_id: str, messages: List[Dict[str, Any]]) -> bool:
        """儲存 Session 摘要"""
        try:
            summary = await self.summarize_session(session_id, messages)
            if not summary:
                logger.warning(f"Session {session_id} 摘要為空，跳過儲存")
                return False
            
            message_count = len([msg for msg in messages if self._is_meaningful_message(msg)])
            success = await database_service.save_session_summary(session_id, summary, message_count)
            
            if success:
                logger.info(f"Session {session_id} 摘要儲存成功")
            else:
                logger.error(f"Session {session_id} 摘要儲存失敗")
            
            return success
            
        except Exception as e:
            logger.error(f"儲存 Session {session_id} 摘要失敗: {str(e)}")
            return False
    
    def _is_meaningful_message(self, msg: Any) -> bool:
        """判斷是否為有意義的訊息"""
        if isinstance(msg, dict):
            content = msg.get('content', '')
            msg_type = msg.get('type', '')
        elif hasattr(msg, 'content'):
            content = msg.content
            msg_type = type(msg).__name__.lower()
        else:
            return False
        
        # 跳過空內容、系統訊息、工具訊息
        if not content or content.strip() == '':
            return False
        if 'system' in msg_type or 'tool' in msg_type:
            return False
        
        return True
    
    async def get_parent_session_context(self, parent_session_id: str) -> Optional[str]:
        """取得父 Session 的上下文摘要"""
        try:
            session_data = await database_service.get_session_summary(parent_session_id)
            if not session_data:
                logger.warning(f"找不到父 Session: {parent_session_id}")
                return None
            
            summary = session_data.get('summary', '')
            if not summary:
                return None
            
            # 建立上下文注入文字
            context = f"""
根據前一次對話的摘要，使用者的偏好和背景如下：
{summary}

請在回應時考慮這些偏好和背景資訊。
"""
            
            logger.info(f"成功取得父 Session {parent_session_id} 的上下文")
            return context.strip()
            
        except Exception as e:
            logger.error(f"取得父 Session {parent_session_id} 上下文失敗: {str(e)}")
            return None
    
    async def create_system_prompt_with_context(self, parent_session_id: Optional[str] = None) -> str:
        """建立包含上下文的系統提示"""
        base_prompt = """
你是 Augment Agent，一個專業的 AI 助理。請遵循以下原則：

1. 一律使用繁體中文回應
2. 嚴禁捏造任何數據，特別是股價、財務資訊
3. 當 API 金鑰缺失時，回傳結構化錯誤而非猜測
4. 提供準確、有用的資訊

"""
        
        if parent_session_id:
            context = await self.get_parent_session_context(parent_session_id)
            if context:
                return base_prompt + context
        
        return base_prompt.strip()
    
    async def list_recent_sessions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """列出最近的 Session"""
        try:
            return await database_service.list_sessions(limit)
        except Exception as e:
            logger.error(f"列出 Session 失敗: {str(e)}")
            return []
    
    async def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """取得 Session 詳細資訊"""
        try:
            return await database_service.get_session_summary(session_id)
        except Exception as e:
            logger.error(f"取得 Session {session_id} 資訊失敗: {str(e)}")
            return None


# 全域 Session 服務實例
session_service = SessionService()
