"""
LINE API 路由器
處理 LINE 訊息查詢、推播和 webhook 端點
支援模擬模式和真實模式切換
"""
import logging
import hashlib
import hmac
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request, Header, Query
from pydantic import BaseModel, Field

from app.settings import settings
from app.services.line_client import line_client
from app.services.database import database_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/line", tags=["line"])


# 請求模型定義
class LineWebhookEvent(BaseModel):
    """LINE Webhook 事件模型"""
    type: str
    timestamp: int
    source: Dict[str, Any]
    message: Optional[Dict[str, Any]] = None
    replyToken: Optional[str] = None


class LineWebhookRequest(BaseModel):
    """LINE Webhook 請求模型"""
    destination: str
    events: List[LineWebhookEvent]


class LinePushRequest(BaseModel):
    """LINE 推播請求模型"""
    user_id: str = Field(..., description="使用者 ID")
    text: str = Field(..., description="推播訊息內容")


# 回應模型定義
class LineMessageResponse(BaseModel):
    """LINE 訊息回應模型"""
    ok: bool
    data: Optional[List[Dict[str, Any]]] = None
    mock: Optional[bool] = None
    notice: Optional[str] = None
    reason: Optional[str] = None
    timestamp: str


class LinePushResponse(BaseModel):
    """LINE 推播回應模型"""
    ok: bool
    mock: Optional[bool] = None
    notice: Optional[str] = None
    reason: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    timestamp: str


def verify_line_signature(body: bytes, signature: str) -> bool:
    """驗證 LINE webhook 簽章 - 使用 Base64 編碼"""
    if not settings.line_channel_secret:
        return False

    import base64
    digest = hmac.new(
        settings.line_channel_secret.encode('utf-8'),
        body,
        hashlib.sha256
    ).digest()

    expected = base64.b64encode(digest).decode('utf-8')
    return hmac.compare_digest(expected, signature)


@router.get("/messages", response_model=LineMessageResponse)
async def get_line_messages(
    user_id: Optional[str] = Query(None, description="使用者 ID"),
    chat_id: Optional[str] = Query(None, description="聊天室 ID"),
    start: Optional[str] = Query(None, description="開始時間 (ISO 格式)"),
    end: Optional[str] = Query(None, description="結束時間 (ISO 格式)"),
    limit: int = Query(10, description="訊息數量限制")
) -> LineMessageResponse:
    """
    取得 LINE 聊天訊息
    
    根據 USE_MOCK_LINE 設定決定回傳模擬資料或真實資料
    """
    logger.info(f"查詢 LINE 訊息: user_id={user_id}, chat_id={chat_id}, limit={limit}")
    
    try:
        if settings.use_mock_line:
            # 模擬模式
            mock_messages = [
                {
                    "id": "msg_001",
                    "type": "text",
                    "text": "請問 AAPL 股價？",
                    "user_id": user_id or "U12345",
                    "timestamp": "2024-01-15T10:30:00Z",
                    "source": "user"
                },
                {
                    "id": "msg_002", 
                    "type": "text",
                    "text": "目前 AAPL 股價為 $185.25（+2.15%）",
                    "user_id": "bot",
                    "timestamp": "2024-01-15T10:30:15Z",
                    "source": "bot"
                },
                {
                    "id": "msg_003",
                    "type": "text", 
                    "text": "謝謝！請再幫我查一下 TSLA",
                    "user_id": user_id or "U12345",
                    "timestamp": "2024-01-15T10:31:00Z",
                    "source": "user"
                }
            ]
            
            # 根據 limit 限制回傳數量
            limited_messages = mock_messages[:limit]
            
            return LineMessageResponse(
                ok=True,
                data=limited_messages,
                mock=True,
                notice="這是模擬資料",
                timestamp=datetime.now().isoformat()
            )
        else:
            # 真實模式 - 從資料庫讀取
            messages = await database_service.get_line_messages(
                user_id=user_id,
                chat_id=chat_id,
                start_time=start,
                end_time=end,
                limit=limit
            )
            
            return LineMessageResponse(
                ok=True,
                data=messages,
                timestamp=datetime.now().isoformat()
            )
            
    except Exception as e:
        logger.error(f"查詢 LINE 訊息失敗: {str(e)}")
        return LineMessageResponse(
            ok=False,
            reason="query_failed",
            timestamp=datetime.now().isoformat()
        )


