"""
数据分析模块
整合: 评论情感分析 + 运营报表 + 数据导出(CSV/JSON)
"""

import re
import csv
import io
import json
import random
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import Counter

from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, extract

from app.models.audit import AuditLog


SENTIMENT_KEYWORDS = {
    "positive": [
        "great", "excellent", "amazing", "love", "perfect", "awesome", "fantastic",
        "wonderful", "best", "good", "nice", "beautiful", "comfortable", "fast",
        "happy", "satisfied", "recommend", "5 star", "worth", "quality", "quick",
        "incredible", "superb", "outstanding", "impressed", "smooth", "easy",
        "太棒了", "好评", "满意", "推荐", "质量好", "物流快", "值得", "喜欢",
        "完美", "优秀", "舒适", "好用"
    ],
    "negative": [
        "terrible", "awful", "bad", "worst", "hate", "poor", "disappointed",
        "broken", "defective", "waste", "scam", "return", "refund", "slow",
        "damaged", "wrong", "missing", "late", "problem", "issue", "complaint",
        "cheap", "uncomfortable", "not worth", "avoid", "frustrated", "regret",
        "糟糕", "差评", "失望", "差", "退货", "退款", "坏了", "慢", "破损",
        "不满意", "投诉", "浪费钱", "假货", "骗"
    ]
}

THEME_KEYWORDS = {
    "quality": [
        "quality", "material", "durable", "sturdy", "well made", "solid", "constructed",
        "做工", "质量", "材质", "耐用", "结实"
    ],
    "shipping": [
        "shipping", "delivery", "arrived", "package", "box", "mail", "courier", "tracking",
        "物流", "快递", "发货", "配送", "到货"
    ],
    "size": [
        "size", "fit", "sizing", "small", "large", "too big", "too small", "run small", "run big",
        "尺码", "大小", "合身", "太大", "太小"
    ],
    "price": [
        "price", "cost", "expensive", "cheap", "worth", "deal", "value", "money", "budget",
        "价格", "贵", "便宜", "划算", "性价比"
    ],
    "appearance": [
        "look", "design", "color", "style", "appearance", "pretty", "cute", "ugly",
        "外观", "设计", "颜色", "样式", "好看", "丑"
    ],
    "functionality": [
        "work", "function", "easy to use", "performance", "feature", "operation",
        "功能", "好用", "操作", "性能"
    ],
    "customer_service": [
        "service", "support", "response", "help", "representative", "chat", "email",
        "客服", "服务", "响应", "帮助"
    ]
}


def _detect_sentiment(text: str) -> Tuple[str, float]:
    text_lower = text.lower()
    pos_count = sum(1 for kw in SENTIMENT_KEYWORDS["positive"] if kw in text_lower)
    neg_count = sum(1 for kw in SENTIMENT_KEYWORDS["negative"] if kw in text_lower)

    if pos_count == 0 and neg_count == 0:
        return ("neutral", 0.3)

    if pos_count > neg_count:
        confidence = min(0.95, 0.5 + (pos_count - neg_count) * 0.1)
        return ("positive", confidence)
    elif neg_count > pos_count:
        confidence = min(0.95, 0.5 + (neg_count - pos_count) * 0.1)
        return ("negative", confidence)
    else:
        return ("neutral", 0.5)


def _extract_themes(text: str) -> List[str]:
    text_lower = text.lower()
    themes = []
    for theme, keywords in THEME_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                themes.append(theme)
                break
    return themes


def _analyze_single_review(review: Dict) -> Dict:
    text = review.get("content", review.get("text", ""))
    rating = review.get("rating")
    review_id = review.get("id", review.get("review_id", ""))

    sentiment, confidence = _detect_sentiment(text)
    themes = _extract_themes(text)

    if rating is not None:
        if rating <= 2 and sentiment == "positive":
            sentiment = "negative"
            confidence = max(confidence, 0.7)
        elif rating >= 4 and sentiment == "negative":
            sentiment = "positive"
            confidence = max(confidence, 0.6)

    return {
        "review_id": review_id,
        "original_rating": rating,
        "sentiment": sentiment,
        "confidence": round(confidence, 3),
        "themes": themes,
        "has_multiple_themes": len(themes) > 1
    }


