"""
API请求/响应数据模型（Pydantic Schema）
用于参数校验和API文档自动生成
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# ==================== 请求模型 ====================

class ChatMessageRequest(BaseModel):
    """
    客服对话请求
    
    用于 POST /api/v1/chat 接口
    """
    message: str = Field(
        ..., 
        min_length=1, 
        max_length=2000, 
        description="用户消息文本"
    )
    session_id: Optional[str] = Field(
        None, 
        description="会话ID（可选，不传则创建新会话）"
    )
    language: str = Field(
        default='zh', 
        description="响应语言: zh/en/es/fr/de"
    )


class ProductSearchRequest(BaseModel):
    """
    商品搜索请求
    
    用于 POST /api/v1/products/search 接口
    """
    query: str = Field(
        ..., 
        min_length=1, 
        max_length=500, 
        description="搜索查询词（支持自然语言）"
    )
    category: Optional[str] = Field(
        None, 
        description="商品分类过滤（可选）"
    )
    language: str = Field(
        default='zh', 
        description="语言"
    )
    top_k: int = Field(
        default=5, 
        ge=1,  # 最小值
        le=20, # 最大值
        description="返回结果数量（1-20）"
    )


class OrderQueryRequest(BaseModel):
    """
    订单查询请求
    
    用于 POST /api/v1/orders/query 接口
    """
    order_no: str = Field(
        ..., 
        min_length=1, 
        description="订单号"
    )
    language: str = Field(
        default='zh', 
        description="语言"
    )


# ==================== 响应模型 ====================

class ChatMessageResponse(BaseModel):
    """
    客服对话响应
    
    返回AI生成的回复及元数据
    """
    success: bool
    session_id: str
    response: str
    intent: str
    confidence: float
    rag_confidence: float
    language: str
    should_transfer: bool
    processing_time_ms: int
    context_used: Dict[str, int]
    transfer_reason: Optional[str] = None
    conversation_summary: Optional[Dict] = None
    session_status: Optional[str] = None
    compliance_blocked: bool = False
    compliance_details: Optional[Dict] = None
    error: Optional[str] = None


class ProductInfoResponse(BaseModel):
    """
    单个商品信息响应
    """
    id: int                          # 商品ID
    sku: str                         # 商品编码
    name: str                        # 商品名称
    description: Optional[str]       # 描述
    category: Optional[str]          # 分类
    price: Optional[float]           # 价格
    stock: int                       # 库存数量
    language: str                    # 语言
    similarity_score: float          # 与查询的相似度 [0, 1]


class ProductSearchResponse(BaseModel):
    """
    商品搜索响应
    
    包含匹配的商品列表和统计信息
    """
    success: bool                    # 是否成功
    query: str                       # 原始查询词
    products: List[ProductInfoResponse]  # 匹配的商品列表
    total_found: int                 # 找到的商品总数
    processing_time_ms: int          # 搜索耗时(毫秒)


class OrderInfoResponse(BaseModel):
    """
    订单信息响应
    
    包含订单详情和商品项列表
    """
    id: int                          # 订单ID
    order_no: str                    # 订单号
    customer_name: Optional[str]     # 客户姓名
    status: str                      # 订单状态
    total_amount: Optional[float]    # 总金额
    currency: str                    # 货币单位
    items: List[Dict]               # 订单项列表 [{sku, name, quantity, unit_price}, ...]
    created_at: Optional[str]        # 创建时间


class HealthCheckResponse(BaseModel):
    """
    健康检查响应
    
    用于负载均衡探活和监控
    """
    status: str                      # 状态: healthy/unhealthy
    timestamp: float                 # 当前时间戳
    environment: str                 # 运行环境: development/production/testing
    version: str = "1.0.0"          # 应用版本


# ==================== 内部数据模型（RAG Pipeline使用）====================

class RAGContext(BaseModel):
    """
    RAG检索到的上下文（内部使用）
    
    存储从向量库检索到的相关信息
    """
    products: List[Dict] = []        # 相关商品列表
    faqs: List[Dict] = []            # 相关FAQ列表
    orders: List[Dict] = []          # 相关订单信息
    max_similarity: float = 0.0      # 最高相似度分数


class SessionInfo(BaseModel):
    """
    会话信息模型（内部使用）
    
    用于存储和管理对话状态
    """
    session_id: str                  # 会话ID
    created_at: datetime             # 创建时间
    last_activity: datetime          # 最后活动时间
    turn_count: int                  # 对话轮次计数
    language_detected: Optional[str] # 检测到的语言


# ==================== 错误响应模型 ====================

class ErrorResponse(BaseModel):
    """
    标准错误响应格式
    
    所有异常情况统一返回此格式
    """
    success: bool = False            # 固定为False
    error_code: str                  # 错误代码（如：PROCESSING_ERROR）
    error_message: str               # 用户可读的错误描述
    details: Optional[Dict[str, Any]] = None  # 详细错误信息（调试用）
    timestamp: datetime = Field(default_factory=datetime.now)  # 错误发生时间


class ValidationErrorResponse(ErrorResponse):
    """
    参数校验错误响应
    
    继承标准错误响应，增加字段校验详情
    """
    error_code: str = "VALIDATION_ERROR"  # 固定错误码
    validation_errors: List[Dict] = []   # 校验错误列表 [{"field": "message", ...}]


# ==================== 意图类型常量（用于文档说明）====================

class IntentType:
    """意图类型枚举值定义（用于API文档注释）"""
    
    ORDER_QUERY = "order_query"         # 订单查询
    SHIPPING_QUERY = "shipping_query"   # 物流查询
    RETURN_POLICY = "return_policy"     # 退货政策咨询
    PRODUCT_SEARCH = "product_search"   # 商品搜索
    GENERAL_FAQ = "general_faq"         # 通用FAQ
    COMPLAINT = "complaint"             # 投诉/差评
    HUMAN_TRANSFER = "human_transfer"   # 转人工请求


# ==================== Listing 生成请求/响应 ====================

class ProductInput(BaseModel):
    """产品输入 - 用于 Listing 和广告词生成"""
    name: str = Field(..., description="产品名称", max_length=200)
    brand: str = Field(default="", description="品牌名")
    category: str = Field(default="", description="产品分类")
    description: str = Field(default="", description="产品描述")
    key_features: List[str] = Field(default_factory=list, description="核心卖点列表")
    target_audience: str = Field(default="everyone", description="目标受众")
    sku: Optional[str] = Field(None, description="SKU编码")
    price: Optional[float] = Field(None, description="售价")


class ListingGenerateRequest(BaseModel):
    """Listing 生成请求"""
    product: ProductInput = Field(..., description="产品信息")
    platform: str = Field("amazon", description="目标平台: amazon/temu/tiktok_shop")
    variants: int = Field(1, ge=1, le=5, description="生成变体数量")
    language: str = Field("en", description="输出语言")


class BatchListingRequest(BaseModel):
    """批量 Listing 生成请求"""
    products: List[ProductInput] = Field(..., description="产品列表")
    platform: str = Field("amazon", description="目标平台")
    variants_per_product: int = Field(1, ge=1, le=5, description="每个产品的变体数")


# ==================== 评论分析请求/响应====================

class ReviewInput(BaseModel):
    """评论输入"""
    id: Optional[str] = Field(None, description="评论ID")
    content: str = Field(..., description="评论内容", max_length=2000)
    rating: Optional[int] = Field(None, ge=1, le=5, description="评分(1-5)")


class ReviewAnalyzeRequest(BaseModel):
    """评论分析请求"""
    reviews: List[ReviewInput] = Field(..., description="评论列表")


class MockReviewGenerateRequest(BaseModel):
    """模拟评论生成请求"""
    count: int = Field(100, ge=10, le=1000, description="生成数量")
    product_category: str = Field("general", description="产品类别")
    sentiment_bias: float = Field(0.7, ge=0.0, le=1.0, description="正面情感倾向")


# ==================== 广告词生成请求/响应====================

class AdGenerateRequest(BaseModel):
    """广告词生成请求"""
    product: ProductInput = Field(..., description="产品信息")
    variants: int = Field(4, ge=2, le=6, description="生成变体数")
    include_compliance_check: bool = Field(True, description="是否进行合规检查")


class QuickAdGenerateRequest(BaseModel):
    """快速广告词生成请求"""
    product_name: str = Field(..., description="产品名称")
    category: str = Field("", description="分类")
    key_feature: str = Field("", description="核心卖点")
    brand: str = Field("", description="品牌")