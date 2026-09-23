import { useState } from 'react';

export default function OperationsDashboard() {
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d'>('30d');

  const statsData = {
    listing_generated: 156,
    reviews_analyzed: 2847,
    ads_created: 89,
    languages_used: 5,
    platforms_connected: 3,
  };

  const recentActivities = [
    { type: 'listing', product: 'Air Max Pro 跑步鞋', platform: 'Amazon', language: '英语', time: '5分钟前', status: 'success' },
    { type: 'review', product: '竞品 B08N5WRWNW', platform: 'Amazon', language: '-', time: '15分钟前', status: 'success' },
    { type: 'ad', product: '运动手表 智能穿戴', platform: 'Google Ads', language: '中文', time: '1小时前', status: 'success' },
    { type: 'listing', product: '无线蓝牙耳机', platform: 'TikTok Shop', language: '西班牙语', time: '2小时前', status: 'success' },
    { type: 'review', product: '竞品 B0CXXXXXXX', platform: 'Temu', language: '-', time: '3小时前', status: 'warning' },
    { type: 'ad', product: '瑜伽垫 防滑', platform: 'Facebook Ads', language: '法语', time: '5小时前', status: 'success' },
    { type: 'listing', product: '便携式充电宝', platform: 'Amazon', language: '德语', time: '昨天', status: 'success' },
    { type: 'review', product: '竞品 B0DYYYYYYY', platform: 'Amazon', language: '-', time: '昨天', status: 'error' },
  ];

  const platformStats = [
    { platform: 'Amazon', listings: 89, reviews: 1523, ads: 45, color: 'amber' },
    { platform: 'Temu', listings: 42, reviews: 856, ads: 23, color: 'orange' },
    { platform: 'TikTok Shop', listings: 25, reviews: 468, ads: 21, color: 'slate' },
  ];

  const languageDistribution = [
    { language: '英语', percentage: 36, count: 54 },
    { language: '中文', percentage: 26, count: 39 },
    { language: '西班牙语', percentage: 19, count: 28 },
    { language: '法语', percentage: 13, count: 19 },
    { language: '德语', percentage: 6, count: 11 },
  ];

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold text-slate-800">运营数据总览</h2>
        <div className="flex gap-2">
          {(['7d', '30d', '90d'] as const).map(range => (
            <button
              key={range}
              onClick={() => setTimeRange(range)}
              className={`px-4 py-2 text-sm rounded-lg border transition ${
                timeRange === range
                  ? 'bg-purple-50 border-purple-400 text-purple-700 font-medium'
                  : 'border-slate-200 text-slate-600 hover:bg-slate-50'
              }`}
            >
              {range === '7d' ? '近7天' : range === '30d' ? '近30天' : '近90天'}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-5 gap-4 mb-6">
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <div className="flex items-center justify-between mb-2">
            <div className="text-xs text-slate-500">Listing生成</div>
          </div>
          <div className="text-3xl font-bold text-slate-800">{statsData.listing_generated}</div>
          <div className="text-xs text-green-600 mt-1">较上期增长 12%</div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <div className="flex items-center justify-between mb-2">
            <div className="text-xs text-slate-500">评论分析</div>
          </div>
          <div className="text-3xl font-bold text-slate-800">{statsData.reviews_analyzed.toLocaleString()}</div>
          <div className="text-xs text-green-600 mt-1">较上期增长 23%</div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <div className="flex items-center justify-between mb-2">
            <div className="text-xs text-slate-500">广告创建</div>
          </div>
          <div className="text-3xl font-bold text-slate-800">{statsData.ads_created}</div>
          <div className="text-xs text-green-600 mt-1">较上期增长 8%</div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <div className="flex items-center justify-between mb-2">
            <div className="text-xs text-slate-500">支持语言</div>
          </div>
          <div className="text-3xl font-bold text-slate-800">{statsData.languages_used}</div>
          <div className="text-xs text-slate-400 mt-1">多语言覆盖</div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <div className="flex items-center justify-between mb-2">
            <div className="text-xs text-slate-500">连接平台</div>
          </div>
          <div className="text-3xl font-bold text-slate-800">{statsData.platforms_connected}</div>
          <div className="text-xs text-slate-400 mt-1">主流平台</div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6 mb-6">
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <h3 className="font-semibold text-slate-800 mb-4">各平台数据</h3>
          <div className="space-y-4">
            {platformStats.map(platform => (
              <div key={platform.platform} className="border border-slate-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-slate-800">{platform.platform}</span>
                  </div>
                  <span className={`px-2 py-1 text-xs font-medium rounded bg-${platform.color}-100 text-${platform.color}-700`}>
                    活跃
                  </span>
                </div>
                <div className="grid grid-cols-3 gap-3 text-center">
                  <div>
                    <div className="text-xs text-slate-500">Listing</div>
                    <div className="text-lg font-bold text-slate-800">{platform.listings}</div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500">评论</div>
                    <div className="text-lg font-bold text-slate-800">{platform.reviews}</div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500">广告</div>
                    <div className="text-lg font-bold text-slate-800">{platform.ads}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <h3 className="font-semibold text-slate-800 mb-4">语言使用分布</h3>
          <div className="space-y-3">
            {languageDistribution.map((lang, idx) => (
              <div key={lang.language}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-slate-700">{lang.language}</span>
                  <span className="text-slate-500">{lang.count} 个 ({lang.percentage}%)</span>
                </div>
                <div className="w-full bg-slate-100 rounded-full h-2.5">
                  <div 
                    className="bg-gradient-to-r from-purple-500 to-pink-500 h-2.5 rounded-full transition-all" 
                    style={{ width: `${lang.percentage}%` }}
                  ></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <h3 className="font-semibold text-slate-800 mb-4">最近活动</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200">
                <th className="text-left py-3 px-3 text-slate-600 font-medium">类型</th>
                <th className="text-left py-3 px-3 text-slate-600 font-medium">产品/项目</th>
                <th className="text-left py-3 px-3 text-slate-600 font-medium">平台</th>
                <th className="text-left py-3 px-3 text-slate-600 font-medium">语言</th>
                <th className="text-left py-3 px-3 text-slate-600 font-medium">时间</th>
                <th className="text-left py-3 px-3 text-slate-600 font-medium">状态</th>
              </tr>
            </thead>
            <tbody>
              {recentActivities.map((activity, idx) => (
                <tr key={idx} className="border-b border-slate-100 hover:bg-slate-50">
                  <td className="py-3 px-3">
                    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium ${
                      activity.type === 'listing' ? 'bg-purple-100 text-purple-700' :
                      activity.type === 'review' ? 'bg-blue-100 text-blue-700' :
                      'bg-orange-100 text-orange-700'
                    }`}>
                      {activity.type === 'listing' ? 'Listing' : activity.type === 'review' ? '评论' : '广告'}
                    </span>
                  </td>
                  <td className="py-3 px-3 font-medium text-slate-800">{activity.product}</td>
                  <td className="py-3 px-3 text-slate-600">{activity.platform}</td>
                  <td className="py-3 px-3 text-slate-600">{activity.language}</td>
                  <td className="py-3 px-3 text-slate-500">{activity.time}</td>
                  <td className="py-3 px-3">
                    <span className={`inline-flex items-center gap-1 text-xs font-medium ${
                      activity.status === 'success' ? 'text-green-600' :
                      activity.status === 'warning' ? 'text-yellow-600' :
                      'text-red-600'
                    }`}>
                      {activity.status === 'success' ? '成功' :
                       activity.status === 'warning' ? '警告' : '失败'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}