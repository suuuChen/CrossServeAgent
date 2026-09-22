"""
订单与物流数据模型
"""

from sqlalchemy import Column, Integer, String, Text, Numeric, DateTime, Date, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Order(Base):
    """订单ORM模型（对应orders表）"""

    __tablename__ = "orders"

    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 订单信息
    order_no = Column(String(50), unique=True, nullable=False, index=True)  # 订单号（唯一）
    customer_name = Column(String(100))  # 客户姓名
    customer_email = Column(String(100))  # 客户邮箱
    status = Column(String(20), default='pending')  # 状态: pending/shipped/delivered/cancelled
    total_amount = Column(Numeric(10, 2))  # 总金额
    currency = Column(String(10), default='USD')  # 货币单位
    language = Column(String(10), default='zh')  # 语言

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关联关系：订单 → 订单项（一对多）
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

    def to_dict(self):
        """转换为字典（包含订单项列表）"""
        return {
            "id": self.id,
            "order_no": self.order_no,
            "customer_name": self.customer_name,
            "customer_email": self.customer_email,
            "status": self.status,
            "total_amount": float(self.total_amount) if self.total_amount else None,
            "currency": self.currency,
            "language": self.language,
            "items": [item.to_dict() for item in self.items],  # 嵌套订单项
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class OrderItem(Base):
    """订单项ORM模型（对应order_items表）"""

    __tablename__ = "order_items"

    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 外键关联订单
    order_id = Column(Integer, ForeignKey('orders.id'))  # 所属订单ID

    # 商品信息（冗余存储，避免频繁JOIN）
    product_sku = Column(String(50))  # 商品编码
    product_name = Column(String(255))  # 商品名称
    quantity = Column(Integer)  # 数量
    unit_price = Column(Numeric(10, 2))  # 单价

    # 关联关系：订单项 → 订单（多对一）
    order = relationship("Order", back_populates="items")

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "product_sku": self.product_sku,
            "product_name": self.product_name,
            "quantity": self.quantity,
            "unit_price": float(self.unit_price) if self.unit_price else None
        }


class Shipment(Base):
    """物流信息ORM模型（对应shipments表）"""

    __tablename__ = "shipments"

    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 外键关联订单号
    order_id = Column(String(50), ForeignKey('orders.order_no'))  # 对应订单号

    # 物流信息
    tracking_number = Column(String(100))  # 运单号
    carrier = Column(String(50))  # 快递公司: SF/YT/ZTO等
    status = Column(String(20))  # 物流状态: in_transit/delivered/exception
    estimated_delivery = Column(Date)  # 预计到达日期
    actual_delivery = Column(Date)  # 实际到达日期

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "order_id": self.order_id,
            "tracking_number": self.tracking_number,
            "carrier": self.carrier,
            "status": self.status,
            "estimated_delivery": self.estimated_delivery.isoformat() if self.estimated_delivery else None,
            "actual_delivery": self.actual_delivery.isoformat() if self.actual_delivery else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }