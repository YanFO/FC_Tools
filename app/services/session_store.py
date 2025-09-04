"""
Session 存储服务
管理对话历史和上下文摘要
"""
import logging
import json
import sqlite3
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
import uuid

from app.settings import settings

logger = logging.getLogger(__name__)


class SessionStore:
    """Session 存储管理类"""
    
    def __init__(self, db_path: Optional[str] = None):
        """初始化 Session 存储"""
        if db_path is None:
            db_path = Path(settings.output_dir) / "sessions.db"
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 初始化数据库
        self._init_database()
    
    def _init_database(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    metadata TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS turns (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    turn_number INTEGER NOT NULL,
                    user_message TEXT NOT NULL,
                    assistant_message TEXT NOT NULL,
                    metadata TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions (id)
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_turns_session_id 
                ON turns (session_id)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_turns_session_turn 
                ON turns (session_id, turn_number)
            """)
    
    def create_session(self, session_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> str:
        """创建新的 session"""
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        now = datetime.now().isoformat()
        metadata_json = json.dumps(metadata or {})
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO sessions (id, created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?)
            """, (session_id, now, now, metadata_json))
        
        logger.info(f"创建 session: {session_id}")
        return session_id
    
    def append_turn(self, session_id: str, user_msg: str, assistant_msg: str, 
                   metadata: Optional[Dict[str, Any]] = None) -> str:
        """添加对话轮次"""
        turn_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        metadata_json = json.dumps(metadata or {})
        
        with sqlite3.connect(self.db_path) as conn:
            # 获取下一个轮次号
            cursor = conn.execute("""
                SELECT COALESCE(MAX(turn_number), 0) + 1 
                FROM turns WHERE session_id = ?
            """, (session_id,))
            turn_number = cursor.fetchone()[0]
            
            # 插入轮次
            conn.execute("""
                INSERT INTO turns (id, session_id, turn_number, user_message, 
                                 assistant_message, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (turn_id, session_id, turn_number, user_msg, assistant_msg, metadata_json, now))
            
            # 更新 session 的 updated_at
            conn.execute("""
                UPDATE sessions SET updated_at = ? WHERE id = ?
            """, (now, session_id))
        
        logger.info(f"添加对话轮次: {session_id} - {turn_number}")
        return turn_id
    
    def get_recent_turns(self, session_id: str, n: int = 5) -> List[Dict[str, Any]]:
        """获取最近的 N 轮对话"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM turns 
                WHERE session_id = ? 
                ORDER BY turn_number DESC 
                LIMIT ?
            """, (session_id, n))
            
            turns = []
            for row in cursor.fetchall():
                turn = dict(row)
                turn['metadata'] = json.loads(turn['metadata']) if turn['metadata'] else {}
                turns.append(turn)
            
            # 按时间顺序返回
            return list(reversed(turns))
    
    def get_last_turn(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取最后一轮对话"""
        turns = self.get_recent_turns(session_id, 1)
        return turns[0] if turns else None
    
    def summarize(self, messages: List[Dict[str, Any]], max_tokens: int = 512) -> str:
        """生成对话摘要"""
        if not messages:
            return ""
        
        # 简单的摘要策略：提取关键信息
        summary_parts = []
        
        # 提取用户偏好和设置
        preferences = []
        topics = []
        
        for turn in messages:
            user_msg = turn.get('user_message', '')
            assistant_msg = turn.get('assistant_message', '')
            
            # 检测偏好设置
            if any(keyword in user_msg.lower() for keyword in ['繁體', '繁体', '中文', '語言', '语言']):
                preferences.append("用户偏好繁体中文")
            
            if any(keyword in user_msg.lower() for keyword in ['預設', '预设', '默认']):
                preferences.append(f"用户设置: {user_msg[:50]}...")
            
            # 提取主要话题
            if any(keyword in user_msg.lower() for keyword in ['股票', '報告', '报告', 'aapl', 'msft', 'nvda']):
                topics.append("股票分析")
            
            if any(keyword in user_msg.lower() for keyword in ['檔案', '文件', 'pdf']):
                topics.append("文件处理")
        
        # 构建摘要
        if preferences:
            summary_parts.append(f"用户偏好: {'; '.join(set(preferences))}")
        
        if topics:
            summary_parts.append(f"讨论话题: {'; '.join(set(topics))}")
        
        if not summary_parts:
            # 如果没有特定模式，使用最后一轮的简要描述
            last_turn = messages[-1]
            user_msg = last_turn.get('user_message', '')[:100]
            summary_parts.append(f"上次讨论: {user_msg}...")
        
        summary = "; ".join(summary_parts)
        
        # 限制长度
        if len(summary) > max_tokens:
            summary = summary[:max_tokens-3] + "..."
        
        return summary
    
    def get_session_summary(self, session_id: str, max_tokens: int = 512) -> str:
        """获取 session 的摘要"""
        turns = self.get_recent_turns(session_id, settings.session_history_max_turns)
        return self.summarize(turns, max_tokens)
    
    def build_session_system_prompt(self, session_id: str, base_prompt: str = "") -> str:
        """构建包含 session 上下文的系统提示"""
        summary = self.get_session_summary(session_id, settings.session_summary_max_tokens)
        
        if not summary:
            return base_prompt
        
        # 在系统提示中注入上下文
        context_section = f"""
[SESSION CONTEXT]
基于之前的对话历史，用户的偏好和上下文如下：
{summary}

请在回答时考虑这些上下文信息，保持对话的连贯性。
[/SESSION CONTEXT]

"""
        
        if base_prompt:
            return context_section + base_prompt
        else:
            return context_section.strip()
    
    def cleanup_old_sessions(self, days: int = 30):
        """清理旧的 session 数据"""
        cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff_date = cutoff_date.replace(day=cutoff_date.day - days)
        cutoff_str = cutoff_date.isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            # 删除旧的轮次
            cursor = conn.execute("""
                DELETE FROM turns 
                WHERE session_id IN (
                    SELECT id FROM sessions WHERE updated_at < ?
                )
            """, (cutoff_str,))
            turns_deleted = cursor.rowcount
            
            # 删除旧的 session
            cursor = conn.execute("""
                DELETE FROM sessions WHERE updated_at < ?
            """, (cutoff_str,))
            sessions_deleted = cursor.rowcount
        
        logger.info(f"清理完成: 删除 {sessions_deleted} 个 session, {turns_deleted} 个轮次")
        return {"sessions_deleted": sessions_deleted, "turns_deleted": turns_deleted}


# 全局实例
session_store = SessionStore()
