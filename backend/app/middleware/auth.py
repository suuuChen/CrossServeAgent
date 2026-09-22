import os
from typing import Optional
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


API_KEYS = {
    "test-key-001": {"role": "admin", "name": "Test Admin"},
    "test-key-002": {"role": "operator", "name": "Test Operator"},
}

DEFAULT_API_KEY = os.environ.get("API_KEY", "test-key-001")


security_scheme = HTTPBearer(auto_error=False)


def verify_api_key(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)) -> dict:
    """验证API Key（生产环境使用，开发环境放宽）"""
    if credentials is None:
        return {"role": "anonymous", "name": "Anonymous", "authenticated": False}

    token = credentials.credentials
    if token in API_KEYS:
        info = API_KEYS[token]
        return {**info, "authenticated": True, "api_key": token}

    raise HTTPException(status_code=401, detail="Invalid API Key")


def require_role(*roles: str):
    """角色权限检查依赖"""
    async def _check(user: dict = Depends(verify_api_key)) -> dict:
        if not user.get("authenticated"):
            raise HTTPException(status_code=401, detail="Authentication required")
        if user.get("role") not in roles and user.get("role") != "admin":
            raise HTTPException(status_code=403, detail=f"Insufficient permissions. Required: {roles}")
        return user
    return _check