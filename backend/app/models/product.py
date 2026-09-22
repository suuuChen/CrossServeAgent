"""
商品数据模型（支持PGVector向量存储）
"""

from sqlalchemy import Column, Integer, String, Text, Numeric, DateTime
from pgvector.sqlalchemy import Vector
from sqlalchemy.sql import func
from app.database import Base
from app.config import settings


class Product(Base):
    """商品ORM模型（对应products表）"""

    __tablename__ = "products"

    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 基础信息
    sku = Column(String(50), unique=True, nullable=False, index=True)  # 商品编码（唯一）
    name = Column(String(255), nullable=False)  # 商品名称
    description = Column(Text)  # 详细描述
    category = Column(String(100))  # 分类
    price = Column(Numeric(10, 2))  # 价格
    stock = Column(Integer, default=0)  # 库存

    # 多语言/多平台
    language = Column(String(10), default='zh')  # 语言: zh/en/es/fr/de
    platform = Column(String(50))  # 平台: amazon/shopify等

    # PGVector向量字段（核心：用于RAG语义搜索）
    embedding = Column(Vector(settings.vector_dimension))  # 1536维向量

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        """转换为字典（用于JSON序列化）"""
        return {
            "id": self.id,
            "sku": self.sku,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "price": float(self.price) if self.price else None,
            "stock": self.stock,
            "language": self.language,
            "platform": self.platform,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }