"""
多语言理解模块 (NLU)
包含: 语言检测 + 意图类型定义 + 意图路由
"""

from typing import Tuple, Optional
from enum import Enum

import re


UNICODE_RANGES = {
    "zh": [(0x4E00, 0x9FFF), (0x3400, 0x4DBF), (0x20000, 0x2A6DF)],
}

LANG_SPECIFIC_CHARS = {
    "es": ["¿", "¡", "ñ", "Ñ", "á", "é", "í", "ó", "ú", "Á", "É", "Í", "Ó", "Ú", "ü", "Ü"],
    "fr": ["ç", "Ç", "é", "è", "ê", "ë", "à", "â", "î", "ô", "û", "ÿ", "œ", "Œ", "æ", "Æ"],
    "de": ["ä", "Ä", "ö", "Ö", "ü", "Ü", "ß"],
    "en": [],
}

LANG_INDICATORS = {
    "zh": ["的", "了", "是", "我", "你", "在", "和", "吗", "吧", "就", "那", "也", "要", "请", "您"],
    "en": ["the", "is", "are", "was", "were", "this", "that", "and", "you", "i", "we", "they", "please", "hello", "hi", "where", "what", "how", "when", "who"],
    "es": ["el", "la", "los", "las", "es", "son", "esta", "este", "por", "para", "hola", "gracias", "por favor", "pedido", "envío", "devolución", "dónde", "cómo", "qué", "mi"],
    "fr": ["le", "la", "les", "est", "sont", "cette", "cet", "pour", "par", "bonjour", "merci", "s'il vous plaît", "commande", "retour", "livraison", "comment", "quoi", "où"],
    "de": ["der", "die", "das", "ist", "sind", "dieser", "diese", "für", "von", "hallo", "danke", "bitte", "bestellung", "rückgabe", "lieferung", "wie", "was", "wo"],
}


CJK_LANGS = {"zh", "ja", "ko"}
RTL_LANGS = {"he"}


def detect_language(text: str, hint: str = None) -> Tuple[str, float]:
    """
    检测文本语言

    参数:
        text: 待检测文本
        hint: 用户提示的语言（优先考虑）

    返回:
        tuple: (language_code, confidence)
    """
    if not text or len(text.strip()) == 0:
        return (hint or "en", 0.5)

    text_lower = text.lower().strip()

    if hint and hint in LANG_INDICATORS:
        hint_match = _score_language(text_lower, hint)
        specific_match = _score_specific_chars(text, hint)
        unicode_match = _score_by_unicode(text, hint)
        combined_hint = hint_match * 0.4 + specific_match * 0.35 + unicode_match * 0.25
        if combined_hint >= 0.08 or hint_match > 0 or specific_match > 0:
            return (hint, min(0.6 + combined_hint * 0.5, 0.95))

    scores = {}

    for lang in LANG_INDICATORS:
        unicode_score = _score_by_unicode(text, lang)
        specific_score = _score_specific_chars(text, lang)
        indicator_score = _score_language(text_lower, lang)
        scores[lang] = unicode_score * 0.3 + specific_score * 0.4 + indicator_score * 0.3

    latin_langs_has_signal = any(
        scores.get(l, 0) >= 0.1
        for l in ["es", "fr", "de"]
    )
    if not latin_langs_has_signal:
        latin_chars = sum(1 for c in text if ord('a') <= ord(c.lower()) <= ord('z'))
        if latin_chars > len(text) * 0.5:
            scores["en"] = scores.get("en", 0) + 0.15

    best_lang = max(scores, key=scores.get)
    best_score = scores[best_lang]

    if best_score < 0.12:
        return ("en", 0.3)

    confidence = min(0.5 + best_score, 0.95)
    return (best_lang, confidence)


def _score_by_unicode(text: str, lang: str) -> float:
    ranges = UNICODE_RANGES.get(lang, [])
    if not ranges:
        return 0.0
    total_chars = len(text)
    if total_chars == 0:
        return 0.0
    count = 0
    for char in text:
        code = ord(char)
        for low, high in ranges:
            if low <= code <= high:
                count += 1
                break
    return count / total_chars


