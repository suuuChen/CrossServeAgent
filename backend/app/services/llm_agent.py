"""
LLM Agent 模块（整合: tools.py + tool_runner.py + agent_graph.py）

三合一:
  1. Function Calling 工具定义 (StructuredTool + 业务函数)
  2. LLM + Function Calling 共享执行引擎 (LLMToolRunner)
  3. LangGraph StateGraph + LLM Function Calling Agent (AgentStateGraph)

工作流:
    START
      -> detect_language
      -> llm_decide (LLM 自主决策要不要调用工具)
      -> conditional_edge
           had_tool_call? YES -> finalize_with_tool_result
           had_tool_call? NO  -> classify_transfer
      -> classify_transfer
      -> END
"""

from __future__ import annotations

import json as _json
from typing import Any, Dict, List, Optional, TypedDict, Tuple

from pydantic import BaseModel, Field
from langchain_core.tools import StructuredTool
from openai import OpenAI

from app.services.nlu import detect_language, IntentType
from app.config import settings

try:
    from langgraph.graph import StateGraph, END

    _LANGGRAPH_AVAILABLE = True
except ImportError:
    _LANGGRAPH_AVAILABLE = False

class QueryOrderInput(BaseModel):
    order_no: str = Field(description="订单号，格式如 ORD-20260901-001")


class QueryShipmentInput(BaseModel):
    tracking_no: Optional[str] = Field(default=None, description="物流单号，如 YT9876543210")
    order_no: Optional[str] = Field(default=None, description="订单号，用于关联查询物流")


class SearchProductInput(BaseModel):
    keyword: str = Field(description="搜索关键词，产品名称或类别")
    limit: int = Field(default=5, description="返回结果数量，默认5")


class CheckReturnPolicyInput(BaseModel):
    product_category: Optional[str] = Field(default=None, description="产品类别")
    reason: Optional[str] = Field(default=None, description="退换原因")


async def _query_order_func(order_no: str, db_session=None) -> Dict[str, Any]:
    if db_session is None:
        return {"success": False, "error": "Function Calling 工具执行需要 db_session"}
    return await _do_query_order(order_no, db_session)


async def _do_query_order(order_no: str, db_session) -> Dict[str, Any]:
    from sqlalchemy import select
    from app.models.order import Order, OrderItem

    try:
        result = await db_session.execute(
            select(Order).where(Order.order_no == order_no).limit(1)
        )
        order = result.scalar_one_or_none()
        if order is None:
            return {"success": False, "error": "订单不存在", "order_no": order_no}

        items_result = await db_session.execute(
            select(OrderItem).where(OrderItem.order_id == order.id)
        )
        items = items_result.scalars().all()

        return {
            "success": True,
            "order": {
                "order_no": order.order_no,
                "status": order.status,
                "total_amount": float(order.total_amount),
                "created_at": order.created_at.isoformat() if order.created_at else None,
                "shipping_carrier": order.shipping_carrier,
                "tracking_no": order.tracking_no,
                "estimated_delivery": order.estimated_delivery.isoformat() if order.estimated_delivery else None,
                "items": [
                    {"product_name": it.product_name, "quantity": it.quantity, "price": float(it.price)}
                    for it in items
                ],
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e), "order_no": order_no}


async def _query_shipment_func(tracking_no: str = None, order_no: str = None, db_session=None) -> Dict[str, Any]:
    if db_session is None:
        return {"success": False, "error": "Function Calling 工具执行需要 db_session"}
    return await _do_query_shipment(tracking_no, order_no, db_session)


