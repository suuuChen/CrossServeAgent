import { useState, useEffect, useCallback } from 'react';
import { humanTransferApi } from '../api';
import type { PendingHumanSession } from '../types';

const LANG_LABELS: Record<string, string> = {
  zh: '中文',
  en: 'English',
  es: 'Español',
  fr: 'Français',
  de: 'Deutsch',
};

const INTENT_LABELS: Record<string, string> = {
  order_query: '订单查询',
  logistics_query: '物流查询',
  return_policy: '退换货',
  complaint: '投诉',
  product_search: '商品搜索',
  faq: '常见问题',
  human_transfer: '请求人工',
  greeting: '问候',
  unclear: '意图不明',
};

const TRANSFER_REASON_LABELS: Record<string, string> = {
  low_confidence: '低置信度',
  complaint: '投诉升级',
  language_barrier: '语言障碍',
  request_human: '请求人工',
  complex_issue: '复杂问题',
};

const SUGGESTED_AGENTS = ['小王', '李华', 'Alice', 'Carlos'];

function formatTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleString('zh-CN', { hour12: false });
  } catch {
    return iso || '-';
  }
}

export default function PendingSessions() {
  const [sessions, setSessions] = useState<PendingHumanSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [takeoverInputs, setTakeoverInputs] = useState<Record<string, string>>({});
  const [takingOver, setTakingOver] = useState<string | null>(null);

  const fetchSessions = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await humanTransferApi.listPending();
      setSessions(data.sessions || []);
    } catch (e: any) {
      setError(e?.message || '获取待处理会话失败');
      setSessions([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSessions();
    const interval = setInterval(fetchSessions, 10000);
    return () => clearInterval(interval);
  }, [fetchSessions]);

  const handleTakeover = async (sessionId: string) => {
    const agentName = takeoverInputs[sessionId]?.trim() || SUGGESTED_AGENTS[0];
    try {
      setTakingOver(sessionId);
      await humanTransferApi.takeover(sessionId, agentName);
      setSessions(prev => prev.filter(s => s.session_id !== sessionId));
      setTakeoverInputs(prev => {
        const next = { ...prev };
        delete next[sessionId];
        return next;
      });
    } catch (e: any) {
      alert(`接管失败: ${e?.message || '未知错误'}`);
    } finally {
      setTakingOver(null);
    }
  };

  if (loading && sessions.length === 0) {
    return (
      <div className="p-4 space-y-3">
        <div className="flex items-center justify-center gap-2 py-8 text-xs text-slate-500">
          <div className="w-3 h-3 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
          加载中...
        </div>
      </div>
    );
  }

  if (error && sessions.length === 0) {
    return (
      <div className="p-4 space-y-3">
        <div className="text-center py-8">
          <div className="text-xs text-red-500 mb-3">⚠️ {error}</div>
          <button
            onClick={fetchSessions}
            className="px-3 py-1 text-xs bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            重试
          </button>
        </div>
      </div>
    );
  }

  if (sessions.length === 0) {
    return (
      <div className="p-4 space-y-3">
        <div className="text-xs text-slate-500 text-center py-8">
          暂无待处理会话
          <div className="mt-2 text-[10px] text-slate-400">（每 10 秒自动刷新）</div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 space-y-3">
      <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
        <span>待人工处理：{sessions.length} 条</span>
        <button onClick={fetchSessions} className="text-blue-500 hover:text-blue-600">
          刷新
        </button>
      </div>

      {sessions.map(session => {
        const isExpanded = expandedId === session.session_id;
        const summary = session.conversation_summary;
        const takeoverName = takeoverInputs[session.session_id] || '';

        return (
          <div
            key={session.session_id}
            className="bg-white rounded-lg border border-slate-200 overflow-hidden shadow-sm hover:shadow-md transition"
          >
            {/* 会话头 */}
            <div
              className="px-3 py-2.5 bg-gradient-to-r from-orange-50 to-amber-50 cursor-pointer"
              onClick={() => setExpandedId(isExpanded ? null : session.session_id)}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${
                    session.transfer_reason === 'complaint' ? 'bg-red-500' : 'bg-orange-400'
                  } animate-pulse`}></span>
                  <span className="text-sm font-semibold text-slate-800 truncate max-w-[160px]">
                    {summary?.summary?.slice(0, 30) || '待处理会话'}
                    {(summary?.summary?.length || 0) > 30 ? '...' : ''}
                  </span>
                </div>
                <div className="flex items-center gap-1.5 text-[10px]">
                  <span className="px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded">
                    {LANG_LABELS[session.language_detected] || session.language_detected}
                  </span>
                  <span className="px-1.5 py-0.5 bg-slate-100 text-slate-600 rounded">
                    {session.turn_count}轮
                  </span>
                </div>
              </div>

              <div className="mt-1.5 flex items-center gap-1 flex-wrap text-[10px] text-slate-500">
                <span className="px-1.5 py-0.5 bg-red-100 text-red-600 rounded">
                  {TRANSFER_REASON_LABELS[session.transfer_reason] || session.transfer_reason}
                </span>
                <span className="px-1.5 py-0.5 bg-purple-100 text-purple-600 rounded">
                  {INTENT_LABELS[session.intent] || session.intent}
                </span>
                <span className="ml-auto text-slate-400">{formatTime(session.transfer_timestamp)}</span>
              </div>
            </div>

            {/* 展开详情：中文摘要 */}
            {isExpanded && summary && (
              <div className="px-3 py-3 space-y-2.5 border-t border-slate-100 bg-slate-50">
                <div>
                  <div className="text-[10px] font-semibold text-slate-500 mb-1 flex items-center gap-1">
                    📋 中文摘要（翻译摘要）
                  </div>
                  <div className="text-xs text-slate-700 leading-relaxed bg-white p-2 rounded border border-slate-100">
                    {summary.summary}
                  </div>
                </div>

                {summary.queries_text && (
                  <div>
                    <div className="text-[10px] font-semibold text-slate-500 mb-1 flex items-center gap-1">
                      💬 买家原话（最近消息）
                    </div>
                    <div className="text-xs text-slate-600 leading-relaxed bg-white p-2 rounded border border-slate-100">
                      {summary.queries_text}
                    </div>
                  </div>
                )}

                <div className="flex items-center gap-3 text-[10px] text-slate-500">
                  {summary.order_text && (
                    <span className="px-2 py-1 bg-cyan-50 text-cyan-700 rounded">
                      📦 {summary.order_text}
                    </span>
                  )}
                  {summary.emotion_label && (
                    <span className={`px-2 py-1 rounded ${
                      summary.emotion === 'angry' ? 'bg-red-50 text-red-600' :
                      summary.emotion === 'frustrated' ? 'bg-orange-50 text-orange-600' :
                      'bg-green-50 text-green-600'
                    }`}>
                      😊 {summary.emotion_label}
                    </span>
                  )}
                </div>

                {/* 人工接管输入 */}
                <div className="flex items-center gap-2 pt-1 border-t border-slate-100">
                  <input
                    type="text"
                    value={takeoverName}
                    onChange={e => setTakeoverInputs(prev => ({ ...prev, [session.session_id]: e.target.value }))}
                    placeholder="输入您的名字..."
                    className="flex-1 px-2 py-1 text-xs border border-slate-200 rounded focus:outline-none focus:ring-1 focus:ring-orange-400"
                    onKeyDown={e => {
                      if (e.key === 'Enter') handleTakeover(session.session_id);
                    }}
                  />
                  <button
                    onClick={() => handleTakeover(session.session_id)}
                    disabled={takingOver === session.session_id}
                    className="px-3 py-1 text-xs font-medium bg-gradient-to-r from-orange-500 to-red-500 text-white rounded hover:from-orange-600 hover:to-red-600 disabled:opacity-50"
                  >
                    {takingOver === session.session_id ? '处理中...' : '✓ 接管'}
                  </button>
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}