def _score_specific_chars(text: str, lang: str) -> float:
    specific_chars = LANG_SPECIFIC_CHARS.get(lang, [])
    if not specific_chars:
        return 0.0
    text_chars = set(text)
    matches = sum(1 for c in specific_chars if c in text_chars)
    if matches == 0:
        return 0.0
    return min(matches / 3, 1.0)


def _has_word_boundary_issues(lang: str) -> bool:
    return lang in CJK_LANGS or lang in RTL_LANGS


def _score_language(text: str, lang: str) -> float:
    indicators = LANG_INDICATORS.get(lang, [])
    if not indicators:
        return 0.0
    if _has_word_boundary_issues(lang):
        matches = sum(1 for indicator in indicators if indicator in text)
    else:
        matches = sum(1 for indicator in indicators if re.search(r'\b' + re.escape(indicator) + r'\b', text))
    return min(matches / max(len(indicators) * 0.2, 1), 1.0)


class IntentType(Enum):
    """
    意图类型枚举

    定义系统支持的所有用户意图类别
    """
    ORDER_QUERY = "order_query"
    SHIPPING_QUERY = "shipping_query"
    RETURN_POLICY = "return_policy"
    PRODUCT_SEARCH = "product_search"
    GENERAL_FAQ = "general_faq"
    COMPLAINT = "complaint"
    HUMAN_TRANSFER = "human_transfer"


class IntentRouter:
    """
    意图路由器类

    功能：
    - 基于关键词匹配识别用户意图
    - 支持多语言（中/英/西/法/德）
    - 判断是否需要转人工客服
    - 提供置信度评分
    """

    def __init__(self):
        self.intent_keywords = {

            IntentType.ORDER_QUERY: {
                'zh': ['订单', '订单号', '下单', '购买记录', '我的订单'],
                'en': ['order', 'order number', 'purchase history', 'my order'],
                'es': ['pedido', 'número de pedido', 'historial de compras'],
                'fr': ['commande', 'numéro de commande', 'historique d\'achats'],
                'de': ['bestellung', 'bestellnummer', 'kaufhistorie']
            },

            IntentType.SHIPPING_QUERY: {
                'zh': ['物流', '快递', '配送', '运输', '发货', '到货'],
                'en': ['shipping', 'delivery', 'tracking', 'logistics', 'shipment'],
                'es': ['envío', 'entrega', 'seguimiento', 'logística'],
                'fr': ['expédition', 'livraison', 'suivi', 'logistique'],
                'de': ['versand', 'lieferung', 'verfolgung', 'logistik']
            },

            IntentType.RETURN_POLICY: {
                'zh': ['退货', '退换', '退款', '换货', '售后'],
                'en': ['return', 'exchange', 'refund', 'after-sales'],
                'es': ['devolución', 'cambio', 'reembolso', 'postventa'],
                'fr': ['retour', 'échange', 'remboursement', 'après-vente'],
                'de': ['rückgabe', 'tausch', 'erstattung', 'kundendienst'],
            },

            IntentType.PRODUCT_SEARCH: {
                'zh': ['产品', '商品', '找', '搜索', '有没有', '推荐'],
                'en': ['product', 'item', 'search for', 'looking for', 'recommend'],
                'es': ['producto', 'artículo', 'buscar', 'recomendar'],
                'fr': ['produit', 'article', 'chercher', 'recommander'],
                'de': ['produkt', 'artikel', 'suchen', 'empfehlen'],
            },

            IntentType.GENERAL_FAQ: {
                'zh': ['支付', '付款', '信用卡', '支付宝', '微信', '尺码', '尺寸',
                       '价格', '多少钱', '费用', '发票', '优惠券', '折扣', '优惠',
                       '会员', '积分', '客服', '电话', '联系', '地址', '营业时间',
                       '包邮', '配送费', '税', '关税'],
                'en': ['payment', 'pay', 'credit card', 'size', 'price', 'how much',
                       'invoice', 'coupon', 'discount', 'deal', 'membership', 'points',
                       'customer service', 'phone', 'contact', 'address', 'hours',
                       'free shipping', 'shipping fee', 'tax', 'duty'],
                'es': ['pago', 'pagar', 'tarjeta', 'tamaño', 'precio', 'cuánto',
                       'factura', 'cupón', 'descuento', 'membresía', 'puntos',
                       'servicio al cliente', 'teléfono', 'contacto', 'dirección',
                       'horario', 'envío gratis', 'impuesto', 'aduana'],
                'fr': ['paiement', 'payer', 'carte bancaire', 'taille', 'prix',
                       'combien', 'facture', 'coupon', 'réduction', 'offre',
                       'adhésion', 'points', 'service client', 'téléphone', 'contact',
                       'adresse', 'heures', 'livraison gratuite', 'taxe', 'douane'],
                'de': ['zahlung', 'bezahlen', 'kreditkarte', 'größe', 'preis',
                       'wie viel', 'rechnung', 'gutschein', 'rabatt', 'angebot',
                       'mitgliedschaft', 'punkte', 'kundenservice', 'telefon', 'kontakt',
                       'adresse', 'öffnungszeiten', 'kostenloser versand', 'steuer', 'zoll']
            },

            IntentType.COMPLAINT: {
                'zh': ['投诉', '抱怨', '不满', '差评', '问题', '糟糕'],
                'en': ['complaint', 'dissatisfied', 'unhappy', 'terrible', 'issue'],
                'es': ['queja', 'insatisfecho', 'problema', 'terrible'],
                'fr': ['plainte', 'mécontent', 'problème', 'terrible'],
                'de': ['beschwerde', 'unzufrieden', 'problem', 'schrecklich']
            }
        }

    def detect_intent(self, query: str, language: str = 'zh') -> dict:
        query_lower = query.lower()

        PRIORITY_INTENTS = {IntentType.COMPLAINT, IntentType.HUMAN_TRANSFER}

        order_no_pattern = re.compile(r'(ORD[-–—]?\d{8}[-–—]?\d{3})', re.IGNORECASE)
        if order_no_pattern.search(query) or re.search(r'(?:订单|order)\s*(?:号|no|number)', query_lower):
            return {
                'intent': IntentType.ORDER_QUERY,
                'confidence': 0.85,
                'language': language,
                'should_transfer': False,
                'reason': None
            }

        best_intent = IntentType.GENERAL_FAQ
        best_confidence = 0.0

        for intent, lang_keywords in self.intent_keywords.items():
            keywords = lang_keywords.get(language, lang_keywords.get('zh', []))
            matches = sum(1 for keyword in keywords if keyword in query_lower)
            if matches > 0:
                confidence = min(0.9, 0.5 + (matches * 0.1))
                should_take = False
                if confidence > best_confidence:
                    should_take = True
                elif confidence == best_confidence and intent in PRIORITY_INTENTS and best_intent not in PRIORITY_INTENTS:
                    should_take = True
                if should_take:
                    best_intent = intent
                    best_confidence = confidence

        transfer_keywords = {
            'zh': ['转人工', '人工客服', '真人', '客服人员', '人工'],
            'en': ['human agent', 'speak to person', 'real person', 'transfer to human', 'human support'],
            'es': ['agente humano', 'hablar con persona', 'persona real', 'servicio humano'],
            'fr': ['agent humain', 'parler à une personne', 'vrai personne', 'service humain'],
            'de': ['menschlicher agent', 'mit person sprechen', 'echte person', 'menschenkundenservice']
        }
        transfer_words = transfer_keywords.get(language, transfer_keywords.get('zh', []))
        if any(word in query_lower for word in transfer_words):
            return {
                'intent': IntentType.HUMAN_TRANSFER,
                'confidence': 0.95,
                'language': language,
                'should_transfer': True,
                'reason': '用户明确要求转人工'
            }

        greeting_keywords = {
            'zh': ['你好', '您好', 'hi', 'hello', '在吗', '在不在', '早上好', '下午好', '晚上好'],
            'en': ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening'],
            'es': ['hola', 'buenos días', 'buenas tardes', 'buenas noches', 'saludos'],
            'fr': ['bonjour', 'salut', 'bonsoir', 'bon après-midi'],
            'de': ['hallo', 'guten morgen', 'guten tag', 'guten abend', 'hi'],
        }
        greeting_words = greeting_keywords.get(language, greeting_keywords.get('zh', []))
        if best_confidence == 0.0 and any(word in query_lower for word in greeting_words):
            best_confidence = 0.3
            return {
                'intent': IntentType.GENERAL_FAQ,
                'confidence': best_confidence,
                'language': language,
                'should_transfer': False,
                'reason': None
            }

        return {
            'intent': best_intent,
            'confidence': best_confidence,
            'language': language,
            'should_transfer': self._should_transfer_to_human(best_intent, best_confidence),
            'reason': self._get_transfer_reason(best_intent, best_confidence)
        }

    def _should_transfer_to_human(self, intent: IntentType, confidence: float) -> bool:
        if intent == IntentType.COMPLAINT:
            return True
        if confidence < 0.4:
            return True
        return False

    def _get_transfer_reason(self, intent: IntentType, confidence: float) -> Optional[str]:
        if intent == IntentType.COMPLAINT:
            return "检测到投诉意图，建议转人工处理"
        if confidence < 0.4:
            return f"系统置信度较低({confidence:.2f})，建议转人工确保准确性"
        return None

    def get_intent_response_template(self, intent: IntentType, language: str = 'zh') -> str:
        templates = {
            IntentType.ORDER_QUERY: {
                'zh': '正在为您查询订单信息...',
                'en': 'Looking up your order information...',
                'es': 'Buscando la información de tu pedido...',
                'fr': 'Recherche des informations de votre commande...',
                'de': 'Suche nach Ihren Bestellinformationen...',
            },
            IntentType.SHIPPING_QUERY: {
                'zh': '正在为您查询物流状态...',
                'en': 'Checking shipping status...',
                'es': 'Verificando el estado del envío...',
                'fr': 'Vérification du statut d\'expédition...',
                'de': 'Überprüfung des Versandstatus...',
            },
            IntentType.RETURN_POLICY: {
                'zh': '正在为您查找退换货政策...',
                'en': 'Finding return and exchange policies...',
                'es': 'Buscando políticas de devolución y cambio...',
                'fr': 'Recherche des politiques de retour et échange...',
                'de': 'Suche nach Rückgabe- und Umtauschrichtlinien...',
            },
            IntentType.PRODUCT_SEARCH: {
                'zh': '正在为您搜索相关商品...',
                'en': 'Searching for related products...',
                'es': 'Buscando productos relacionados...',
                'fr': 'Recherche de produits connexes...',
                'de': 'Suche nach verwandten Produkten...',
            },
            IntentType.GENERAL_FAQ: {
                'zh': '正在为您查找相关信息...',
                'en': 'Finding relevant information...',
                'es': 'Buscando información relevante...',
                'fr': 'Recherche des informations pertinentes...',
                'de': 'Suche nach relevanten Informationen...',
            },
            IntentType.COMPLAINT: {
                'zh': '非常抱歉给您带来不便，我们非常重视您的反馈...',
                'en': 'We sincerely apologize for the inconvenience. We value your feedback...',
                'es': 'Lamentamos mucho las molestias. Valoramos tu opinión...',
                'fr': 'Nous nous excusons pour le désagrément. Nous apprécions votre retour...',
                'de': 'Wir entschuldigen uns für die Unannehmlichkeiten. Wir schätzen Ihr Feedback...',
            },
            IntentType.HUMAN_TRANSFER: {
                'zh': '正在为您转接人工客服...',
                'en': 'Transferring you to a human agent...',
                'es': 'Transfiriéndote a un agente humano...',
                'fr': 'Vous êtes transféré vers un agent humain...',
                'de': 'Weiterleitung zu einem menschlichen Agenten...',
            }
        }
        intent_templates = templates.get(intent, {})
        return intent_templates.get(language, intent_templates.get('zh', '正在处理您的请求...'))