async def _do_query_shipment(tracking_no: str, order_no: str, db_session) -> Dict[str, Any]:
    from sqlalchemy import select
    from app.models.order import Order

    try:
        order = None
        if order_no:
            result = await db_session.execute(
                select(Order).where(Order.order_no == order_no).limit(1)
            )
            order = result.scalar_one_or_none()
        elif tracking_no:
            result = await db_session.execute(
                select(Order).where(Order.tracking_no == tracking_no).limit(1)
            )
            order = result.scalar_one_or_none()

        if order is None:
            return {"success": False, "error": "物流信息不存在", "tracking_no": tracking_no, "order_no": order_no}

        return {
            "success": True,
            "shipment": {
                "carrier": order.shipping_carrier or "未知",
                "tracking_no": order.tracking_no,
                "status": order.status,
                "estimated_delivery": order.estimated_delivery.isoformat() if order.estimated_delivery else None,
                "order_no": order.order_no,
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


RETURN_POLICY_RULES = {
    "default": {
        "window_days": 30,
        "shipping_cost": "buyer",
        "condition_required": "商品未使用、吊牌完好、原包装",
        "refund_method": "原路退回，7-15 个工作日到账",
        "process_steps": [
            "买家在订单详情页点击「申请退换货」",
            "填写退换原因并提交",
            "客服审核（1-2 工作日）",
            "买家寄回商品，上传快递单号",
            "仓库验货后退款/补发",
        ],
    },
    "electronics": {
        "window_days": 15,
        "shipping_cost": "buyer（质量问题除外）",
        "condition_required": "未拆封或质量问题可拆封",
        "refund_method": "原路退回，7 个工作日到账",
        "process_steps": [
            "买家申请退换货并说明问题",
            "客服审核，可能要求提供照片/视频",
            "质量问题由卖家承担运费并优先处理",
            "非质量问题买家承担运费",
            "仓库验货后退款",
        ],
    },
    "clothing": {
        "window_days": 30,
        "shipping_cost": "buyer（尺码/颜色错发除外）",
        "condition_required": "未穿着、吊牌完整、无污渍",
        "refund_method": "原路退回，5-10 个工作日到账",
        "process_steps": [
            "买家申请退换货",
            "客服审核（1 个工作日内）",
            "买家寄回",
            "仓库验货后退款或换码",
        ],
    },
    "beauty": {
        "window_days": 7,
        "shipping_cost": "buyer",
        "condition_required": "未开封、未使用",
        "refund_method": "原路退回，7 个工作日到账",
        "process_steps": [
            "买家申请退换货",
            "客服审核，可能要求提供过敏/不适照片",
            "未开封商品直接受理",
            "开封使用过的仅支持质量问题",
        ],
    },
    "food": {
        "window_days": 0,
        "shipping_cost": "不适用",
        "condition_required": "不支持退换（除非商品破损/变质）",
        "refund_method": "破损/变质情况，拍照后直接全额退款",
        "process_steps": [
            "签收时发现问题立即拍照",
            "联系客服并提供照片",
            "客服核实后全额退款，无需寄回",
        ],
    },
}


async def _do_check_return_policy(product_category: str, reason: str) -> Dict[str, Any]:
    category_key = product_category.lower() if product_category else "default"

    matched_key = "default"
    for key in RETURN_POLICY_RULES:
        if key == "default":
            continue
        if key in category_key or category_key in key:
            matched_key = key
            break

    policy = RETURN_POLICY_RULES[matched_key]

    reason_lower = (reason or "").lower()
    quality_issue = any(k in reason_lower for k in [
        "质量", "破损", "缺陷", "坏", "broken", "defect", "damage", "quality",
        "损坏", "不工作", "无法使用", "not work",
    ])
    wrong_item = any(k in reason_lower for k in [
        "错发", "发错", "wrong", "mistake", "错误", "不match",
    ])

    adjusted_shipping = policy["shipping_cost"]
    if quality_issue or wrong_item:
        adjusted_shipping = "seller（质量/错发问题由卖家承担运费）"

    return {
        "success": True,
        "product_category": product_category or "通用",
        "matched_rule": matched_key,
        "policy": {
            "return_window_days": policy["window_days"],
            "shipping_cost_bearer": adjusted_shipping,
            "condition_required": policy["condition_required"],
            "refund_method": policy["refund_method"],
            "process_steps": policy["process_steps"],
            "special_notes": (
                "质量问题/错发情况下运费由卖家承担，请先拍照留证"
                if (quality_issue or wrong_item)
                else None
            ),
        },
        "quality_issue_detected": quality_issue,
        "wrong_item_detected": wrong_item,
    }


async def _check_return_policy_func(
    product_category: str = None, reason: str = None
) -> Dict[str, Any]:
    return await _do_check_return_policy(product_category or "", reason or "")


query_order_tool = StructuredTool.from_function(
    func=_query_order_func,
    name="query_order",
    description="查询订单详情，包括状态、金额、商品清单、物流信息。需要提供订单号(ORD-开头)。",
    args_schema=QueryOrderInput,
    coroutine=_query_order_func,
)

query_shipment_tool = StructuredTool.from_function(
    func=_query_shipment_func,
    name="query_shipment",
    description="查询物流/配送状态，可通过物流单号或订单号查询。",
    args_schema=QueryShipmentInput,
    coroutine=_query_shipment_func,
)

check_return_policy_tool = StructuredTool.from_function(
    func=_check_return_policy_func,
    name="check_return_policy",
    description=(
        "查询退换货政策。根据产品类别和退换原因，返回可退换时效、运费承担方、"
        "退换条件、退款方式、处理流程。适用于买家询问能否退货、退货需要注意什么、"
        "退货流程等场景。"
    ),
    args_schema=CheckReturnPolicyInput,
    coroutine=_check_return_policy_func,
)

ALL_TOOLS = [query_order_tool, query_shipment_tool, check_return_policy_tool]

TOOL_MAP = {
    "query_order": query_order_tool,
    "query_shipment": query_shipment_tool,
    "check_return_policy": check_return_policy_tool,
}

class LLMToolRunner:
    """
    LLM 客户端 + Function Calling 循环执行器
    被 retriever.RAGRetriever 和 AgentStateGraph 共同使用。
    """

    def __init__(self, db=None, model_override: Optional[str] = None):
        self.db = db

        if settings.use_local_llm:
            print(f'[LLMToolRunner] use local LLM: {settings.local_llm_model} @ {settings.local_llm_url}')
            self.llm_client = OpenAI(
                base_url=settings.local_llm_url,
                api_key='ollama',
            )
            self.model_name = model_override or settings.local_llm_model
        else:
            print(f'[LLMToolRunner] use OpenAI API: {settings.openai_model}')
            self.llm_client = OpenAI(api_key=settings.openai_api_key)
            self.model_name = model_override or settings.openai_model

    @classmethod
    def get_tools_schema(cls) -> List[Dict[str, Any]]:
        schemas: List[Dict[str, Any]] = []
        for t in ALL_TOOLS:
            schema = t.args_schema.model_json_schema()
            schemas.append({
                'type': 'function',
                'function': {
                    'name': t.name,
                    'description': t.description,
                    'parameters': {
                        'type': 'object',
                        'properties': schema.get('properties', {}),
                        'required': schema.get('required', []),
                    },
                },
            })
        return schemas

    @classmethod
    async def execute_tool(cls, tool_name: str, tool_args: Dict[str, Any], db=None) -> Dict[str, Any]:
        tool = TOOL_MAP.get(tool_name)
        if tool is None:
            return {'success': False, 'error': f'unknown tool: {tool_name}'}

        coro = getattr(tool, 'coroutine', None) or getattr(tool, 'func', None)
        if coro is None:
            return {'success': False, 'error': f'tool {tool_name} is not callable'}

        args = dict(tool_args)
        if db is not None:
            args['db_session'] = db

        result = await coro(**args)
        if not isinstance(result, dict):
            result = {'success': True, 'data': result}
        return result

    async def call_llm_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = 'auto',
        max_tool_rounds: int = 3,
        temperature: float = 0.7,
        max_tokens: int = 1200,
    ) -> Dict[str, Any]:
        """
        Function Calling 循环: LLM 自主决定是否调用工具 -> 执行 -> 回灌 -> 生成自然语言回复
        """
        current_messages = list(messages)
        tool_calls_made: List[Dict[str, Any]] = []
        tool_results: List[Dict[str, Any]] = []

        for round_idx in range(max_tool_rounds + 1):
            kwargs: Dict[str, Any] = {
                'model': self.model_name,
                'messages': current_messages,
                'temperature': temperature,
                'max_tokens': max_tokens,
            }

            if tools and round_idx == 0:
                kwargs['tools'] = tools
                kwargs['tool_choice'] = tool_choice

            try:
                response = self.llm_client.chat.completions.create(**kwargs)
            except Exception as e:
                print(f'[LLMToolRunner] LLM call failed: {e}')
                break

            message = response.choices[0].message

            if not getattr(message, 'tool_calls', None):
                return {
                    'final_text': (message.content or '').strip(),
                    'tool_calls_made': tool_calls_made,
                    'tool_results': tool_results,
                    'had_tool_call': len(tool_calls_made) > 0,
                    'raw_messages_count': len(current_messages),
                }

            current_messages.append({
                'role': 'assistant',
                'tool_calls': [
                    {
                        'id': tc.id,
                        'type': 'function',
                        'function': {
                            'name': tc.function.name,
                            'arguments': tc.function.arguments,
                        },
                    }
                    for tc in message.tool_calls
                ],
            })

            for tc in message.tool_calls:
                tool_name = tc.function.name
                tool_args_str = tc.function.arguments or '{}'
                try:
                    tool_args = _json.loads(tool_args_str)
                except Exception:
                    tool_args = {}

                tool_calls_made.append({
                    'id': tc.id,
                    'name': tool_name,
                    'args': tool_args,
                })

                tool_result = await self.execute_tool(tool_name, tool_args, db=self.db)
                tool_results.append({
                    'name': tool_name,
                    'args': tool_args,
                    'result': tool_result,
                })

                current_messages.append({
                    'role': 'tool',
                    'tool_call_id': tc.id,
                    'content': _json.dumps(tool_result, ensure_ascii=False, default=str)[:3000],
                })

        if tool_calls_made:
            last_tc = tool_calls_made[-1]
            last_res = tool_results[-1]['result'] if tool_results else {}
            return {
                'final_text': (
                    '[tool ' + last_tc['name'] + ' called] '
                    'but LLM did not produce final text within ' + str(max_tool_rounds) + ' rounds. '
                    'Last result: ' + _json.dumps(last_res, ensure_ascii=False, default=str)[:500]
                ),
                'tool_calls_made': tool_calls_made,
                'tool_results': tool_results,
                'had_tool_call': True,
                'raw_messages_count': len(current_messages),
            }

        return {
            'final_text': 'sorry, i could not process your request',
            'tool_calls_made': [],
            'tool_results': [],
            'had_tool_call': False,
            'raw_messages_count': len(current_messages),
        }

SYSTEM_PROMPT_TEMPLATE = """You are a multilingual customer service agent for a cross-border e-commerce store.

    Your capabilities:
    - Respond naturally in the buyer's detected language
    - When asked about order details, shipping, or return policy: call the appropriate tool
    - When the user is confused: ask one clarifying question
    - Never fabricate order details - ALWAYS use tools for factual data
    
    Available tools:
    - query_order:     订单详情（需 order_no）
    - query_shipment:  物流状态（需 tracking_no 或 order_no）
    - check_return_policy:  退换货政策（产品类别 + 退换原因）
    
    Current buyer language: {language}
    Conversation turns so far: {turn_count}
    
    If the user asks something that matches a tool signature, you MUST call the tool instead of guessing.
    After receiving a tool result, compose a friendly multilingual answer in {language}."""


class AgentState(TypedDict, total=False):
    query: str
    hint_lang: Optional[str]
    detected_lang: str
    lang_confidence: float
    llm_result: Optional[Dict[str, Any]]
    had_tool_call: bool
    final_text: str
    tool_calls_made: List[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]
    intent: Optional[IntentType]
    should_transfer: bool
    transfer_reason: Optional[str]
    order_no_from_tools: Optional[str]


def is_available() -> bool:
    return _LANGGRAPH_AVAILABLE


if _LANGGRAPH_AVAILABLE:

    class AgentStateGraph:
        """
        真正的 LLM Agent StateGraph

        构造参数:
            db: AsyncSession  —— 注入到工具执行器里
            llm_override: 可自定义模型名
        """

        def __init__(self, db=None, llm_override: Optional[str] = None):
            self.db = db
            self.llm_override = llm_override
            self._tool_runner = None
            self.graph = self._build_graph()

        def _get_tool_runner(self):
            if self._tool_runner is None:
                self._tool_runner = LLMToolRunner(db=self.db, model_override=self.llm_override)
            return self._tool_runner

        def _build_graph(self):
            g = StateGraph(AgentState)
            g.add_node('detect_language', self._node_detect_language)
            g.add_node('llm_decide', self._node_llm_decide)
            g.add_node('finalize_with_tool_result', self._node_finalize_with_tool_result)
            g.add_node('classify_transfer', self._node_classify_transfer)

            g.set_entry_point('detect_language')
            g.add_edge('detect_language', 'llm_decide')
            g.add_conditional_edges(
                'llm_decide',
                self._route_after_llm,
                {
                    'tool_path': 'finalize_with_tool_result',
                    'direct_path': 'classify_transfer',
                },
            )
            g.add_edge('finalize_with_tool_result', 'classify_transfer')
            g.add_edge('classify_transfer', END)
            return g.compile()

        def _node_detect_language(self, state: AgentState) -> dict:
            lang, conf = detect_language(state['query'], hint=state.get('hint_lang'))
            return {
                'detected_lang': lang,
                'lang_confidence': conf,
            }

        async def _node_llm_decide(self, state: AgentState) -> dict:
            if settings.use_fast_mode:
                print('[AgentGraph] use_fast_mode=True, 跳过 LLM tool-calling, 直接走 RAG 兜底')
                return {
                    'had_tool_call': False,
                    'final_text': '',
                    'tool_calls_made': [],
                    'tool_results': [],
                    'llm_result': {'bypassed': True},
                }

            query = state['query']
            lang = state.get('detected_lang', 'zh')
            turn_count = state.get('turn_count', 0)

            system_msg = SYSTEM_PROMPT_TEMPLATE.format(language=lang, turn_count=turn_count)

            messages = [
                {'role': 'system', 'content': system_msg},
                {'role': 'user', 'content': query},
            ]

            runner = self._get_tool_runner()
            tools_schema = runner.get_tools_schema()

            try:
                llm_result = await runner.call_llm_with_tools(
                    messages=messages,
                    tools=tools_schema,
                    tool_choice='auto',
                    max_tool_rounds=3,
                    temperature=0.4,
                    max_tokens=1200,
                )

                had_tool_call = llm_result['had_tool_call']
                final_text = llm_result['final_text']
                tool_calls_made = llm_result['tool_calls_made']
                tool_results = llm_result['tool_results']

                order_no_from_tools = None
                for tc in tool_calls_made:
                    if tc['name'] == 'query_order':
                        order_no_from_tools = tc['args'].get('order_no')

                print(
                    f'[AgentGraph] llm_decide: had_tool_call={had_tool_call}, '
                    f'tools=[{", ".join(tc["name"] for tc in tool_calls_made)}], '
                    f'final_text_len={len(final_text)}'
                )

                return {
                    'llm_result': llm_result,
                    'had_tool_call': had_tool_call,
                    'final_text': final_text,
                    'tool_calls_made': tool_calls_made,
                    'tool_results': tool_results,
                    'order_no_from_tools': order_no_from_tools,
                }

            except Exception as e:
                print(f'[AgentGraph] llm_decide 出错, 回退到 RAG: {e}')
                return {
                    'had_tool_call': False,
                    'final_text': '',
                    'tool_calls_made': [],
                    'tool_results': [],
                    'llm_result': {'error': str(e)},
                }

        def _route_after_llm(self, state: AgentState) -> str:
            if state.get('had_tool_call'):
                return 'tool_path'
            return 'direct_path'

        def _node_finalize_with_tool_result(self, state: AgentState) -> dict:
            return {
                'final_text': state.get('final_text', ''),
            }

        def _node_classify_transfer(self, state: AgentState) -> dict:
            lang = state.get('detected_lang', 'zh')
            query = state['query']
            final_text = state.get('final_text', '')
            had_tool_call = state.get('had_tool_call', False)

            intent = None
            if had_tool_call:
                tool_names = [tc['name'] for tc in state.get('tool_calls_made', [])]
                if 'query_order' in tool_names:
                    intent = IntentType.ORDER_QUERY
                elif 'query_shipment' in tool_names:
                    intent = IntentType.SHIPPING_QUERY
                elif 'check_return_policy' in tool_names:
                    intent = IntentType.RETURN_POLICY
                else:
                    intent = IntentType.GENERAL_FAQ
            else:
                query_lower = query.lower()
                transfer_kws = {
                    'zh': ['转人工', '人工客服', '真人'],
                    'en': ['human agent', 'speak to person', 'real person', 'transfer'],
                }
                for lang_key, kws in transfer_kws.items():
                    if any(k in query_lower for k in kws):
                        intent = IntentType.HUMAN_TRANSFER
                        break

            should_transfer = False
            transfer_reason = None

            transfer_explicit = {
                'zh': ['转人工', '人工客服', '找客服', '真人客服'],
                'en': ['human agent', 'speak to person', 'real person', 'transfer to human'],
                'es': ['agente humano', 'persona real', 'transferir'],
                'fr': ['agent humain', 'personne réelle'],
                'de': ['menschlicher agent', 'echte person'],
            }
            for lang_key, kws in transfer_explicit.items():
                if any(k in query.lower() for k in kws):
                    should_transfer = True
                    transfer_reason = '用户明确要求转人工'
                    break

            if not should_transfer and not had_tool_call and len(final_text) < 20:
                should_transfer = True
                transfer_reason = 'LLM 未调用工具且回复较短, 置信度不足'

            return {
                'intent': intent or IntentType.GENERAL_FAQ,
                'should_transfer': should_transfer,
                'transfer_reason': transfer_reason,
            }

        async def ainvoke(
            self,
            query: str,
            language: Optional[str] = None,
            turn_count: int = 0,
        ) -> Dict[str, Any]:
            initial: AgentState = {
                'query': query,
                'hint_lang': language,
                'turn_count': turn_count,
            }
            final = await self.graph.ainvoke(initial)

            intent = final.get('intent', IntentType.GENERAL_FAQ)
            if isinstance(intent, str):
                try:
                    intent = IntentType(intent)
                except Exception:
                    intent = IntentType.GENERAL_FAQ

            return {
                'intent': intent,
                'detected_lang': final.get('detected_lang', language or 'zh'),
                'lang_confidence': final.get('lang_confidence', 0.0),
                'final_text': final.get('final_text', ''),
                'had_tool_call': final.get('had_tool_call', False),
                'tool_calls_made': final.get('tool_calls_made', []),
                'tool_results': final.get('tool_results', []),
                'order_no_from_tools': final.get('order_no_from_tools'),
                'should_transfer': final.get('should_transfer', False),
                'transfer_reason': final.get('transfer_reason'),
                'llm_result': final.get('llm_result'),
            }