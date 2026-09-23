"""
文本向量化服务（支持本地模型和OpenAI API）
优先使用本地sentence-transformers模型，无需API key
"""

from typing import List
import numpy as np
import hashlib
import os
import threading
from app.config import settings


HF_OFFLINE = os.environ.get("HF_HUB_OFFLINE", "1") == "1"
HF_TIMEOUT = int(os.environ.get("HF_DOWNLOAD_TIMEOUT", "15"))


class EmbeddingService:
    """
    文本向量化服务类
    
    功能：将文本转换为高维向量（用于语义搜索）
    
    策略：
    1. 优先使用本地 sentence-transformers 模型（无需API key）
    2. 加载失败快速降级到哈希向量（保证可用性，不阻塞）
    """

    def __init__(self):
        """初始化向量化服务（延迟加载模型）"""
        self.model = None
        self.client = None
        self.dimension = settings.vector_dimension
        self.use_local_model = True
        self._model_loaded = False
        self._load_attempted = False

    def _ensure_model_loaded(self):
        """延迟加载本地模型（首次使用时才加载，带超时保护）"""
        if self._model_loaded:
            return

        if self._load_attempted:
            return

        self._load_attempted = True

        def _do_load():
            try:
                print("[Embedding] Loading local sentence-transformers model (offline mode)...")
                os.environ.setdefault("HF_HUB_OFFLINE", "1")
                os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer(
                    "paraphrase-multilingual-MiniLM-L12-v2",
                    device="cpu"
                )
                self.dimension = self.model.get_sentence_embedding_dimension()
                print(f"[Embedding] Local model loaded OK (dim={self.dimension})")
                self.use_local_model = True
            except Exception as e:
                print(f"[Embedding] Local model unavailable: {e}")
                print("[Embedding] Falling back to hash-based embeddings (fast, offline)")
                self.use_local_model = False
            finally:
                self._model_loaded = True

        loader = threading.Thread(target=_do_load, daemon=True)
        loader.start()
        loader.join(timeout=HF_TIMEOUT)

        if not self._model_loaded:
            print(f"[Embedding] Model load timed out after {HF_TIMEOUT}s, using hash fallback")
            self.use_local_model = False
            self._model_loaded = True

    async def embed_text(self, text: str) -> List[float]:
        """
        单文本向量化
        
        参数:
            text: 待向量化的文本
            
        返回:
            维浮点数列表
        """
        self._ensure_model_loaded()

        if self.use_local_model and self.model:
            try:
                embedding = self.model.encode(text)
                return embedding.tolist()
            except Exception as e:
                print(f"Error with local model: {e}, falling back to hash")

        return self._hash_embedding(text)

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        批量文本向量化（高效处理多个文本）
        
        参数:
            texts: 文本列表
            
        返回:
            向量列表
        """
        self._ensure_model_loaded()

        if self.use_local_model and self.model:
            try:
                embeddings = self.model.encode(texts)
                return [emb.tolist() for emb in embeddings]
            except Exception as e:
                print(f"Error with local model batch: {e}, falling back to hash")

        return [self._hash_embedding(text) for text in texts]

    async def embed_product(self, product_data: dict) -> List[float]:
        """
        商品向量化（合并名称+描述）
        
        参数:
            product_data: 商品字典（需包含name和description字段）
            
        返回:
            商品的向量表示
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
            FAQ的向量表示
        """
        text_to_embed = f"{question} {answer}"
        return await self.embed_text(text_to_embed)

    def _hash_embedding(self, text: str) -> List[float]:
        """
        基于哈希的简单向量化（最终降级方案）
        
        使用文本的哈希值生成固定维度的向量
        虽然语义信息有限，但能保证系统可用性
        """
        hash_obj = hashlib.sha256(text.encode('utf-8'))
        hash_hex = hash_obj.hexdigest()
        
        vector = []
        for i in range(0, min(len(hash_hex), self.dimension * 2), 2):
            hex_pair = hash_hex[i:i+2]
            value = int(hex_pair, 16) / 255.0 - 0.5
            vector.append(value)
        
        while len(vector) < self.dimension:
            vector.append(0.0)
        
        return vector[:self.dimension]

    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """
        计算余弦相似度（衡量两个向量的相似程度）
        
        参数:
            vec1: 向量1
            vec2: 向量2
            
        返回:
            相似度分数 [0, 1]（1表示完全相同，0表示完全不同）
        """
        if not vec1 or not vec2:
            return 0.0

        vec1_array = np.array(vec1)
        vec2_array = np.array(vec2)

        dot_product = np.dot(vec1_array, vec2_array)
        norm1 = np.linalg.norm(vec1_array)
        norm2 = np.linalg.norm(vec2_array)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))


# 全局单例实例（延迟初始化，不会在导入时失败）
embedding_service = EmbeddingService()