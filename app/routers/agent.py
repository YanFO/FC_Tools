"""
Agent 路由器
處理 /agent/run 端點，支援四種輸入類型的智能代理請求
"""
import logging
from typing import Dict, Any, Optional, List, Literal
from datetime import datetime
import uuid

from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel, Field, validator

from app.graphs.agent_graph import agent_graph
from app.services.session import session_service
from app.services.rules import rules_service


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent", tags=["agent"])


async def save_session_summary_task(session_id: str, messages: List[Dict[str, Any]], trace_id: str):
    """背景任務：儲存 Session 摘要"""
    try:
        logger.info(f"[{trace_id}] 開始儲存 Session {session_id} 摘要")
        success = await session_service.save_session_summary(session_id, messages)
        if success:
            logger.info(f"[{trace_id}] Session {session_id} 摘要儲存成功")
        else:
            logger.warning(f"[{trace_id}] Session {session_id} 摘要儲存失敗")
    except Exception as e:
        logger.error(f"[{trace_id}] 儲存 Session {session_id} 摘要時發生錯誤: {str(e)}")


# 請求模型定義
class FileRequest(BaseModel):
    """檔案處理請求"""
    path: str = Field(..., description="檔案路徑")
    task: Literal["qa", "report"] = Field(default="qa", description="處理任務類型")
    template_id: Optional[str] = Field(default=None, description="報告模板 ID（僅用於 report 任務）")


class LineRequest(BaseModel):
    """LINE 聊天記錄請求"""
    user_id: Optional[str] = Field(default=None, description="使用者 ID")
    chat_id: Optional[str] = Field(default=None, description="聊天室 ID")
    start: Optional[str] = Field(default=None, description="開始時間 (ISO 格式)")
    end: Optional[str] = Field(default=None, description="結束時間 (ISO 格式)")
    
    @validator('start', 'end')
    def validate_datetime(cls, v):
        if v is not None:
            try:
                datetime.fromisoformat(v.replace('Z', '+00:00'))
            except ValueError:
                raise ValueError('日期時間格式必須為 ISO 格式')
        return v


class RuleRequest(BaseModel):
    """規則查詢請求"""
    rules: Dict[str, Any] = Field(..., description="規則定義")
    symbols: Optional[List[str]] = Field(default=None, description="股票代號列表")
    indicators: Optional[List[str]] = Field(default=None, description="指標列表")
    thresholds: Optional[Dict[str, float]] = Field(default=None, description="門檻值")


class AgentOptions(BaseModel):
    """Agent 選項"""
    lang: str = Field(default="tw", description="回應語言")
    top_k: int = Field(default=5, description="回傳結果數量")
    include_sources: bool = Field(default=True, description="是否包含資料來源")
    format: Literal["json", "markdown", "plain"] = Field(default="json", description="回應格式")


class AgentRequest(BaseModel):
    """Agent 請求模型"""
    input_type: Literal["text", "file", "line", "rule"] = Field(..., description="輸入類型")
    session_id: Optional[str] = Field(default=None, description="當前 Session ID")
    parent_session_id: Optional[str] = Field(default=None, description="父 Session ID（用於上下文注入）")
    query: Optional[str] = Field(default=None, description="查詢文字（用於 text 和 file QA）")
    file: Optional[FileRequest] = Field(default=None, description="檔案處理請求")
    line: Optional[LineRequest] = Field(default=None, description="LINE 聊天記錄請求")
    rule: Optional[RuleRequest] = Field(default=None, description="規則查詢請求")
    options: Optional[AgentOptions] = Field(default_factory=AgentOptions, description="Agent 選項")
    
    @validator('query')
    def validate_query_for_text_and_file_qa(cls, v, values):
        input_type = values.get('input_type')
        file_info = values.get('file')
        
        if input_type == 'text' and not v:
            raise ValueError('text 類型需要提供 query')
        
        if input_type == 'file' and file_info and file_info.task == 'qa' and not v:
            raise ValueError('file QA 任務需要提供 query')
        
        return v
    
    @validator('file')
    def validate_file_for_file_type(cls, v, values):
        input_type = values.get('input_type')
        
        if input_type == 'file' and not v:
            raise ValueError('file 類型需要提供 file 資訊')
        
        return v
    
    @validator('line')
    def validate_line_for_line_type(cls, v, values):
        input_type = values.get('input_type')
        
        if input_type == 'line' and not v:
            raise ValueError('line 類型需要提供 line 資訊')
        
        if input_type == 'line' and v and not v.user_id and not v.chat_id:
            raise ValueError('line 類型需要提供 user_id 或 chat_id')
        
        return v
    
    @validator('rule')
    def validate_rule_for_rule_type(cls, v, values):
        input_type = values.get('input_type')
        
        if input_type == 'rule' and not v:
            raise ValueError('rule 類型需要提供 rule 資訊')
        
        return v


