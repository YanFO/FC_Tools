# app/services/ticker_resolver.py
from __future__ import annotations
import os
import json
import logging
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

# ---- 可與 settings.py 對接；若 settings 不存在相應欄位，走環境變數 ----
def _get_env(name: str, default: Optional[str] = None) -> Optional[str]:
    return os.getenv(name, default)

OPENAI_API_KEY = _get_env("OPENAI_API_KEY")
OPENAI_MODEL_TICKER = _get_env("LLM_TICKER_MODEL", "gpt-4o-mini")
FMP_API_KEY = _get_env("FMP_API_KEY")
FMP_BASE = _get_env("FMP_BASE_URL", "https://financialmodelingprep.com/api/v3")

@dataclass
class SymbolCandidate:
    symbol: str
    score: float
    name: Optional[str] = None
    exchange: Optional[str] = None
    reason: Optional[str] = None

LLM_SYSTEM = """你是金融實體對齊助理。任務：從使用者訊息中辨識可能的美股代號。
要求：
1) 支援中英文公司別名（如「蘋果、台積電、谷歌C」）與直接代號（AAPL、TSM、GOOG、BRK.B）。
2) 不要幻想；模糊時標記 ambiguous。
3) 必須用函式工具 emit_symbols 回傳 JSON：symbols=[{symbol,score,reason}], ambiguity='low|medium|high'，預設 country='US'。
4) 若為非美股或無把握，降低 score；偏向常見 ADR（台積電→TSM、阿里巴巴→BABA）。
"""

LLM_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "emit_symbols",
            "description": "輸出解析到的股票代號候選清單",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbols": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "symbol": {"type": "string", "description": "股票代號"},
                                "score": {"type": "number", "description": "信心分數 0-1"},
                                "reason": {"type": "string", "description": "解析理由"}
                            },
                            "required": ["symbol", "score"]
                        }
                    },
                    "ambiguity": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "整體模糊度"
                    },
                    "country": {
                        "type": "string",
                        "default": "US",
                        "description": "主要市場"
                    }
                },
                "required": ["symbols", "ambiguity"]
            }
        }
    }
]

# 提取 SCHEMA 定義
SCHEMA = LLM_TOOLS[0]["function"]

def _openai_chat_completions():
    """建立 OpenAI 客戶端"""
    try:
        from openai import OpenAI
        if not OPENAI_API_KEY:
            return None
        return OpenAI(api_key=OPENAI_API_KEY)
    except ImportError:
        logger.warning("OpenAI 套件未安裝")
        return None

class TickerResolver:
    def __init__(self, openai_key: Optional[str] = None, fmp_key: Optional[str] = None):
        self.openai_key = openai_key or OPENAI_API_KEY
        self.fmp_key = fmp_key or FMP_API_KEY
        self.model = OPENAI_MODEL_TICKER
        self.fmp_base = FMP_BASE

    async def resolve_symbols(self, text: str, verify_with_fmp: bool = True) -> Dict[str, Any]:
        """
        從文字中解析股票代號

        Args:
            text: 使用者輸入文字
            verify_with_fmp: 是否用 FMP 驗證代號存在性

        Returns:
            {
                "ok": bool,
                "symbols": List[SymbolCandidate],
                "ambiguity": str,
                "country": str,
                "raw_llm_response": dict,
                "fmp_verification": dict
            }
        """
        try:
            # 第一步：LLM 解析
            llm_result = await self._llm_parse_symbols(text)
            if not llm_result.get("ok"):
                return llm_result

            candidates = []
            for item in llm_result.get("symbols", []):
                candidates.append(SymbolCandidate(
                    symbol=item.get("symbol", "").upper(),
                    score=float(item.get("score", 0.0)),
                    reason=item.get("reason")
                ))

            # 第二步：FMP 驗證（可選）
            fmp_verification = {}
            if verify_with_fmp and self.fmp_key:
                fmp_verification = await self._verify_symbols_with_fmp([c.symbol for c in candidates])
                # 更新候選者資訊
                for candidate in candidates:
                    fmp_info = fmp_verification.get("results", {}).get(candidate.symbol)
                    if fmp_info:
                        candidate.name = fmp_info.get("name")
                        candidate.exchange = fmp_info.get("exchange")

            return {
                "ok": True,
                "symbols": candidates,
                "ambiguity": llm_result.get("ambiguity", "medium"),
                "country": llm_result.get("country", "US"),
                "raw_llm_response": llm_result,
                "fmp_verification": fmp_verification
            }

        except Exception as e:
            logger.exception("resolve_symbols 失敗：%s", e)
            return {"ok": False, "reason": "exception", "error": str(e)}

    async def _llm_parse_symbols(self, text: str) -> Dict[str, Any]:
        """使用 LLM 解析股票代號"""
        if not self.openai_key:
            return {"ok": False, "reason": "missing_openai_key"}

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.openai_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": LLM_SYSTEM},
                            {"role": "user", "content": f"請解析以下文字中的股票代號：{text}"}
                        ],
                        "tools": LLM_TOOLS,
                        "tool_choice": {"type": "function", "function": {"name": "emit_symbols"}},
                        "temperature": 0.1
                    }
                )
                response.raise_for_status()

                data = response.json()
                if not data.get("choices"):
                    return {"ok": False, "reason": "no_choices"}

                choice = data["choices"][0]
                if choice.get("finish_reason") != "tool_calls":
                    return {"ok": False, "reason": "no_tool_calls"}

                tool_call = choice["message"]["tool_calls"][0]
                if tool_call["function"]["name"] != "emit_symbols":
                    return {"ok": False, "reason": "wrong_function"}

                result = json.loads(tool_call["function"]["arguments"])
                return {"ok": True, **result}

        except Exception as e:
            logger.exception("LLM 解析失敗：%s", e)
            return {"ok": False, "reason": "llm_error", "error": str(e)}

    async def _verify_symbols_with_fmp(self, symbols: List[str]) -> Dict[str, Any]:
        """使用 FMP 驗證股票代號"""
        if not self.fmp_key or not symbols:
            return {"ok": False, "reason": "missing_fmp_key_or_symbols"}

        results = {}
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                for symbol in symbols:
                    try:
                        response = await client.get(
                            f"{self.fmp_base}/search",
                            params={"query": symbol, "limit": 5, "apikey": self.fmp_key}
                        )
                        response.raise_for_status()

                        data = response.json()
                        if data and isinstance(data, list):
                            # 尋找完全匹配的代號
                            exact_match = next((item for item in data if item.get("symbol") == symbol), None)
                            if exact_match:
                                results[symbol] = {
                                    "found": True,
                                    "name": exact_match.get("name"),
                                    "exchange": exact_match.get("exchangeShortName"),
                                    "currency": exact_match.get("currency")
                                }
                            else:
                                results[symbol] = {"found": False, "candidates": data[:3]}
                        else:
                            results[symbol] = {"found": False}

                    except Exception as e:
                        logger.warning("FMP 驗證 %s 失敗：%s", symbol, e)
                        results[symbol] = {"found": False, "error": str(e)}

            return {"ok": True, "results": results}

        except Exception as e:
            logger.exception("FMP 批量驗證失敗：%s", e)
            return {"ok": False, "reason": "fmp_error", "error": str(e)}


