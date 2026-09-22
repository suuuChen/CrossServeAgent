"""
向量存储操作层（PGVector数据库交互）
"""

from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, text
from sqlalchemy.orm import selectinload
from app.models.product import Product
from app.models.order import Order
from app.rag.embedding import embedding_service
from app.config import settings


class VectorStore:
    """
    向量存储管理类
    
    功能：
    - 商品/FAQ的向量索引（写入）
    - 语义相似度搜索（读取）
    - 精确查询（SKU/订单号）
    """

    def __init__(self, db: AsyncSession):
        """
        初始化向量存储
        
        参数:
            db: SQLAlchemy异步会话
        """
        self.db = db

    async def add_product_embedding(self, product_id: int, text: str) -> bool:
        """
        添加或更新商品向量
        
        参数:
            product_id: 商品ID
            text: 待向量化的文本（通常是名称+描述）
            
        返回:
            bool: 是否成功
        """
        try:
            # 调用OpenAI API生成向量
            embedding = await embedding_service.embed_text(text)
            
            # 更新数据库中的embedding字段
            await self.db.execute(
                update(Product)
                .where(Product.id == product_id)
                .values(embedding=embedding)
            )
            await self.db.commit()
            return True
            
        except Exception as e:
            print(f"Error adding product embedding: {e}")
            await self.db.rollback()  # 回滚事务
            return False

    async def search_products(
        self,
        query: str,
        top_k: int = None,
        threshold: float = None,
        language: str = 'zh'
    ) -> List[Dict]:
        """
        商品语义搜索（RAG核心功能）
        
        功能：使用PGVector的余弦相似度算法，找到与查询最相关的商品
        
        参数:
            query: 用户查询文本（如"舒适的跑鞋"）
            top_k: 返回结果数量（默认5条）
            threshold: 相似度阈值（默认0.7，过滤低质量结果）
            language: 语言过滤（默认中文）
            
        返回:
            List[Dict]: 商品字典列表（每项包含id/sku/name/price等字段及similarity_score相似度分数）
        """
        # 使用默认值（从配置文件读取）
        if top_k is None:
            top_k = settings.rag_top_k
        if threshold is None:
            threshold = settings.rag_similarity_threshold

        try:
            # Step 1: 将用户查询转换为向量
            query_embedding = await embedding_service.embed_text(query)
            
            # Step 2: 执行PGVector相似度搜索（SQL原生查询）
            sql_query = text("""
                SELECT id, sku, name, description, category, price, stock, language, platform,
                       1 - (embedding <=> CAST(:query_vector AS vector)) as similarity
                FROM products
                WHERE language = :language
                  AND embedding IS NOT NULL
                ORDER BY embedding <=> CAST(:query_vector AS vector)
                LIMIT :limit
            """)
            
            result = await self.db.execute(sql_query, {
                "query_vector": str(query_embedding),
                "language": language,
                "limit": top_k
            })
            
            rows = result.fetchall()
            
            # Step 3: 过滤低于阈值的结果并格式化输出
            products = []
            for row in rows:
                similarity = float(row[-1])  # 最后一列是相似度分数
                
                if similarity >= threshold:  # 只保留高质量匹配
                    products.append({
                        "id": row[0],
                        "sku": row[1],
                        "name": row[2],
                        "description": row[3],
                        "category": row[4],
                        "price": float(row[5]) if row[5] else None,
                        "stock": row[6],
                        "language": row[7],
                        "platform": row[8],
                        "similarity_score": similarity  # 核心字段：相似度
                    })
            
            return products
            
        except Exception as e:
            print(f"Error searching products: {e}")
            return []  # 异常时返回空列表

    async def search_faq(
        self,
        query: str,
        top_k: int = 3,
        language: str = 'zh'
    ) -> List[Dict]:
        """
        FAQ知识库语义搜索
        
        参数:
            query: 用户问题
            top_k: 返回数量（默认3条）
            language: 语言
            
        返回:
            FAQ字典列表（包含question/answer/similarity_score）
        """
        try:
            query_embedding = await embedding_service.embed_text(query)
            
            # PGVector FAQ搜索（类似商品搜索）
            sql_query = text("""
                SELECT id, question, answer, category, language,
                       1 - (embedding <=> CAST(:query_vector AS vector)) as similarity
                FROM faq_knowledge
                WHERE language = :language
                  AND embedding IS NOT NULL
                ORDER BY embedding <=> CAST(:query_vector AS vector)
                LIMIT :limit
            """)
            
            result = await self.db.execute(sql_query, {
                "query_vector": str(query_embedding),
                "language": language,
                "limit": top_k
            })
            
            rows = result.fetchall()
            
            # 格式化FAQ结果
            faqs = []
            for row in rows:
                faqs.append({
                    "id": row[0],
                    "question": row[1],       # 问题文本
                    "answer": row[2],          # 答案文本
                    "category": row[3],        # 分类标签
                    "language": row[4],
                    "similarity_score": float(row[-1])  # 相似度
                })
            
            return faqs
            
        except Exception as e:
            print(f"Error searching FAQ: {e}")
            return []

    async def get_product_by_sku(self, sku: str) -> Optional[Dict]:
        """
        通过SKU精确查询商品
        
        参数:
            sku: 商品编码
            
        返回:
            商品字典（未找到返回None）
        """
        try:
            result = await self.db.execute(
                select(Product).where(Product.sku == sku)  # WHERE条件：SKU精确匹配
            )
            product = result.scalar_one_or_none()  # 获取单条记录（或None）
            
            if product:
                return product.to_dict()  # ORM对象→字典
            return None
            
        except Exception as e:
            print(f"Error getting product by SKU: {e}")
            return None

    async def get_order_by_no(self, order_no: str) -> Optional[Dict]:
        """
        通过订单号精确查询订单
        
        参数:
            order_no: 订单号
            
        返回:
            订单字典（包含订单项列表，未找到返回None）
        """
        try:
            result = await self.db.execute(
                select(Order)
                .options(selectinload(Order.items))
                .where(Order.order_no == order_no)
            )
            order = result.scalar_one_or_none()
            
            if order:
                return order.to_dict()
            return None
            
        except Exception as e:
            print(f"Error getting order by number: {e}")
            return None

    async def index_all_products(self) -> int:
        """
        批量索引所有未建立向量的商品（初始化用）
        
        遍历products表，为embedding为NULL的记录生成向量
        
        返回:
            int: 成功索引的商品数量
        """
        try:
            from sqlalchemy import text as sql_text
            
            result = await self.db.execute(sql_text("""
                SELECT id, name, description FROM products WHERE embedding IS NULL
            """))
            rows = result.fetchall()
            
            indexed_count = 0
            for row in rows:
                product_id, name, desc = row[0], row[1], row[2]
                text_to_embed = f"{name} {desc or ''}"
                success = await self.add_product_embedding(product_id, text_to_embed)
                if success:
                    indexed_count += 1
            
            return indexed_count
            
        except Exception as e:
            print(f"Error indexing products: {e}")
            return 0

    async def index_all_faqs(self) -> int:
        """
        批量索引所有未建立向量的FAQ条目（初始化用）
        
        返回:
            int: 成功索引的FAQ数量
        """
        try:
            from sqlalchemy import text as sql_text
            
            result = await self.db.execute(sql_text("""
                SELECT id, question, answer FROM faq_knowledge WHERE embedding IS NULL
            """))
            rows = result.fetchall()
            
            indexed_count = 0
            for row in rows:
                faq_id, question, answer = row[0], row[1], row[2]
                text_to_embed = f"{question} {answer or ''}"
                try:
                    vector = await embedding_service.embed_text(text_to_embed)
                    await self.db.execute(sql_text("""
                        UPDATE faq_knowledge SET embedding = CAST(:vector AS vector) WHERE id = :id
                    """), {"vector": str(vector), "id": faq_id})
                    await self.db.commit()
                    indexed_count += 1
                except Exception as e:
                    print(f"Error indexing FAQ {faq_id}: {e}")
                    await self.db.rollback()
            
            return indexed_count
            
        except Exception as e:
            print(f"Error indexing FAQs: {e}")
            return 0