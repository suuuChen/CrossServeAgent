import logging
import traceback
from datetime import datetime
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:
            if hasattr(exc, "status_code"):
                raise exc

            logger.error(f"Unhandled error on {request.method} {request.url.path}: {exc}")
            logger.debug(traceback.format_exc())

            error_response = self._build_response(exc, request)
            return JSONResponse(
                status_code=500,
                content=error_response
            )

    @staticmethod
    def _build_response(exc: Exception, request: Request) -> dict:
        return {
            "success": False,
            "error_code": "INTERNAL_SERVER_ERROR",
            "error_message": "系统内部错误，请稍后重试",
            "details": str(exc)[:500],
            "path": request.url.path,
            "method": request.method,
            "timestamp": datetime.now().isoformat(),
            "degraded_mode": True,
            "fallback": "请刷新页面或联系管理员"
        }