# 全域實例
ticker_resolver = TickerResolver()

# 向後相容的函數（保留舊的 API）
async def _llm_candidates(text: str, k: int = 4) -> List[SymbolCandidate]:
    if not OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY 未設定，跳過 LLM 解析")
        return []
    client = _openai_chat_completions()
    if client is None:
        return []
    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL_TICKER,
            temperature=0,
            messages=[
                {"role":"system","content":LLM_SYSTEM},
                {"role":"user","content":text}
            ],
            tools=[{"type":"function","function":SCHEMA}],
            tool_choice={"type":"function","function":{"name":"emit_symbols"}}
        )
        tcalls = resp.choices[0].message.tool_calls or []
        if not tcalls:
            return []
        args = json.loads(tcalls[0].function.arguments)
        out: List[SymbolCandidate] = []
        for it in (args.get("symbols") or [])[:k]:
            sym = (it.get("symbol") or "").upper().strip()
            score = float(it.get("score") or 0)
            if sym and 0 <= score <= 1:
                out.append(SymbolCandidate(symbol=sym, score=score, reason=it.get("reason")))
        return out
    except Exception as e:
        logger.error("LLM 解析失敗：%s", e)
        return []

async def _fmp_search(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    if not FMP_API_KEY:
        logger.warning("FMP_API_KEY 未設定，跳過 FMP 驗證")
        return []
    url = f"{FMP_BASE}/search"
    params = {"query": query, "limit": limit, "apikey": FMP_API_KEY}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
            return data or []
    except Exception as e:
        logger.error("FMP 搜尋失敗：%s", e)
        return []

async def _verify_with_fmp(cands: List[SymbolCandidate]) -> List[SymbolCandidate]:
    verified: List[SymbolCandidate] = []
    for c in cands:
        # 先以 symbol 搜尋；若沒結果再用 free text（此處等同）
        res = await _fmp_search(c.symbol, limit=5)
        if not res:
            continue
        # 匹配度：完全相等優先，其次去除 .A/.B 等級別
        best = None
        for r in res:
            rsym = (r.get("symbol") or "").upper()
            if rsym == c.symbol or rsym.split(".")[0] == c.symbol.split(".")[0]:
                best = r; break
        if best is None:
            best = res[0]
        c.name = best.get("name")
        c.exchange = best.get("exchangeShortName") or best.get("exchange")
        c.score = min(1.0, c.score * 0.6 + 0.4)  # LLM×檢索加權
        verified.append(c)

    def _priority(x: SymbolCandidate) -> Tuple[int,float]:
        ex = (x.exchange or "").upper()
        tier = 0 if ex in {"NASDAQ","NYSE"} else 1
        return (tier, -x.score)

    return sorted(verified, key=_priority)

async def resolve_symbols(text: str, top_k: int = 4) -> List[SymbolCandidate]:
    """
    主流程：LLM 解析 → FMP 驗證 → 回傳候選（依交易所/分數排序）
    """
    if not text:
        return []
    cands = await _llm_candidates(text, k=top_k)
    if not cands:
        return []
    return await _verify_with_fmp(cands)
