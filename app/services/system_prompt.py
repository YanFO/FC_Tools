# -*- coding: utf-8 -*-  #zh-TW
"""
System Prompt 建構器
動態組裝 System Prompt：基礎原則 + Rules + Session Context + Intent-Specific 指引
"""

from typing import Optional
from .router import Intent

BASE_RULES_HEADER = (
    "【工作守則】\n"
    "- 嚴禁捏造或猜測任何數據；API 失敗必須回傳結構化錯誤；除 LINE 模擬外不得使用模擬資料。\n"
    "- 一律以繁體中文回覆；Python 指令一律使用 uv。\n"
    "- 【重要】當查詢涉及股價、新聞、總經數據時，必須使用 tool_calls 呼叫相應工具獲取實時數據。\n"
    "- 【禁止】不可僅提供工具調用的文字描述或 JSON 範例，必須實際執行 tool_calls。\n"
    "- 【執行順序】先呼叫工具獲取數據，再基於工具結果提供回覆。\n"
)


INTENT_PROMPTS = {
    Intent.quote: "【執行策略】必須先呼叫 tool_fmp_quote 獲取股價數據，然後基於結果回覆。【回覆樣式】格式如「目前 {symbol} 股價為 $價格（±漲跌幅%）」；若 tool_results 已含公司基本資料（profile），請在股價行後面加上『｜公司簡介：{一句話描述（行業/主營/地區，≤35字）}』。",
    Intent.news: "【執行策略】必須先呼叫 tool_fmp_news 獲取新聞數據，然後基於結果回覆。【回覆樣式】僅列最近 N 則：每則 1–2 句摘要；其後加「標題｜來源｜時間」。",
    Intent.macro: "【強制執行】立即使用 tool_fmp_macro 工具調用獲取總經數據，不可提供文字描述。【參數】indicator: 指標名稱, country: 國家代碼。【回覆樣式】基於工具結果輸出最近 N 期指定指標；格式：指標名稱｜最新值｜期別。",
    Intent.report: "【執行策略】必須先呼叫相關工具收集數據，然後呼叫 tool_report_generate 生成報告。【回覆樣式】僅回報 PDF 產製狀態（路徑/渲染模式/大小）。",
    Intent.rules: "【回覆樣式】輸出目前生效規則清單（id｜名稱｜一句話）。",
    Intent.ambiguous: "【執行策略】若疑似查價/新聞/總經，必須先呼叫相應工具獲取數據。【回覆樣式】基於工具結果提供準確回覆；不確定請反問 1 句。"
}


def build_system_prompt(intent: Intent, rules_block: str, session_block: Optional[str] = None, symbol: Optional[str] = None) -> str:
    """建構完整的 System Prompt"""
    parts = ["【角色】你是謹慎的金融研究助理。回覆需可驗證、可追溯。", BASE_RULES_HEADER]
    if rules_block:
        parts.append(rules_block)
    if session_block:
        parts.append(session_block)
    p = INTENT_PROMPTS.get(intent, INTENT_PROMPTS[Intent.ambiguous])
    if symbol:
        p = p.replace("{symbol}", symbol)
    parts.append(p)
    return "\n".join(parts)


class SystemPromptBuilder:
    """System Prompt 動態建構器（保持向後相容）"""

    def __init__(self):
        pass
    
    def build_system_prompt(
        self,
        intent: Intent,
        rules_block: str = "",
        session_block: Optional[str] = None,
        symbol: Optional[str] = None
    ) -> str:
        """使用全域函數建構 System Prompt"""
        return build_system_prompt(intent, rules_block, session_block, symbol)


# 全域建構器實例
system_prompt_builder = SystemPromptBuilder()