@router.post("/push", response_model=LinePushResponse)
async def push_line_message(request: LinePushRequest) -> LinePushResponse:
    """
    推播 LINE 訊息
    
    根據 USE_MOCK_LINE 設定決定模擬推播或真實推播
    """
    logger.info(f"推播 LINE 訊息: user_id={request.user_id}")
    
    try:
        if settings.use_mock_line:
            # 模擬模式
            logger.info(f"模擬推播訊息給 {request.user_id}: {request.text}")
            
            return LinePushResponse(
                ok=True,
                mock=True,
                notice="這是模擬推播",
                timestamp=datetime.now().isoformat()
            )
        else:
            # 真實模式 - 呼叫 LINE API
            result = await line_client.push_message(request.user_id, request.text)
            
            if result.get("ok"):
                return LinePushResponse(
                    ok=True,
                    timestamp=datetime.now().isoformat()
                )
            else:
                return LinePushResponse(
                    ok=False,
                    reason=result.get("reason", "push_failed"),
                    timestamp=datetime.now().isoformat()
                )
                
    except Exception as e:
        logger.error(f"推播 LINE 訊息失敗: {str(e)}")
        return LinePushResponse(
            ok=False,
            reason="push_failed",
            timestamp=datetime.now().isoformat()
        )


@router.post("/webhook")
async def line_webhook(
    request: Request,
    x_line_signature: str = Header(..., alias="X-Line-Signature")
) -> Dict[str, str]:
    """
    LINE Webhook 端點
    
    接收 LINE 平台的事件通知並儲存到資料庫
    僅在 USE_MOCK_LINE=0 時啟用
    """
    if settings.use_mock_line:
        raise HTTPException(
            status_code=400, 
            detail="Webhook 在模擬模式下不可用，請設定 USE_MOCK_LINE=0"
        )
    
    try:
        # 讀取請求內容
        body = await request.body()
        
        # 驗證簽章
        if not verify_line_signature(body, x_line_signature):
            logger.warning("LINE webhook 簽章驗證失敗")
            raise HTTPException(status_code=400, detail="簽章驗證失敗")
        
        # 解析 JSON
        webhook_data = json.loads(body.decode('utf-8'))
        webhook_request = LineWebhookRequest(**webhook_data)
        
        # 處理每個事件
        for event in webhook_request.events:
            await database_service.save_line_event(event.dict())
            logger.info(f"儲存 LINE 事件: type={event.type}, timestamp={event.timestamp}")
        
        return {"status": "ok"}
        
    except json.JSONDecodeError:
        logger.error("LINE webhook JSON 解析失敗")
        raise HTTPException(status_code=400, detail="JSON 格式錯誤")
    except Exception as e:
        logger.error(f"LINE webhook 處理失敗: {str(e)}")
        raise HTTPException(status_code=500, detail="內部伺服器錯誤")


# 推播相關的 Pydantic 模型
class PushTextRequest(BaseModel):
    user_id: str = Field(..., description="使用者 ID")
    text: str = Field(..., description="推播文字內容")


class PushFlexRequest(BaseModel):
    user_id: str = Field(..., description="使用者 ID")
    alt_text: str = Field(..., description="替代文字")
    flex_content: Dict[str, Any] = Field(..., description="Flex 內容")


class PushStockQuoteRequest(BaseModel):
    user_id: str = Field(..., description="使用者 ID")
    symbol: str = Field(..., description="股票代號")
    price: float = Field(..., description="股價")
    change: float = Field(..., description="漲跌金額")
    change_percent: float = Field(..., description="漲跌百分比")


@router.post("/push")
async def push_text_message(request: PushTextRequest):
    """推播文字訊息"""
    try:
        result = await line_client.push_text_message(request.user_id, request.text)
        return result
    except Exception as e:
        logger.error(f"推播文字訊息失敗: {str(e)}")
        raise HTTPException(status_code=500, detail="推播失敗")


@router.post("/push/flex")
async def push_flex_message(request: PushFlexRequest):
    """推播 Flex 訊息"""
    try:
        result = await line_client.push_flex_message(
            request.user_id,
            request.alt_text,
            request.flex_content
        )
        return result
    except Exception as e:
        logger.error(f"推播 Flex 訊息失敗: {str(e)}")
        raise HTTPException(status_code=500, detail="推播失敗")


