"""
LINE Messaging API 客戶端
提供 LINE 聊天訊息抓取與分析功能
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import httpx
import re

from app.settings import settings


logger = logging.getLogger(__name__)


class LINEClient:
    """LINE Messaging API 客戶端類別"""
    
    def __init__(self):
        self.base_url = "https://api.line.me/v2/bot"
        self.access_token = settings.line_channel_access_token
        self.channel_secret = settings.line_channel_secret
        self.timeout = 30.0
        
        # 股票代號與總經關鍵詞正則表達式
        self.ticker_pattern = re.compile(r'\b([A-Z]{1,5})\b')
        self.macro_keywords = {
            'gdp': ['GDP', 'gdp', '國內生產毛額', '經濟成長'],
            'cpi': ['CPI', 'cpi', '消費者物價指數', '通膨', '通脹'],
            'unemployment': ['失業率', '非農', '就業', 'unemployment'],
            'interest_rate': ['利率', '升息', '降息', 'fed', 'FED', '聯準會']
        }
    
    def _check_credentials(self) -> Dict[str, Any]:
        """檢查 LINE API 憑證是否可用"""
        if not self.access_token or not self.channel_secret:
            return {
                "ok": False,
                "reason": "missing_credentials",
                "message": "LINE API 憑證未設定",
                "data": None
            }
        return {"ok": True}
    
    def _get_headers(self) -> Dict[str, str]:
        """取得 API 請求標頭"""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    async def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """發送 HTTP 請求到 LINE API"""
        cred_check = self._check_credentials()
        if not cred_check["ok"]:
            return cred_check
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}{endpoint}",
                    headers=self._get_headers(),
                    params=params or {}
                )
                response.raise_for_status()
                
                data = response.json()
                
                return {
                    "ok": True,
                    "data": data,
                    "source": "LINE",
                    "timestamp": datetime.now().isoformat()
                }
                
        except httpx.TimeoutException:
            logger.error(f"LINE API 請求逾時: {endpoint}")
            return {
                "ok": False,
                "reason": "timeout",
                "message": "API 請求逾時",
                "data": None
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"LINE API HTTP 錯誤: {e.response.status_code} - {endpoint}")
            return {
                "ok": False,
                "reason": "http_error",
                "message": f"HTTP {e.response.status_code} 錯誤",
                "data": None
            }
        except Exception as e:
            logger.error(f"LINE API 請求失敗: {str(e)} - {endpoint}")
            return {
                "ok": False,
                "reason": "request_failed",
                "message": str(e),
                "data": None
            }
    
    def _extract_keywords(self, text: str) -> Dict[str, List[str]]:
        """從文字中抽取股票代號與總經關鍵詞"""
        result = {
            "tickers": [],
            "macro_indicators": []
        }
        
        # 抽取股票代號
        tickers = self.ticker_pattern.findall(text.upper())
        # 過濾常見非股票代號的詞彙
        excluded_words = {'THE', 'AND', 'FOR', 'ARE', 'BUT', 'NOT', 'YOU', 'ALL', 'CAN', 'HER', 'WAS', 'ONE', 'OUR', 'HAD', 'BY'}
        result["tickers"] = [t for t in tickers if t not in excluded_words and len(t) <= 5]
        
        # 抽取總經關鍵詞
        text_lower = text.lower()
        for indicator, keywords in self.macro_keywords.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    result["macro_indicators"].append(indicator)
                    break
        
        return result
    
    async def push_message(self, user_id: str, text: str) -> Dict[str, Any]:
        """
        推播訊息給指定使用者

        Args:
            user_id: 目標使用者 ID
            text: 訊息內容

        Returns:
            推播結果字典
        """
        logger.info(f"推播 LINE 訊息給 {user_id}")

        cred_check = self._check_credentials()
        if not cred_check["ok"]:
            return cred_check

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/message/push",
                    headers=self._get_headers(),
                    json={
                        "to": user_id,
                        "messages": [
                            {
                                "type": "text",
                                "text": text
                            }
                        ]
                    }
                )
                response.raise_for_status()

                return {
                    "ok": True,
                    "message": "推播成功",
                    "timestamp": datetime.now().isoformat()
                }

        except httpx.HTTPStatusError as e:
            logger.error(f"LINE 推播 HTTP 錯誤: {e.response.status_code}")
            return {
                "ok": False,
                "reason": "http_error",
                "message": f"HTTP {e.response.status_code}",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"LINE 推播失敗: {str(e)}")
            return {
                "ok": False,
                "reason": "push_failed",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def fetch_messages(self,
                           user_id: Optional[str] = None,
                           chat_id: Optional[str] = None,
                           start_date: Optional[str] = None,
                           end_date: Optional[str] = None,
                           limit: int = 100) -> Dict[str, Any]:
        """
        抓取 LINE 聊天訊息

        Args:
            user_id: 使用者 ID（可選）
            chat_id: 聊天室 ID（可選）
            start_date: 開始日期 ISO 格式（可選）
            end_date: 結束日期 ISO 格式（可選）
            limit: 訊息數量限制

        Returns:
            包含聊天訊息的字典
        """
        # 注意：實際的 LINE Messaging API 不提供歷史訊息查詢功能
        # 這裡提供一個模擬實作，實際使用時需要透過 webhook 儲存訊息

        logger.info(f"模擬抓取 LINE 訊息: user_id={user_id}, chat_id={chat_id}")

        cred_check = self._check_credentials()
        if not cred_check["ok"]:
            return cred_check
        
        # 模擬訊息資料（實際應用中需要從資料庫查詢）
        mock_messages = [
            {
                "id": "msg001",
                "type": "text",
                "text": "AAPL 今天表現如何？",
                "userId": user_id or "U1234567890",
                "timestamp": "2025-09-01T10:00:00Z",
                "source": {"type": "user"}
            },
            {
                "id": "msg002", 
                "type": "text",
                "text": "最近 CPI 數據出來了嗎？通膨情況怎樣？",
                "userId": user_id or "U1234567890",
                "timestamp": "2025-09-01T10:05:00Z",
                "source": {"type": "user"}
            },
            {
                "id": "msg003",
                "type": "text", 
                "text": "NVDA 和 TSLA 哪個比較值得投資？",
                "userId": user_id or "U1234567890",
                "timestamp": "2025-09-01T10:10:00Z",
                "source": {"type": "user"}
            }
        ]
        
        # 過濾日期範圍
        filtered_messages = []
        for msg in mock_messages:
            msg_time = datetime.fromisoformat(msg["timestamp"].replace('Z', '+00:00'))
            
            if start_date:
                start_time = datetime.fromisoformat(start_date)
                if msg_time < start_time:
                    continue
            
            if end_date:
                end_time = datetime.fromisoformat(end_date)
                if msg_time > end_time:
                    continue
            
            filtered_messages.append(msg)
        
        # 限制數量
        filtered_messages = filtered_messages[:limit]
        
        return {
            "ok": True,
            "data": {
                "messages": filtered_messages,
                "total": len(filtered_messages),
                "user_id": user_id,
                "chat_id": chat_id,
                "date_range": {
                    "start": start_date,
                    "end": end_date
                }
            },
            "source": "LINE",
            "timestamp": datetime.now().isoformat(),
            "warning": "這是模擬資料，實際使用需要透過 webhook 儲存訊息"
        }
    
    def analyze_messages(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析聊天訊息，抽取關鍵資訊
        
        Args:
            messages: 訊息列表
            
        Returns:
            分析結果字典
        """
        analysis = {
            "total_messages": len(messages),
            "text_messages": 0,
            "keywords_found": {
                "tickers": set(),
                "macro_indicators": set()
            },
            "message_analysis": [],
            "summary": {
                "main_topics": [],
                "investment_interest": [],
                "macro_concerns": []
            }
        }
        
        for msg in messages:
            if msg.get("type") == "text" and msg.get("text"):
                analysis["text_messages"] += 1
                text = msg["text"]
                
                # 抽取關鍵詞
                keywords = self._extract_keywords(text)
                analysis["keywords_found"]["tickers"].update(keywords["tickers"])
                analysis["keywords_found"]["macro_indicators"].update(keywords["macro_indicators"])
                
                # 訊息分析
                msg_analysis = {
                    "id": msg.get("id"),
                    "timestamp": msg.get("timestamp"),
                    "text": text,
                    "keywords": keywords,
                    "intent": self._classify_intent(text)
                }
                analysis["message_analysis"].append(msg_analysis)
        
        # 轉換 set 為 list 以便 JSON 序列化
        analysis["keywords_found"]["tickers"] = list(analysis["keywords_found"]["tickers"])
        analysis["keywords_found"]["macro_indicators"] = list(analysis["keywords_found"]["macro_indicators"])
        
        # 生成摘要
        analysis["summary"]["investment_interest"] = analysis["keywords_found"]["tickers"]
        analysis["summary"]["macro_concerns"] = analysis["keywords_found"]["macro_indicators"]
        
        return analysis
    
    def _classify_intent(self, text: str) -> str:
        """分類訊息意圖"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['價格', '報價', '多少', '漲', '跌', 'price']):
            return "price_inquiry"
        elif any(word in text_lower for word in ['新聞', '消息', '資訊', 'news']):
            return "news_inquiry"
        elif any(word in text_lower for word in ['分析', '建議', '投資', '買', '賣', 'analysis']):
            return "investment_advice"
        elif any(word in text_lower for word in ['總經', '經濟', '數據', 'macro', 'economic']):
            return "macro_inquiry"
        else:
            return "general"

    async def push_text_message(self, user_id: str, text: str) -> Dict[str, Any]:
        """推播文字訊息"""
        if settings.use_mock_line:
            return {
                "ok": True,
                "mock": True,
                "message": "這是模擬資料 - 文字推播",
                "user_id": user_id,
                "text": text
            }

        url = f"{self.base_url}/message/push"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "to": user_id,
            "messages": [
                {
                    "type": "text",
                    "text": text
                }
            ]
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, headers=headers, json=payload)
                if response.status_code == 200:
                    return {"ok": True, "data": response.json()}
                else:
                    return {"ok": False, "error": f"HTTP {response.status_code}: {response.text}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def push_flex_message(self, user_id: str, alt_text: str, flex_content: Dict[str, Any]) -> Dict[str, Any]:
        """推播 Flex 訊息"""
        if settings.use_mock_line:
            return {
                "ok": True,
                "mock": True,
                "message": "這是模擬資料 - Flex 推播",
                "user_id": user_id,
                "alt_text": alt_text,
                "flex_content": flex_content
            }

        url = f"{self.base_url}/message/push"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "to": user_id,
            "messages": [
                {
                    "type": "flex",
                    "altText": alt_text,
                    "contents": flex_content
                }
            ]
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, headers=headers, json=payload)
                if response.status_code == 200:
                    return {"ok": True, "data": response.json()}
                else:
                    return {"ok": False, "error": f"HTTP {response.status_code}: {response.text}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def create_stock_quote_flex(self, symbol: str, price: float, change: float, change_percent: float) -> Dict[str, Any]:
        """創建股票報價 Flex 卡片"""
        # 根據漲跌決定顏色
        color = "#FF5551" if change < 0 else "#00C851" if change > 0 else "#6C757D"
        change_text = f"{change:+.2f} ({change_percent:+.2f}%)"

        return {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": f"{symbol} 股價",
                        "weight": "bold",
                        "size": "xl"
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "margin": "lg",
                        "spacing": "sm",
                        "contents": [
                            {
                                "type": "box",
                                "layout": "baseline",
                                "spacing": "sm",
                                "contents": [
                                    {
                                        "type": "text",
                                        "text": "價格",
                                        "color": "#aaaaaa",
                                        "size": "sm",
                                        "flex": 1
                                    },
                                    {
                                        "type": "text",
                                        "text": f"${price:.2f}",
                                        "wrap": True,
                                        "color": "#666666",
                                        "size": "sm",
                                        "flex": 5
                                    }
                                ]
                            },
                            {
                                "type": "box",
                                "layout": "baseline",
                                "spacing": "sm",
                                "contents": [
                                    {
                                        "type": "text",
                                        "text": "漲跌",
                                        "color": "#aaaaaa",
                                        "size": "sm",
                                        "flex": 1
                                    },
                                    {
                                        "type": "text",
                                        "text": change_text,
                                        "wrap": True,
                                        "color": color,
                                        "size": "sm",
                                        "flex": 5,
                                        "weight": "bold"
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        }

    def create_stock_news_flex(self, symbol: str, news_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """創建股票新聞 Flex 卡片"""
        contents = [{"type":"text","text":f"{symbol} 最新新聞","weight":"bold","size":"xl","color":"#1DB446"}]
        if not news_items:
            contents.append({"type":"text","text":"暫無相關新聞","color":"#666666","margin":"md"})
        else:
            for n in news_items[:3]:
                title = (n.get("title") or "")[:80]
                meta = " / ".join(filter(None, [n.get("site"), n.get("publishedDate")]))
                contents.extend([
                    {"type":"separator","margin":"md"},
                    {"type":"text","text":title,"size":"sm","weight":"bold","wrap":True,"margin":"sm"},
                    {"type":"text","text":meta,"size":"xs","color":"#666666","wrap":True}
                ])
        return {"type":"bubble","body":{"type":"box","layout":"vertical","contents":contents}}


# 全域 LINE 客戶端實例
line_client = LINEClient()