# 回應模型定義
class SourceInfo(BaseModel):
    """資料來源資訊"""
    source: str = Field(..., description="來源名稱")
    timestamp: Optional[str] = Field(default=None, description="時間戳")
    tool: Optional[str] = Field(default=None, description="使用的工具")


class NLGInfo(BaseModel):
    """NLG 處理資訊模型"""
    raw: Optional[str] = Field(default=None, description="正式摘要（處理前）")
    colloquial: Optional[str] = Field(default=None, description="口語化摘要（處理後）")
    system_prompt: Optional[str] = Field(default=None, description="口語化系統提示")


class AgentResponse(BaseModel):
    """Agent 回應模型"""
    ok: bool = Field(..., description="請求是否成功")
    response: Optional[str] = Field(default=None, description="回應內容")
    input_type: str = Field(..., description="輸入類型")
    tool_results: Optional[List[Dict[str, Any]]] = Field(default=None, description="工具執行結果")
    sources: Optional[List[SourceInfo]] = Field(default=None, description="資料來源")
    warnings: Optional[List[str]] = Field(default=None, description="警告訊息")
    error: Optional[str] = Field(default=None, description="錯誤訊息")
    timestamp: str = Field(..., description="回應時間戳")
    trace_id: Optional[str] = Field(default=None, description="追蹤 ID")
    nlg: Optional[NLGInfo] = Field(default=None, description="NLG 處理資訊（口語化前後對照）")


