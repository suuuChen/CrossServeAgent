import { useState } from 'react';
import ListingGenerator from './ListingGenerator';
import ReviewDashboard from './ReviewDashboard';
import AdGenerator from './AdGenerator';
import OperationsDashboard from './OperationsDashboard';

type OperationsTab = 'listing' | 'reviews' | 'ads' | 'dashboard';

export default function OperationsWorkbench() {
  const [activeTab, setActiveTab] = useState<OperationsTab>('listing');

  const tabs: { id: OperationsTab; label: string; desc: string }[] = [
    { id: 'listing', label: '商品Listing', desc: '多平台自动生成' },
    { id: 'reviews', label: '评论分析', desc: '情感与主题聚类' },
    { id: 'ads', label: '广告词生成', desc: 'PPC智能建议' },
    { id: 'dashboard', label: '数据报表', desc: '运营统计分析' },
  ];

  const renderContent = (): React.ReactNode => {
    switch (activeTab) {
      case 'listing':
        return <ListingGenerator />;
      case 'reviews':
        return <ReviewDashboard />;
      case 'ads':
        return <AdGenerator />;
      case 'dashboard':
        return <OperationsDashboard />;
      default:
        return null;
    }
  };

  return (
    <div className="flex h-full min-h-0 bg-gradient-to-br from-slate-50 to-purple-50">
      {/* 左侧导航 - 只保留功能按钮列表 */}
      <div className="w-64 bg-white border-r border-slate-200 flex flex-col shrink-0">

        {/* 功能导航按钮 */}
        <div className="flex-1 overflow-y-auto p-3 pt-6">
          <nav className="space-y-1.5">
            {tabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`w-full text-left px-4 py-3 rounded-lg text-sm font-medium transition-all ${
                  activeTab === tab.id
                    ? 'bg-gradient-to-r from-purple-500 to-purple-600 text-white shadow-md shadow-purple-200'
                    : 'text-slate-700 hover:bg-slate-50 hover:text-slate-900'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* 底部平台标识 */}
        <div className="p-4 border-t border-slate-100 shrink-0">
          <div className="px-3 py-2 bg-slate-50 rounded-lg">
            <div className="text-xs text-slate-500 mb-2">支持平台</div>
            <div className="flex gap-2">
              <span className="px-2 py-1 bg-amber-100 text-amber-700 text-xs font-medium rounded-md">Amazon</span>
              <span className="px-2 py-1 bg-orange-100 text-orange-700 text-xs font-medium rounded-md">Temu</span>
              <span className="px-2 py-1 bg-slate-800 text-white text-xs font-medium rounded-md">TikTok</span>
            </div>
          </div>
        </div>
      </div>

      {/* 右侧内容区域 */}
      <div className="flex-1 flex flex-col overflow-hidden min-h-0">
        <div className="flex-1 overflow-y-auto min-h-0">
          {renderContent()}
        </div>
      </div>
    </div>
  );
}