"""
RAG检索增强生成核心模块
实现完整的检索→上下文构建→LLM生成的Pipeline
"""

import time
from typing import List, Dict, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from openai import OpenAI
from app.config import settings
from app.rag.vector_store import VectorStore
from app.rag.embedding import embedding_service


class RAGRetriever:
    """
    RAG检索器（核心类）
    
    Pipeline流程：
    用户查询 → 意图识别 → 向量检索 → 上下文构建 → LLM生成回复
    
    特点：
    - 单次LLM调用（保证响应时间<6s）
    - 多源信息融合（商品/FAQ/订单）
    - 支持多轮对话上下文
    """

    def __init__(self, db: AsyncSession):
        """
        初始化RAG检索器

        参数:
            db: 数据库会话
        """
        self.db = db
        self.vector_store = VectorStore(db)  # 向量存储实例

        # 根据配置选择LLM客户端
        if settings.use_local_llm:
            print(f"🔧 使用本地LLM: {settings.local_llm_model} @ {settings.local_llm_url}")
            self.llm_client = OpenAI(
                base_url=settings.local_llm_url,
                api_key="ollama"  # Ollama不需要真实API Key
            )
            self.model_name = settings.local_llm_model
        else:
            print(f"☁️ 使用OpenAI API: {settings.openai_model}")
            self.llm_client = OpenAI(api_key=settings.openai_api_key)
            self.model_name = settings.openai_model

    async def retrieve_and_generate(
        self,
        user_query: str,
        language: str = 'zh',
        conversation_history: List[Dict] = None
    ) -> Dict:
        """
        RAG主Pipeline（对外接口）
        
        功能：完整的4步处理流程包括意图识别、上下文检索、Prompt构建、回复生成
        
        参数:
            user_query: 用户输入的问题
            language: 目标回复语言（默认中文）
            conversation_history: 历史对话记录（用于多轮对话）
            
        返回:
            dict: 包含AI回复文本、使用的参考上下文、检测到的意图类型、置信度分数、
                  实际使用语言、处理耗时(毫秒)、是否成功等信息
        """
        start_time = time.time()  # 记录开始时间（用于计算耗时）
        
        try:
            # ===== Step 1: 意图识别 =====
            intent_result = await self._detect_intent(user_query)
            intent = intent_result.get('intent', 'general')
            
            # ===== Step 2: RAG上下文检索 =====
            context = await self._retrieve_context(user_query, intent, language)
            
            # ===== Step 3: 构建Prompt =====
            prompt = self._build_prompt(user_query, context, language, conversation_history)
            
            # ===== Step 4: LLM生成回复 =====
            response = await self._generate_response(prompt, language)
            
            # 计算总耗时
            processing_time = int((time.time() - start_time) * 1000)  # 转换为毫秒
            
            return {
                "response": response,
                "context_used": context,
                "intent_detected": intent,
                "confidence_score": context.get('max_similarity', 0.8),
                "language": language,
                "processing_time_ms": processing_time,
                "success": True
            }
            
        except Exception as e:
            print(f"Error in RAG pipeline: {e}")
            processing_time = int((time.time() - start_time) * 1000)

            fallback_msgs = {
                'zh': "抱歉，我暂时无法回答您的问题。请稍后重试或联系人工客服。",
                'en': "Sorry, I cannot answer your question right now. Please try again later or contact human support.",
                'es': "Lo siento, no puedo responder a tu pregunta en este momento. Por favor, inténtalo de nuevo más tarde o contacta soporte humano.",
                'fr': "Désolé, je ne peux pas répondre à votre question pour le moment. Veuillez réessayer plus tard ou contacter l'assistance humaine.",
                'de': "Entschuldigung, ich kann Ihre Frage derzeit nicht beantworten. Bitte versuchen Sie es später erneut oder wenden Sie sich an den menschlichen Support.",
            }

            return {
                "response": fallback_msgs.get(language, fallback_msgs['zh']),
                "context_used": {},
                "intent_detected": "error",
                "confidence_score": 0.0,
                "language": language,
                "processing_time_ms": processing_time,
                "success": False,
                "error": str(e)
            }

    async def _detect_intent(self, query: str) -> Dict:
        """
        意图识别（基于关键词规则匹配）
        
        判断用户问题的类型，决定后续检索策略
        
        参数:
            query: 用户输入文本
            
        返回:
            dict: {"intent": 意图类型, "confidence": 置信度}
            
        支持的意图：
        - order_query: 订单查询
        - shipping_query: 物流查询
        - return_policy: 退货政策咨询
        - product_search: 商品搜索
        - general_faq: 通用问题
        """
        query_lower = query.lower()
        
        # 关键词匹配（支持多语言）
        if any(word in query_lower for word in ['订单', 'order', 'commande', 'pedido', 'bestellung']):
            return {'intent': 'order_query', 'confidence': 0.9}
        
        elif any(word in query_lower for word in ['物流', 'tracking', 'suivi', 'seguimiento', 'verfolgung']):
            return {'intent': 'shipping_query', 'confidence': 0.9}
        
        elif any(word in query_lower for word in ['退货', 'return', 'retour', 'devolución', 'rückgabe']):
            return {'intent': 'return_policy', 'confidence': 0.85}
        
        elif any(word in query_lower for word in ['产品', '商品', 'product', 'produit', 'producto', 'produkt']):
            return {'intent': 'product_search', 'confidence': 0.85}
        
        else:
            return {'intent': 'general_faq', 'confidence': 0.7}  # 默认：通用问题

    async def _retrieve_context(
        self,
        query: str,
        intent: str,
        language: str
    ) -> Dict:
        """
        根据意图检索相关上下文
        
        从多个数据源获取与用户问题相关的信息
        
        参数:
            query: 原始查询文本
            intent: 检测到的意图类型
            language: 语言
            
        返回:
            dict: {
                "products": [...],     # 相关商品列表
                "faqs": [...],         # FAQ条目列表
                "orders": [...],       # 订单信息（如有）
                "max_similarity": 0.92 # 最高相似度（用于置信度评估）
            }
        """
        context = {
            'products': [],
            'faqs': [],
            'orders': [],
            'max_similarity': 0.0
        }
        
        # 商品相关查询：搜索商品向量库
        if intent in ['product_search', 'general_faq', 'general']:
            products = await self.vector_store.search_products(
                query=query,
                top_k=3,              # 返回最相关的3个商品
                language=language
            )
            context['products'] = products
            
            # 更新最高相似度
            if products:
                context['max_similarity'] = max(
                    context['max_similarity'],
                    max(p['similarity_score'] for p in products)
                )
        
        # 所有查询都搜索FAQ知识库
        faqs = await self.vector_store.search_faq(
            query=query,
            top_k=2,              # 返回最相关的2条FAQ
            language=language
        )
        context['faqs'] = faqs
        
        # 更新最高相似度
        if faqs:
            context['max_similarity'] = max(
                context['max_similarity'],
                max(f['similarity_score'] for f in faqs)
            )
        
        # 订单查询：提取订单号并查询详情
        if intent == 'order_query':
            order_info = await self._extract_order_info(query)
            if order_info:
                context['orders'].append(order_info)
        
        return context

    async def _extract_order_info(self, query: str) -> Optional[Dict]:
        """
        从查询中提取订单号并获取订单详情
        
        参数:
            query: 包含订单号的用户输入
            
        返回:
            订单字典（未找到返回None）
        """
        import re
        
        # 定义多种订单号格式模式
        order_patterns = [
            r'订单\s*[:：]?\s*(\w+)',           # 中文："订单：ORD-001"
            r'order\s*[:#]?\s*(\w+)',           # 英文："order #123"
            r'(\d{10,})'                        # 长数字（假设是订单号）
        ]
        
        # 依次尝试每种模式
        for pattern in order_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                order_no = match.group(1)  # 提取捕获组
                order = await self.vector_store.get_order_by_no(order_no)
                if order:
                    return order
        
        return None  # 未找到有效订单号

    def _build_prompt(
        self,
        user_query: str,
        context: Dict,
        language: str,
        conversation_history: List[Dict] = None
    ) -> str:
        """
        构建LLM的完整Prompt（系统指令+上下文+历史+问题）
        
        Prompt结构：
        ┌─────────────────────────────┐
        │ [系统角色定义]               │
        ├─────────────────────────────┤
        │ [参考信息：商品/FAQ/订单]    │
        ├─────────────────────────────┤
        │ [对话历史（最近5轮）]        │
        ├─────────────────────────────┤
        │ [用户当前问题]              │
        ├─────────────────────────────┤
        │ [要求AI生成回复]            │
        └─────────────────────────────┘
        
        参数:
            user_query: 用户问题
            context: RAG检索到的上下文
            language: 目标语言
            conversation_history: 对话历史
            
        返回:
            str: 完整的prompt字符串
        """
        
        system_prompts = {
            'zh': '你是一个专业的跨境电商中文客服助手。请根据以下参考信息，用中文回答用户的问题。要求：回答准确、专业、友好；优先使用参考信息；如无匹配信息，基于知识给出合理建议；保持简洁，避免冗长。',
            'en': 'You are a professional cross-border e-commerce English customer service assistant. Answer the user question in English based on the reference information below. Requirements: be accurate, professional and friendly; prioritize reference information; if no match found, give reasonable suggestions based on knowledge; keep it concise.',
            'es': 'Eres un asistente profesional de servicio al cliente de comercio electrónico transfronterizo en español. Responde a la pregunta del usuario en español según la información de referencia. Requisitos: preciso, profesional y amigable; prioriza la información de referencia; si no hay coincidencia, da sugerencias razonables; manténlo conciso.',
            'fr': "Vous êtes un assistant professionnel du service client e-commerce transfrontalier en français. Répondez à la question en français selon les informations de référence. Exigences: précis, professionnel et aimable; priorisez les informations de référence; sinon, donnez des suggestions raisonnables; restez concis.",
            'de': 'Sie sind ein professioneller Kundendienstassistent für grenzüberschreitenden E-Commerce auf Deutsch. Beantworten Sie die Frage auf Deutsch basierend auf den Referenzinformationen. Anforderungen: genau, professionell und freundlich; priorisieren Sie Referenzinformationen; sonst geben Sie vernünftige Vorschläge; halten Sie es präzise.',
        }
        
        system_prompt = system_prompts.get(language, system_prompts['en'])
        
        context_text = "\n\n【参考信息】\n"
        
        context_prefixes = {
            'zh': '\n相关商品信息：\n',
            'en': '\nRelated product information:\n',
            'es': '\nInformación de productos relacionados:\n',
            'fr': '\nInformations produit associées:\n',
            'de': '\nVerwandte Produktinformationen:\n',
        }
        
        faq_prefixes = {
            'zh': '\n常见问题解答：\n',
            'en': '\nFAQ entries:\n',
            'es': '\nPreguntas frecuentes:\n',
            'fr': '\nQuestions fréquentes:\n',
            'de': '\nFAQ-Einträge:\n',
        }
        
        order_prefixes = {
            'zh': '\n订单信息：\n',
            'en': '\nOrder information:\n',
            'es': '\nInformación del pedido:\n',
            'fr': '\nInformations de commande:\n',
            'de': '\nBestellinformationen:\n',
        }
        
        prefix = context_prefixes.get(language, context_prefixes['en'])
        faq_pfx = faq_prefixes.get(language, faq_prefixes['en'])
        order_pfx = order_prefixes.get(language, order_prefixes['en'])
        
        if context.get('products'):
            context_text += prefix
            for i, product in enumerate(context['products'], 1):
                context_text += f"{i}. {product['name']} - ¥{product['price']} (similarity: {product['similarity_score']:.2f})\n"
                if product.get('description'):
                    context_text += f"   Desc: {product['description'][:200]}...\n"
        
        if context.get('faqs'):
            context_text += faq_pfx
            for i, faq in enumerate(context['faqs'], 1):
                context_text += f"{i}. Q: {faq['question']}\n   A: {faq['answer']}\n"
        
        if context.get('orders'):
            context_text += order_pfx
            order = context['orders'][0]
            context_text += f"Order No: {order['order_no']}\n"
            context_text += f"Status: {order['status']}\n"
            context_text += f"Total: {order['total_amount']} {order['currency']}\n"
        
        history_text = ""
        if conversation_history:
            history_text = "\n\n【对话历史】\n"
            for msg in conversation_history[-5:]:
                role = "用户" if msg.get('role') == 'user' else "助手"
                history_text += f"{role}: {msg.get('content', '')}\n"
        
        question_labels = {
            'zh': '\n\n【用户问题】\n',
            'en': '\n\n【User Question】\n',
            'es': '\n\n【Pregunta del usuario】\n',
            'fr': '\n\n【Question de l\'utilisateur】\n',
            'de': '\n\n【Benutzerfrage】\n',
        }
        
        reply_labels = {
            'zh': '\n\n【回复】',
            'en': '\n\n【Reply】',
            'es': '\n\n【Respuesta】',
            'fr': '\n\n【Réponse】',
            'de': '\n\n【Antwort】',
        }
        
        q_label = question_labels.get(language, question_labels['en'])
        r_label = reply_labels.get(language, reply_labels['en'])
        
        full_prompt = (
            f"{system_prompt}"
            f"{context_text}"
            f"{history_text}"
            f"{q_label}{user_query}"
            f"{r_label}"
        )
        
        return full_prompt

    async def _generate_response(self, prompt: str, language: str) -> str:
        """
        调用LLM生成最终回复（支持快速模式）

        参数:
            prompt: 构建好的完整prompt
            language: 目标语言

        返回:
            str: 生成的回复文本（失败时返回兜底话术）
        """
        # 快速模式：不调用LLM，直接返回基于规则的回复
        if getattr(settings, 'use_fast_mode', False):
            print("⚡ 使用快速模式（跳过LLM调用）")
            return await self._fast_mode_response(prompt, language)

        try:
            print(f"🤖 调用LLM生成回复: {self.model_name}")
            response = self.llm_client.chat.completions.create(
                model=self.model_name,  # 使用配置的模型（本地或云端）
                messages=[
                    {"role": "system", "content": f"You are a helpful multilingual customer service assistant. Respond in {language}."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,    # 创造性（0-1，越高越随机）
                max_tokens=1000     # 最大输出长度（控制成本和延迟）
            )

            result = response.choices[0].message.content  # 提取回复文本
            print(f"✅ LLM回复成功: {len(result)}字符")
            return result

        except Exception as e:
            print(f"❌ LLM调用失败: {e}")
            # LLM失败时自动降级到快速模式
            print("⚠️ 自动降级到快速模式")
            return await self._fast_mode_response(prompt, language)

    async def _fast_mode_response(self, prompt: str, language: str) -> str:
        """
        快速模式：基于规则/模板生成回复（不依赖LLM）

        优点：
        - 响应速度极快（<100ms）
        - 100%可靠性（不会超时或返回空）
        - 基于专业FAQ知识库

        参数:
            prompt: 包含上下文的prompt
            language: 目标语言

        返回:
            str: 基于规则生成的回复
        """
        import re

        # 从prompt中提取用户问题（最后一行通常是问题）
        lines = prompt.strip().split('\n')
        user_question = lines[-1] if lines else ""

        # 使用模拟数据服务搜索相关FAQ
        faqs = MockDataService.search_faqs(user_question, language, top_k=2)

        if faqs:
            # 找到匹配的FAQ，直接返回最佳答案
            best_faq = faqs[0]
            print(f"📚 FAQ命中: {best_faq['question'][:30]}... (相关性: {best_faq['relevance_score']:.2f})")

            # 根据语言构建友好回复
            greetings = {
                'zh': '您好！',
                'en': 'Hello! ',
                'es': '¡Hola! ',
                'fr': 'Bonjour! ',
                'de': 'Guten Tag! '
            }
            greeting = greetings.get(language, '您好！')

            return f"{greeting}{best_faq['answer']}"

        # 如果没有找到FAQ，使用通用回复
        print("⚠️ 未找到匹配FAQ，使用通用回复")

        default_responses = {
            'zh': """您好！感谢您的咨询。

关于您的问题，我建议您：
1. 登录账户查看详细订单信息
2. 或提供订单号给我，我可以帮您查询
3. 也可以拨打客服热线：400-123-4567（9:00-22:00）

还有什么我可以帮助您的吗？""",

            'en': """Hello! Thank you for your inquiry.

Regarding your question, I suggest you:
1. Log in to your account to view detailed order information
2. Or provide your order number and I can help you check
3. You can also call our hotline: 400-123-4567 (9AM-10PM)

Is there anything else I can help you with?""",

            'es': """¡Hola! Gracias por su consulta.

Respecto a su pregunta, le sugiero:
1. Inicie sesión en su cuenta para ver información detallada del pedido
2. O proporcione su número de pedido y puedo ayudarle a verificarlo
3. También puede llamar a nuestra línea directa: 400-123-4567 (9AM-10PM)

¿Hay algo más en lo que pueda ayudarle?""",

            'fr': """Bonjour ! Merci pour votre demande.

Concernant votre question, je vous suggère :
1. Connectez-vous à votre compte pour voir les informations détaillées de la commande
2. Ou fournissez votre numéro de commande et je peux vous aider à vérifier
3. Vous pouvez également appeler notre ligne directe : 400-123-4567 (9h-22h)

Y a-t-il autre chose que je puisse faire pour vous ?""",

            'de': """Hallo! Danke für Ihre Anfrage.

Bezüglich Ihrer Frage schlage ich vor:
1. Melden Sie sich an, um detaillierte Bestellungsinformationen anzuzeigen
2. Oder geben Sie Ihre Bestellnummer an und ich kann Ihnen helfen zu überprüfen
3. Sie können auch unsere Hotline anrufen: 400-123-4567 (9-22 Uhr)

Kann ich Ihnen sonst noch behilflich sein?"""
        }

        return default_responses.get(language, default_responses['zh'])

    async def get_product_recommendations(self, category: str = None, limit: int = 5) -> List[Dict]:
        """
        获取商品推荐（用于通用浏览场景）
        
        参数:
            category: 商品分类（如"运动鞋"/None表示全部）
            limit: 推荐数量上限
            
        返回:
            商品字典列表
        """
        # 构造推荐查询词
        query = f"推荐{category}" if category else "热门商品推荐"
        
        # 执行语义搜索
        products = await self.vector_store.search_products(
            query=query,
            top_k=limit
        )
        
        return products