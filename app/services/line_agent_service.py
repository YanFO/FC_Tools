# app/services/line_agent_service.py
from __future__ import annotations
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class LineAgentService:
    """LINE ↔ Agent 整合服務"""

    def __init__(self):
        self.line_client = None
        self.agent_graph = None
        self.ticker_resolver = None
        self._init_dependencies()

    def _init_dependencies(self):
        """初始化依賴項目"""
        try:
            from app.services.line_client import line_client
            self.line_client = line_client
        except ImportError:
            logger.warning("LINE client 未找到")

        try:
            from app.graphs.agent_graph import agent_graph
            self.agent_graph = agent_graph
        except ImportError:
            logger.warning("Agent graph 未找到")

        try:
            from app.services.ticker_resolver import ticker_resolver
            self.ticker_resolver = ticker_resolver
        except ImportError:
            logger.warning("Ticker resolver 未找到")

    async def process_line_message(self, user_id: str, message_text: str) -> Dict[str, Any]:
        """處理 LINE 訊息，自動解析股票代號並推播相關資訊"""
        try:
            logger.info("處理 LINE 訊息: %s -> %s", user_id, message_text)

            # 第一步：解析股票代號
            if not self.ticker_resolver:
                return {"ok": False, "reason": "ticker_resolver_not_available"}

            symbol_result = await self.ticker_resolver.resolve_symbols(message_text)
            if not symbol_result.get("ok") or not symbol_result.get("symbols"):
                # 沒有找到股票代號，回傳一般訊息
                await self._push_text_message(user_id, "抱歉，我無法從您的訊息中識別出股票代號。請嘗試輸入如「AAPL」或「蘋果股價」等。")
                return {"ok": True, "symbols": [], "action": "no_symbols_found"}

            # 第二步：處理找到的股票代號
            symbols = [c.symbol for c in symbol_result["symbols"] if c.score > 0.5]
            if not symbols:
                await self._push_text_message(user_id, "找到了一些可能的股票代號，但信心度不高。請提供更明確的股票代號。")
                return {"ok": True, "symbols": [], "action": "low_confidence"}

            # 第三步：查詢股價並推播
            for symbol in symbols[:3]:  # 最多處理3個代號
                await self.process_stock_inquiry(user_id, symbol)

            return {
                "ok": True,
                "symbols": symbols,
                "action": "stock_inquiry_processed",
                "count": len(symbols)
            }

        except Exception as e:
            logger.exception("處理 LINE 訊息失敗：%s", e)
            await self._push_text_message(user_id, "處理您的訊息時發生錯誤，請稍後再試。")
            return {"ok": False, "reason": "exception", "error": str(e)}

    async def process_stock_inquiry(self, user_id: str, symbol: str) -> Dict[str, Any]:
        """處理股票查詢請求，推播股價 Flex 卡片"""
        try:
            logger.info("處理股票查詢: %s -> %s", user_id, symbol)

            if not self.agent_graph:
                return {"ok": False, "reason": "agent_graph_not_available"}

            # 調用 Agent 查詢股價
            query = f"請問{symbol}股價？"
            agent_result = await self._call_agent(query)

            if not agent_result.get("ok"):
                await self._push_text_message(user_id, f"無法查詢 {symbol} 的股價資訊。")
                return {"ok": False, "reason": "agent_query_failed"}

            # 推播文字回應
            await self._push_text_message(user_id, agent_result.get("response", "查詢完成"))

            return {"ok": True, "symbol": symbol}

        except Exception as e:
            logger.exception("處理股票查詢失敗：%s", e)
            await self._push_text_message(user_id, f"查詢 {symbol} 時發生錯誤。")
            return {"ok": False, "reason": "exception", "error": str(e)}

    async def process_report_request(self, user_id: str, symbols: List[str]) -> Dict[str, Any]:
        """處理報告生成請求"""
        try:
            logger.info("處理報告請求: %s -> %s", user_id, symbols)

            if not self.agent_graph:
                return {"ok": False, "reason": "agent_graph_not_available"}

            # 調用 Agent 生成報告
            query = f"/report stock {' '.join(symbols)}"
            agent_result = await self._call_agent(query)

            if not agent_result.get("ok"):
                await self._push_text_message(user_id, f"無法生成 {', '.join(symbols)} 的報告。")
                return {"ok": False, "reason": "agent_report_failed"}

            await self._push_text_message(user_id, agent_result.get("response", "報告生成完成"))

            return {"ok": True, "symbols": symbols}

        except Exception as e:
            logger.exception("處理報告請求失敗：%s", e)
            await self._push_text_message(user_id, f"生成 {', '.join(symbols)} 報告時發生錯誤。")
            return {"ok": False, "reason": "exception", "error": str(e)}

    async def _call_agent(self, query: str) -> Dict[str, Any]:
        """調用 Agent 處理查詢"""
        try:
            if not self.agent_graph:
                return {"ok": False, "reason": "agent_not_available"}

            # 簡化的 Agent 調用，直接使用 HTTP 請求
            import httpx
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    "http://localhost:8000/api/agent/run",
                    json={"input_type": "text", "query": query}
                )
                if response.status_code == 200:
                    data = response.json()
                    return {"ok": True, "response": data.get("response", "")}
                else:
                    return {"ok": False, "reason": "agent_http_error"}

        except Exception as e:
            logger.exception("調用 Agent 失敗：%s", e)
            return {"ok": False, "reason": "agent_call_failed", "error": str(e)}

    async def _push_text_message(self, user_id: str, text: str) -> Dict[str, Any]:
        """推播文字訊息"""
        if not self.line_client:
            logger.warning("LINE client 不可用，無法推播訊息")
            return {"ok": False, "reason": "line_client_not_available"}

        return await self.line_client.push_text_message(user_id, text)


# 全域實例
line_agent_service = LineAgentService()