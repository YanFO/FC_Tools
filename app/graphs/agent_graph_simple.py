"""
簡化版 LangGraph Agent 實作
精簡版的代理圖，允許 LLM 自主決策同時保持核心功能。

主要簡化項目：
1. **降低狀態複雜度**：將 AgentState 簡化為僅包含必要欄位
2. **精簡圖結構**：僅 3 個節點 (agent -> tools -> response_builder) 相較於原版的 7+ 個
3. **LLM 自主性**：移除複雜路由邏輯，讓 LLM 決定使用哪些工具
4. **移除監督架構**：移除 supervisor_copywriting、nlg_compose、colloquialize 節點
5. **簡化決策邏輯**：基於工具循環和工具呼叫的基本 should_continue()
6. **移除複雜功能**：無對話歷史、會話管理或進階 NLG
7. **錯誤處理**：服務不可用時的優雅降級
8. **直接工具存取**：LLM 可直接呼叫任何可用工具，無路由限制

架構：
- 入口：agent_node（初始化訊息，使用工具呼叫 LLM）
- 條件：should_continue（檢查工具呼叫和循環限制）
- 工具：ToolNode（執行工具呼叫）
- 出口：response_builder（格式化最終回應）

此簡化版本保持所有核心功能，同時更容易理解和修改。
LLM 擁有完全自主權，可根據使用者查詢決定使用哪些工具。
"""
import logging
from typing import Dict, Any, List, Optional, Literal, TypedDict, Annotated
from datetime import datetime
import json
import os
import sys
from pathlib import Path

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain.callbacks.tracers import LangChainTracer
from langgraph.config import get_stream_writer

# 將專案根目錄加入路徑
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
sys.path.append(project_root)

# 帶錯誤處理的服務導入
try:
    from app.settings import settings
    SETTINGS_AVAILABLE = True
    print(f"設定已載入 - OpenAI API Key: {'已設定' if settings.openai_api_key else '未設定'}")
except ImportError as e:
    print(f"警告：無法載入設定：{e}")
    SETTINGS_AVAILABLE = False

    # 模擬設定
    class MockSettings:
        openai_api_key = None
        azure_openai_api_key = None
        azure_openai_endpoint = None
        azure_openai_deployment = "gpt-4"
        azure_openai_api_version = "2023-12-01-preview"
        max_tool_loops = 3
        execute_tools = 1

    settings = MockSettings()

try:
    from app.services.fmp_client import fmp_client
    from app.services.line_client import line_client
    from app.services.file_ingest import file_ingest_service
    from app.services.rag import rag_service
    from app.services.report import report_service
    SERVICES_AVAILABLE = True
except ImportError as e:
    print(f"警告：部分服務不可用：{e}")
    SERVICES_AVAILABLE = False

    # 為缺失的服務建立模擬物件
    class MockService:
        async def get_quote(self, *args, **kwargs):
            return {"ok": False, "reason": "service_unavailable"}
        async def get_profile(self, *args, **kwargs):
            return {"ok": False, "reason": "service_unavailable"}
        async def get_news(self, *args, **kwargs):
            return {"ok": False, "reason": "service_unavailable"}
        async def get_macro_data(self, *args, **kwargs):
            return {"ok": False, "reason": "service_unavailable"}
        async def process_file(self, *args, **kwargs):
            return {"ok": False, "reason": "service_unavailable"}
        async def query_documents(self, *args, **kwargs):
            return {"ok": False, "reason": "service_unavailable"}
        async def answer_question(self, *args, **kwargs):
            return {"ok": False, "reason": "service_unavailable"}
        async def generate_report(self, *args, **kwargs):
            return {"ok": False, "reason": "service_unavailable"}
        async def fetch_messages(self, *args, **kwargs):
            return {"ok": False, "reason": "service_unavailable"}

    fmp_client = MockService()
    line_client = MockService()
    file_ingest_service = MockService()
    rag_service = MockService()
    report_service = MockService()

logger = logging.getLogger(__name__)


# 簡化狀態定義
class SimpleAgentState(TypedDict):
    """簡化代理狀態 - 僅專注於必要欄位"""
    messages: Annotated[List[BaseMessage], add_messages]
    input_type: Literal["text", "file", "line", "rule"]
    query: Optional[str]
    file_info: Optional[Dict[str, Any]]
    line_info: Optional[Dict[str, Any]]
    rule_info: Optional[Dict[str, Any]]

    # 必要處理欄位
    tool_results: Optional[List[Dict[str, Any]]]
    final_response: Optional[Dict[str, Any]]
    warnings: List[str]

    # 循環控制
    tool_loop_count: int


# 工具定義（重用自原版）
@tool
async def tool_fmp_quote(symbols: List[str]) -> Dict[str, Any]:
    """取得股票報價"""
    logger.info(f"呼叫 FMP 報價工具：{symbols}")
    return await fmp_client.get_quote(symbols)


@tool
async def tool_fmp_profile(symbols: List[str]) -> Dict[str, Any]:
    """取得公司資料"""
    logger.info(f"呼叫 FMP 公司資料工具：{symbols}")
    return await fmp_client.get_profile(symbols)


@tool
async def tool_fmp_news(symbols: Optional[List[str]] = None,
                       query: Optional[str] = None,
                       limit: int = 10) -> Dict[str, Any]:
    """取得新聞資料"""
    logger.info(f"呼叫 FMP 新聞工具：symbols={symbols}, query={query}")
    return await fmp_client.get_news(symbols=symbols, query=query, limit=limit)


@tool
async def tool_fmp_macro(indicator: str, country: str = "US") -> Dict[str, Any]:
    """取得總體經濟資料
    參數:
    - indicator: 總經指標名稱，必須是以下之一：
      GDP, realGDP, nominalPotentialGDP, realGDPPerCapita, federalFunds, CPI,
      inflationRate, inflation, retailSales, consumerSentiment, durableGoods,
      unemploymentRate, totalNonfarmPayroll, initialClaims, industrialProductionTotalIndex,
      newPrivatelyOwnedHousingUnitsStartedTotalUnits, totalVehicleSales, retailMoneyFunds,
      smoothedUSRecessionProbabilities, 3MonthOr90DayRatesAndYieldsCertificatesOfDeposit,
      commercialBankInterestRateOnCreditCardPlansAllAccounts, 30YearFixedRateMortgageAverage,
      15YearFixedRateMortgageAverage
    - country: 國家代碼，預設為 "US"
    """

    logger.info(f"呼叫 FMP 總經工具：{indicator}, {country}")
    return await fmp_client.get_macro_data(indicator, country)


@tool
async def tool_file_load(file_path: str) -> Dict[str, Any]:
    """載入檔案內容"""
    logger.info(f"呼叫檔案載入工具：{file_path}")
    return await file_ingest_service.process_file(file_path)


@tool
async def tool_rag_query(question: str, top_k: int = 5) -> Dict[str, Any]:
    """RAG 查詢"""
    logger.info(f"呼叫 RAG 查詢工具：{question}")
    query_result = await rag_service.query_documents(question, top_k)
    if query_result["ok"] and query_result["data"]["relevant_chunks"]:
        return await rag_service.answer_question(question, query_result["data"]["relevant_chunks"])
    return query_result


@tool
async def tool_report_generate(template_id: str, context: Dict[str, Any],
                              output_formats: List[str] = None) -> Dict[str, Any]:
    """產生報告"""
    logger.info(f"呼叫報告產生工具：{template_id}")
    output_formats = output_formats or ["markdown", "pdf"]
    return await report_service.generate_report(template_id, context, output_formats[0])


@tool
async def tool_line_fetch(user_id: Optional[str] = None,
                         chat_id: Optional[str] = None,
                         start_date: Optional[str] = None,
                         end_date: Optional[str] = None,
                         limit: int = 100) -> Dict[str, Any]:
    """抓取 LINE 訊息"""
    logger.info(f"呼叫 LINE 抓取工具：user_id={user_id}, chat_id={chat_id}")
    return await line_client.fetch_messages(user_id, chat_id, start_date, end_date, limit)


# 工具清單
tools = [
    tool_fmp_quote,
    tool_fmp_profile,
    tool_fmp_news,
    tool_fmp_macro,
    tool_file_load,
    tool_rag_query,
    tool_report_generate,
    tool_line_fetch
]


