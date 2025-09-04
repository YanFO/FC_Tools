"""
專用報告 API 路由器
處理 /report 指令觸發的報告生成功能
"""
import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel

from app.graphs.report_agent import report_agent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/report", tags=["report"])


# 請求模型
class ReportGenerateRequest(BaseModel):
    """報告生成請求模型"""
    query: str
    session_id: Optional[str] = None


# 回應模型
class ReportGenerateResponse(BaseModel):
    """報告生成回應模型"""
    ok: bool
    response: str
    input_type: str
    query: str
    output_files: List[Dict[str, Any]]
    session_id: Optional[str]
    timestamp: str
    trace_id: str
    error: Optional[str] = None


@router.post("/generate", response_model=ReportGenerateResponse)
async def generate_report(
    request: ReportGenerateRequest,
    http_request: Request,
    background_tasks: BackgroundTasks
) -> ReportGenerateResponse:
    """
    生成報告
    
    支援的報告類型：
    - /report stock AAPL TSLA - 股票報告
    - /report macro GDP CPI - 總經報告  
    - /report news AAPL - 新聞報告
    - /report custom 自訂內容 - 自訂報告
    """
    # 取得追蹤 ID
    trace_id = getattr(http_request.state, 'trace_id', str(uuid.uuid4()))
    
    logger.info(f"[{trace_id}] 報告生成請求: {request.query}")
    
    try:
        # 驗證查詢格式
        if not request.query.strip().startswith("/report"):
            raise HTTPException(
                status_code=400,
                detail="查詢必須以 /report 開頭"
            )
        
        # 準備輸入資料
        input_data = {
            "input_type": "text",
            "query": request.query,
            "session_id": request.session_id,
            "trace_id": trace_id
        }
        
        # 執行 Report Agent
        result = await report_agent.run(input_data)
        
        # 建構回應
        return ReportGenerateResponse(
            ok=result["ok"],
            response=result["response"],
            input_type=result["input_type"],
            query=result["query"],
            output_files=result["output_files"],
            session_id=result["session_id"],
            timestamp=result["timestamp"],
            trace_id=result["trace_id"],
            error=result.get("error")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{trace_id}] 報告生成失敗: {str(e)}")
        return ReportGenerateResponse(
            ok=False,
            response=f"報告生成失敗：{str(e)}",
            input_type="text",
            query=request.query,
            output_files=[],
            session_id=request.session_id,
            timestamp=datetime.now().isoformat(),
            trace_id=trace_id,
            error=str(e)
        )


@router.get("/status")
async def get_report_status() -> Dict[str, Any]:
    """取得報告模組狀態"""
    try:
        from pathlib import Path
        from app.settings import settings
        
        reports_dir = Path(settings.output_dir) / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        # 統計報告檔案
        md_files = list(reports_dir.glob("**/*.md"))
        pdf_files = list(reports_dir.glob("**/*.pdf"))
        pptx_files = list(reports_dir.glob("**/*.pptx"))
        
        total_size = sum(f.stat().st_size for f in md_files + pdf_files + pptx_files)
        
        return {
            "ok": True,
            "reports_directory": str(reports_dir),
            "file_counts": {
                "markdown": len(md_files),
                "pdf": len(pdf_files),
                "pptx": len(pptx_files),
                "total": len(md_files) + len(pdf_files) + len(pptx_files)
            },
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "directory_exists": reports_dir.exists(),
            "directory_writable": reports_dir.exists() and reports_dir.is_dir(),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"取得報告狀態失敗: {str(e)}")
        return {
            "ok": False,
            "reason": "status_failed",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.get("/templates")
async def list_templates() -> Dict[str, Any]:
    """列出可用的報告模板"""
    try:
        from pathlib import Path
        
        templates_dir = Path("templates/reports")
        
        if not templates_dir.exists():
            return {
                "ok": False,
                "reason": "templates_dir_not_found",
                "message": f"模板目錄不存在: {templates_dir}",
                "timestamp": datetime.now().isoformat()
            }
        
        # 掃描模板檔案
        template_files = list(templates_dir.glob("*.j2"))
        
        templates = []
        for template_file in template_files:
            template_name = template_file.stem
            templates.append({
                "id": template_file.name,
                "name": template_name,
                "path": str(template_file),
                "size": template_file.stat().st_size,
                "modified": datetime.fromtimestamp(template_file.stat().st_mtime).isoformat()
            })
        
        return {
            "ok": True,
            "templates": templates,
            "count": len(templates),
            "templates_directory": str(templates_dir),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"列出模板失敗: {str(e)}")
        return {
            "ok": False,
            "reason": "list_failed",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }
