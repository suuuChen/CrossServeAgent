"""
数据库ORM模型模块

导出：
    Product: 商品数据模型（支持PGVector向量存储）
    Order: 订单数据模型（含订单项关联）
    OrderItem: 订单项数据模型
    Shipment: 物流信息数据模型
    FAQKnowledge: FAQ知识库数据模型（支持PGVector向量存储）
"""

from app.models.product import Product
from app.models.order import Order, OrderItem, Shipment
from app.models.faq import FAQKnowledge
from app.models.audit import AuditLog

__all__ = ["Product", "Order", "OrderItem", "Shipment", "FAQKnowledge", "AuditLog"]