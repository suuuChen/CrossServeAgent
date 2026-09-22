"""
FastAPI应用入口
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import os

from app.config import settings
from app.api.routes import api_router
from app.middleware.rate_limiter import RateLimitMiddleware, rate_limiter
from app.middleware.exception_handler import ExceptionHandlerMiddleware
from app.utils.logger import setup_logging, get_logger
from app.utils.security import RateLimitConfig

# 项目根目录 (MultilingualAgent/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = setup_logging(
    log_dir=os.environ.get("LOG_DIR", os.path.join(PROJECT_ROOT, "backend", "logs")),
    level="INFO" if settings.debug else "WARNING",
    app_name="multilingual_agent"
)

rate_limiter._limits = RateLimitConfig.get_endpoint_limits()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.app_name} v1.0.0 (env={settings.app_env})")
    logger.info(f"Rate limiter configured: {len(rate_limiter._limits)} endpoint-specific limits")

    yield

    logger.info(f"Shutting down {settings.app_name}...")


app = FastAPI(
    title=settings.app_name,
    description="跨境电商多语言智能客服与运营Agent - 6语言客服 + Listing生成 + 评论分析 + 广告词生成",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(ExceptionHandlerMiddleware)
app.add_middleware(RateLimitMiddleware, limiter=rate_limiter)

app.include_router(api_router, prefix="/api/v1")

# 静态文件与前端服务 (React 构建产物)
# 前端在项目根目录的 frontend/dist 中
FRONTEND_DIST_DIR = os.path.join(PROJECT_ROOT, "frontend", "dist")
if os.path.isdir(FRONTEND_DIST_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIST_DIR, html=True), name="frontend")

    @app.get("/workspace")
    async def workspace():
        return FileResponse(os.path.join(FRONTEND_DIST_DIR, "index.html"))


@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "workspace": "/workspace",
        "modules": {
            "customer_service": "6-language AI chat agent",
            "listing_generator": "Amazon/Temu/TikTok Shop listing",
            "review_analyzer": "Sentiment + theme clustering",
            "ad_campaign": "PPC ad copy generator",
            "compliance": "Prohibited content filtering",
            "reporting": "Analytics dashboard & export"
        }
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": settings.app_env,
        "timestamp": __import__("time").time(),
        "services": {
            "database": "postgresql+pgvector",
            "redis": "redis://localhost:6379",
            "llm": settings.openai_model,
            "embedding": settings.embedding_model
        },
        "languages_supported": settings.supported_languages,
        "compliance_enabled": settings.compliance_enabled,
        "human_transfer_enabled": settings.human_transfer_enabled
    }


@app.get("/api/v1/monitor/metrics")
async def system_metrics():
    """系统监控指标（供运维监控使用）"""
    return {
        "service": settings.app_name,
        "version": "1.0.0",
        "uptime_metrics": {
            "rate_limiter": rate_limiter.get_stats()
        }
    }


@app.post("/api/v1/monitor/rate-limiter/reset")
async def reset_rate_limiter(client_id: str = None, path: str = None):
    """开发调试用：重置限流计数"""
    if settings.app_env != "development":
        return JSONResponse(status_code=403, content={"success": False, "error": "only available in development"})
    cleared = rate_limiter.reset(client_id=client_id, path=path)
    return {"success": True, "cleared_entries": cleared}