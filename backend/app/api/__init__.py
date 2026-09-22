"""
API路由与数据模型模块

导出：
    api_router: FastAPI路由器实例（包含所有RESTful接口）
"""

from app.api.routes import api_router

__all__ = ["api_router"]