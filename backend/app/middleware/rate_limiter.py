from typing import Dict, Tuple
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.utils.redis_client import RedisRateLimiter


class RateLimiter(RedisRateLimiter):
    """基于 Redis 有序集合的滑动窗口限流"""
    pass


rate_limiter = RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limiter: RateLimiter = None):
        super().__init__(app)
        self.limiter = limiter or rate_limiter

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if path.startswith("/docs") or path.startswith("/redoc") or path.startswith("/openapi"):
            return await call_next(request)
        if path in ("/health", "/", "/static") or path.startswith("/static/") or path == "/workspace":
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"

        allowed, retry_after = self.limiter.is_allowed(client_ip, path)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "error": {
                        "error_code": "RATE_LIMITED",
                        "message": "请求过于频繁，请稍后重试",
                        "retry_after_seconds": retry_after,
                        "path": path
                    }
                },
                headers={"Retry-After": str(retry_after)}
            )

        response = await call_next(request)
        return response