@router.post("/run", response_model=AgentResponse)
async def run_agent(
    request: AgentRequest,
    http_request: Request,
    background_tasks: BackgroundTasks
) -> AgentResponse:
    """
    執行 Agent 處理請求
    
    支援四種輸入類型：
    - text: 文字查詢，支援股票、新聞、總經數據查詢
    - file: 檔案處理，支援 QA 和報告生成
    - line: LINE 聊天記錄分析
    - rule: 規則查詢，批次處理多個條件
    """
    # 取得追蹤 ID
    trace_id = getattr(http_request.state, 'trace_id', str(uuid.uuid4()))
    
    logger.info(f"[{trace_id}] Agent 請求: {request.input_type}")
    
    try:
        # 處理 parent_session_id 上下文注入
        system_prompt_context = None
        if request.parent_session_id:
            logger.info(f"[{trace_id}] 注入父 Session 上下文: {request.parent_session_id}")
            system_prompt_context = await session_service.create_system_prompt_with_context(
                request.parent_session_id
            )

        # 準備輸入資料
        input_data = {
            "input_type": request.input_type,
            "session_id": request.session_id,
            "parent_session_id": request.parent_session_id,
            "query": request.query,
            "options": request.options.dict() if request.options else {},
            "system_prompt_context": system_prompt_context
        }

        # 根據輸入類型加入特定資料
        if request.file:
            input_data["file"] = request.file.dict()

        if request.line:
            input_data["line"] = request.line.dict()

        if request.rule:
            input_data["rule"] = request.rule.dict()

        # 處理文字查詢的前置檢查
        if request.input_type == "text" and request.query:
            # 1. /rules 快路徑：直接回規則摘要，不進 Graph、不調工具
            if request.query.strip() == "/rules":
                logger.info(f"[{trace_id}] 處理 /rules 查詢，直接返回規則摘要")
                rules_summary = rules_service.get_rules_summary()
                return AgentResponse(
                    ok=True,
                    response=rules_summary,
                    input_type=request.input_type,
                    tool_results=[],  # 不調工具
                    sources=[],
                    warnings=[],
                    timestamp=datetime.now().isoformat(),
                    trace_id=trace_id,
                    nlg=NLGInfo(
                        raw=rules_summary,
                        colloquial=None,
                        system_prompt=None
                    )
                )

            # 3. 規則違規檢查
            violation = rules_service.check_violation(request.query)
            if violation:
                logger.info(f"[{trace_id}] 檢測到規則違規，直接拒絕: {violation['rule_id']}")
                # 直接返回拒絕回應，不進入 Graph
                return AgentResponse(
                    ok=True,  # 技術上成功處理了請求
                    response=violation["rule_explanation"],
                    input_type=request.input_type,
                    tool_results=[],  # 沒有執行工具
                    sources=[],
                    warnings=[f"rule_violation:{violation['rule_id']}"],
                    timestamp=datetime.now().isoformat(),
                    trace_id=trace_id,
                    nlg=NLGInfo(
                        raw=violation["rule_explanation"],
                        colloquial=None,
                        system_prompt=None
                    )
                )

            # 4. 其他文字查詢委派至 Supervisor Agent
            logger.info(f"[{trace_id}] 文字查詢委派至 Supervisor Agent")
            try:
                # 準備輸入資料
                agent_input = {
                    "input_type": request.input_type,
                    "query": request.query,
                    "session_id": request.session_id,
                    "trace_id": trace_id
                }

                # 執行 Supervisor Agent
                agent_result = await agent_graph.run_sync(agent_input)

                # 防禦式檢查回應格式
                if not isinstance(agent_result, dict):
                    logger.error(f"[{trace_id}] agent_result 不是字典格式: {type(agent_result)}")
                    raise ValueError(f"Supervisor Agent 回傳格式錯誤: {type(agent_result)}")

                # 防禦式取值，避免 KeyError
                response_text = agent_result.get("response")
                if not response_text or not str(response_text).strip():
                    response_text = "查詢處理完成，但無回應內容"
                    logger.warning(f"[{trace_id}] agent_result 缺少或為空的 'response' 欄位")
                    agent_result["response"] = response_text

                # 轉換為 AgentResponse 格式
                return AgentResponse(
                    ok=agent_result.get("ok", True),
                    response=response_text,
                    input_type=request.input_type,
                    tool_results=agent_result.get("tool_results", []),
                    sources=[SourceInfo(
                        source=source.get("source", "UNKNOWN"),
                        tool=source.get("tool", "unknown_tool"),
                        timestamp=source.get("timestamp", datetime.now().isoformat())
                    ) for source in agent_result.get("sources", [])],
                    warnings=agent_result.get("warnings", []),
                    timestamp=datetime.now().isoformat(),
                    trace_id=trace_id,
                    nlg=NLGInfo(
                        raw=agent_result.get("nlg", {}).get("raw", ""),
                        colloquial=agent_result.get("nlg", {}).get("colloquial"),
                        system_prompt=None
                    ),
                    output_files=agent_result.get("output_files", [])
                )

            except Exception as e:
                logger.error(f"[{trace_id}] Supervisor Agent 執行失敗: {str(e)}")
                return AgentResponse(
                    ok=False,
                    response=f"查詢處理失敗：{str(e)}",
                    input_type=request.input_type,
                    tool_results=[],
                    sources=[],
                    warnings=[f"supervisor_agent_error:{str(e)}"],
                    timestamp=datetime.now().isoformat(),
                    trace_id=trace_id,
                    nlg=NLGInfo(
                        raw=f"查詢處理失敗：{str(e)}",
                        colloquial=None,
                        system_prompt=None
                    )
                )

        # 執行 Agent
        logger.info(f"[{trace_id}] 開始執行 Agent")
        result = await agent_graph.run_sync(input_data)
        
        # 檢查結果
        if not result.get("ok", False):
            logger.error(f"[{trace_id}] Agent 執行失敗: {result.get('error', 'Unknown error')}")
            raise HTTPException(
                status_code=500,
                detail=f"Agent 執行失敗: {result.get('error', 'Unknown error')}"
            )
        
        # 格式化回應
        nlg_info = result.get("nlg")
        response = AgentResponse(
            ok=True,
            response=result.get("response", ""),
            input_type=result.get("input_type", request.input_type),
            tool_results=result.get("tool_results", []),
            sources=[SourceInfo(**source) for source in result.get("sources", [])],
            warnings=result.get("warnings", []),
            timestamp=result.get("timestamp", datetime.now().isoformat()),
            trace_id=trace_id,
            nlg=NLGInfo(**nlg_info) if nlg_info else None
        )

        # 背景任務：儲存 Session 摘要（如果有 session_id）
        if request.session_id and result.get("messages"):
            background_tasks.add_task(
                save_session_summary_task,
                request.session_id,
                result.get("messages", []),
                trace_id
            )

        logger.info(f"[{trace_id}] Agent 執行成功")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{trace_id}] Agent 請求處理失敗: {str(e)}", exc_info=True)
        
        return AgentResponse(
            ok=False,
            error=str(e),
            input_type=request.input_type,
            timestamp=datetime.now().isoformat(),
            trace_id=trace_id
        )


