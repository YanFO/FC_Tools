"""
Financial Modeling Prep (FMP) API 客戶端
提供股票報價、公司檔案、新聞和總經數據查詢功能
"""
import logging
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import httpx

from app.settings import settings


logger = logging.getLogger(__name__)


class FMPClient:
    """FMP API 客戶端類別"""
    
    def __init__(self):
        self.base_url = "https://financialmodelingprep.com/api"
        self.api_key = settings.fmp_api_key
        self.timeout = 30.0
    
    def _check_api_key(self) -> Dict[str, Any]:
        """檢查 API 金鑰是否可用"""
        if not self.api_key:
            return {
                "ok": False,
                "reason": "missing_api_key",
                "message": "FMP API 金鑰未設定",
                "data": None
            }
        return {"ok": True}
    
    async def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """發送 HTTP 請求到 FMP API"""
        key_check = self._check_api_key()
        if not key_check["ok"]:
            return key_check
        
        if params is None:
            params = {}
        
        params["apikey"] = self.api_key
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}{endpoint}", params=params)
                response.raise_for_status()
                
                data = response.json()
                
                return {
                    "ok": True,
                    "data": data,
                    "source": "FMP",
                    "timestamp": datetime.now().isoformat()
                }
                
        except httpx.TimeoutException:
            logger.error(f"FMP API 請求逾時: {endpoint}")
            return {
                "ok": False,
                "reason": "timeout",
                "message": "API 請求逾時",
                "data": None
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"FMP API HTTP 錯誤: {e.response.status_code} - {endpoint}")
            return {
                "ok": False,
                "reason": "http_error",
                "message": f"HTTP {e.response.status_code} 錯誤",
                "data": None
            }
        except Exception as e:
            logger.error(f"FMP API 請求失敗: {str(e)} - {endpoint}")
            return {
                "ok": False,
                "reason": "request_failed",
                "message": str(e),
                "data": None
            }
    
    async def get_quote(self, symbols: Union[str, List[str]]) -> Dict[str, Any]:
        """
        取得股票即時報價
        
        Args:
            symbols: 股票代號或代號列表
            
        Returns:
            包含報價資料的字典
        """
        if isinstance(symbols, str):
            symbols = [symbols]
        
        symbols_str = ",".join(symbols)
        endpoint = f"/v3/quote/{symbols_str}"
        
        logger.info(f"查詢股票報價: {symbols_str}")
        result = await self._make_request(endpoint)
        
        if result["ok"] and result["data"]:
            # 格式化報價資料
            quotes = result["data"] if isinstance(result["data"], list) else [result["data"]]
            formatted_quotes = []
            
            for quote in quotes:
                formatted_quotes.append({
                    "symbol": quote.get("symbol"),
                    "name": quote.get("name"),
                    "price": quote.get("price"),
                    "change": quote.get("change"),
                    "changesPercentage": quote.get("changesPercentage"),
                    "dayLow": quote.get("dayLow"),
                    "dayHigh": quote.get("dayHigh"),
                    "volume": quote.get("volume"),
                    "timestamp": quote.get("timestamp")
                })
            
            result["data"] = formatted_quotes
        
        return result
    
    async def get_profile(self, symbols: Union[str, List[str]]) -> Dict[str, Any]:
        """
        取得公司基本資料
        
        Args:
            symbols: 股票代號或代號列表
            
        Returns:
            包含公司資料的字典
        """
        if isinstance(symbols, str):
            symbols = [symbols]
        
        symbols_str = ",".join(symbols)
        endpoint = f"/v3/profile/{symbols_str}"
        
        logger.info(f"查詢公司資料: {symbols_str}")
        result = await self._make_request(endpoint)
        
        if result["ok"] and result["data"]:
            # 格式化公司資料
            profiles = result["data"] if isinstance(result["data"], list) else [result["data"]]
            formatted_profiles = []
            
            for profile in profiles:
                formatted_profiles.append({
                    "symbol": profile.get("symbol"),
                    "companyName": profile.get("companyName"),
                    "industry": profile.get("industry"),
                    "sector": profile.get("sector"),
                    "description": profile.get("description"),
                    "website": profile.get("website"),
                    "marketCap": profile.get("mktCap"),
                    "employees": profile.get("fullTimeEmployees"),
                    "country": profile.get("country"),
                    "exchange": profile.get("exchangeShortName")
                })
            
            result["data"] = formatted_profiles
        
        return result
    
    async def get_news(self,
                      symbols: Optional[Union[str, List[str]]] = None,
                      query: Optional[str] = None,
                      from_date: Optional[str] = None,
                      to_date: Optional[str] = None,
                      limit: int = 10,
                      **kwargs) -> Dict[str, Any]:
        """
        取得新聞資料

        Args:
            symbols: 股票代號或代號列表（可選）
            query: 搜尋關鍵字（可選）
            from_date: 開始日期 YYYY-MM-DD（可選）
            to_date: 結束日期 YYYY-MM-DD（可選）
            limit: 回傳筆數限制

        Returns:
            包含新聞資料的字典
        """
        # 處理 kwargs 中的重複參數，避免 multiple values 錯誤
        kwargs.pop("symbols", None)
        kwargs.pop("query", None)
        kwargs.pop("limit", None)
        kwargs.pop("from_date", None)
        kwargs.pop("to_date", None)
        if symbols:
            if isinstance(symbols, str):
                symbols = [symbols]
            endpoint = f"/v3/stock_news"
            params = {"tickers": ",".join(symbols), "limit": limit}
        else:
            endpoint = "/v3/fmp/articles"
            params = {"page": 0, "size": limit}
        
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        
        logger.info(f"查詢新聞: symbols={symbols}, query={query}, limit={limit}")
        result = await self._make_request(endpoint, params)
        
        if result["ok"] and result["data"]:
            # 格式化新聞資料
            news_items = result["data"] if isinstance(result["data"], list) else [result["data"]]
            formatted_news = []
            
            for item in news_items[:limit]:  # 確保不超過限制
                formatted_news.append({
                    "title": item.get("title"),
                    "text": item.get("text", "")[:500] + "..." if len(item.get("text", "")) > 500 else item.get("text", ""),
                    "url": item.get("url"),
                    "symbol": item.get("symbol"),
                    "publishedDate": item.get("publishedDate"),
                    "site": item.get("site")
                })
            
            result["data"] = formatted_news
        
        return result
    
    async def get_macro_data(self, 
                           indicator: str,
                           country: str = "US",
                           period: str = "annual") -> Dict[str, Any]:
        """
        取得總體經濟數據
        
        Args:
            indicator: 經濟指標 (GDP, CPI, unemployment, etc.)
            country: 國家代碼 (預設 US)
            period: 期間 (annual, quarterly, monthly)
            
        Returns:
            包含總經數據的字典
        """
        # FMP 總經數據端點映射
        indicator_map = {
            "gdp": "/v4/economic",
            "cpi": "/v4/economic", 
            "unemployment": "/v4/economic",
            "interest_rate": "/v4/economic"
        }
        
        endpoint = indicator_map.get(indicator.lower(), "/v4/economic")
        params = {
            "name": indicator.upper(),
            "country": country.upper()
        }
        
        logger.info(f"查詢總經數據: {indicator} - {country}")
        result = await self._make_request(endpoint, params)
        
        if result["ok"] and result["data"]:
            # 格式化總經數據
            macro_data = result["data"] if isinstance(result["data"], list) else [result["data"]]
            formatted_data = []
            
            for item in macro_data[:10]:  # 限制回傳筆數
                formatted_data.append({
                    "indicator": indicator,
                    "country": country,
                    "date": item.get("date"),
                    "value": item.get("value"),
                    "unit": item.get("unit", ""),
                    "period": item.get("period", period)
                })
            
            result["data"] = formatted_data
        
        return result


# 全域 FMP 客戶端實例
fmp_client = FMPClient()
