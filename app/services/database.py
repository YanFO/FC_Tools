"""
資料庫服務模組
處理 SQLite 資料庫操作，包含 LINE 訊息儲存和 Session 管理
"""
import logging
import sqlite3
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

from app.settings import settings

logger = logging.getLogger(__name__)


class DatabaseService:
    """資料庫服務類別"""
    
    def __init__(self):
        self.db_path = self._get_db_path()
        self._init_database()
    
    def _get_db_path(self) -> str:
        """取得資料庫路徑"""
        if settings.database_url.startswith("sqlite:///"):
            db_path = settings.database_url.replace("sqlite:///", "")
            # 確保目錄存在
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            return db_path
        else:
            # 預設路徑
            db_path = "./outputs/sessions.db"
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            return db_path
    
    def _init_database(self):
        """初始化資料庫結構"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 建立 LINE 訊息表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS line_messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_id TEXT UNIQUE,
                        event_type TEXT NOT NULL,
                        user_id TEXT,
                        chat_id TEXT,
                        message_type TEXT,
                        message_text TEXT,
                        timestamp INTEGER NOT NULL,
                        raw_data TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # 建立 Session 摘要表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS session_summaries (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT UNIQUE NOT NULL,
                        summary TEXT NOT NULL,
                        message_count INTEGER DEFAULT 0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # 建立索引
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_line_user_id ON line_messages(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_line_timestamp ON line_messages(timestamp)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_session_id ON session_summaries(session_id)")
                
                conn.commit()
                logger.info("資料庫初始化完成")
                
        except Exception as e:
            logger.error(f"資料庫初始化失敗: {str(e)}")
            raise
    
    async def save_line_event(self, event_data: Dict[str, Any]) -> bool:
        """儲存 LINE 事件到資料庫"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 生成事件 ID
                event_id = f"{event_data.get('timestamp', 0)}_{event_data.get('source', {}).get('userId', 'unknown')}"
                
                # 提取訊息資訊
                message = event_data.get('message', {})
                message_type = message.get('type') if message else None
                message_text = message.get('text') if message and message.get('type') == 'text' else None
                
                cursor.execute("""
                    INSERT OR REPLACE INTO line_messages 
                    (event_id, event_type, user_id, chat_id, message_type, message_text, timestamp, raw_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event_id,
                    event_data.get('type'),
                    event_data.get('source', {}).get('userId'),
                    event_data.get('source', {}).get('groupId') or event_data.get('source', {}).get('roomId'),
                    message_type,
                    message_text,
                    event_data.get('timestamp'),
                    json.dumps(event_data, ensure_ascii=False)
                ))
                
                conn.commit()
                logger.info(f"儲存 LINE 事件成功: {event_id}")
                return True
                
        except Exception as e:
            logger.error(f"儲存 LINE 事件失敗: {str(e)}")
            return False
    
    async def get_line_messages(
        self,
        user_id: Optional[str] = None,
        chat_id: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """從資料庫查詢 LINE 訊息"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # 建構查詢條件
                conditions = []
                params = []
                
                if user_id:
                    conditions.append("user_id = ?")
                    params.append(user_id)
                
                if chat_id:
                    conditions.append("chat_id = ?")
                    params.append(chat_id)
                
                if start_time:
                    # 轉換 ISO 時間為 timestamp
                    start_timestamp = int(datetime.fromisoformat(start_time.replace('Z', '+00:00')).timestamp() * 1000)
                    conditions.append("timestamp >= ?")
                    params.append(start_timestamp)
                
                if end_time:
                    end_timestamp = int(datetime.fromisoformat(end_time.replace('Z', '+00:00')).timestamp() * 1000)
                    conditions.append("timestamp <= ?")
                    params.append(end_timestamp)
                
                where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
                
                query = f"""
                    SELECT event_id as id, message_type as type, message_text as text, 
                           user_id, timestamp, 'user' as source
                    FROM line_messages
                    {where_clause}
                    ORDER BY timestamp DESC
                    LIMIT ?
                """
                params.append(limit)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                messages = []
                for row in rows:
                    # 轉換 timestamp 為 ISO 格式
                    timestamp_iso = datetime.fromtimestamp(row['timestamp'] / 1000).isoformat() + 'Z'
                    
                    messages.append({
                        "id": row['id'],
                        "type": row['type'] or 'text',
                        "text": row['text'] or '',
                        "user_id": row['user_id'],
                        "timestamp": timestamp_iso,
                        "source": row['source']
                    })
                
                return messages
                
        except Exception as e:
            logger.error(f"查詢 LINE 訊息失敗: {str(e)}")
            return []
    
    async def save_session_summary(self, session_id: str, summary: str, message_count: int = 0) -> bool:
        """儲存 Session 摘要"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO session_summaries 
                    (session_id, summary, message_count, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """, (session_id, summary, message_count))
                
                conn.commit()
                logger.info(f"儲存 Session 摘要成功: {session_id}")
                return True
                
        except Exception as e:
            logger.error(f"儲存 Session 摘要失敗: {str(e)}")
            return False
    
    async def get_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """取得 Session 摘要"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT session_id, summary, message_count, created_at, updated_at
                    FROM session_summaries
                    WHERE session_id = ?
                """, (session_id,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        "session_id": row['session_id'],
                        "summary": row['summary'],
                        "message_count": row['message_count'],
                        "created_at": row['created_at'],
                        "updated_at": row['updated_at']
                    }
                
                return None
                
        except Exception as e:
            logger.error(f"取得 Session 摘要失敗: {str(e)}")
            return None
    
    async def list_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """列出所有 Session"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT session_id, summary, message_count, created_at, updated_at
                    FROM session_summaries
                    ORDER BY updated_at DESC
                    LIMIT ?
                """, (limit,))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"列出 Session 失敗: {str(e)}")
            return []
    
    def get_database_stats(self) -> Dict[str, Any]:
        """取得資料庫統計資訊"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 統計 LINE 訊息數量
                cursor.execute("SELECT COUNT(*) FROM line_messages")
                line_message_count = cursor.fetchone()[0]
                
                # 統計 Session 數量
                cursor.execute("SELECT COUNT(*) FROM session_summaries")
                session_count = cursor.fetchone()[0]
                
                return {
                    "line_messages": line_message_count,
                    "sessions": session_count,
                    "database_path": self.db_path
                }
                
        except Exception as e:
            logger.error(f"取得資料庫統計失敗: {str(e)}")
            return {
                "line_messages": 0,
                "sessions": 0,
                "database_path": self.db_path,
                "error": str(e)
            }


# 全域資料庫服務實例
database_service = DatabaseService()