class ReviewAnalyzer:
    """评论分析服务"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def analyze(self, reviews: List[Dict]) -> Dict[str, Any]:
        if not reviews:
            return self._empty_result()

        analyzed = []
        all_sentiments = []
        all_themes = []
        ratings = []

        for review in reviews:
            result = _analyze_single_review(review)
            analyzed.append(result)
            all_sentiments.append(result["sentiment"])
            all_themes.extend(result["themes"])
            if result["original_rating"] is not None:
                ratings.append(result["original_rating"])

        sentiment_counts = Counter(all_sentiments)
        total = len(reviews)

        sentiment_dist = {
            "positive": sentiment_counts.get("positive", 0),
            "negative": sentiment_counts.get("negative", 0),
            "neutral": sentiment_counts.get("neutral", 0),
            "percentages": {
                "positive": round(sentiment_counts.get("positive", 0) / total * 100, 1),
                "negative": round(sentiment_counts.get("negative", 0) / total * 100, 1),
                "neutral": round(sentiment_counts.get("neutral", 0) / total * 100, 1)
            }
        }

        theme_counts = Counter(all_themes)
        theme_dist = {theme: count for theme, count in theme_counts.most_common()}

        theme_cooccurrence = []
        pair_counts = Counter()
        for r in analyzed:
            tlist = r["themes"]
            for i in range(len(tlist)):
                for j in range(i + 1, len(tlist)):
                    pair = tuple(sorted([tlist[i], tlist[j]]))
                    pair_counts[pair] += 1
        for (a, b), count in pair_counts.most_common(10):
            theme_cooccurrence.append({"theme_a": a, "theme_b": b, "count": count})

        avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else None

        summary = self._generate_summary(sentiment_dist, theme_dist, avg_rating, total)

        return {
            "total_reviews": total,
            "sentiment_distribution": sentiment_dist,
            "theme_distribution": theme_dist,
            "theme_cooccurrence": theme_cooccurrence,
            "avg_rating": avg_rating,
            "theme_list": list(THEME_KEYWORDS.keys()),
            "analyzed_reviews": analyzed,
            "summary": summary,
            "generated_at": datetime.now().isoformat()
        }

    def analyze_text(self, text: str) -> Dict:
        result = _analyze_single_review({"content": text})
        return {
            "text": text,
            "sentiment": result["sentiment"],
            "confidence": result["confidence"],
            "themes": result["themes"]
        }

    def analyze_from_csv(self, csv_content: str) -> Dict[str, Any]:
        reviews = []
        reader = csv.DictReader(io.StringIO(csv_content))
        for row in reader:
            reviews.append(row)
        return self.analyze(reviews)

    def generate_mock_reviews(
        self,
        count: int = 100,
        product_category: str = "general",
        sentiment_bias: float = 0.7
    ) -> List[Dict]:
        positive_templates = [
            "This {item} is absolutely amazing! The {aspect} exceeded my expectations.",
            "Great {item}, love the {aspect}! Highly recommend to everyone.",
            "Best {item} I've ever bought. The {aspect} is perfect.",
            "Excellent quality {item}, very happy with my purchase. {aspect} is great!",
            "Wonderful {item}, works perfectly. The {aspect} is fantastic."
        ]
        negative_templates = [
            "Terrible {item}, very disappointed. The {aspect} is awful.",
            "Worst {item} ever. The {aspect} is broken already.",
            "Poor quality {item}, the {aspect} is completely wrong.",
            "Hate this {item}. The {aspect} is damaged. Want my money back!",
            "Bad experience with this {item}. {aspect} arrived late and broken."
        ]
        neutral_templates = [
            "It's an okay {item}. The {aspect} is what I expected.",
            "Average {item}, nothing special about the {aspect}.",
            "Standard {item}. The {aspect} works as described.",
            "Not bad, not great. The {aspect} is functional.",
            "Decent {item}. The {aspect} meets basic expectations."
        ]

        items = ["product", "item", "purchase", "order", "delivery", "package"]
        aspects_map = {
            "general": ["quality", "shipping", "size", "price", "appearance", "customer service"],
            "electronics": ["performance", "battery", "screen", "build quality", "sound"],
            "clothing": ["fit", "fabric", "color", "sizing", "comfort"],
            "home": ["design", "material", "durability", "appearance", "functionality"]
        }
        aspects = aspects_map.get(product_category, aspects_map["general"])

        reviews = []
        for i in range(count):
            r = random.random()
            item = random.choice(items)
            aspect = random.choice(aspects)

            if r < sentiment_bias:
                template = random.choice(positive_templates)
                sentiment_label = "positive"
                rating = random.choice([4, 4, 5, 5])
            elif r < sentiment_bias + (1 - sentiment_bias) * 0.6:
                template = random.choice(neutral_templates)
                sentiment_label = "neutral"
                rating = random.choice([3, 3, 4])
            else:
                template = random.choice(negative_templates)
                sentiment_label = "negative"
                rating = random.choice([1, 1, 2])

            content = template.format(item=item, aspect=aspect)
            reviews.append({
                "id": f"mock_{i + 1:04d}",
                "content": content,
                "rating": rating,
                "product_category": product_category,
                "created_at": datetime.now().isoformat()
            })

        return reviews

    def _empty_result(self) -> Dict[str, Any]:
        return {
            "total_reviews": 0,
            "sentiment_distribution": {"positive": 0, "negative": 0, "neutral": 0, "percentages": {}},
            "theme_distribution": {},
            "theme_cooccurrence": [],
            "avg_rating": None,
            "theme_list": list(THEME_KEYWORDS.keys()),
            "analyzed_reviews": [],
            "summary": "无评论数据可分析",
            "generated_at": datetime.now().isoformat()
        }

    def _generate_summary(
        self,
        sentiment_dist: Dict,
        theme_dist: Dict,
        avg_rating: Optional[float],
        total: int
    ) -> str:
        pos_pct = sentiment_dist["percentages"].get("positive", 0)
        neg_pct = sentiment_dist["percentages"].get("negative", 0)

        if pos_pct >= 70:
            overall = "整体评价正面"
        elif neg_pct >= 50:
            overall = "整体评价负面"
        else:
            overall = "评价分布较为分散"

        top_themes = list(theme_dist.keys())[:3]
        theme_str = "、".join(top_themes) if top_themes else "无明显主题聚集"

        rating_str = f"平均评分 {avg_rating}/5" if avg_rating else "无评分数据"

        return f"共分析 {total} 条评论，{overall}（正面 {pos_pct}%，负面 {neg_pct}%），" \
               f"主要讨论主题：{theme_str}，{rating_str}。"


class ReportService:
    """报表服务"""

    @staticmethod
    def _time_filter(hours: Optional[int]):
        if hours:
            since = datetime.now() - timedelta(hours=hours)
            return AuditLog.created_at >= since
        return None

    @staticmethod
    async def get_dashboard_summary(
        db: AsyncSession,
        hours: Optional[int] = None
    ) -> Dict[str, Any]:
        time_cond = ReportService._time_filter(hours)

        total_stmt = select(func.count()).select_from(AuditLog)
        chat_stmt = select(func.count()).select_from(AuditLog).where(AuditLog.event_type == "chat")
        transfer_stmt = select(func.count()).select_from(AuditLog).where(AuditLog.should_transfer == 1)
        blocked_stmt = select(func.count()).select_from(AuditLog).where(AuditLog.compliance_blocked == 1)
        avg_time_stmt = select(func.avg(AuditLog.processing_time_ms)).select_from(AuditLog)

        if time_cond is not None:
            total_stmt = total_stmt.where(time_cond)
            chat_stmt = chat_stmt.where(time_cond)
            transfer_stmt = transfer_stmt.where(time_cond)
            blocked_stmt = blocked_stmt.where(time_cond)
            avg_time_stmt = avg_time_stmt.where(time_cond)

        total = (await db.execute(total_stmt)).scalar() or 0
        chat_total = (await db.execute(chat_stmt)).scalar() or 0
        transfer_count = (await db.execute(transfer_stmt)).scalar() or 0
        blocked_count = (await db.execute(blocked_stmt)).scalar() or 0

        avg_time_row = (await db.execute(avg_time_stmt)).scalar()
        avg_processing_time = round(float(avg_time_row), 1) if avg_time_row else 0.0

        return {
            "period": f"最近{hours}小时" if hours else "全部时间",
            "summary": {
                "total_interactions": total,
                "chat_messages": chat_total,
                "transfer_to_human": transfer_count,
                "compliance_blocked": blocked_count,
                "transfer_rate": round(transfer_count / chat_total, 4) if chat_total > 0 else 0.0,
                "blocked_rate": round(blocked_count / total, 4) if total > 0 else 0.0,
                "avg_processing_time_ms": avg_processing_time
            },
            "generated_at": datetime.now().isoformat()
        }

    @staticmethod
    async def get_language_distribution(
        db: AsyncSession,
        hours: Optional[int] = None
    ) -> Dict[str, Any]:
        time_cond = ReportService._time_filter(hours)

        stmt = select(
            AuditLog.language,
            func.count(AuditLog.id)
        ).group_by(AuditLog.language)

        if time_cond is not None:
            stmt = stmt.where(time_cond)

        rows = (await db.execute(stmt)).all()

        return {
            "period": f"最近{hours}小时" if hours else "全部时间",
            "distribution": {row[0] or "unknown": row[1] for row in rows},
            "generated_at": datetime.now().isoformat()
        }

    @staticmethod
    async def get_intent_distribution(
        db: AsyncSession,
        hours: Optional[int] = None
    ) -> Dict[str, Any]:
        time_cond = ReportService._time_filter(hours)

        stmt = select(
            AuditLog.intent,
            func.count(AuditLog.id)
        ).where(AuditLog.intent.isnot(None)).group_by(AuditLog.intent)

        if time_cond is not None:
            stmt = stmt.where(time_cond)

        rows = (await db.execute(stmt)).all()

        return {
            "period": f"最近{hours}小时" if hours else "全部时间",
            "distribution": {row[0]: row[1] for row in rows},
            "generated_at": datetime.now().isoformat()
        }

    @staticmethod
    async def get_hourly_trend(
        db: AsyncSession,
        hours: int = 24
    ) -> Dict[str, Any]:
        since = datetime.now() - timedelta(hours=hours)

        stmt = select(
            extract('hour', AuditLog.created_at).label('hour'),
            func.count(AuditLog.id)
        ).where(AuditLog.created_at >= since).group_by('hour').order_by('hour')

        rows = (await db.execute(stmt)).all()

        trend = [{"hour": int(row[0]), "count": row[1]} for row in rows]

        return {
            "period_hours": hours,
            "trend": trend,
            "generated_at": datetime.now().isoformat()
        }

    @staticmethod
    async def get_agent_efficiency(
        db: AsyncSession,
        hours: Optional[int] = None
    ) -> Dict[str, Any]:
        time_cond = ReportService._time_filter(hours)

        confidence_stmt = select(func.avg(AuditLog.confidence)).select_from(AuditLog).where(AuditLog.confidence.isnot(None))
        high_conf_stmt = select(func.count()).select_from(AuditLog).where(AuditLog.confidence >= 0.7)
        low_conf_stmt = select(func.count()).select_from(AuditLog).where(AuditLog.confidence < 0.4)
        total_stmt = select(func.count()).select_from(AuditLog)

        if time_cond is not None:
            confidence_stmt = confidence_stmt.where(time_cond)
            high_conf_stmt = high_conf_stmt.where(time_cond)
            low_conf_stmt = low_conf_stmt.where(time_cond)
            total_stmt = total_stmt.where(time_cond)

        avg_conf_row = (await db.execute(confidence_stmt)).scalar()
        high_conf = (await db.execute(high_conf_stmt)).scalar() or 0
        low_conf = (await db.execute(low_conf_stmt)).scalar() or 0
        total = (await db.execute(total_stmt)).scalar() or 0

        return {
            "period": f"最近{hours}小时" if hours else "全部时间",
            "efficiency": {
                "avg_confidence": round(float(avg_conf_row), 4) if avg_conf_row else 0.0,
                "high_confidence_count": high_conf,
                "low_confidence_count": low_conf,
                "confidence_distribution": {
                    "high (>=0.7)": high_conf,
                    "medium (0.4-0.7)": total - high_conf - low_conf,
                    "low (<0.4)": low_conf
                },
                "auto_resolve_rate": round((total - low_conf) / total, 4) if total > 0 else 0.0
            },
            "generated_at": datetime.now().isoformat()
        }

    @staticmethod
    async def get_export_data(
        db: AsyncSession,
        event_type: Optional[str] = None,
        hours: Optional[int] = None,
        limit: int = 10000
    ) -> List[Dict]:
        stmt = select(AuditLog)

        if event_type:
            stmt = stmt.where(AuditLog.event_type == event_type)
        if hours:
            since = datetime.now() - timedelta(hours=hours)
            stmt = stmt.where(AuditLog.created_at >= since)

        stmt = stmt.order_by(AuditLog.created_at.desc()).limit(limit)

        result = await db.execute(stmt)
        rows = result.scalars().all()

        return [
            {
                "id": row.id,
                "event_type": row.event_type,
                "session_id": row.session_id,
                "language": row.language,
                "intent": row.intent,
                "confidence": row.confidence,
                "should_transfer": bool(row.should_transfer),
                "compliance_blocked": bool(row.compliance_blocked),
                "processing_time_ms": row.processing_time_ms,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "user_query": (row.user_query or "")[:200],
                "response": (row.response or "")[:200]
            }
            for row in rows
        ]


def export_to_csv(
    data: List[Dict],
    filename: str = "audit_logs",
    columns: Optional[List[str]] = None
) -> StreamingResponse:
    if not data:
        data = [{"message": "暂无数据"}]

    fieldnames = columns or list(data[0].keys())

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in data:
        clean_row = {}
        for k, v in row.items():
            if k in fieldnames:
                if isinstance(v, (dict, list)):
                    clean_row[k] = json.dumps(v, ensure_ascii=False)
                else:
                    clean_row[k] = v
        writer.writerow(clean_row)

    output.seek(0)

    safe_filename = f"{filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        iter([output.getvalue().encode('utf-8-sig')]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{safe_filename}",
            "Content-Type": "text/csv; charset=utf-8-sig"
        }
    )


def export_to_json(
    data: List[Dict],
    filename: str = "audit_logs"
) -> StreamingResponse:
    export_payload = {
        "exported_at": datetime.now().isoformat(),
        "total_records": len(data),
        "data": data
    }

    safe_filename = f"{filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    return StreamingResponse(
        iter([json.dumps(export_payload, ensure_ascii=False, indent=2).encode('utf-8')]),
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{safe_filename}"
        }
    )