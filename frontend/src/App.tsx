import { useState } from 'react';
import CustomerServiceWorkbench from './components/CustomerServiceWorkbench';
import OperationsWorkbench from './components/OperationsWorkbench';

type WorkbenchType = 'customer-service' | 'operations';

export default function App() {
  const [activeWorkbench, setActiveWorkbench] = useState<WorkbenchType>('customer-service');

  return (
    <div className="flex h-screen bg-slate-100">
      <div className="fixed top-0 left-0 right-0 z-50 bg-white border-b border-slate-200 shadow-sm">
        <div className="flex items-center justify-between px-6 py-3">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-xl shadow-lg">
                🤖
              </div>
              <div>
                <h1 className="text-lg font-bold text-slate-800">跨境电商多语言智能Agent平台</h1>
                <p className="text-xs text-slate-500">Multilingual Customer Service & Operations Agent</p>
              </div>
            </div>
          </div>

          <div className="flex items-center bg-slate-100 rounded-lg p-1">
            <button
              onClick={() => setActiveWorkbench('customer-service')}
              className={`px-6 py-2 rounded-md text-sm font-medium transition-all ${
                activeWorkbench === 'customer-service'
                  ? 'bg-blue-500 text-white shadow-md'
                  : 'text-slate-600 hover:text-slate-800'
              }`}
            >
              💬 客服Agent工作台
            </button>
            <button
              onClick={() => setActiveWorkbench('operations')}
              className={`px-6 py-2 rounded-md text-sm font-medium transition-all ${
                activeWorkbench === 'operations'
                  ? 'bg-purple-500 text-white shadow-md'
                  : 'text-slate-600 hover:text-slate-800'
              }`}
            >
              📊 运营Agent工作台
            </button>
          </div>

          <div className="text-xs text-slate-400">
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></div>
              <span>系统运行中</span>
            </div>
          </div>
        </div>
      </div>

      <div className="pt-16 w-full h-screen">
        {activeWorkbench === 'customer-service' ? (
          <CustomerServiceWorkbench />
        ) : (
          <OperationsWorkbench />
        )}
      </div>
    </div>
  );
}