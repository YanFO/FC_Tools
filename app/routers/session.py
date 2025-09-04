"""
Session API 路由器
處理對話 Session 的查詢和管理
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from fastapi import APIRouter, Path
from pydantic import BaseModel

from app.services.session import session_service
from app.services.database import database_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/session", tags=["session"])


# 回應模型定義
class SessionResponse(BaseModel):
    """Session 回應模型"""
    ok: bool
    data: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None
    timestamp: str


class SessionListResponse(BaseModel):
    """Session 列表回應模型"""
    ok: bool
    data: Optional[List[Dict[str, Any]]] = None
    count: Optional[int] = None
    reason: Optional[str] = None
    timestamp: str


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str = Path(..., description="Session ID")) -> SessionResponse:
    """
    取得指定 Session 的摘要資訊
    
    用於 debug 和檢查 Session 持久化狀態
    """
    logger.info(f"查詢 Session: {session_id}")
    
    try:
        session_data = await session_service.get_session_info(session_id)
        
        if not session_data:
            return SessionResponse(
                ok=False,
                reason="session_not_found",
                timestamp=datetime.now().isoformat()
            )
        
        # 過濾敏感資訊，只回傳摘要
        filtered_data = {
            "session_id": session_data.get("session_id"),
            "summary": session_data.get("summary"),
            "message_count": session_data.get("message_count"),
            "created_at": session_data.get("created_at"),
            "updated_at": session_data.get("updated_at")
        }
        
        return SessionResponse(
            ok=True,
            data=filtered_data,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"查詢 Session {session_id} 失敗: {str(e)}")
        return SessionResponse(
            ok=False,
            reason="query_failed",
            timestamp=datetime.now().isoformat()
        )


@router.get("", response_model=SessionListResponse)
async def list_sessions(limit: int = 20) -> SessionListResponse:
    """
    列出最近的 Session
    
    用於 debug 和管理 Session
    """
    logger.info(f"列出 Session，限制: {limit}")
    
    try:
        sessions = await session_service.list_recent_sessions(limit)
        
        # 過濾敏感資訊
        filtered_sessions = []
        for session in sessions:
            filtered_sessions.append({
                "session_id": session.get("session_id"),
                "summary": session.get("summary", "")[:100] + "..." if len(session.get("summary", "")) > 100 else session.get("summary", ""),
                "message_count": session.get("message_count"),
                "created_at": session.get("created_at"),
                "updated_at": session.get("updated_at")
            })
        
        return SessionListResponse(
            ok=True,
            data=filtered_sessions,
            count=len(filtered_sessions),
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"列出 Session 失敗: {str(e)}")
        return SessionListResponse(
            ok=False,
            reason="query_failed",
            timestamp=datetime.now().isoformat()
        )


@router.get("/stats/database")
async def get_database_stats() -> Dict[str, Any]:
    """取得資料庫統計資訊"""
    try:
        stats = database_service.get_database_stats()
        return {
            "ok": True,
            "data": stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"取得資料庫統計失敗: {str(e)}")
        return {
            "ok": False,
            "reason": "stats_failed",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }
