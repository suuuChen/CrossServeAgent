"""
API路由定义
定义所有RESTful接口端点及其处理逻辑
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.services.agent import CustomerServiceAgent
from app.services.compliance import AuditLogger, ComplianceService
from app.api.schemas import (
    ChatMessageRequest,
    ChatMessageResponse,
    ProductSearchRequest,
    ProductSearchResponse,
    OrderQueryRequest,
    OrderInfoResponse,
    HealthCheckResponse,
    ErrorResponse,
    ListingGenerateRequest,
    BatchListingRequest,
    ReviewAnalyzeRequest,
    MockReviewGenerateRequest,
    AdGenerateRequest,
    QuickAdGenerateRequest
)


api_router = APIRouter()


# ==================== 系统接口 ====================

@api_router.get("/health", response_model=HealthCheckResponse, tags=["系统"])
async def health_check():
    return HealthCheckResponse(
        status="healthy",
        timestamp=datetime.now().timestamp(),
        environment="development"
    )


# ==================== 客服对话接口（核心）====================

@api_router.post(
    "/chat",
    response_model=ChatMessageResponse,
    responses={
        200: {"description": "成功处理消息"},
        500: {"model": ErrorResponse, "description": "服务器内部错误"}
    },
    tags=["客服对话"]
)
async def chat_message(
    request: ChatMessageRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        agent = CustomerServiceAgent(db)

        result = await agent.process_message(
            user_query=request.message,
            session_id=request.session_id,
            language=request.language
        )

        return ChatMessageResponse(**result)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "PROCESSING_ERROR",
                "error_message": f"处理消息时出错: {str(e)}",
                "timestamp": str(datetime.now())
            }
        )


# ==================== 商品搜索接口 ====================

@api_router.post(
    "/products/search",
    response_model=ProductSearchResponse,
    tags=["商品搜索"]
)
async def search_products(
    request: ProductSearchRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        from app.rag.vector_store import VectorStore

        vector_store = VectorStore(db)

        products = await vector_store.search_products(
            query=request.query,
            top_k=request.top_k,
            language=request.language
        )

        return ProductSearchResponse(
            success=True,
            query=request.query,
            products=products,
            total_found=len(products),
            processing_time_ms=0
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"搜索商品时出错: {str(e)}"
        )


# ==================== 订单查询接口 ====================

@api_router.post(
    "/orders/query",
    response_model=OrderInfoResponse,
    tags=["订单查询"]
)
async def query_order(
    request: OrderQueryRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        from app.rag.vector_store import VectorStore

        vector_store = VectorStore(db)

        order = await vector_store.get_order_by_no(request.order_no)

        if not order:
            raise HTTPException(
                status_code=404,
                detail=f"未找到订单号: {request.order_no}"
            )

        return OrderInfoResponse(**order)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"查询订单时出错: {str(e)}"
        )


# ==================== 商品推荐接口 ====================

@api_router.get("/products/recommendations", tags=["商品推荐"])
async def get_recommendations(
    category: str = Query(None, description="商品分类过滤"),
    limit: int = Query(5, ge=1, le=20, description="返回数量(1-20)"),
    language: str = Query('zh', description="语言"),
    db: AsyncSession = Depends(get_db)
):
    try:
        agent = CustomerServiceAgent(db)

        recommendations = await agent.get_product_recommendations(
            category=category,
            limit=limit
        )

        return {
            "success": True,
            "recommendations": recommendations,
            "total": len(recommendations),
            "category": category or "all"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取推荐时出错: {str(e)}"
        )


# ==================== 转人工会话管理接口====================

@api_router.get("/sessions/pending-human", tags=["转人工管理"])
async def list_pending_human_sessions(db: AsyncSession = Depends(get_db)):
    try:
        pending = []

        for sid, session in CustomerServiceAgent._sessions.items():
            if session.get('status') == 'pending_human':
                transfer_info = session.get('transfer_to_human', {})
                pending.append({
                    'session_id': sid,
                    'status': session.get('status'),
                    'transfer_reason': transfer_info.get('reason'),
                    'intent': transfer_info.get('intent'),
                    'turn_count': session.get('turn_count', 0),
                    'language_detected': session.get('language_detected'),
                    'transfer_timestamp': transfer_info.get('timestamp'),
                    'conversation_summary': transfer_info.get('summary'),
                    'last_activity': session.get('last_activity').isoformat() if session.get('last_activity') else None
                })

        return {
            "success": True,
            "total": len(pending),
            "sessions": pending
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取待人工会话失败: {str(e)}")


@api_router.post("/sessions/{session_id}/human-takeover", tags=["转人工管理"])
async def human_takeover_session(
    session_id: str,
    agent_name: str = Query(..., description="人工客服名称"),
    db: AsyncSession = Depends(get_db)
):
    try:
        sessions = CustomerServiceAgent._sessions

        if session_id not in sessions:
            raise HTTPException(status_code=404, detail=f"未找到会话: {session_id}")

        session = sessions[session_id]
        if session.get('status') != 'pending_human':
            return {
                "success": True,
                "session_id": session_id,
                "message": "该会话不在待处理队列中",
                "current_status": session.get('status')
            }

        session['status'] = 'human_assisted'
        session['human_agent'] = {
            'name': agent_name,
            'takeover_time': datetime.now().isoformat()
        }

        return {
            "success": True,
            "session_id": session_id,
            "new_status": "human_assisted",
            "agent_name": agent_name,
            "message": f"会话已由 {agent_name} 接管"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"接管会话失败: {str(e)}")


# ==================== 会话管理接口 ====================

@api_router.get("/sessions/{session_id}", tags=["会话管理"])
async def get_session_info(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    try:
        agent = CustomerServiceAgent(db)

        session_info = await agent.get_session_info(session_id)

        if not session_info:
            raise HTTPException(
                status_code=404,
                detail=f"未找到会话: {session_id}"
            )

        return {
            "success": True,
            "session": session_info
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取会话信息时出错: {str(e)}"
        )


@api_router.delete("/sessions/{session_id}", tags=["会话管理"])
async def clear_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    try:
        agent = CustomerServiceAgent(db)

        success = await agent.clear_session(session_id)

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"未找到会话: {session_id}"
            )

        return {
            "success": True,
            "message": f"会话 {session_id} 已清除"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"清除会话时出错: {str(e)}"
        )


# ==================== 开发工具接口（仅开发环境使用）====================

@api_router.post("/rag/index-products", tags=["开发工具"])
async def index_all_products(db: AsyncSession = Depends(get_db)):
    try:
        from app.rag.vector_store import VectorStore

        vector_store = VectorStore(db)
        indexed_count = await vector_store.index_all_products()

        return {
            "success": True,
            "message": f"成功索引 {indexed_count} 个商品",
            "indexed_count": indexed_count
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"索引商品时出错: {str(e)}"
        )


@api_router.post("/rag/index-faqs", tags=["开发工具"])
async def index_all_faqs(db: AsyncSession = Depends(get_db)):
    try:
        from app.rag.vector_store import VectorStore

        vector_store = VectorStore(db)
        indexed_count = await vector_store.index_all_faqs()

        return {
            "success": True,
            "message": f"成功索引 {indexed_count} 条FAQ",
            "indexed_count": indexed_count
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"索引FAQ时出错: {str(e)}"
        )


# ==================== 审计日志接口====================

@api_router.get("/audit/logs", tags=["审计日志"])
async def query_audit_logs(
    event_type: Optional[str] = Query(None, description="事件类型: chat/compliance_blocked/human_transfer"),
    session_id: Optional[str] = Query(None, description="会话ID过滤"),
    language: Optional[str] = Query(None, description="语言过滤: zh/en/es/fr/de/ar"),
    hours: Optional[int] = Query(None, ge=1, le=720, description="最近N小时（默认全部）"),
    limit: int = Query(100, ge=1, le=500, description="返回数量"),
    db: AsyncSession = Depends(get_db)
):
    try:
        start_time = None
        if hours:
            start_time = datetime.now() - timedelta(hours=hours)

        logs = await AuditLogger.query_logs(
            db=db,
            event_type=event_type,
            session_id=session_id,
            language=language,
            start_time=start_time,
            limit=limit
        )

        return {
            "success": True,
            "total": len(logs),
            "logs": logs
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询审计日志失败: {str(e)}")


@api_router.get("/audit/stats", tags=["审计日志"])
async def get_audit_stats(
    hours: Optional[int] = Query(None, ge=1, le=720, description="统计最近N小时"),
    db: AsyncSession = Depends(get_db)
):
    try:
        since = None
        if hours:
            since = datetime.now() - timedelta(hours=hours)

        stats = await AuditLogger.get_stats(db=db, since=since)
        return {"success": True, "stats": stats}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计失败: {str(e)}")


# ==================== 合规管理接口====================

@api_router.get("/compliance/categories", tags=["合规管理"])
async def get_compliance_categories():
    try:
        categories = ComplianceService.get_support_categories()
        return {"success": True, "categories": categories}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取合规分类失败: {str(e)}")


@api_router.post("/compliance/check", tags=["合规管理"])
async def check_compliance(
    request: dict,
    db: AsyncSession = Depends(get_db)
):
    try:
        text = request.get("text", "").strip()
        language = request.get("language", "zh")
        if not text:
            raise HTTPException(status_code=400, detail="text 不能为空")

        service = ComplianceService()
        result = service.check(text, language=language)
        return {"success": True, "result": result}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"合规检测失败: {str(e)}")


# ==================== Listing 生成接口====================

@api_router.get("/listing/platforms", tags=["Listing生成"])
async def get_listing_platforms():
    try:
        from app.services.generators import ListingGenerator
        generator = ListingGenerator()
        return {"success": True, "platforms": generator.get_platforms()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取平台列表失败: {str(e)}")


@api_router.post("/listing/generate", tags=["Listing生成"])
async def generate_listing(request: ListingGenerateRequest):
    try:
        from app.services.generators import ListingGenerator
        generator = ListingGenerator()
        result = generator.generate(
            product=request.product.model_dump(),
            platform=request.platform,
            variants=request.variants,
            language=request.language
        )
        return {"success": True, "result": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成Listing失败: {str(e)}")


@api_router.post("/listing/batch", tags=["Listing生成"])
async def batch_generate_listings(request: BatchListingRequest):
    try:
        from app.services.generators import ListingGenerator
        generator = ListingGenerator()
        products = [p.model_dump() for p in request.products]
        result = generator.batch_generate(
            products=products,
            platform=request.platform,
            variants_per_product=request.variants_per_product
        )
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量生成失败: {str(e)}")


# ==================== 评论分析接口====================

@api_router.post("/reviews/analyze", tags=["评论分析"])
async def analyze_reviews(request: ReviewAnalyzeRequest):
    try:
        from app.services.analytics import ReviewAnalyzer
        analyzer = ReviewAnalyzer()
        reviews = [r.model_dump() for r in request.reviews]
        result = analyzer.analyze(reviews)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"评论分析失败: {str(e)}")


@api_router.get("/reviews/themes", tags=["评论分析"])
async def get_review_themes():
    try:
        from app.services.analytics import ReviewAnalyzer, THEME_KEYWORDS
        return {
            "success": True,
            "themes": {k: len(v) for k, v in THEME_KEYWORDS.items()},
            "theme_details": THEME_KEYWORDS
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取主题列表失败: {str(e)}")


@api_router.post("/reviews/generate-mock", tags=["评论分析"])
async def generate_mock_reviews(request: MockReviewGenerateRequest):
    try:
        from app.services.analytics import ReviewAnalyzer
        analyzer = ReviewAnalyzer()
        reviews = analyzer.generate_mock_reviews(
            count=request.count,
            product_category=request.product_category,
            sentiment_bias=request.sentiment_bias
        )
        return {"success": True, "reviews": reviews, "total": len(reviews)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成模拟评论失败: {str(e)}")


# ==================== 广告词生成接口====================

@api_router.post("/ads/generate", tags=["广告词生成"])
async def generate_ads(request: AdGenerateRequest):
    try:
        from app.services.generators import AdCampaignGenerator
        generator = AdCampaignGenerator()
        result = generator.generate(
            product=request.product.model_dump(),
            variants=request.variants,
            include_compliance_check=request.include_compliance_check
        )
        return {"success": True, "result": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"广告词生成失败: {str(e)}")


@api_router.post("/ads/quick-generate", tags=["广告词生成"])
async def quick_generate_ads(request: QuickAdGenerateRequest):
    try:
        from app.services.generators import AdCampaignGenerator
        generator = AdCampaignGenerator()
        result = generator.quick_generate(
            product_name=request.product_name,
            category=request.category,
            key_feature=request.key_feature,
            brand=request.brand
        )
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"快速生成广告词失败: {str(e)}")


@api_router.get("/ads/conversion-patterns", tags=["广告词生成"])
async def get_conversion_patterns():
    try:
        from app.services.generators import AdCampaignGenerator
        generator = AdCampaignGenerator()
        return {"success": True, "patterns": generator.get_conversion_patterns()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取高转化词库失败: {str(e)}")


# ==================== 运营报表系统====================

@api_router.get("/reports/dashboard", tags=["运营报表"])
async def get_dashboard_summary(
    hours: Optional[int] = Query(None, ge=1, le=720, description="统计最近N小时"),
    db: AsyncSession = Depends(get_db)
):
    """仪表盘核心指标（总交互量/转人工率/拦截率/平均响应时间）"""
    try:
        from app.services.analytics import ReportService
        result = await ReportService.get_dashboard_summary(db, hours=hours)
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取仪表盘数据失败: {str(e)}")


@api_router.get("/reports/language-distribution", tags=["运营报表"])
async def get_language_distribution(
    hours: Optional[int] = Query(None, ge=1, le=720, description="统计最近N小时"),
    db: AsyncSession = Depends(get_db)
):
    """按语言维度统计交互量"""
    try:
        from app.services.analytics import ReportService
        result = await ReportService.get_language_distribution(db, hours=hours)
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取语言分布失败: {str(e)}")


@api_router.get("/reports/intent-distribution", tags=["运营报表"])
async def get_intent_distribution(
    hours: Optional[int] = Query(None, ge=1, le=720, description="统计最近N小时"),
    db: AsyncSession = Depends(get_db)
):
    """按意图类型统计交互量"""
    try:
        from app.services.analytics import ReportService
        result = await ReportService.get_intent_distribution(db, hours=hours)
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取意图分布失败: {str(e)}")


@api_router.get("/reports/hourly-trend", tags=["运营报表"])
async def get_hourly_trend(
    hours: int = Query(24, ge=1, le=168, description="统计最近N小时（最大168）"),
    db: AsyncSession = Depends(get_db)
):
    """按小时的交互趋势（支持前端图表）"""
    try:
        from app.services.analytics import ReportService
        result = await ReportService.get_hourly_trend(db, hours=hours)
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取小时趋势失败: {str(e)}")


@api_router.get("/reports/agent-efficiency", tags=["运营报表"])
async def get_agent_efficiency(
    hours: Optional[int] = Query(None, ge=1, le=720, description="统计最近N小时"),
    db: AsyncSession = Depends(get_db)
):
    """客服效率指标（平均置信度/高置信占比/自动解决率）"""
    try:
        from app.services.analytics import ReportService
        result = await ReportService.get_agent_efficiency(db, hours=hours)
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取效率指标失败: {str(e)}")


# ==================== 数据导出接口====================

@api_router.get("/export/audit-logs", tags=["数据导出"])
async def export_audit_logs(
    format: str = Query("csv", regex="^(csv|json)$", description="导出格式: csv/json"),
    event_type: Optional[str] = Query(None, description="按事件类型过滤"),
    hours: Optional[int] = Query(None, ge=1, le=720, description="最近N小时"),
    limit: int = Query(10000, ge=1, le=50000, description="最大导出条数"),
    db: AsyncSession = Depends(get_db)
):
    """导出审计日志（CSV/JSON）"""
    try:
        from app.services.analytics import ReportService
        from app.services.analytics import export_to_csv, export_to_json

        data = await ReportService.get_export_data(
            db=db, event_type=event_type, hours=hours, limit=limit
        )

        if format == "csv":
            return export_to_csv(data, filename="audit_logs")
        else:
            return export_to_json(data, filename="audit_logs")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出数据失败: {str(e)}")