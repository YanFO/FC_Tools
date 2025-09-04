# -*- coding: utf-8 -*-  #zh-TW
"""
意圖路由器 (Intent Router)
實施最小工具原則：每個查詢最多使用一個工具
"""

from enum import Enum
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class Intent(str, Enum):
    """意圖分類枚舉"""
    quote = "quote"          # 股價查詢
    news = "news"            # 新聞查詢
    macro = "macro"          # 總經數據查詢
    report = "report"        # 報告生成
    rules = "rules"          # 規則查詢
    line = "line"            # LINE 聊天記錄分析
    ambiguous = "ambiguous"  # 模糊/未分類


# 可擴充：中文公司名→Ticker 的極小字典；必要時移到設定或資料檔
NAME2TICKER: Dict[str, str] = {"台積電": "TSM", "臺積電": "TSM", "蘋果": "AAPL"}


def normalize_symbol(q: str) -> Optional[str]:
    """從查詢中提取股票代號"""
    for k, v in NAME2TICKER.items():
        if k in q:
            return v
    # 改進的正則表達式：使用 lookaround 支援中英文混合文本
    import re
    m = re.search(r"(?<![A-Za-z])[A-Z]{1,5}(?![A-Za-z])", q.upper())
    return m.group(0) if m else None


# 國別映射表
COUNTRY_MAPPING = {
    "US": ["美國", "USA", "U.S.", "US", "United States", "美"],
    "CN": ["中國", "中", "China", "CN", "Mainland", "大陸", "中華人民共和國"],
    "TW": ["台灣", "臺灣", "Taiwan", "TW"],
    "JP": ["日本", "Japan", "JP"],
    "EU": ["歐元區", "歐洲區", "Eurozone", "EU", "EZ"]
}


def extract_country(query: str) -> str:
    """
    從查詢中抽取國別代碼

    Args:
        query: 使用者查詢字串

    Returns:
        str: 國別代碼 (US/CN/TW/JP/EU)，預設 US
    """
    if not query:
        return "US"

    query_upper = query.upper()

    # 檢查每個國別的關鍵詞
    for country_code, keywords in COUNTRY_MAPPING.items():
        for keyword in keywords:
            if keyword.upper() in query_upper:
                return country_code

    # 預設美國
    return "US"


def classify_intent(q: str) -> Intent:
    """分類查詢意圖"""
    t = q.strip().lower()
    if t.startswith("/rules") or "規則" in t:
        return Intent.rules
    if t.startswith("/template") or t.startswith("/report") or "簡報" in t or "報告" in t:
        return Intent.report
    if any(k in t for k in ["新聞", "news", "頭條", "消息"]):
        return Intent.news
    if any(k in t for k in ["總經", "宏觀", "經濟", "經濟數據", "經濟指標", "macro", "cpi", "gdp", "失業", "利率", "殖利率", "ism", "宏觀經濟", "總體經濟"]):
        return Intent.macro
    if any(k in t for k in ["股價", "報價", "price", "收盤", "開盤", "盤中", "stock", "stocks", "quote", "quotes"]):
        return Intent.quote
    return Intent.ambiguous  # 保守預設，後續以 quote 處理


class IntentRouter:
    """意圖路由器 - 實施最小工具原則"""

    def __init__(self):
        pass
    
    def classify_intent(self, query: str) -> Intent:
        """使用全域函數進行意圖分類"""
        return classify_intent(query)
    
    def get_allowed_tools(self, intent: Intent) -> List[str]:
        """根據意圖獲取允許的工具列表"""
        tool_mapping = {
            Intent.quote: ["tool_fmp_quote", "tool_fmp_profile", "tool_fmp_news"],  # 支持股價、公司資料和新聞
            Intent.news: ["tool_fmp_news"],
            Intent.macro: ["tool_fmp_macro"],
            Intent.report: ["tool_fmp_quote", "tool_fmp_profile", "tool_fmp_news"],
            Intent.rules: [],  # 不使用工具
            Intent.line: ["tool_line_analysis"],
            Intent.ambiguous: ["tool_fmp_quote"]  # 保守預設為股價查詢
        }
        return tool_mapping.get(intent, [])

    def filter_tool_calls(self, intent: Intent, tool_calls: List[Dict]) -> List[Dict]:
        """根據意圖過濾工具調用，對於 QUOTE 意圖允許多個相關工具"""
        if not tool_calls:
            return []

        allowed_tools = self.get_allowed_tools(intent)
        if not allowed_tools:
            return []

        # 對於 QUOTE 意圖，允許 quote 和 profile 工具同時執行
        if intent == Intent.quote:
            filtered_tools = []
            for tool_call in tool_calls:
                tool_name = tool_call.get("name", "")
                if tool_name in allowed_tools:
                    logger.info(f"保留工具調用: {tool_name} (意圖: {intent})")
                    filtered_tools.append(tool_call)
            return filtered_tools

        # 其他意圖維持最小工具原則（最多1個）
        for tool_call in tool_calls:
            tool_name = tool_call.get("name", "")
            if tool_name in allowed_tools:
                logger.info(f"保留工具調用: {tool_name} (意圖: {intent})")
                return [tool_call]  # 只返回第一個匹配的工具

        logger.warning(f"沒有找到匹配的工具 (意圖: {intent}, 允許: {allowed_tools})")
        return []


# 全域路由器實例
intent_router = IntentRouter()
