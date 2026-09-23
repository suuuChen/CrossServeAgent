"""
文本向量化服务（调用OpenAI Embedding API）
"""

from typing import List, Optional
import numpy as np
from openai import OpenAI
from app.config import settings


class EmbeddingService:
    """
    文本向量化服务类
    
    功能：将文本转换为高维向量（用于语义搜索）
    模型：text-embedding-3-large（1536维）
    """

    def __init__(self):
        """初始化OpenAI客户端"""
        if settings.use_glm and settings.glm_api_key:
            self.client = OpenAI(api_key=settings.glm_api_key, base_url=settings.glm_base_url)
            self.model = settings.glm_embedding_model
        else:
            self.client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None
            self.model = settings.embedding_model  # 向量化模型名称
        self.dimension = settings.vector_dimension  # 向量维度

    async def embed_text(self, text: str) -> List[float]:
        """
        单文本向量化
        
        参数:
            text: 待向量化的文本
            
        返回:
            1536维浮点数列表（失败时返回零向量）
        """
        if self.client is None:
            return [0.0] * self.dimension

        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text
            )
            return response.data[0].embedding  # 提取第一个结果的向量
        except Exception as e:
            print(f"Error embedding text: {e}")
            return [0.0] * self.dimension  # 异常降级：返回零向量

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        批量文本向量化（高效处理多个文本）
        
        参数:
            texts: 文本列表
            
        返回:
            向量列表（每个文本对应一个1536维向量）
        """
        if self.client is None:
            return [[0.0] * self.dimension for _ in texts]

        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=texts
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            print(f"Error embedding texts: {e}")
            return [[0.0] * self.dimension for _ in texts]  # 异常降级

    async def embed_product(self, product_data: dict) -> List[float]:
        """
        商品向量化（合并名称+描述）
        
        参数:
            product_data: 商品字典（需包含name和description字段）
            
        返回:
            商品的1536维向量表示
        """
        text_to_embed = f"{product_data.get('name', '')} {product_data.get('description', '')}"
        return await self.embed_text(text_to_embed)

    async def embed_faq(self, question: str, answer: str) -> List[float]:
        """
        FAQ条目向量化（合并问题+答案）
        
        参数:
            question: 问题文本
            answer: 答案文本
            
        返回:
            FAQ的1536维向量表示
        """
        text_to_embed = f"{question} {answer}"
        return await self.embed_text(text_to_embed)

    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        计算余弦相似度（衡量两个向量的相似程度）
        
        参数:
            vec1: 向量1
            vec2: 向量2
            
        返回:
            相似度分数 [0, 1]（1表示完全相同，0表示完全不同）
            
        公式：cos(θ) = (A·B) / (||A|| × ||B||)
        """
        if not vec1 or not vec2:
            return 0.0
        
        vec1_array = np.array(vec1)
        vec2_array = np.array(vec2)
        
        # 点积（分子）
        dot_product = np.dot(vec1_array, vec2_array)
        
        # 向量模长（分母）
        norm1 = np.linalg.norm(vec1_array)
        norm2 = np.linalg.norm(vec2_array)
        
        # 防止除以零
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)


# 全局单例实例（所有模块共享）
embedding_service = EmbeddingService()