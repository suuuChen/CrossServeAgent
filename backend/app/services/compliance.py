"""
合规与审计模块
整合: 违禁词合规过滤 + 全量审计日志
"""

import json
import re
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from openai import OpenAI

from app.config import settings
from app.models.audit import AuditLog
from app.utils.security import mask_ip, sanitize_user_query


class ComplianceService:
    """违禁词合规检查器"""

    _instance = None
    _rules_cache = None
    _soft_cache = None
    _compiled_patterns = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_rules()
        return cls._instance

    def _load_rules(self):
        json_path = Path(__file__).resolve().parent.parent.parent / "data" / "prohibited_words.json"
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._rules_cache = data.get("rules", [])
            self._soft_cache = data.get("soft_keywords", [])

            self._compiled_patterns = []
            for rule in self._rules_cache:
                for kw in rule.get("keywords", []):
                    try:
                        pattern = re.compile(re.escape(kw), re.IGNORECASE)
                        self._compiled_patterns.append((pattern, rule))
                    except re.error:
                        continue

            self._compiled_soft = []
            for rule in self._soft_cache:
                for kw in rule.get("keywords", []):
                    try:
                        pattern = re.compile(re.escape(kw), re.IGNORECASE)
                        self._compiled_soft.append((pattern, rule))
                    except re.error:
                        continue

            print(f"[ComplianceService] Loaded {len(self._rules_cache)} hard rules, "
                  f"{len(self._soft_cache)} soft rules, "
                  f"{len(self._compiled_patterns)} compiled patterns")

        except Exception as e:
            print(f"[ComplianceService] Failed to load rules: {e}")
            self._rules_cache = []
            self._soft_cache = []
            self._compiled_patterns = []
            self._compiled_soft = []

    def check(
        self,
        text: str,
        language: str = None,
        use_llm: bool = None
    ) -> Dict:
        if not settings.compliance_enabled:
            return {
                "blocked": False, "severity": None, "categories": [],
                "total_matches": 0, "check_method": "disabled", "llm_result": None
            }

        if not text or len(text.strip()) == 0:
            return {
                "blocked": False, "severity": None, "categories": [],
                "total_matches": 0, "check_method": "regex", "llm_result": None
            }

        categories = []
        seen_categories = set()

        for pattern, rule in self._compiled_patterns:
            match = pattern.search(text)
            if match:
                cat = rule.get("category", "unknown")
                if cat not in seen_categories:
                    seen_categories.add(cat)
                    categories.append({
                        "category": cat,
                        "matched": match.group(),
                        "severity": rule.get("severity", "medium"),
                        "note": rule.get("note", "")
                    })

        for pattern, rule in self._compiled_soft:
            match = pattern.search(text)
            if match:
                cat = rule.get("category", "unknown")
                if cat not in seen_categories:
                    seen_categories.add(cat)
                    categories.append({
                        "category": cat,
                        "matched": match.group(),
                        "severity": "low",
                        "note": rule.get("note", "soft match")
                    })

        has_high_severity = any(c["severity"] == "high" for c in categories)
        has_medium_severity = any(c["severity"] == "medium" for c in categories)
        has_low_severity = any(c["severity"] == "low" for c in categories)

        hard_matches = [c for c in categories if c["severity"] in ("high", "medium")]
        blocked = has_high_severity or len(hard_matches) > 0
        max_severity = None
        if has_high_severity:
            max_severity = "high"
        elif has_medium_severity:
            max_severity = "medium"
        elif has_low_severity:
            max_severity = "low"

        llm_result = None
        should_use_llm = use_llm if use_llm is not None else settings.compliance_llm_check

        if not blocked and should_use_llm and len(text) > 20:
            llm_result = self._llm_check(text, language)
            if llm_result and llm_result.get("blocked"):
                blocked = True
                if llm_result.get("severity") == "high":
                    max_severity = "high"
                if llm_result.get("category"):
                    categories.append({
                        "category": llm_result["category"],
                        "matched": "LLM_detected",
                        "severity": llm_result.get("severity", "medium"),
                        "note": "llm_secondary_check"
                    })

        return {
            "blocked": blocked,
            "severity": max_severity,
            "categories": categories,
            "total_matches": len(categories),
            "check_method": "regex+llm" if (llm_result and should_use_llm) else "regex",
            "llm_result": llm_result
        }

    def _llm_check(self, text: str, language: str = None) -> Optional[Dict]:
        api_key = settings.glm_api_key if settings.use_glm else settings.openai_api_key
        if not api_key:
            return None
        try:
            client_kwargs = {"api_key": api_key}
            if settings.use_glm:
                client_kwargs["base_url"] = settings.glm_base_url
            client = OpenAI(**client_kwargs)
            lang_note = f"text is in {language}" if language else "text may be mixed language"

            prompt = f"""请检查以下跨境电商客服对话内容是否包含违规信息。违规类型包括:
1. 政治敏感话题
2. 种族/民族歧视
3. 宗教亵渎
4. 暴力/威胁/自残
5. 色情/低俗内容
6. 违禁商品（毒品/枪支/仿牌/电子烟/处方药/种子/活体动物）
7. 诈骗（刷单/洗钱/套现/钓鱼）
8. 严重文化禁忌

{lang_note}
"对话内容": "{text[:500]}"

请以 JSON 格式返回:
{{
    "blocked": true/false,
    "category": "违规分类",
    "severity": "high/medium/low",
    "reason": "判断理由",
    "confidence": 0.0-1.0
}}"""

            response = client.chat.completions.create(
                model=settings.glm_model if settings.use_glm else settings.openai_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=200,
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content
            result = json.loads(content)
            return result

        except Exception as e:
            print(f"[ComplianceService] LLM check failed: {e}")
            return None

    @staticmethod
    def get_support_categories() -> List[Dict]:
        json_path = Path(__file__).resolve().parent.parent.parent / "data" / "prohibited_words.json"
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            cats = data.get("categories", {})
            return [{"key": k, **v} for k, v in cats.items()]
        except Exception:
            return []


class AuditLogger:
    """审计日志记录器"""

    @staticmethod
    def _time_cond(since: Optional[datetime]):
        return AuditLog.created_at >= since if since is not None else None

    @staticmethod
    async def log_event(
        db: AsyncSession,
        event_type: str,
        session_id: str = None,
        user_query: str = None,
        response: str = None,
        intent: str = None,
        language: str = None,
        confidence: float = None,
        should_transfer: bool = False,
        transfer_reason: str = None,
        compliance_blocked: bool = False,
        compliance_reason: str = None,
        processing_time_ms: int = None,
        user_ip: str = None
    ) -> Optional[AuditLog]:
        try:
            safe_query = sanitize_user_query(user_query)
            masked_ip = mask_ip(user_ip) if user_ip else None

            log = AuditLog(
                session_id=session_id,
                user_query=safe_query[:2000],
                response=response[:2000] if response else None,
                intent=intent,
                language=language,
                confidence=confidence,
                should_transfer=1 if should_transfer else 0,
                transfer_reason=transfer_reason,
                compliance_blocked=1 if compliance_blocked else 0,
                compliance_reason=compliance_reason,
                event_type=event_type,
                user_ip=masked_ip,
                processing_time_ms=processing_time_ms
            )
            db.add(log)
            await db.commit()
            await db.refresh(log)
            return log
        except Exception as e:
            print(f"[AuditLogger] Failed to write audit log: {e}")
            try:
                await db.rollback()
            except Exception:
                pass
            return None

    @staticmethod
    async def query_logs(
        db: AsyncSession,
        event_type: str = None,
        session_id: str = None,
        language: str = None,
        start_time: datetime = None,
        end_time: datetime = None,
        limit: int = 100
    ) -> List[Dict]:
        try:
            stmt = select(AuditLog)

            if event_type:
                stmt = stmt.where(AuditLog.event_type == event_type)
            if session_id:
                stmt = stmt.where(AuditLog.session_id == session_id)
            if language:
                stmt = stmt.where(AuditLog.language == language)
            if start_time:
                stmt = stmt.where(AuditLog.created_at >= start_time)
            if end_time:
                stmt = stmt.where(AuditLog.created_at <= end_time)

            stmt = stmt.order_by(desc(AuditLog.created_at)).limit(limit)

            result = await db.execute(stmt)
            rows = result.scalars().all()

            return [
                {
                    "id": row.id,
                    "session_id": row.session_id,
                    "user_query": row.user_query,
                    "response": row.response,
                    "intent": row.intent,
                    "language": row.language,
                    "confidence": row.confidence,
                    "should_transfer": bool(row.should_transfer),
                    "transfer_reason": row.transfer_reason,
                    "compliance_blocked": bool(row.compliance_blocked),
                    "compliance_reason": row.compliance_reason,
                    "event_type": row.event_type,
                    "user_ip": row.user_ip,
                    "processing_time_ms": row.processing_time_ms,
                    "created_at": row.created_at.isoformat() if row.created_at else None
                }
                for row in rows
            ]
        except Exception as e:
            print(f"[AuditLogger] Failed to query logs (DB unavailable): {e}")
            return []

    @staticmethod
    async def get_stats(db: AsyncSession, since: datetime = None) -> Dict:
        try:
            time_cond = AuditLogger._time_cond(since)

            total_stmt = select(func.count()).select_from(AuditLog)
            transfer_stmt = select(func.count()).select_from(AuditLog).where(AuditLog.should_transfer == 1)
            blocked_stmt = select(func.count()).select_from(AuditLog).where(AuditLog.compliance_blocked == 1)
            event_types_stmt = select(AuditLog.event_type, func.count(AuditLog.id)).group_by(AuditLog.event_type)

            if time_cond is not None:
                total_stmt = total_stmt.where(time_cond)
                transfer_stmt = transfer_stmt.where(time_cond)
                blocked_stmt = blocked_stmt.where(time_cond)
                event_types_stmt = event_types_stmt.where(time_cond)

            total = (await db.execute(total_stmt)).scalar() or 0
            transfers = (await db.execute(transfer_stmt)).scalar() or 0
            blocked = (await db.execute(blocked_stmt)).scalar() or 0
            event_types_rows = (await db.execute(event_types_stmt)).all()

            return {
                "total_interactions": total,
                "transfer_rate": round(transfers / total, 4) if total > 0 else 0.0,
                "blocked_count": blocked,
                "blocked_rate": round(blocked / total, 4) if total > 0 else 0.0,
                "event_type_distribution": {row[0]: row[1] for row in event_types_rows}
            }
        except Exception as e:
            print(f"[AuditLogger] Failed to get stats (DB unavailable): {e}")
            return {
                "total_interactions": 0,
                "transfer_rate": 0.0,
                "blocked_count": 0,
                "blocked_rate": 0.0,
                "event_type_distribution": {}
            }