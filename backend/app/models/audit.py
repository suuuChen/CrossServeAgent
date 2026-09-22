"""
审计日志ORM模型
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Index
from sqlalchemy.sql import func
from app.database import Base


class AuditLog(Base):
    """全量审计日志表（记录所有客服交互和系统操作）"""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), index=True, nullable=True)
    user_query = Column(Text, nullable=True)
    response = Column(Text, nullable=True)
    intent = Column(String(32), nullable=True)
    language = Column(String(8), nullable=True)
    confidence = Column(Float, nullable=True)
    should_transfer = Column(Integer, default=0)
    transfer_reason = Column(String(256), nullable=True)
    compliance_blocked = Column(Integer, default=0)
    compliance_reason = Column(String(256), nullable=True)
    event_type = Column(String(32), index=True, nullable=False)
    user_ip = Column(String(64), nullable=True)
    processing_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_audit_session", "session_id"),
        Index("idx_audit_event", "event_type"),
        Index("idx_audit_created", "created_at"),
    )