@router.get("/templates")
async def list_report_templates():
    """列出可用的報告模板"""
    try:
        from app.services.report import report_service
        templates = report_service.list_templates()
        
        return {
            "ok": True,
            "templates": templates,
            "count": len(templates),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"列出模板失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"列出模板失敗: {str(e)}")


@router.get("/reports")
async def list_generated_reports(limit: int = 50):
    """列出已生成的報告"""
    try:
        from app.services.report import report_service
        reports = report_service.list_generated_reports(limit)
        
        return {
            "ok": True,
            "reports": reports,
            "count": len(reports),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"列出報告失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"列出報告失敗: {str(e)}")


@router.get("/reports/{filename}")
async def get_report_content(filename: str):
    """取得報告內容"""
    try:
        from app.services.report import report_service
        result = report_service.get_report_content(filename)
        
        if not result["ok"]:
            raise HTTPException(status_code=404, detail=result["message"])
        
        return {
            "ok": True,
            "report": result["data"],
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取得報告失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"取得報告失敗: {str(e)}")


@router.get("/stats")
async def get_agent_stats():
    """取得 Agent 統計資訊"""
    try:
        from app.services.rag import rag_service
        from app.services.report import report_service
        
        rag_stats = rag_service.get_store_stats()
        report_stats = {
            "total_reports": len(report_service.list_generated_reports()),
            "available_templates": len(report_service.list_templates())
        }
        
        return {
            "ok": True,
            "stats": {
                "rag": rag_stats,
                "reports": report_stats,
                "api_status": {
                    "openai": bool(agent_graph.llm),
                    "fmp": bool(agent_graph.llm),  # 這裡應該檢查 FMP 狀態
                    "line": True  # 這裡應該檢查 LINE 狀態
                }
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"取得統計資訊失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"取得統計資訊失敗: {str(e)}")


@router.post("/rules/reload")
async def reload_rules():
    """重新載入規則配置"""
    try:
        result = rules_service.reload_rules()
        return result
    except Exception as e:
        logger.error(f"重新載入規則失敗: {e}")
        return {
            "ok": False,
            "message": f"重新載入規則失敗: {str(e)}"
        }
