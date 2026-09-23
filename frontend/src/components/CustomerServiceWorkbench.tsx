import { useState } from 'react';
import ChatPanel from './ChatPanel';
import PendingSessions from './PendingSessions';
import type { ConversationSummary } from '../types';

export default function CustomerServiceWorkbench() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [showPendingPanel, setShowPendingPanel] = useState(false);
  const [lastSummary, setLastSummary] = useState<ConversationSummary | null>(null);

  const handleSessionChange = (newSessionId: string): void => {
    setSessionId(newSessionId);
  };

  const handleTransfer = (summary?: ConversationSummary): void => {
    if (summary) setLastSummary(summary);
    setShowPendingPanel(true);
  };

  return (
    <div className="flex h-full bg-slate-50">
      <div className={`flex-1 flex flex-col transition-all duration-300 min-h-0 ${showPendingPanel ? 'mr-0' : ''}`}>
        <ChatPanel
          sessionId={sessionId}
          onSessionChange={handleSessionChange}
          onTransfer={handleTransfer}
        />
      </div>

      {showPendingPanel && (
        <div className="w-[420px] bg-white border-l border-slate-200 shadow-2xl flex flex-col">
          <div className="px-5 py-3 border-b border-slate-100 bg-gradient-to-r from-orange-50 to-red-50 shrink-0">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-slate-800 flex items-center gap-2">
                <span className="w-6 h-6 rounded-full bg-gradient-to-br from-orange-400 to-red-500 flex items-center justify-center text-white text-xs font-bold">人</span>
                人工客服工作台
              </h3>
              <button
                onClick={() => setShowPendingPanel(false)}
                className="w-7 h-7 rounded-full hover:bg-slate-100 flex items-center justify-center text-slate-400 hover:text-slate-600 transition"
              >
                ×
              </button>
            </div>
            <p className="text-xs text-slate-500 mt-1">低置信度/投诉自动转人工 · 每 10 秒刷新</p>
          </div>

          {lastSummary && (
            <div className="px-5 py-3 border-b border-orange-100 bg-gradient-to-r from-amber-50 to-orange-50 shrink-0">
              <div className="flex items-center gap-1.5 text-[11px] font-semibold text-orange-700 mb-2">
                🔄 最新转人工摘要（双语对照）
              </div>
              <div className="space-y-2">
                {lastSummary.translated_summary && lastSummary.summary_language ? (
                  <div className="grid grid-cols-2 gap-2 text-[11px]">
                    <div className="bg-white p-2 rounded border border-slate-100">
                      <div className="text-[9px] text-slate-400 mb-1">买家原语言 ({lastSummary.summary_language})</div>
                      <div className="text-slate-600 leading-relaxed">{lastSummary.translated_summary}</div>
                    </div>
                    <div className="bg-white p-2 rounded border border-slate-100">
                      <div className="text-[9px] text-slate-400 mb-1">中文摘要</div>
                      <div className="text-slate-700 leading-relaxed font-medium">{lastSummary.summary}</div>
                    </div>
                  </div>
                ) : (
                  <div className="bg-white p-2 rounded border border-slate-100 text-[11px] text-slate-700 leading-relaxed">
                    {lastSummary.summary}
                  </div>
                )}
                <button
                  onClick={() => setLastSummary(null)}
                  className="text-[10px] text-orange-500 hover:text-orange-600"
                >
                  ✕ 清除此摘要
                </button>
              </div>
            </div>
          )}

          <div className="flex-1 overflow-auto min-h-0">
            <PendingSessions />
          </div>
        </div>
      )}
    </div>
  );
}