class SimpleAgentGraph:
    """簡化代理圖 - LLM 驅動，最小路由複雜度"""

    def __init__(self):
        self.llm = self._create_llm()
        self.graph = self._create_graph()
        self.tracer = LangChainTracer(project_name="agent") 

    def _create_llm(self) -> Optional[ChatOpenAI]:
        """建立 LLM 實例"""
        if settings.openai_api_key:
            return ChatOpenAI(
                model="gpt-4o-mini",
                api_key=settings.openai_api_key,
                temperature=0.3
            )
        elif settings.azure_openai_api_key and settings.azure_openai_endpoint:
            return ChatOpenAI(
                model=settings.azure_openai_deployment,
                api_key=settings.azure_openai_api_key,
                azure_endpoint=settings.azure_openai_endpoint,
                api_version=settings.azure_openai_api_version,
                temperature=0.3
            )
        else:
            logger.warning("未設定 OpenAI 或 Azure OpenAI API 金鑰")
            return None


    def _create_graph(self) -> StateGraph:
        """建立簡化 LangGraph"""
        workflow = StateGraph(SimpleAgentState)

        # 加入節點 - 僅簡化為必要節點
        workflow.add_node("agent", self.agent_node)
        workflow.add_node("tools", ToolNode(tools))
        workflow.add_node("response_builder", self.response_builder)

        # 設定入口點
        workflow.set_entry_point("agent")

        # 加入條件邊 - 簡化決策邏輯
        workflow.add_conditional_edges(
            "agent",
            self.should_continue,
            {
                "continue": "tools",
                "end": "response_builder"
            }
        )

        # 工具回到代理進行潛在的額外處理
        workflow.add_edge("tools", "agent")

        # 回應建構器結束流程
        workflow.add_edge("response_builder", END)

        return workflow.compile()

    def should_continue(self, state: SimpleAgentState) -> str:
        """簡化決策邏輯 - 讓 LLM 決定何時使用工具"""
        # 檢查工具執行限制
        tool_loop_count = state.get("tool_loop_count", 0)
        max_loops = getattr(settings, 'max_tool_loops', 3)

        if tool_loop_count >= max_loops:
            logger.info(f"達到最大工具循環次數（{max_loops}）")
            return "end"

        # 檢查工具是否被停用
        execute_tools = getattr(settings, 'execute_tools', 1)
        if isinstance(execute_tools, str):
            execute_tools = int(execute_tools)

        if execute_tools == 0:
            logger.info("工具執行已停用")
            return "end"

        # 檢查最後一則訊息是否有工具呼叫
        messages = state.get("messages", [])
        if messages:
            last_message = messages[-1]
            
            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                return "continue"

        return "end"

    async def _handle_special_commands(self, state: SimpleAgentState) -> Optional[SimpleAgentState]:
        """處理特殊指令 (/report, /template)"""
        query = state.get("query", "").strip()

        if not query:
            return None

        # 處理 /report 指令
        if query.startswith("/report"):
            return await self._handle_report_command(state, query)

        # 處理 /template 指令
        elif query.startswith("/template"):
            return await self._handle_template_command(state, query)

        return None

    async def _handle_report_command(self, state: SimpleAgentState, query: str) -> SimpleAgentState:
        """處理 /report 指令"""
        try:
            # 提取報告參數
            report_params = query[7:].strip()  # 移除 "/report" 前綴

            if not report_params:
                error_msg = AIMessage(content="錯誤：/report 指令需要參數。使用方式：/report AAPL NVDA 股票分析")
                state["messages"].append(error_msg)
                return state

            # 導入並實例化 SimpleReportAgent
            from app.graphs.report_agent_simple import SimpleReportAgent
            report_agent = SimpleReportAgent()

            # 準備 ReportAgent 輸入
            report_input = {
                "input_type": "text",
                "query": f"/report {report_params}",
                "session_id": state.get("session_id", "simple_agent"),
                "trace_id": f"simple_agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            }

            # 執行報告生成
            logger.info(f"執行報告生成：{report_params}")
            report_result = await report_agent.run(report_input)

            # 整合結果到標準回應格式
            if report_result.get("ok", False):
                success_msg = AIMessage(content=report_result["response"])
                state["messages"].append(success_msg)

                # 添加報告結果到 tool_results
                if not state.get("tool_results"):
                    state["tool_results"] = []
                state["tool_results"].append({
                    "ok": True,
                    "type": "report_generation",
                    "output_files": report_result.get("output_files", []),
                    "session_id": report_result.get("session_id"),
                    "timestamp": report_result.get("timestamp")
                })
            else:
                error_msg = AIMessage(content=f"報告生成失敗：{report_result.get('response', '未知錯誤')}")
                state["messages"].append(error_msg)

                # 添加錯誤到 warnings
                if not state.get("warnings"):
                    state["warnings"] = []
                state["warnings"].append(f"報告生成失敗：{report_result.get('error', '未知錯誤')}")

        except Exception as e:
            logger.error(f"處理 /report 指令時發生錯誤：{e}")
            error_msg = AIMessage(content=f"處理報告指令時發生錯誤：{str(e)}")
            state["messages"].append(error_msg)

            if not state.get("warnings"):
                state["warnings"] = []
            state["warnings"].append(f"報告指令處理錯誤：{str(e)}")

        return state

    async def _handle_template_command(self, state: SimpleAgentState, query: str) -> SimpleAgentState:
        """處理 /template 指令"""
        try:
            # 提取模板 ID
            template_id = query[9:].strip()  # 移除 "/template" 前綴

            if not template_id: 
                error_msg = AIMessage(content="錯誤：/template 指令需要模板 ID。使用方式：/template stock.j2")
                state["messages"].append(error_msg)
                return state

            # 驗證模板檔案
            template_path = Path(project_root) / "templates" / "reports" / template_id

            # 檢查副檔名
            if not (template_id.endswith('.j2') or template_id.endswith('.md')):
                error_msg = AIMessage(content=f"錯誤：模板檔案必須是 .j2 或 .md 格式。收到：{template_id}")
                state["messages"].append(error_msg)
                return state

            # 檢查檔案是否存在
            if not template_path.exists():
                available_templates = []
                templates_dir = Path(project_root) / "templates" / "reports"
                if templates_dir.exists():
                    available_templates = [f.name for f in templates_dir.glob("*.j2")] + [f.name for f in templates_dir.glob("*.md")]

                error_msg = AIMessage(content=f"錯誤：模板檔案不存在：{template_id}\n可用的模板：{', '.join(available_templates) if available_templates else '無'}")
                state["messages"].append(error_msg)
                return state

            # 更新全域模板設定（通過環境變數）
            os.environ["REPORT_TEMPLATE_ID"] = template_id

            # 確認回應
            success_msg = AIMessage(content=f"✅ 模板已成功切換為：{template_id}\n模板路徑：{template_path}\n此設定將用於後續的報告生成。")
            state["messages"].append(success_msg)

            logger.info(f"模板已切換為：{template_id}")

        except Exception as e:
            logger.error(f"處理 /template 指令時發生錯誤：{e}")
            error_msg = AIMessage(content=f"處理模板指令時發生錯誤：{str(e)}")
            state["messages"].append(error_msg)

            if not state.get("warnings"):
                state["warnings"] = []
            state["warnings"].append(f"模板指令處理錯誤：{str(e)}")

        return state

    async def agent_node(self, state: SimpleAgentState) -> SimpleAgentState:
        """簡化代理節點 - 讓 LLM 處理所有決策"""
        logger.info("執行簡化代理節點")
        messages = state.get("messages", [])
        writer = get_stream_writer()

        # 根據輸入類型初始化訊息（如果為空）
        if not messages:
            messages = self._initialize_messages(state)
            state["messages"] = messages

        # 優先處理特殊指令 (/report, /template)
        special_result = await self._handle_special_commands(state)
        if special_result is not None:
            logger.info("特殊指令已處理，跳過一般 LLM 處理流程")
            return special_result

        # 檢查是否剛完成工具執行
        if self._has_tool_results(messages):
            current_count = state.get("tool_loop_count", 0)
            state["tool_loop_count"] = current_count + 1
            logger.info(f"工具循環計數：{state['tool_loop_count']}")

        # 如果 LLM 不可用，提供降級回應
        if not self.llm:
            logger.warning("LLM 不可用，使用降級回應")
            fallback_msg = AIMessage(content="LLM 未設定。請設定 OpenAI API 金鑰。")
            state["messages"].append(fallback_msg)
            return state

        # 讓 LLM 決定下一步 - 無複雜路由
        try:
            llm_with_tools = self.llm.bind_tools(tools)
            # response = await llm_with_tools.ainvoke(messages)

            # 使用 astream 進行串流處理，支援工具呼叫
            response_content = ""
            first = True
            gathered = None
            tool_calls_sent = False
            
            async for chunk in llm_with_tools.astream(messages):
                # 累積訊息塊以處理工具呼叫
                if first:
                    gathered = chunk
                    first = False
                else:
                    gathered = gathered + chunk
                
                # 串流內容到 writer
                if hasattr(chunk, 'content') and chunk.content:
                    writer(chunk.content)
                    response_content += chunk.content
                
                # 檢查是否有完整的工具呼叫且尚未發送
                if (hasattr(gathered, 'tool_calls') and gathered.tool_calls and 
                    not tool_calls_sent and 
                    all(tc.get('args') and isinstance(tc.get('args'), dict) for tc in gathered.tool_calls)):
                    print("!tool_calls", gathered.tool_calls)

                #   writer(f"\n[工具呼叫] {len(gathered.tool_calls)} 個工具")

                    # 格式化工具呼叫資訊
                    tool_info = []
                    for tc in gathered.tool_calls:
                        tool_name = tc.get('name', 'unknown')
                        tool_args = tc.get('args', {})
                        tool_info.append(f"{tool_name}工具被呼叫，參數為{tool_args}\n\n")
                    
                    writer(f"\n[工具呼叫] {', '.join(tool_info)}")
                    tool_calls_sent = True
            
            # 使用累積的訊息作為回應（包含工具呼叫）
            response = gathered if gathered else AIMessage(content=response_content)
            
            state["messages"].append(response)
            tool_calls_count = len(getattr(response, 'tool_calls', []))
            logger.info(f"LLM 回應已產生，包含 {tool_calls_count} 個工具呼叫")
        except Exception as e:
            logger.error(f"LLM 調用失敗：{e}")
            error_msg = AIMessage(content=f"處理請求時發生錯誤：{str(e)}")
            state["messages"].append(error_msg)

        return state

    def _initialize_messages(self, state: SimpleAgentState) -> List[BaseMessage]:
        """根據輸入類型和簡化系統提示初始化訊息"""
        input_type = state.get("input_type", "text")
        query = state.get("query", "")

        # 鼓勵 LLM 自主性的簡單系統提示
        system_prompt = """你是一個有用的金融和資料分析助理。你可以使用各種工具：
            - 股票報價和金融資料 (tool_fmp_quote, tool_fmp_profile, tool_fmp_news, tool_fmp_macro)
            - 檔案處理 (tool_file_load)
            - 文件搜尋 (tool_rag_query)
            - 報告產生 (tool_report_generate)
            - LINE 訊息抓取 (tool_line_fetch)

            分析使用者的請求並決定使用哪些工具。如有需要，你可以呼叫多個工具。在決策時要保持自主性，若查詢總經相關問題，至少需調用3個不同總經指標。

        """

        messages = [SystemMessage(content=system_prompt)]

        if input_type == "text":
            if query:
                messages.append(HumanMessage(content=query))
            else:
                messages.append(HumanMessage(content="今天我可以如何幫助您？"))

        elif input_type == "file":
            file_info = state.get("file_info", {})
            file_path = file_info.get("path", "")
            task = file_info.get("task", "qa")

            if task == "qa" and query:
                content = f"請處理檔案 '{file_path}' 並回答：{query}"
            else:
                content = f"請處理檔案 '{file_path}' 執行任務：{task}"
            messages.append(HumanMessage(content=content))

        elif input_type == "line":
            line_info = state.get("line_info", {})
            content = f"請抓取並分析 LINE 訊息：{line_info}"
            messages.append(HumanMessage(content=content))

        elif input_type == "rule":
            rule_info = state.get("rule_info", {})
            content = f"請執行規則查詢：{rule_info}"
            messages.append(HumanMessage(content=content))

        return messages

    def _has_tool_results(self, messages: List[BaseMessage]) -> bool:
        """檢查訊息是否包含最近的工具執行結果"""
        if len(messages) < 2:
            return False

        # 尋找模式：帶有 tool_calls 的 AIMessage 後跟 ToolMessage(s)
        for i in range(len(messages) - 1):
            msg = messages[i]
            if (hasattr(msg, "tool_calls") and msg.tool_calls and
                i + 1 < len(messages) and
                isinstance(messages[i + 1], ToolMessage)):
                return True
        return False

    async def response_builder(self, state: SimpleAgentState) -> SimpleAgentState:
        """從對話和工具結果建構最終回應"""
        logger.info("建構最終回應")
        writer = get_stream_writer()
        messages = state.get("messages", [])
        tool_results = []
        warnings = state.get("warnings", [])

        # 從訊息中提取工具結果
        for msg in messages:
            if isinstance(msg, ToolMessage):
                try:
                    if isinstance(msg.content, str):
                        content = json.loads(msg.content)
                    else:
                        content = msg.content
                    tool_results.append(content)
                except (json.JSONDecodeError, TypeError):
                    tool_results.append({"raw_content": str(msg.content)})

        # 取得最終 AI 回應
        final_ai_response = ""
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and not msg.tool_calls:
                final_ai_response = msg.content
                # writer(msg.content)
                break

        # 如果沒有最終回應，使用 LLM 產生自然語言回應
        # if not final_ai_response and tool_results:
        #     print("generate natural response")
        #     final_ai_response = await self._generate_natural_response(state, tool_results)
        # elif not final_ai_response:
        #     final_ai_response = "我準備好幫助您！請告訴我您需要什麼。"

        # 建構最終回應
        state["final_response"] = {
            "ok": True,
            "response": final_ai_response,
            "input_type": state["input_type"],
            "tool_results": tool_results,
            "warnings": warnings,
            "tool_loop_count": state.get("tool_loop_count", 0),
            "timestamp": datetime.now().isoformat(),
            "simplified": True  # 標記為簡化版本
        }

        state["tool_results"] = tool_results
        return state

    # async def _generate_natural_response(self, state: SimpleAgentState, tool_results: List[Dict[str, Any]]) -> str:
    #     """使用 LLM 產生自然語言回應"""
    #     try:
    #         # 如果 LLM 不可用，使用降級回應
    #         writer = get_stream_writer()
    #         if not self.llm:
    #             successful_tools = sum(1 for tr in tool_results if isinstance(tr, dict) and tr.get("ok", False))
    #             return f"執行了 {len(tool_results)} 個工具（{successful_tools} 個成功）。請查看 tool_results 取得詳細資訊。"

    #         # 準備工具結果摘要
    #         tool_summary = self._prepare_tool_summary(tool_results)

    #         # 取得原始查詢
    #         original_query = state.get("query", "")

    #         # 建立提示來產生自然回應
    #         response_prompt = f"""基於以下工具執行結果，請為使用者提供一個清晰、有用的回應。

    #         原始查詢：{original_query}

    #         工具執行結果：
    #         {tool_summary}

    #         請提供一個自然、直接的回應，專注於回答使用者的問題。不要提及技術細節如「工具執行」或「API 呼叫」。
    #         如果有具體的資料（如股價、新聞等），請直接呈現給使用者。
    #         如果工具執行失敗，請禮貌地說明無法取得資訊的原因。"""

    #         # 使用 LLM 產生回應
    #         # response = self.llm.invoke([HumanMessage(content=response_prompt)])
    #         print(response_prompt)
            
    #         # 使用 astream 進行串流處理
    #         response_content = ""
    #         async for chunk in self.llm.astream([HumanMessage(content=response_prompt)]):
    #             print(chunk)
    #             if hasattr(chunk, 'content') and chunk.content:
    #                 writer(chunk.content)
    #                 response_content += chunk.content
            
    #         return response_content.strip()

    #     except Exception as e:
    #         logger.error(f"產生自然語言回應時發生錯誤：{e}")
    #         # 降級到技術性摘要
    #         successful_tools = sum(1 for tr in tool_results if isinstance(tr, dict) and tr.get("ok", False))
    #         return f"執行了 {len(tool_results)} 個工具（{successful_tools} 個成功）。請查看 tool_results 取得詳細資訊。"

    # def _prepare_tool_summary(self, tool_results: List[Dict[str, Any]]) -> str:
    #     """準備工具結果摘要供 LLM 使用"""
    #     if not tool_results:
    #         return "沒有工具執行結果。"

    #     summary_parts = []
    #     for i, result in enumerate(tool_results, 1):
    #         if isinstance(result, dict):
    #             if result.get("ok", False):
    #                 # 成功的工具結果
    #                 data = result.get("data", {})
    #                 source = result.get("source", "未知來源")

    #                 if isinstance(data, list) and data:
    #                     # 處理列表資料（如股票報價）
    #                     summary_parts.append(f"工具 {i} ({source}) 成功：{json.dumps(data, ensure_ascii=False, indent=2)}")
    #                 elif isinstance(data, dict):
    #                     # 處理字典資料
    #                     summary_parts.append(f"工具 {i} ({source}) 成功：{json.dumps(data, ensure_ascii=False, indent=2)}")
    #                 else:
    #                     # 處理其他資料類型
    #                     summary_parts.append(f"工具 {i} ({source}) 成功：{str(data)}")
    #             else:
    #                 # 失敗的工具結果
    #                 reason = result.get("reason", "未知錯誤")
    #                 error = result.get("error", "")
    #                 summary_parts.append(f"工具 {i} 失敗：{reason} {error}".strip())
    #         else:
    #             # 處理非字典結果
    #             summary_parts.append(f"工具 {i} 結果：{str(result)}")

    #     return "\n".join(summary_parts)

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """執行簡化代理"""
        try:
            # 準備初始狀態
            initial_state = SimpleAgentState(
                messages=[],
                input_type=input_data["input_type"],
                query=input_data.get("query"),
                file_info=input_data.get("file"),
                line_info=input_data.get("line"),
                rule_info=input_data.get("rule"),
                tool_results=None,
                final_response=None,
                warnings=[],
                tool_loop_count=0
            )

            # 執行圖
            config = {"recursion_limit": 10, "callbacks": [self.tracer]}
            # result = await self.graph.ainvoke(initial_state, config=config)
            async for result in self.graph.astream(initial_state,subgraphs=False,stream_mode=["custom"],config=config):
                yield result

            # return result["final_response"]

        except Exception as e:
            logger.error(f"簡化代理執行失敗：{str(e)}", exc_info=True)
            yield "error"
            # return {
            #     "ok": False,
            #     "error": str(e),
            #     "input_type": input_data.get("input_type", "unknown"),
            #     "timestamp": datetime.now().isoformat(),
            #     "simplified": True
            # }

    async def run_sync(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """執行簡化代理（同步版本，用於測試）"""
        try:
            # 準備初始狀態
            initial_state = SimpleAgentState(
                messages=[],
                input_type=input_data["input_type"],
                query=input_data.get("query"),
                file_info=input_data.get("file"),
                line_info=input_data.get("line"),
                rule_info=input_data.get("rule"),
                tool_results=None,
                final_response=None,
                warnings=[],
                tool_loop_count=0
            )

            # 執行圖
            config = {"recursion_limit": 10, "callbacks": [self.tracer]}
            result = await self.graph.ainvoke(initial_state, config=config)

            return result["final_response"]

        except Exception as e:
            logger.error(f"簡化代理執行失敗：{str(e)}", exc_info=True)
            return {
                "ok": False,
                "error": str(e),
                "input_type": input_data.get("input_type", "unknown"),
                "timestamp": datetime.now().isoformat(),
                "simplified": True
            }


# 建立全域實例
# simple_agent_graph = SimpleAgentGraph()


def build_simple_graph():
    """與現有程式碼相容的建構函數"""
    return simple_agent_graph.graph


# 現有介面的相容性函數
def build_graph():
    """回傳簡化圖的相容性函數"""
    return build_simple_graph()


if __name__ == "__main__":
    """直接執行支援"""
    import asyncio
    async def test_simple_agent():

        simple_agent_graph = SimpleAgentGraph()

        """使用範例查詢測試簡化代理"""
        try:
            input = {
                "input_type": "text",
                "query": "最近AAPL有什麼新聞？"
                # "query": "你好"
                # "query": "/report AAPL"
            }
            async for result in simple_agent_graph.run(input):
                print(result[1],flush=True,end="")
            # print(f"✅ 成功：{result.get('response', '無回應')}")
            # if result.get('tool_results'):
                # print(f"🔧 執行的工具：{len(result['tool_results'])}")
        except Exception as e:
            print(f"❌ 錯誤：{str(e)}")

        print("-" * 30)
        print("\n🎉 測試完成！")

    asyncio.run(test_simple_agent())