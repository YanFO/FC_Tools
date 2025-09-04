"""
Agent-Only LangGraph Service
主要 FastAPI 應用程式入口點
"""
import logging
import hashlib
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from app.settings import settings


# 設定結構化日誌
def setup_logging():
    """設定應用程式日誌"""
    log_format = {
        "timestamp": "%(asctime)s",
        "level": "%(levelname)s",
        "module": "%(name)s",
        "message": "%(message)s"
    }
    
    if settings.log_format == "json":
        logging.basicConfig(
            level=getattr(logging, settings.log_level.upper()),
            format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "module": "%(name)s", "message": "%(message)s"}',
            handlers=[
                logging.FileHandler(settings.log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
    else:
        logging.basicConfig(
            level=getattr(logging, settings.log_level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(settings.log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )


def _mask_token(token: str | None) -> str:
    """遮蔽敏感 token，顯示 hash 前 8 碼"""
    if not token:
        return "None"
    h = hashlib.sha256(token.encode()).hexdigest()[:8]
    return f"<set:{h}>"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用程式生命週期管理"""
    # 啟動時
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info(f"啟動 {settings.app_name} - 環境: {settings.app_env}")
    logger.info(f"API 狀態: {settings.api_status}")

    # 輸出設定摘要（遮蔽機密）
    config_summary = {
        "execute_tools": settings.execute_tools,
        "colloquial_enabled": settings.colloquial_enabled,
        "max_tool_loops": settings.max_tool_loops,
        "llm_report_enhancement": settings.llm_report_enhancement,
        "llm_provider": settings.llm_provider,
        "openai_api_key": _mask_token(settings.openai_api_key),
        "azure_openai_api_key": _mask_token(settings.azure_openai_api_key),
        "azure_openai_endpoint": settings.azure_openai_endpoint,
        "fmp_api_key": _mask_token(settings.fmp_api_key),
        "output_dir": settings.output_dir,
        "templates_dir": settings.templates_dir,
        "pdf_css_path": settings.pdf_css_path,
        "fonts_dir": settings.fonts_dir,
        "rag_index_dir": settings.rag_index_dir,
    }
    logger.info(f"設定摘要: {config_summary}")

    yield

    # 關閉時
    logger.info(f"關閉 {settings.app_name}")


# 建立 FastAPI 應用程式
app = FastAPI(
    title=settings.app_name,
    description="Agent-Only LangGraph Service - 支援文字、檔案、LINE 聊天與規則查詢的智能代理服務",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 中介軟體
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """請求日誌中介軟體"""
    start_time = datetime.now()
    
    # 生成 trace ID
    trace_id = f"{start_time.strftime('%Y%m%d%H%M%S')}-{hash(str(request.url)) % 10000:04d}"
    request.state.trace_id = trace_id
    
    logger = logging.getLogger(__name__)
    logger.info(f"[{trace_id}] {request.method} {request.url}")
    
    response = await call_next(request)
    
    process_time = (datetime.now() - start_time).total_seconds()
    logger.info(f"[{trace_id}] 完成 - 狀態: {response.status_code}, 耗時: {process_time:.3f}s")
    
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全域例外處理器"""
    logger = logging.getLogger(__name__)
    trace_id = getattr(request.state, 'trace_id', 'unknown')
    
    logger.error(f"[{trace_id}] 未處理的例外: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "ok": False,
            "error": "內部伺服器錯誤",
            "trace_id": trace_id,
            "timestamp": datetime.now().isoformat()
        }
    )


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    健康檢查端點
    回傳應用程式狀態與 API 金鑰可用性
    """
    return {
        "ok": True,
        "service": settings.app_name,
        "version": "1.0.0",
        "environment": settings.app_env,
        "timestamp": datetime.now().isoformat(),
        "api_status": settings.api_status
    }


@app.get("/")
async def root():
    """根端點"""
    return {
        "message": f"歡迎使用 {settings.app_name}",
        "docs": "/docs",
        "health": "/health",
        "agent": "/api/agent/run"
    }


# 註冊路由器
from app.routers import agent, line, session, reports, report
app.include_router(agent.router)
app.include_router(line.router)
app.include_router(session.router)
app.include_router(reports.router)
app.include_router(report.router)


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.app_env == "dev",
        log_level=settings.log_level.lower()
    )
