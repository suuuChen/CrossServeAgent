import time
from collections import defaultdict
from typing import Dict, Tuple
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimiter:
    """基于滑动窗口的内存限流实现（可替换为Redis版本）"""

    def __init__(self):
        self._requests: Dict[Tuple[str, str], list] = defaultdict(list)
        self._limits: Dict[str, Tuple[int, int]] = {
            "/api/v1/chat": (30, 60),
            "/api/v1/listing/generate": (10, 60),
            "/api/v1/listing/batch": (5, 60),
            "/api/v1/reviews/analyze": (15, 60),
            "/api/v1/ads/generate": (15, 60),
            "/api/v1/compliance/check": (60, 60),
        }
        self._default_limit = (120, 60)

    def is_allowed(self, client_id: str, path: str) -> Tuple[bool, int]:
        now = time.time()
        rate, window = self._limits.get(path, self._default_limit)
        window_start = now - window

        key = (client_id, path)

        if key not in self._requests:
            self._requests[key] = []

        self._requests[key] = [
            ts for ts in self._requests[key] if ts > window_start
        ]

        if len(self._requests[key]) >= rate:
            retry_after = int(window - (now - self._requests[key][0]))
            return False, max(1, retry_after)

        self._requests[key].append(now)
        return True, 0

    def reset(self, client_id: str = None, path: str = None) -> int:
        """重置限流计数。参数都为 None 时清空全部，否则按 client_id/path 精确清空。返回清除的条目数。"""
        count = 0
        if client_id is None and path is None:
            count = len(self._requests)
            self._requests.clear()
        else:
            to_remove = [k for k in self._requests
                         if (client_id is None or k[0] == client_id)
                         and (path is None or k[1] == path)]
            for k in to_remove:
                del self._requests[k]
                count += 1
        return count

    def get_stats(self) -> Dict:
        tracked_clients = set(k[0] for k in self._requests)
        return {
            "tracked_clients": len(tracked_clients),
            "tracked_endpoints": len(self._requests),
            "configured_limits": {
                path: {"max_requests": limit, "window_seconds": window}
                for path, (limit, window) in self._limits.items()
            },
            "default_limit": {
                "max_requests": self._default_limit[0],
                "window_seconds": self._default_limit[1]
            }
        }


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