@router.post("/push/stock-quote")
async def push_stock_quote(request: PushStockQuoteRequest):
    """推播股票報價卡片"""
    try:
        flex_content = line_client.create_stock_quote_flex(
            request.symbol,
            request.price,
            request.change,
            request.change_percent
        )

        alt_text = f"{request.symbol} 股價: ${request.price:.2f} ({request.change_percent:+.2f}%)"

        result = await line_client.push_flex_message(
            request.user_id,
            alt_text,
            flex_content
        )
        return result
    except Exception as e:
        logger.error(f"推播股票報價失敗: {str(e)}")
        raise HTTPException(status_code=500, detail="推播失敗")


@router.get("/status")
async def get_line_status() -> Dict[str, Any]:
    """取得 LINE 模組狀態"""
    return {
        "ok": True,
        "mode": "mock" if settings.use_mock_line else "real",
        "use_mock_line": settings.use_mock_line,
        "has_credentials": bool(settings.line_channel_access_token and settings.line_channel_secret),
        "timestamp": datetime.now().isoformat()
    }


# ---- 新增請求模型 ----
class LineMessageRequest(BaseModel):
    user_id: str = Field(..., description="LINE 使用者 ID")
    message_text: str = Field(..., description="訊息內容")

class LineStockQueryRequest(BaseModel):
    user_id: str
    symbol: str

class LineReportRequest(BaseModel):
    user_id: str
    symbols: List[str]


# ---- 新增端點 ----
@router.post("/process-message", response_model=LinePushResponse)
async def process_line_message(request: LineMessageRequest) -> LinePushResponse:
    logger.info("LINE process-message: %s -> %s", request.user_id, request.message_text)
    try:
        from app.services.line_agent_service import line_agent_service
        result = await line_agent_service.process_line_message(request.user_id, request.message_text)
        if result.get("ok"):
            return LinePushResponse(ok=True, notice=f"已處理，抽取到代號：{result.get('symbols', [])}")
        return LinePushResponse(ok=False, reason=result.get("reason","processing_failed"))
    except Exception as e:
        logger.exception("process-message 失敗：%s", e)
        return LinePushResponse(ok=False, reason="exception")

@router.post("/query-stock", response_model=LinePushResponse)
async def query_stock(request: LineStockQueryRequest) -> LinePushResponse:
    logger.info("LINE query-stock: %s -> %s", request.user_id, request.symbol)
    try:
        from app.services.line_agent_service import line_agent_service
        result = await line_agent_service.process_stock_inquiry(request.user_id, request.symbol)
        if result.get("ok"):
            return LinePushResponse(ok=True, notice=f"已推播 {request.symbol} 股票資訊")
        return LinePushResponse(ok=False, reason=result.get("reason","stock_query_failed"))
    except Exception as e:
        logger.exception("query-stock 失敗：%s", e)
        return LinePushResponse(ok=False, reason="exception")

@router.post("/generate-report", response_model=LinePushResponse)
async def generate_stock_report(request: LineReportRequest) -> LinePushResponse:
    logger.info("LINE generate-report: %s -> %s", request.user_id, request.symbols)
    try:
        from app.services.line_agent_service import line_agent_service
        result = await line_agent_service.process_report_request(request.user_id, request.symbols)
        if result.get("ok"):
            return LinePushResponse(ok=True, notice=f"已生成報告：{', '.join(request.symbols)}")
        return LinePushResponse(ok=False, reason=result.get("reason","report_generation_failed"))
    except Exception as e:
        logger.exception("generate-report 失敗：%s", e)
        return LinePushResponse(ok=False, reason="exception")

@router.get("/user-symbols/{user_id}")
async def get_user_stock_symbols(user_id: str, limit: int = 20) -> Dict[str, Any]:
    """示例：如需從 DB 取用戶歷史可在 line_agent_service 裡補，這裡回傳空集合以免耦合。"""
    try:
        from app.services.line_agent_service import line_agent_service  # noqa
        # 如果已在 service 實作歷史解析，可改為：
        # symbols = await line_agent_service.extract_stock_symbols_from_messages(user_id, limit)
        symbols: List[str] = []
        return {"ok": True, "user_id": user_id, "symbols": symbols, "count": len(symbols), "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.exception("user-symbols 失敗：%s", e)
        return {"ok": False, "reason": "exception", "error": str(e), "timestamp": datetime.now().isoformat()}
