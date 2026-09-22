"""
批量生成模拟订单数据
用于端到端演练：100商品/1000订单
用法: python scripts/generate_orders.py --count 1000
"""
import asyncio
import random
import argparse
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import sys
sys.path.insert(0, '.')

from app.config import settings
from app.database import Base, engine, AsyncSessionLocal
from app.models.product import Product
from app.models.order import Order, OrderItem, Shipment


CUSTOMER_NAMES = [
    "张三", "李四", "王五", "赵六", "陈七", "周八", "吴九", "郑十",
    "Tom Smith", "Alice Johnson", "Bob Wilson", "Emma Brown", "James Davis",
    "María García", "José López", "Ana Martínez",
    "Pierre Dubois", "Marie Bernard", "Luc Martin",
    "Hans Müller", "Anna Schmidt", "Klaus Fischer",
    "Ahmed Hassan", "Fatima Ali", "Omar Said",
    "John Doe", "Jane Smith", "Michael Chen", "Sarah Kim"
]

STATUSES = ["pending", "paid", "processing", "shipped", "in_transit", "delivered", "completed", "cancelled"]
STATUS_WEIGHTS = [5, 10, 15, 20, 25, 15, 8, 2]

CARRIERS = [
    ("SF", "顺丰速运"), ("YT", "圆通快递"), ("ZT", "中通快递"),
    ("JD", "京东物流"), ("EMS", "EMS国际"), ("DHL", "DHL国际"),
    ("FedEx", "FedEx"), ("UPS", "UPS")
]


def generate_order_no(idx: int) -> str:
    date_str = datetime.now().strftime("%Y%m%d")
    return f"ORD-{date_str}-{idx:05d}"


def generate_email(name: str, idx: int) -> str:
    domain = ["gmail.com", "yahoo.com", "outlook.com", "qq.com", "163.com", "hotmail.com"]
    clean_name = name.lower().replace(" ", ".").replace("é", "e").replace("ü", "u")
    return f"{clean_name}{idx}@{random.choice(domain)}"


async def get_products():
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        result = await session.execute(select(Product))
        return list(result.scalars().all())


async def generate_orders(count: int = 1000):
    products = await get_products()

    if not products:
        print("❌ 没有找到商品数据，请先运行 init_test_data.py")
        return

    print(f"\n📦 开始生成 {count} 个订单 (使用 {len(products)} 个商品)...")

    created = 0
    batch_size = 100

    for batch_start in range(0, count, batch_size):
        batch_end = min(batch_start + batch_size, count)

        async with AsyncSessionLocal() as session:
            for i in range(batch_start, batch_end):
                try:
                    status = random.choices(STATUSES, weights=STATUS_WEIGHTS, k=1)[0]
                    customer = random.choice(CUSTOMER_NAMES)

                    num_items = random.randint(1, 5)
                    selected_products = random.sample(products, min(num_items, len(products)))

                    items = []
                    total_amount = 0
                    for p in selected_products:
                        qty = random.randint(1, 3)
                        price = float(p.price) if p.price else round(random.uniform(9.9, 999.9), 2)
                        items.append({
                            "sku": p.sku,
                            "name": p.name,
                            "qty": qty,
                            "price": price
                        })
                        total_amount += price * qty

                    order_no = generate_order_no(i + 1)
                    order = Order(
                        order_no=order_no,
                        customer_name=customer,
                        customer_email=generate_email(customer, i + 1),
                        status=status,
                        total_amount=round(total_amount, 2),
                        created_at=datetime.now() - timedelta(days=random.randint(0, 30))
                    )
                    session.add(order)
                    await session.flush()

                    for item in items:
                        order_item = OrderItem(
                            order_id=order.id,
                            product_sku=item["sku"],
                            product_name=item["name"],
                            quantity=item["qty"],
                            unit_price=item["price"]
                        )
                        session.add(order_item)

                    if status in ("shipped", "in_transit", "delivered", "completed"):
                        carrier_code, carrier_name = random.choice(CARRIERS)
                        tracking = f"{carrier_code}{random.randint(1000000000, 9999999999)}"
                        estimated = datetime.now() + timedelta(days=random.randint(1, 14))
                        shipment = Shipment(
                            order_id=order_no,
                            tracking_number=tracking,
                            carrier=carrier_name,
                            status=status if status != "completed" else "delivered",
                            estimated_delivery=estimated.date()
                        )
                        session.add(shipment)

                    created += 1

                except Exception as e:
                    print(f"  ⚠️ 订单 {i+1} 生成失败: {e}")
                    continue

            await session.commit()

        print(f"  ✅ 批次完成: {batch_end}/{count}")

    print(f"\n✨ 成功生成 {created} 个订单！")
    print(f"\n📊 数据概览:")
    print(f"   订单总数: {created}")
    print(f"   商品复用: {len(products)} 个")
    print(f"   状态分布: {dict(zip(STATUSES, STATUS_WEIGHTS))}")
    print(f"\n🎯 现在可以使用这些订单测试:")
    print(f"   - POST /api/v1/chat (询单场景)")
    print(f"   - GET /api/v1/orders/{{order_no}} (订单查询)")


def main():
    parser = argparse.ArgumentParser(description="批量生成模拟订单")
    parser.add_argument("--count", "-n", type=int, default=1000, help="订单数量 (默认: 1000)")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"🚀 数据准备: 生成 {args.count} 个模拟订单")
    print(f"{'='*60}")

    asyncio.run(generate_orders(args.count))


if __name__ == "__main__":
    main()