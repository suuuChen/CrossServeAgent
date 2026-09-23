"""
多语言客服Agent引擎
整合: 客服编排 + 转人工会话管理 + 订单查询
"""

from typing import Tuple, Optional, List, Dict
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
import re

from app.services.timezone_service import TimezoneService
from app.services.nlu import IntentRouter, IntentType, detect_language
from app.config import settings
from app.rag.retriever import RAGRetriever
from app.services.compliance import ComplianceService, AuditLogger
from app.models.order import Order, OrderItem, Shipment


class CustomerServiceAgent:
    """客服Agent类（对外统一接口）"""

    _sessions: Dict[str, Dict] = {}

    def __init__(self, db: AsyncSession):
        self.db = db
        self.rag_retriever = RAGRetriever(db)
        self.intent_router = IntentRouter()
        self.compliance = ComplianceService()
        self.audit = AuditLogger()

    async def process_message(
        self,
        user_query: str,
        session_id: str = None,
        language: str = 'zh'
    ) -> Dict:
        start_time = datetime.now()

        if not session_id:
            session_id = str(uuid.uuid4())

        session = await self._get_or_create_session(session_id)

        detected_lang = language
        if settings.auto_detect_language:
            hint_lang = session.get('language_detected') or language
            detected, conf = detect_language(user_query, hint=hint_lang)

            is_short_query = len(user_query.strip()) <= 30
            has_order_no = bool(re.search(r'(ORD[-–—]?\d{8}[-–—]?\d{3})', user_query, re.IGNORECASE))
            if (is_short_query or has_order_no) and session.get('language_detected'):
                detected_lang = session['language_detected']
            else:
                detected_lang = detected
                session['language_detected'] = detected_lang

        try:
            compliance_result = self.compliance.check(user_query, language=detected_lang)
            if compliance_result["blocked"]:
                processing_time = (datetime.now() - start_time).total_seconds() * 1000

                await AuditLogger.log_event(
                    db=self.db,
                    event_type="compliance_blocked",
                    session_id=session_id,
                    user_query=user_query,
                    intent=None,
                    language=detected_lang,
                    compliance_blocked=True,
                    compliance_reason=str(compliance_result.get("categories", [])),
                    processing_time_ms=int(processing_time)
                )

                return self._build_compliance_block_response(
                    session_id, user_query, detected_lang, compliance_result, start_time
                )

            intent_result = self.intent_router.detect_intent(user_query, detected_lang)

            if intent_result['intent'] == IntentType.ORDER_QUERY:
                print(f"[Agent] Handling ORDER_QUERY intent for: {user_query[:50]}")
                order_result = await self._handle_order_query(
                    session_id, user_query, intent_result, detected_lang, start_time
                )

                await AuditLogger.log_event(
                    db=self.db,
                    event_type="chat",
                    session_id=session_id,
                    user_query=user_query,
                    response=order_result.get('response'),
                    intent=intent_result['intent'].value,
                    language=detected_lang,
                    confidence=intent_result['confidence'],
                    should_transfer=False,
                    compliance_blocked=False,
                    processing_time_ms=order_result.get('processing_time_ms')
                )
                return order_result

            if intent_result['should_transfer']:
                result = await self._handle_human_transfer(
                    session_id, user_query, intent_result, detected_lang, start_time
                )

                await AuditLogger.log_event(
                    db=self.db,
                    event_type="human_transfer",
                    session_id=session_id,
                    user_query=user_query,
                    response=result.get('response'),
                    intent=intent_result['intent'].value,
                    language=detected_lang,
                    confidence=intent_result['confidence'],
                    should_transfer=True,
                    transfer_reason=intent_result.get('reason'),
                    processing_time_ms=result.get('processing_time_ms')
                )
                return result

            rag_result = await self.rag_retriever.retrieve_and_generate(
                user_query=user_query,
                language=detected_lang,
                conversation_history=session.get('history', [])
            )

            await self._update_session_history(
                session_id, user_query, rag_result['response']
            )

            processing_time = (datetime.now() - start_time).total_seconds() * 1000

            result = {
                'session_id': session_id,
                'response': TimezoneService.append_timezone_promise(
                    rag_result['response'], detected_lang
                ),
                'intent': intent_result['intent'].value,
                'confidence': intent_result['confidence'],
                'rag_confidence': rag_result.get('confidence_score', 0),
                'language': detected_lang,
                'should_transfer': False,
                'processing_time_ms': int(processing_time),
                'context_used': {
                    'products_found': len(rag_result.get('context_used', {}).get('products', [])),
                    'faqs_found': len(rag_result.get('context_used', {}).get('faqs', []))
                },
                'success': rag_result.get('success', True)
            }

            await AuditLogger.log_event(
                db=self.db,
                event_type="chat",
                session_id=session_id,
                user_query=user_query,
                response=rag_result.get('response'),
                intent=intent_result['intent'].value,
                language=detected_lang,
                confidence=intent_result['confidence'],
                should_transfer=False,
                compliance_blocked=False,
                processing_time_ms=int(processing_time)
            )

            return result

        except Exception as e:
            print(f"Error processing message: {e}")
            processing_time = (datetime.now() - start_time).total_seconds() * 1000

            err_msgs = {
                'zh': '抱歉，系统出现错误。请稍后重试或联系人工客服。',
                'en': 'Sorry, a system error occurred. Please try again later or contact human support.',
                'es': 'Lo siento, ocurrió un error del sistema. Por favor, inténtalo de nuevo más tarde o contacta soporte humano.',
                'fr': "Désolé, une erreur système est survenue. Veuillez réessayer plus tard ou contacter l'assistance humaine.",
                'de': 'Entschuldigung, ein Systemfehler ist aufgetreten. Bitte versuchen Sie es später erneut oder wenden Sie sich an den menschlichen Support.',
            }

            return {
                'session_id': session_id,
                'response': err_msgs.get(detected_lang, err_msgs['zh']),
                'intent': 'error',
                'confidence': 0.0,
                'rag_confidence': 0.0,
                'language': detected_lang,
                'should_transfer': True,
                'processing_time_ms': int(processing_time),
                'context_used': {'products_found': 0, 'faqs_found': 0},
                'error': str(e),
                'success': False
            }

    def _build_compliance_block_response(
        self, session_id, user_query, language, compliance_result, start_time
    ) -> Dict:
        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        block_msgs = {
            'zh': '抱歉，您的消息包含违规内容，无法处理。如有疑问，请联系人工客服。',
            'en': 'Sorry, your message contains prohibited content and cannot be processed. Please contact human support if you have questions.',
            'es': 'Lo siento, tu mensaje contiene contenido prohibido y no puede ser procesado. Por favor, contacta soporte humano si tienes preguntas.',
            'fr': "Désolé, votre message contient du contenu interdit et ne peut pas être traité. Veuillez contacter l'assistance humaine si vous avez des questions.",
            'de': 'Entschuldigung, Ihre Nachricht enthält verbotene Inhalte und kann nicht verarbeitet werden. Bitte wenden Sie sich an den menschlichen Support, wenn Sie Fragen haben.',
        }

        categories_str = ', '.join(
            f"{c.get('category', 'unknown')}(severity={c.get('severity', '?')}, matched='{c.get('matched', '')}')"
            for c in compliance_result.get('categories', [])
        )

        return {
            'session_id': session_id,
            'response': block_msgs.get(language, block_msgs['zh']),
            'intent': 'compliance_blocked',
            'confidence': 1.0,
            'rag_confidence': 0.0,
            'language': language,
            'should_transfer': True,
            'processing_time_ms': int(processing_time),
            'context_used': {'products_found': 0, 'faqs_found': 0},
            'compliance_blocked': True,
            'compliance_details': {
                'check_method': compliance_result.get('check_method', 'regex'),
                'total_matches': compliance_result.get('total_matches', 0),
                'categories': compliance_result.get('categories', []),
                'description': categories_str
            },
            'success': False
        }

    async def _handle_order_query(
        self,
        session_id: str,
        user_query: str,
        intent_result: Dict,
        language: str,
        start_time: datetime
    ) -> Dict:
        """
        处理订单查询请求

        从用户消息中提取订单号，查询数据库并生成结构化回复
        """
        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        order_no = self._extract_order_no(user_query)

        if not order_no:
            return {
                'session_id': session_id,
                'response': TimezoneService.append_timezone_promise(
                    self._get_order_not_found_response(language, need_order_no=True), language
                ),
                'intent': IntentType.ORDER_QUERY.value,
                'confidence': intent_result['confidence'],
                'rag_confidence': 0.0,
                'language': language,
                'should_transfer': False,
                'processing_time_ms': int(processing_time),
                'context_used': {'products_found': 0, 'faqs_found': 0, 'orders_found': 0},
                'success': True
            }

        order_data = await self._query_order_from_db(order_no)

        if not order_data:
            return {
                'session_id': session_id,
                'response': TimezoneService.append_timezone_promise(
                    self._get_order_not_found_response(language, order_no=order_no), language
                ),
                'intent': IntentType.ORDER_QUERY.value,
                'confidence': intent_result['confidence'],
                'rag_confidence': 0.0,
                'language': language,
                'should_transfer': False,
                'processing_time_ms': int(processing_time),
                'context_used': {'products_found': 0, 'faqs_found': 0, 'orders_found': 0},
                'success': True
            }

        response_text = self._format_order_response(order_data, language)

        await self._update_session_history(session_id, user_query, response_text)

        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        return {
            'session_id': session_id,
            'response': TimezoneService.append_timezone_promise(response_text, language),
            'intent': IntentType.ORDER_QUERY.value,
            'confidence': intent_result['confidence'],
            'rag_confidence': 1.0,
            'language': language,
            'should_transfer': False,
            'processing_time_ms': int(processing_time),
            'context_used': {
                'products_found': 0,
                'faqs_found': 0,
                'orders_found': 1
            },
            'success': True
        }

    def _extract_order_no(self, text: str) -> Optional[str]:
        """
        从用户消息中提取订单号

        支持格式：
        - ORD-20240101-001（标准格式）
        - ord-20240101-001（大小写不敏感）
        - 纯数字订单号
        """
        patterns = [
            r'(ORD[-–—]?\d{8}[-–—]?\d{3})',
            r'(?:订单号?|order\s*(?:no|number)?[:：]?\s*)([A-Z]{2,}[-–—]?\d+)',
            r'(\d{10,})'
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).upper().replace('–', '-').replace('—', '-')

        return None

    async def _query_order_from_db(self, order_no: str) -> Optional[Dict]:
        """
        从数据库查询订单信息（包含订单项和物流信息）
        """
        try:
            print(f"[Order Query] Searching for order: {order_no}")
            result = await self.db.execute(
                select(Order).where(Order.order_no == order_no)
            )
            order = result.scalar_one_or_none()

            if not order:
                print(f"[Order Query] Order {order_no} not found in database")
                return None

            print(f"[Order Query] Found order: {order.order_no} (ID: {order.id})")

            items_result = await self.db.execute(
                select(OrderItem).where(OrderItem.order_id == order.id)
            )
            items = items_result.scalars().all()

            shipment_result = await self.db.execute(
                select(Shipment).where(Shipment.order_id == order.order_no)
            )
            shipment = shipment_result.scalar_one_or_none()

            return {
                'order_no': order.order_no,
                'customer_name': order.customer_name,
                'status': order.status,
                'total_amount': float(order.total_amount) if order.total_amount else None,
                'currency': order.currency or 'CNY',
                'created_at': order.created_at.isoformat() if order.created_at else None,
                'items': [
                    {
                        'product_name': item.product_name,
                        'product_sku': item.product_sku,
                        'quantity': item.quantity,
                        'unit_price': float(item.unit_price) if item.unit_price else None
                    }
                    for item in items
                ],
                'shipment': {
                    'tracking_number': shipment.tracking_number,
                    'carrier': shipment.carrier,
                    'status': shipment.status,
                    'estimated_delivery': shipment.estimated_delivery.isoformat() if shipment and shipment.estimated_delivery else None
                } if shipment else None
            }

        except Exception as e:
            print(f"Error querying order {order_no}: {e}")
            return None

    def _format_order_response(self, order_data: Dict, language: str) -> str:
        """
        格式化订单信息为用户友好的多语言回复
        """
        status_map = {
            'zh': {'pending': '待处理', 'paid': '已支付', 'shipped': '已发货', 'delivered': '已送达', 'cancelled': '已取消'},
            'en': {'pending': 'Pending', 'paid': 'Paid', 'shipped': 'Shipped', 'delivered': 'Delivered', 'cancelled': 'Cancelled'},
            'es': {'pending': 'Pendiente', 'paid': 'Pagado', 'shipped': 'Enviado', 'delivered': 'Entregado', 'cancelado': 'Cancelado'},
            'fr': {'pending': 'En attente', 'payé': 'Payé', 'expédié': 'Expédié', 'livré': 'Livré', 'annulé': 'Annulé'},
            'de': {'pending': 'Ausstehend', 'bezahlt': 'Bezahlt', 'versandet': 'Versendet', 'geliefert': 'Geliefert', 'storniert': 'Storniert'}
        }

        status_texts = status_map.get(language, status_map['zh'])
        status_text = status_texts.get(order_data['status'], order_data['status'])

        if language == 'zh':
            response = f"找到您的订单信息：\n\n"
            response += f"订单号：{order_data['order_no']}\n"
            response += f"客户：{order_data['customer_name']}\n"
            response += f"状态：{status_text}\n"
            response += f"金额：¥{order_data['total_amount']:.2f}\n"
            response += f"下单时间：{order_data['created_at'][:10]}\n\n"

            if order_data['items']:
                response += "商品清单：\n"
                for idx, item in enumerate(order_data['items'], 1):
                    response += f"  {idx}. {item['product_name']} x{item['quantity']} (¥{item['unit_price']:.2f})\n"

            if order_data.get('shipment'):
                ship = order_data['shipment']
                response += f"\n物流信息：\n"
                response += f"   快递公司：{ship['carrier']}\n"
                response += f"   运单号：{ship['tracking_number']}\n"
                if ship.get('estimated_delivery'):
                    response += f"   预计送达：{ship['estimated_delivery'][:10]}\n"

            response += "\n如需帮助，请随时告诉我！"

        elif language == 'en':
            response = f"Order Found:\n\n"
            response += f"Order No: {order_data['order_no']}\n"
            response += f"Customer: {order_data['customer_name']}\n"
            response += f"Status: {status_text}\n"
            response += f"Amount: ${order_data['total_amount']:.2f}\n"
            response += f"Order Date: {order_data['created_at'][:10]}\n\n"

            if order_data['items']:
                response += "Items:\n"
                for idx, item in enumerate(order_data['items'], 1):
                    response += f"  {idx}. {item['product_name']} x{item['quantity']} (${item['unit_price']:.2f})\n"

            if order_data.get('shipment'):
                ship = order_data['shipment']
                response += f"\nShipping Info:\n"
                response += f"   Carrier: {ship['carrier']}\n"
                response += f"   Tracking No: {ship['tracking_number']}\n"
                if ship.get('estimated_delivery'):
                    response += f"   Est. Delivery: {ship['estimated_delivery'][:10]}\n"

            response += "\nLet me know if you need any help!"

        elif language == 'es':
            response = f"Pedido Encontrado:\n\n"
            response += f"Número de pedido: {order_data['order_no']}\n"
            response += f"Cliente: {order_data['customer_name']}\n"
            response += f"Estado: {status_text}\n"
            response += f"Monto: ${order_data['total_amount']:.2f}\n"
            response += f"Fecha del pedido: {order_data['created_at'][:10]}\n\n"

            if order_data['items']:
                response += "Artículos:\n"
                for idx, item in enumerate(order_data['items'], 1):
                    response += f"  {idx}. {item['product_name']} x{item['quantity']} (${item['unit_price']:.2f})\n"

            if order_data.get('shipment'):
                ship = order_data['shipment']
                response += f"\nInformación de envío:\n"
                response += f"   Transportista: {ship['carrier']}\n"
                response += f"   Número de seguimiento: {ship['tracking_number']}\n"
                if ship.get('estimated_delivery'):
                    response += f"   Entrega estimada: {ship['estimated_delivery'][:10]}\n"

            response += "\n¡Avísame si necesitas ayuda!"

        elif language == 'fr':
            response = f"Commande Trouvée:\n\n"
            response += f"Numéro de commande: {order_data['order_no']}\n"
            response += f"Client: {order_data['customer_name']}\n"
            response += f"Statut: {status_text}\n"
            response += f"Montant: ${order_data['total_amount']:.2f}\n"
            response += f"Date de commande: {order_data['created_at'][:10]}\n\n"

            if order_data['items']:
                response += "Articles:\n"
                for idx, item in enumerate(order_data['items'], 1):
                    response += f"  {idx}. {item['product_name']} x{item['quantity']} (${item['unit_price']:.2f})\n"

            if order_data.get('shipment'):
                ship = order_data['shipment']
                response += f"\nInformations d'expédition:\n"
                response += f"   Transporteur: {ship['carrier']}\n"
                response += f"   Numéro de suivi: {ship['tracking_number']}\n"
                if ship.get('estimated_delivery'):
                    response += f"   Livraison estimée: {ship['estimated_delivery'][:10]}\n"

            response += "\nFaites-moi savoir si vous avez besoin d'aide!"

        elif language == 'de':
            response = f"Bestellung Gefunden:\n\n"
            response += f"Bestellnummer: {order_data['order_no']}\n"
            response += f"Kunde: {order_data['customer_name']}\n"
            response += f"Status: {status_text}\n"
            response += f"Betrag: ${order_data['total_amount']:.2f}\n"
            response += f"Bestelldatum: {order_data['created_at'][:10]}\n\n"

            if order_data['items']:
                response += "Artikel:\n"
                for idx, item in enumerate(order_data['items'], 1):
                    response += f"  {idx}. {item['product_name']} x{item['quantity']} (${item['unit_price']:.2f})\n"

            if order_data.get('shipment'):
                ship = order_data['shipment']
                response += f"\nVersandinformationen:\n"
                response += f"   Transporteur: {ship['carrier']}\n"
                response += f"   Sendungsnummer: {ship['tracking_number']}\n"
                if ship.get('estimated_delivery'):
                    response += f"   Voraussichtliche Lieferung: {ship['estimated_delivery'][:10]}\n"

            response += "\nLassen Sie es mich wissen, wenn Sie Hilfe benötigen!"

        else:
            response = f"订单信息：{order_data['order_no']} 状态:{status_text} 金额:{order_data['total_amount']}"

        return response

    def _get_order_not_found_response(self, language: str, need_order_no: bool = False, order_no: str = None) -> str:
        """
        生成订单未找到的友好提示
        """
        if need_order_no:
            messages = {
                'zh': "请问您的订单号是多少？我可以帮您查询订单状态和物流信息。",
                'en': "Could you please provide your order number? I can help you check the order status and shipping information.",
                'es': "¿Podría proporcionarme su número de pedido? Puedo ayudarle a verificar el estado del envío.",
                'fr': "Pourriez-vous me donner votre numéro de commande ? Je peux vous aider à vérifier le statut de la commande.",
                'de': "Könnten Sie mir Ihre Bestellnummer geben? Ich kann Ihnen helfen, den Bestellstatus zu überprüfen."
            }
        else:
            messages = {
                'zh': f"抱歉，未找到订单号 {order_no} 的信息。请确认订单号是否正确，或提供其他订单号。",
                'en': f"Sorry, I couldn't find order {order_no}. Please verify the order number or provide a different one.",
                'es': f"Lo siento, no encontré el pedido {order_no}. Verifique el número o proporcione otro.",
                'fr': f"Désolé, je n'ai pas trouvé la commande {order_no}. Vérifiez le numéro ou fournissez-en un autre.",
                'de': f"Entschuldigung, ich konnte die Bestellung {order_no} nicht finden. Überprüfen Sie die Nummer oder geben Sie eine andere an."
            }

        return messages.get(language, messages['zh'])

    async def _get_or_create_session(self, session_id: str) -> Dict:
        sessions = CustomerServiceAgent._sessions

        if session_id in sessions:
            session = sessions[session_id]
            last_activity = session.get('last_activity')
            if last_activity:
                if datetime.now() - last_activity > timedelta(minutes=settings.session_expire_minutes):
                    session = self._create_new_session(session_id)
                    sessions[session_id] = session
            return session
        else:
            session = self._create_new_session(session_id)
            sessions[session_id] = session
            return session

    def _create_new_session(self, session_id: str) -> Dict:
        return {
            'session_id': session_id,
            'created_at': datetime.now(),
            'last_activity': datetime.now(),
            'history': [],
            'turn_count': 0,
            'language_detected': None,
            'status': 'normal',
            'transfer_to_human': None
        }

    async def _update_session_history(
        self, session_id: str, user_message: str, agent_response: str
    ):
        sessions = CustomerServiceAgent._sessions

        if session_id in sessions:
            session = sessions[session_id]
            session['history'].append({
                'role': 'user',
                'content': user_message,
                'timestamp': datetime.now().isoformat()
            })
            session['history'].append({
                'role': 'agent',
                'content': agent_response,
                'timestamp': datetime.now().isoformat()
            })
            session['turn_count'] += 1
            session['last_activity'] = datetime.now()

            max_history = settings.max_conversation_turns * 2
            if len(session['history']) > max_history:
                session['history'] = session['history'][-max_history:]

    async def _handle_human_transfer(
        self, session_id, user_query, intent_result, language, start_time
    ) -> Dict:
        session = CustomerServiceAgent._sessions.get(session_id)
        if session:
            session['status'] = 'pending_human'
            session['transfer_to_human'] = {
                'reason': intent_result.get('reason'),
                'intent': intent_result['intent'].value,
                'confidence': intent_result['confidence'],
                'timestamp': datetime.now().isoformat(),
                'summary': await self._generate_conversation_summary(session_id)
            }

        summary = await self._generate_conversation_summary(session_id)
        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        transfer_msgs = {
            'zh': '好的，我正在为您转接人工客服。请稍候。',
            'en': 'Okay, I am transferring you to a human agent now. Please wait a moment.',
            'es': 'Okay, te estoy transfiriendo a un agente humano ahora. Por favor, espera un momento.',
            'fr': "D'accord, je vous transfère vers un agent humain. Veuillez patienter un instant.",
            'de': 'Okay, ich leite Sie jetzt an einen menschlichen Agenten weiter. Bitte warten Sie einen Moment.',
        }

        return {
            'session_id': session_id,
            'response': transfer_msgs.get(language, transfer_msgs['zh']),
            'intent': intent_result['intent'].value,
            'confidence': intent_result['confidence'],
            'rag_confidence': 0.0,
            'language': language,
            'should_transfer': True,
            'transfer_reason': intent_result.get('reason'),
            'conversation_summary': summary,
            'session_status': 'pending_human',
            'processing_time_ms': int(processing_time),
            'context_used': {'products_found': 0, 'faqs_found': 0},
            'success': True
        }

    async def _generate_conversation_summary(self, session_id: str) -> Dict:
        if session_id not in CustomerServiceAgent._sessions:
            return {
                'turn_count': 0,
                'user_queries': [],
                'key_entities': {},
                'emotion': 'neutral',
                'note': '新会话，无历史记录'
            }

        session = CustomerServiceAgent._sessions[session_id]
        history = session.get('history', [])

        user_messages = [msg['content'] for msg in history if msg['role'] == 'user']

        order_nos = []
        for msg in user_messages:
            matches = re.findall(r'(ORD[-\w]+)', msg, re.IGNORECASE)
            order_nos.extend(matches)

        emotion = self._analyze_emotion(user_messages)

        return {
            'turn_count': session.get('turn_count', 0),
            'user_queries': user_messages[-8:],
            'key_entities': {
                'order_numbers': list(set(order_nos))[:5],
                'detected_language': session.get('language_detected')
            },
            'emotion': emotion,
            'session_status': session.get('status', 'normal')
        }

    def _analyze_emotion(self, user_messages: List[str]) -> str:
        text = ' '.join(user_messages).lower()

        angry_keywords = ['angry', 'furious', 'terrible', 'bad', 'worst', 'complain',
                          '不满', '生气', '投诉', '糟糕', '太差', '垃圾']
        sad_keywords = ['sad', 'disappointed', 'unhappy', 'sorry', '失望', '难过', '不开心']
        happy_keywords = ['thanks', 'thank you', 'great', 'excellent', 'good',
                          '谢谢', '感谢', '很好', '满意', '不错']

        if any(kw in text for kw in angry_keywords):
            return 'angry'
        if any(kw in text for kw in sad_keywords):
            return 'sad'
        if any(kw in text for kw in happy_keywords):
            return 'happy'
        return 'neutral'

    async def get_product_recommendations(self, category: str = None, limit: int = 5) -> List[Dict]:
        return await self.rag_retriever.get_product_recommendations(category, limit)

    async def get_session_info(self, session_id: str) -> Optional[Dict]:
        return CustomerServiceAgent._sessions.get(session_id)

    async def clear_session(self, session_id: str) -> bool:
        if session_id in CustomerServiceAgent._sessions:
            del CustomerServiceAgent._sessions[session_id]
            return True
        return False