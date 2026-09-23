import { useState } from 'react';
import ChatPanel from './ChatPanel';
import PendingSessions from './PendingSessions';

export default function CustomerServiceWorkbench() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [showPendingPanel, setShowPendingPanel] = useState(false);

  const handleSessionChange = (newSessionId: string): void => {
    setSessionId(newSessionId);
  };

  const handleTransfer = (): void => {
    setShowPendingPanel(true);
  };

  return (
    <div className="flex h-full bg-slate-50">
      {/* 主聊天区域 */}
      <div className={`flex-1 flex flex-col transition-all duration-300 min-h-0 ${showPendingPanel ? 'mr-0' : ''}`}>
        <ChatPanel
          sessionId={sessionId}
          onSessionChange={handleSessionChange}
          onTransfer={handleTransfer}
        />
      </div>

      {/* 转人工面板（可选显示） */}
      {showPendingPanel && (
        <div className="w-[400px] bg-white border-l border-slate-200 shadow-2xl flex flex-col">
          <div className="px-6 py-4 border-b border-slate-100 bg-gradient-to-r from-orange-50 to-red-50 shrink-0">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-slate-800">人工客服</h3>
              <button
                onClick={() => setShowPendingPanel(false)}
                className="w-7 h-7 rounded-full hover:bg-slate-100 flex items-center justify-center text-slate-400 hover:text-slate-600 transition"
              >
                ×
              </button>
            </div>
            <p className="text-xs text-slate-500 mt-1">正在为您转接人工客服，请稍候...</p>
          </div>
          <div className="flex-1 overflow-auto p-4">
            <PendingSessions />
          </div>
        </div>
      )}
    </div>
  );
}