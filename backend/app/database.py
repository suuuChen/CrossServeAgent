"""
数据库连接模块
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings


# 异步数据库引擎（连接池）
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,        # 调试时打印SQL
    pool_size=10,               # 连接池大小
    max_overflow=20,            # 峰值额外连接数
    pool_pre_ping=True          # 自动检测断连
)

# 异步会话工厂
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# ORM模型基类
Base = declarative_base()


async def get_db():
    """获取数据库会话（FastAPI依赖注入）"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()