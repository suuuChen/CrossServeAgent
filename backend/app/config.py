"""
应用配置模块
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """全局配置类（从.env文件自动加载）"""

    # 应用基础
    app_name: str = "Multilingual Agent"
    app_env: str = "development"  # 运行环境: development/production/testing
    debug: bool = True

    # 服务器
    host: str = "0.0.0.0"
    port: int = 8000

    # 数据库 (PostgreSQL + PGVector)
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/multilingual_agent"  # 异步连接
    database_sync_url: str = "postgresql://postgres:postgres@localhost:5432/multilingual_agent"  # 同步连接

    # Redis缓存
    redis_url: str = "redis://localhost:6379/0"

    # OpenAI API
    openai_api_key: Optional[str] = None  # 从环境变量 OPENAI_API_KEY 读取
    openai_model: str = "gpt-4o"  # 对话模型
    embedding_model: str = "text-embedding-3-large"  # 向量化模型

    # 智谱 GLM API（OpenAI兼容接口）
    use_glm: bool = False
    glm_api_key: Optional[str] = None
    glm_base_url: str = "https://open.bigmodel.cn/api/paas/v4/"
    glm_model: str = "GLM-4.5-Air"
    glm_embedding_model: str = "embedding-3"

    # 本地LLM (Ollama)
    use_local_llm: bool = False  # 是否使用本地部署的LLM
    local_llm_url: str = "http://localhost:11434/v1"  # Ollama API地址（OpenAI兼容）
    local_llm_model: str = "qwen3.5:4b"  # 本地模型名称

    # 快速模式（跳过LLM调用，使用规则/FAQ直接回复）
    use_fast_mode: bool = True  # 启用快速模式（适合演示/测试）

    # 向量数据库
    vector_dimension: int = 1536  # 向量维度（与embedding模型一致）

    # RAG检索参数
    rag_top_k: int = 5  # 返回最相关的K条结果
    rag_similarity_threshold: float = 0.7  # 相似度阈值 [0, 1]

    # 会话管理
    session_expire_minutes: int = 30  # 会话超时(分钟)
    max_conversation_turns: int = 10  # 最大对话轮数

    # 多语言支持
    supported_languages: list = ["zh", "en", "es", "fr", "de"]
    default_language: str = "zh"
    auto_detect_language: bool = True

    # 违禁词过滤
    compliance_enabled: bool = True
    compliance_llm_check: bool = True
    compliance_log_all: bool = True

    # 转人工
    human_transfer_enabled: bool = True
    auto_transfer_on_complaint: bool = True
    auto_transfer_confidence_threshold: float = 0.4

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# 全局配置实例
settings = Settings()