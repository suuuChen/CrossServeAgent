"""
初始化测试数据脚本
导入50个SKU商品数据和模拟订单数据
"""

import asyncio
import json
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add parent directory to path for imports
import sys
import os
sys.path.insert(0, '.')

# 获取脚本所在目录的绝对路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

from app.config import settings
from app.database import Base, engine, AsyncSessionLocal
from app.models.product import Product
from app.models.order import Order, OrderItem, Shipment


async def init_database():
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database tables created successfully")


async def import_products():
    """Import 50 sample products from JSON file"""
    
    # Load product data
    test_data_path = os.path.join(SCRIPT_DIR, 'test_data', 'sample_products.json')
    with open(test_data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    products = data['products']
    print(f"📦 Loading {len(products)} products...")
    
    async with AsyncSessionLocal() as session:
        imported_count = 0
        
        for prod in products:
            try:
                product = Product(
                    sku=prod['sku'],
                    name=prod['name'],
                    description=prod['description'],
                    category=prod['category'],
                    price=prod['price'],
                    stock=prod['stock'],
                    language=prod.get('language', 'zh'),
                    platform=prod.get('platform')
                )
                session.add(product)
                imported_count += 1
                
            except Exception as e:
                print(f"❌ Error importing product {prod.get('sku')}: {e}")
        
        await session.commit()
        print(f"✅ Successfully imported {imported_count} products")


async def create_sample_orders():
    """Create sample orders for testing order query functionality"""
    
    sample_orders = [
        {
            "order_no": "ORD-20240101-001",
            "customer_name": "张三",
            "customer_email": "zhangsan@example.com",
            "status": "delivered",
            "total_amount": 458.00,
            "items": [
                {"product_sku": "SHOE-001", "product_name": "云感轻便跑鞋", "quantity": 1, "unit_price": 299.00},
                {"product_sku": "CLOT-001", "product_name": "纯棉基础款T恤(白色)", "quantity": 2, "unit_price": 79.50}
            ],
            "shipment": {
                "tracking_number": "SF1234567890",
                "carrier": "顺丰速运",
                "status": "delivered"
            }
        },
        {
            "order_no": "ORD-20240102-002",
            "customer_name": "李四",
            "customer_email": "lisi@example.com",
            "status": "shipped",
            "total_amount": 1698.00,
            "items": [
                {"product_sku": "ELEC-002", "product_name": "智能手表S8", "quantity": 1, "unit_price": 1299.00},
                {"product_sku": "ELEC-003", "product_name": "便携式充电宝20000mAh", "quantity": 3, "unit_price": 133.00}
            ],
            "shipment": {
                "tracking_number": "YT9876543210",
                "carrier": "圆通快递",
                "status": "in_transit",
                "estimated_delivery": (datetime.now() + timedelta(days=3)).date()
            }
        },
        {
            "order_no": "ORD-20240103-003",
            "customer_name": "王五",
            "customer_email": "wangwu@example.com",
            "status": "pending",
            "total_amount": 237.00,
            "items": [
                {"product_sku": "BEAU-001", "product_name": "玻尿酸保湿精华液", "quantity": 1, "unit_price": 168.00},
                {"product_sku": "BEAU-002", "product_name": "防晒霜SPF50+ PA+++", "quantity": 1, "unit_price": 69.00}
            ]
        }
    ]
    
    print(f"📋 Creating {len(sample_orders)} sample orders...")
    
    async with AsyncSessionLocal() as session:
        created_count = 0
        
        for order_data in sample_orders:
            try:
                # Create order
                order = Order(
                    order_no=order_data['order_no'],
                    customer_name=order_data['customer_name'],
                    customer_email=order_data['customer_email'],
                    status=order_data['status'],
                    total_amount=order_data['total_amount']
                )
                session.add(order)
                await session.flush()  # Get order ID
                
                # Create order items
                for item in order_data['items']:
                    order_item = OrderItem(
                        order_id=order.id,
                        product_sku=item['product_sku'],
                        product_name=item['product_name'],
                        quantity=item['quantity'],
                        unit_price=item['unit_price']
                    )
                    session.add(order_item)
                
                # Create shipment if exists
                if 'shipment' in order_data:
                    shipment_data = order_data['shipment']
                    shipment = Shipment(
                        order_id=order_data['order_no'],
                        tracking_number=shipment_data.get('tracking_number'),
                        carrier=shipment_data.get('carrier'),
                        status=shipment_data.get('status'),
                        estimated_delivery=shipment_data.get('estimated_delivery')
                    )
                    session.add(shipment)
                
                created_count += 1
                
            except Exception as e:
                print(f"❌ Error creating order {order_data.get('order_no')}: {e}")
        
        await session.commit()
        print(f"✅ Successfully created {created_count} sample orders")


async def create_faq_knowledge():
    """Create FAQ knowledge base entries"""
    
    faqs = [
        {
            "question": "如何查看我的订单状态？",
            "answer": "您可以通过以下方式查看订单状态：1) 登录账户进入\"我的订单\"页面；2) 提供订单号给客服查询；3) 查看订单确认邮件中的物流链接。订单状态包括：待付款、待发货、运输中、已送达、已完成。",
            "category": "订单相关",
            "language": "zh"
        },
        {
            "question": "退货政策是什么？",
            "answer": "我们提供7天无理由退换货服务。商品需保持原包装未拆封、未使用。质量问题可延长至30天退换。退货流程：申请退货→客服审核→寄回商品→退款处理（3-5个工作日到账）。运费由我们承担（质量问题）或买家承担（非质量问题）。",
            "category": "售后政策",
            "language": "zh"
        },
        {
            "question": "配送需要多长时间？",
            "answer": "标准配送时间：国内3-5个工作日，国际10-20个工作日。加急快递：国内1-2天，国际5-7天（需额外付费）。偏远地区可能延迟1-2天。您可以在订单详情页查看预计送达时间和实时物流信息。",
            "category": "物流配送",
            "language": "zh"
        },
        {
            "question": "支持哪些支付方式？",
            "answer": "我们支持多种支付方式：1) 支付宝/微信支付（推荐）；2) 银联卡/信用卡；3) PayPal（国际订单）；4) 货到付款（部分地区）。大额订单建议使用信用卡以获得银行提供的消费保障。",
            "category": "支付方式",
            "language": "zh"
        },
        {
            "question": "如何联系客服？",
            "answer": "您可以通过以下方式联系我们：1) 在线客服（9:00-22:00，即时回复）；2) 客服热线400-XXX-XXXX（工作日9:00-18:00）；3) 邮件support@example.com（24小时内回复）；4) 在线提交工单系统。紧急问题建议优先使用在线客服或电话。",
            "category": "联系方式",
            "language": "zh"
        },
        {
            "question": "商品有质量保证吗？",
            "answer": "所有商品均提供正品保证和品质承诺。我们与品牌官方合作，确保100%正品。电子产品享受1年质保，服装鞋帽3个月质保。如收到假冒伪劣商品，我们承诺假一赔三并承担所有运费。",
            "category": "品质保证",
            "language": "zh"
        },
        {
            "question": "可以修改已下单的订单吗？",
            "answer": "订单状态为\"待发货\"时可以修改：1) 修改收货地址（在订单详情页操作）；2) 增减商品数量（联系客服协助）；3) 取消订单（全额退款）。一旦订单进入\"待收货\"或之后的状态，将无法修改，只能走退换货流程。",
            "category": "订单修改",
            "language": "zh"
        },
        {
            "question": "尺码怎么选择？",
            "answer": "每个商品详情页都有详细的尺码对照表。建议您：1) 测量身高体重参照推荐尺码；2) 查看其他买家的尺码评价；3) 不确定时选择大一码（特别是鞋子）；4) 联系客服获取个性化推荐。如收到后尺码不合适，支持免费换货一次。",
            "category": "购物指南",
            "language": "zh"
        },
        {
            "question": "How can I check my order status?",
            "answer": "You can check your order status in the following ways: 1) Log in and go to 'My Orders'; 2) Provide your order number to our customer service; 3) Click the tracking link in your order confirmation email. Order statuses include: pending payment, pending shipment, in transit, delivered, completed.",
            "category": "order",
            "language": "en"
        },
        {
            "question": "What is the return policy?",
            "answer": "We offer a 7-day no-reason return policy. Items must be unused and in original packaging. Quality issues can be returned within 30 days. Return process: Request return → CS approval → Ship item → Refund (3-5 business days). Shipping is free for quality issues; otherwise buyer pays.",
            "category": "returns",
            "language": "en"
        },
        {
            "question": "How long does delivery take?",
            "answer": "Standard shipping: domestic 3-5 business days, international 10-20 business days. Express: domestic 1-2 days, international 5-7 days (extra fee). Remote areas may take 1-2 extra days. Track real-time status on your order detail page.",
            "category": "shipping",
            "language": "en"
        },
        {
            "question": "What payment methods do you accept?",
            "answer": "We accept: 1) Credit/debit cards (Visa/Mastercard/Amex); 2) PayPal (international orders); 3) Apple Pay / Google Pay; 4) Bank transfer (large orders). We recommend credit cards for purchase protection.",
            "category": "payment",
            "language": "en"
        },
        {
            "question": "Cómo puedo verificar el estado de mi pedido?",
            "answer": "Puede verificar su pedido: 1) Inicie sesión y vaya a 'Mis Pedidos'; 2) Proporcione el número de pedido a nuestro servicio al cliente; 3) Use el enlace de seguimiento en su email de confirmación. Estados: pendiente pago, pendiente envío, en tránsito, entregado, completado.",
            "category": "pedido",
            "language": "es"
        },
        {
            "question": "Cuál es la política de devolución?",
            "answer": "Ofrecemos devolución sin motivo de 7 días. Los artículos deben estar sin usar y en su embalaje original. Problemas de calidad: 30 días de devolución gratuita. Proceso: Solicitar devolución → Aprobación → Enviar → Reembolso (3-5 días hábiles). Envío gratis para problemas de calidad.",
            "category": "devoluciones",
            "language": "es"
        },
        {
            "question": "Combien de temps prend la livraison?",
            "answer": "Livraison standard: 3-5 jours ouvrés (domestique), 10-20 jours (international). Express: 1-2 jours, 5-7 jours (international, frais supplémentaires). Suivez en temps réel dans les détails de votre commande.",
            "category": "livraison",
            "language": "fr"
        },
        {
            "question": "Quels modes de paiement acceptez-vous?",
            "answer": "Nous acceptons: 1) Cartes bancaires (Visa/Mastercard); 2) PayPal; 3) Apple Pay; 4) Virement bancaire. Nous recommandons les cartes bancaires pour leur protection achat.",
            "category": "paiement",
            "language": "fr"
        },
        {
            "question": "Wie lange dauert die Lieferung?",
            "answer": "Standardversand: 3-5 Werktage (national), 10-20 Tage (international). Express: 1-2 Werktage, 5-7 Tage (international, Aufpreis). Echtzeit-Tracking in Ihrer Bestellübersicht.",
            "category": "versand",
            "language": "de"
        },
        {
            "question": "Was ist die Rückgaberichtlinie?",
            "answer": "7 Tage kostenlose Rückgabe ohne Angabe von Gründen. Artikel müssen unbenutzt in Originalverpackung sein. Qualitätsmängel: 30 Tage kostenlose Rückgabe. Prozess: Rückgabe beantragen → Freigabe → Versand → Rückerstattung (3-5 Werktage). Kostenlos bei Qualitätsmängeln.",
            "category": "rückgabe",
            "language": "de"
        }
    ]
    
    print(f"📚 Creating {len(faqs)} FAQ entries...")
    
    async with AsyncSessionLocal() as session:
        created_count = 0
        
        for faq in faqs:
            try:
                from sqlalchemy import text
                
                sql = """
                    INSERT INTO faq_knowledge (question, answer, category, language)
                    VALUES (:question, :answer, :category, :language)
                """
                
                await session.execute(text(sql), {
                    "question": faq['question'],
                    "answer": faq['answer'],
                    "category": faq['category'],
                    "language": faq['language']
                })
                
                created_count += 1
                
            except Exception as e:
                print(f"❌ Error creating FAQ: {e}")
        
        await session.commit()
        print(f"✅ Successfully created {created_count} FAQ entries")


async def main():
    """Main function to initialize all test data"""
    print("\n" + "="*60)
    print("🚀 Initializing Test Data for Week 1 Development")
    print("="*60 + "\n")
    
    try:
        # Step 1: Initialize database tables
        await init_database()
        
        # Step 2: Import products
        await import_products()
        
        # Step 3: Create sample orders
        await create_sample_orders()
        
        # Step 4: Create FAQ knowledge base
        await create_faq_knowledge()
        
        print("\n" + "="*60)
        print("✨ All test data initialized successfully!")
        print("="*60 + "\n")
        
        print("📊 Summary:")
        print("   - 50 Products imported")
        print("   - 3 Sample orders created")
        print("   - 8 FAQ entries added")
        print("   - Database tables ready")
        print("\n🎯 Next steps:")
        print("   1. Start the application: docker-compose up -d")
        print("   2. Index products to vector DB: POST /api/v1/rag/index-products")
        print("   3. Test chat endpoint: POST /api/v1/chat")
        print("   4. Access API docs: http://localhost:8000/docs\n")
        
    except Exception as e:
        print(f"\n❌ Error during initialization: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())