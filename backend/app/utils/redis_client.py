"""Redis 客户端封装"""
from typing import Optional, Dict, Any
import time, json
import redis as sync_redis
from app.config import settings

_sync_client = None

def get_sync_client():
    global _sync_client
    if _sync_client is None:
        _sync_client = sync_redis.Redis.from_url(settings.redis_url, decode_responses=True)
    return _sync_client

def is_available():
    try:
        get_sync_client().ping()
        return True
    except Exception:
        return False

class RedisRateLimiter:
    def __init__(self):
        self._limits = {
            "/api/v1/chat": (30, 60),
            "/api/v1/listing/generate": (10, 60),
            "/api/v1/listing/batch": (5, 60),
            "/api/v1/reviews/analyze": (15, 60),
            "/api/v1/ads/generate": (15, 60),
            "/api/v1/compliance/check": (60, 60),
        }
        self._default_limit = (120, 60)
        self._enabled = is_available()

    def _key(self, cid, path):
        return f"ratelimit:{cid}:{path}"

    def is_allowed(self, client_id, path):
        if not self._enabled:
            return True, 0
        rate, window = self._limits.get(path, self._default_limit)
        now = time.time()
        key = self._key(client_id, path)
        try:
            c = get_sync_client()
            c.zremrangebyscore(key, 0, now - window)
            if c.zcard(key) >= rate:
                oldest = c.zrange(key, 0, 0, withscores=True)
                retry = int(window - (now - oldest[0][1])) if oldest else 1
                return False, max(1, retry)
            c.zadd(key, {str(now): now})
            c.expire(key, window + 10)
            return True, 0
        except Exception:
            return True, 0

    def reset(self, client_id=None, path=None):
        if not self._enabled:
            return 0
        count = 0
        try:
            c = get_sync_client()
            pattern = "ratelimit:*"
            keys = list(c.scan_iter(match=pattern))
            count = len(keys)
            if keys:
                c.delete(*keys)
        except Exception:
            pass
        return count

    def get_stats(self):
        return {
            "engine": "redis" if self._enabled else "memory",
            "configured_limits": {p: {"max_requests": l, "window_seconds": w} for p, (l, w) in self._limits.items()},
            "default_limit": {"max_requests": self._default_limit[0], "window_seconds": self._default_limit[1]},
        }

class SessionCache:
    @staticmethod
    def set(sid, data, ttl=1800):
        if not is_available():
            return False
        try:
            get_sync_client().setex(f"session:{sid}", ttl, json.dumps(data, default=str, ensure_ascii=False))
            return True
        except Exception:
            return False

    @staticmethod
    def get(sid):
        if not is_available():
            return None
        try:
            raw = get_sync_client().get(f"session:{sid}")
            return json.loads(raw) if raw else None
        except Exception:
            return None

class ComplianceCache:
    @staticmethod
    def check(hash_val):
        if not is_available():
            return None
        try:
            raw = get_sync_client().get(f"compliance:{hash_val}")
            return json.loads(raw) if raw else None
        except Exception:
            return None

    @staticmethod
    def cache(hash_val, result, ttl=3600):
        if not is_available():
            return False
        try:
            get_sync_client().setex(f"compliance:{hash_val}", ttl, json.dumps(result, default=str, ensure_ascii=False))
            return True
        except Exception:
            return False
