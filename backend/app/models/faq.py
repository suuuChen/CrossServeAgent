"""
FAQ知识库数据模型（支持PGVector向量存储）
"""

from sqlalchemy import Column, Integer, String, Text, DateTime
from pgvector.sqlalchemy import Vector
from sqlalchemy.sql import func
from app.database import Base
from app.config import settings


class FAQKnowledge(Base):
    """FAQ知识库ORM模型（对应faq_knowledge表）"""

    __tablename__ = "faq_knowledge"

    id = Column(Integer, primary_key=True, autoincrement=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    category = Column(String(100))
    language = Column(String(10), default='zh')
    embedding = Column(Vector(settings.vector_dimension))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def to_dict(self):
        """转换为字典（用于JSON序列化）"""
        return {
            "id": self.id,
            "question": self.question,
            "answer": self.answer,
            "category": self.category,
            "language": self.language,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }