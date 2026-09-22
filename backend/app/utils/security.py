"""
安全工具
数据加密 / IP脱敏 / 敏感信息处理
"""
import hashlib
import ipaddress
from typing import Optional


def mask_ip(ip_str: str) -> str:
    """IP地址脱敏 - 保留前两段"""
    if not ip_str:
        return "unknown"
    try:
        ip = ipaddress.ip_address(ip_str)
        if isinstance(ip, ipaddress.IPv4Address):
            parts = ip_str.split(".")
            return f"{parts[0]}.{parts[1]}.*.*"
        else:
            parts = ip_str.split(":")
            return f"{parts[0]}:{parts[1]}:*:*:*:*:*:*"
    except ValueError:
        return ip_str[:10] + "***"


def hash_sensitive(text: str, salt: str = "multilingual_agent_v1") -> str:
    """敏感信息哈希（不可逆，用于审计）"""
    if not text:
        return ""
    data = f"{salt}:{text}".encode("utf-8")
    return hashlib.sha256(data).hexdigest()[:32]


def mask_text(text: str, keep_start: int = 2, keep_end: int = 2) -> str:
    """文本脱敏 - 中间用*代替"""
    if not text or len(text) <= keep_start + keep_end:
        return text
    return text[:keep_start] + "*" * (len(text) - keep_start - keep_end) + text[-keep_end:]


def sanitize_user_query(query: str) -> str:
    """用户查询清理（去除换行、多余空格）"""
    if not query:
        return ""
    cleaned = query.replace("\n", " ").replace("\r", " ").replace("\t", " ")
    cleaned = " ".join(cleaned.split())
    return cleaned[:500]


def is_production() -> bool:
    import os
    return os.getenv("APP_ENV", "development").lower() == "production"


class RateLimitConfig:
    """限流配置 - 生产环境更严格"""
    @staticmethod
    def get_endpoint_limits() -> dict:
        if is_production():
            return {
                "/api/v1/chat": (30, 60),
                "/api/v1/listing/generate": (10, 60),
                "/api/v1/listing/batch": (5, 60),
                "/api/v1/reviews/analyze": (15, 60),
                "/api/v1/ads/generate": (15, 60),
                "/api/v1/compliance/check": (60, 60),
            }
        return {
            "/api/v1/chat": (120, 60),
            "/api/v1/listing/generate": (30, 60),
            "/api/v1/listing/batch": (15, 60),
            "/api/v1/reviews/analyze": (60, 60),
            "/api/v1/ads/generate": (60, 60),
            "/api/v1/compliance/check": (200, 60),
        }