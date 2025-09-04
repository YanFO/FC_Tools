"""
報告 API 路由器
處理 PDF 報告的列表和下載功能
"""
import logging
import os
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reports", tags=["reports"])


# 回應模型定義
class ReportInfo(BaseModel):
    """報告資訊模型"""
    name: str
    path: str
    size: int
    generated_at: str
    render_mode: str
    watermark: str


class ReportListResponse(BaseModel):
    """報告列表回應模型"""
    ok: bool
    data: List[ReportInfo]
    count: int
    reason: str = None
    timestamp: str


def get_reports_directory() -> Path:
    """取得報告目錄路徑"""
    from app.settings import settings
    reports_dir = Path(settings.output_dir) / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    return reports_dir


def is_safe_path(file_path: str) -> bool:
    """檢查路徑是否安全（防目錄穿越攻擊）"""
    try:
        # 解析路徑
        requested_path = Path(file_path).resolve()
        reports_dir = get_reports_directory().resolve()
        
        # 檢查是否在允許的目錄內
        return str(requested_path).startswith(str(reports_dir))
    except Exception:
        return False


def get_file_info(file_path: Path) -> Dict[str, Any]:
    """取得檔案資訊"""
    try:
        stat = file_path.stat()
        return {
            "name": file_path.name,
            "path": str(file_path.relative_to(Path.cwd())),
            "size": stat.st_size,
            "generated_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "render_mode": "unknown",  # 可從檔案 metadata 或檔名推斷
            "watermark": "Lens Qunat"  # 固定浮水印
        }
    except Exception as e:
        logger.error(f"取得檔案資訊失敗: {file_path}, 錯誤: {str(e)}")
        return None


@router.get("/list", response_model=ReportListResponse)
async def list_reports(limit: int = Query(20, description="報告數量限制")) -> ReportListResponse:
    """
    列出最近的報告檔案
    
    回傳報告清單，包含檔案名稱、路徑、大小、生成時間等資訊
    """
    logger.info(f"列出報告，限制: {limit}")
    
    try:
        reports_dir = get_reports_directory()
        
        # 取得所有 PDF 檔案（包含子目錄）
        pdf_files = list(reports_dir.glob("**/*.pdf"))

        # 按修改時間排序（最新的在前）
        pdf_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        
        # 限制數量
        pdf_files = pdf_files[:limit]
        
        # 建立報告資訊列表
        reports = []
        for pdf_file in pdf_files:
            file_info = get_file_info(pdf_file)
            if file_info:
                # 嘗試從檔名推斷 render_mode
                if ".overlay." in pdf_file.name or "_overlay_" in pdf_file.name:
                    file_info["render_mode"] = "overlay"
                elif ".acroform." in pdf_file.name or "_acroform_" in pdf_file.name:
                    file_info["render_mode"] = "acroform"
                else:
                    file_info["render_mode"] = "auto"
                
                reports.append(ReportInfo(**file_info))
        
        return ReportListResponse(
            ok=True,
            data=reports,
            count=len(reports),
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"列出報告失敗: {str(e)}")
        return ReportListResponse(
            ok=False,
            data=[],
            count=0,
            reason="list_failed",
            timestamp=datetime.now().isoformat()
        )


@router.get("/download")
async def download_report(path: str = Query(..., description="報告檔案相對路徑")):
    """
    下載指定的報告檔案
    
    僅允許下載 outputs/reports/ 目錄內的檔案，包含路徑安全檢查
    """
    logger.info(f"下載報告: {path}")
    
    try:
        # 安全檢查
        if not is_safe_path(path):
            logger.warning(f"不安全的檔案路徑: {path}")
            raise HTTPException(
                status_code=400,
                detail="不允許的檔案路徑，僅可下載 outputs/reports/ 目錄內的檔案"
            )
        
        # 檢查檔案是否存在
        file_path = Path(path)
        if not file_path.exists():
            logger.warning(f"檔案不存在: {path}")
            raise HTTPException(
                status_code=404,
                detail="檔案不存在"
            )
        
        # 檢查是否為 PDF 檔案
        if file_path.suffix.lower() != '.pdf':
            logger.warning(f"不支援的檔案類型: {path}")
            raise HTTPException(
                status_code=400,
                detail="僅支援 PDF 檔案下載"
            )
        
        # 回傳檔案
        return FileResponse(
            path=str(file_path),
            filename=file_path.name,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={file_path.name}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下載報告失敗: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="下載失敗"
        )


@router.get("/status")
async def get_reports_status() -> Dict[str, Any]:
    """取得報告模組狀態"""
    try:
        reports_dir = get_reports_directory()
        pdf_files = list(reports_dir.glob("*.pdf"))
        
        total_size = sum(f.stat().st_size for f in pdf_files)
        
        return {
            "ok": True,
            "reports_directory": str(reports_dir),
            "total_reports": len(pdf_files),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "directory_exists": reports_dir.exists(),
            "directory_writable": os.access(reports_dir, os.W_OK),
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
