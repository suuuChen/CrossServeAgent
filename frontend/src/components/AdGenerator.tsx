import { useState } from 'react';

const AD_PLATFORMS = [
  { id: 'amazon_ppc', label: 'Amazon PPC' },
  { id: 'google_ads', label: 'Google Ads' },
  { id: 'facebook_ads', label: 'Facebook Ads' },
  { id: 'tiktok_ads', label: 'TikTok Ads' },
];

export default function AdGenerator() {
  const [productName, setProductName] = useState('');
  const [category, setCategory] = useState('');
  const [targetAudience, setTargetAudience] = useState('');
  const [budget, setBudget] = useState('50');
  const [platform, setPlatform] = useState('amazon_ppc');
  const [language, setLanguage] = useState('zh');
  const [generating, setGenerating] = useState(false);
  const [results, setResults] = useState<any>(null);

  const handleGenerate = async (): Promise<void> => {
    if (!productName) return;
    
    setGenerating(true);
    setTimeout(() => {
      setResults({
        keywords: [
          { keyword: '跑步鞋男', search_volume: '10K-100K', cpc: '$0.85', competition: '中', score: 95 },
          { keyword: '运动鞋透气', search_volume: '1K-10K', cpc: '$0.65', competition: '低', score: 92 },
          { keyword: '轻便跑鞋', search_volume: '1K-10K', cpc: '$0.72', competition: '低', score: 89 },
          { keyword: '减震跑步鞋', search_volume: '10K-100K', cpc: '$1.05', competition: '高', score: 87 },
          { keyword: '马拉松跑鞋', search_volume: '1K-10K', cpc: '$0.95', competition: '中', score: 85 },
          { keyword: '健身鞋男士', search_volume: '10K-100K', cpc: '$0.78', competition: '中', score: 83 },
          { keyword: '户外跑步鞋', search_volume: '1K-10K', cpc: '$0.88', competition: '低', score: 81 },
          { keyword: '专业跑鞋', search_volume: '10K-100K', cpc: '$1.15', competition: '高', score: 79 },
        ],
        ad_copies: [
          {
            type: '标题广告',
            headline: '轻便透气跑步鞋 | 减震科技 | 限时特惠',
            description: '专业马拉松级跑鞋，响应式缓震系统，让每一步都舒适自如',
            cta: '立即购买',
            estimated_ctr: '3.2%'
          },
          {
            type: '搜索广告',
            headline: '2024新款运动鞋 | 透气网面 | 5折起',
            description: '超轻量化设计，适合跑步健身，今日下单包邮',
            cta: '查看详情',
            estimated_ctr: '2.8%'
          },
          {
            type: '展示广告',
            headline: '爆款跑步鞋 | 10000+好评 | 7天无理由退换',
            description: '时尚外观+专业性能，运动达人首选',
            cta: '抢购',
            estimated_ctr: '2.5%'
          }
        ],
        budget_suggestion: {
          daily_budget: `$${budget}`,
          estimated_clicks: Math.round(parseFloat(budget) / 0.85 * 10),
          estimated_impressions: Math.round(parseFloat(budget) / 0.85 * 10 * 15),
          estimated_conversions: Math.round(parseFloat(budget) / 0.85 * 10 * 0.03),
          recommended_bid_range: '$0.70 - $1.20'
        }
      });
      setGenerating(false);
    }, 1500);
  };

  return (
    <div className="p-8">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 bg-white rounded-xl border border-slate-200 p-6 h-fit">
          <h2 className="font-semibold text-slate-800 mb-4 flex items-center gap-2">
            <span className="w-1 h-4 bg-orange-500 rounded"></span> 广告投放设置
          </h2>

          <div className="space-y-4">
            <div>
              <label className="text-xs text-slate-500 block mb-1.5">产品名称 *</label>
              <input
                type="text"
                value={productName}
                onChange={(e) => setProductName(e.target.value)}
                placeholder="例如：Air Max Pro 跑步鞋"
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500"
              />
            </div>

            <div>
              <label className="text-xs text-slate-500 block mb-1.5">产品类目</label>
              <input
                type="text"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                placeholder="例如：运动鞋/跑步装备"
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500"
              />
            </div>

            <div>
              <label className="text-xs text-slate-500 block mb-1.5">目标人群</label>
              <textarea
                rows={2}
                value={targetAudience}
                onChange={(e) => setTargetAudience(e.target.value)}
                placeholder="例如：25-40岁男性，跑步爱好者"
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500"
              />
            </div>

            <div>
              <label className="text-xs text-slate-500 block mb-1.5">日预算 ($)</label>
              <input
                type="number"
                value={budget}
                onChange={(e) => setBudget(e.target.value)}
                min="10"
                max="1000"
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500"
              />
            </div>

            <div>
              <label className="text-xs text-slate-500 block mb-2">广告平台</label>
              <div className="grid grid-cols-2 gap-2">
                {AD_PLATFORMS.map(p => (
                  <button
                    key={p.id}
                    onClick={() => setPlatform(p.id)}
                    className={`px-3 py-2.5 text-sm rounded-lg border transition flex items-center justify-center gap-2 ${
                      platform === p.id
                        ? 'bg-orange-50 border-orange-400 text-orange-700 font-medium'
                        : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                    }`}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="text-xs text-slate-500 block mb-2">目标语言</label>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { code: 'zh', label: '中文' },
                  { code: 'en', label: 'English' },
                  { code: 'es', label: 'Español' },
                ].map(lang => (
                  <button
                    key={lang.code}
                    onClick={() => setLanguage(lang.code)}
                    className={`px-3 py-2 text-xs rounded-lg border transition ${
                      language === lang.code
                        ? 'bg-orange-50 border-orange-400 text-orange-700 font-medium'
                        : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                    }`}
                  >
                    {lang.label}
                  </button>
                ))}
              </div>
            </div>

            <button
              onClick={handleGenerate}
              disabled={generating || !productName}
              className="w-full py-3 bg-gradient-to-r from-orange-500 to-red-500 text-white text-sm font-medium rounded-lg hover:from-orange-600 hover:to-red-600 disabled:opacity-50 disabled:cursor-not-allowed transition shadow-md"
            >
              {generating ? '生成中...' : '智能生成广告'}
            </button>
          </div>
        </div>

        <div className="lg:col-span-2 space-y-6">
          {results ? (
            <>
              <div className="grid grid-cols-4 gap-4">
                <div className="bg-white rounded-xl border border-slate-200 p-4">
                  <div className="text-xs text-slate-500 mb-1">日预算</div>
                  <div className="text-xl font-bold text-orange-600">{results.budget_suggestion.daily_budget}</div>
                </div>
                <div className="bg-white rounded-xl border border-slate-200 p-4">
                  <div className="text-xs text-slate-500 mb-1">预估点击</div>
                  <div className="text-xl font-bold text-blue-600">{results.budget_suggestion.estimated_clicks}</div>
                </div>
                <div className="bg-white rounded-xl border border-slate-200 p-4">
                  <div className="text-xs text-slate-500 mb-1">预估展示</div>
                  <div className="text-xl font-bold text-purple-600">{results.budget_suggestion.estimated_impressions.toLocaleString()}</div>
                </div>
                <div className="bg-white rounded-xl border border-slate-200 p-4">
                  <div className="text-xs text-slate-500 mb-1">预估转化</div>
                  <div className="text-xl font-bold text-green-600">{results.budget_suggestion.estimated_conversions}</div>
                </div>
              </div>

              <div className="bg-white rounded-xl border border-slate-200 p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-semibold text-slate-800">推荐关键词</h3>
                  <span className="text-xs text-slate-500">建议出价: {results.budget_suggestion.recommended_bid_range}</span>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-200">
                        <th className="text-left py-3 px-2 text-slate-600 font-medium">关键词</th>
                        <th className="text-left py-3 px-2 text-slate-600 font-medium">搜索量</th>
                        <th className="text-left py-3 px-2 text-slate-600 font-medium">CPC</th>
                        <th className="text-left py-3 px-2 text-slate-600 font-medium">竞争度</th>
                        <th className="text-left py-3 px-2 text-slate-600 font-medium">评分</th>
                      </tr>
                    </thead>
                    <tbody>
                      {results.keywords.map((kw: any, idx: number) => (
                        <tr key={idx} className="border-b border-slate-100 hover:bg-slate-50">
                          <td className="py-3 px-2 font-medium text-slate-800">{kw.keyword}</td>
                          <td className="py-3 px-2 text-slate-600">{kw.search_volume}</td>
                          <td className="py-3 px-2 text-orange-600 font-medium">{kw.cpc}</td>
                          <td className="py-3 px-2">
                            <span className={`px-2 py-1 text-xs rounded ${
                              kw.competition === '高' ? 'bg-red-100 text-red-700' :
                              kw.competition === '中' ? 'bg-yellow-100 text-yellow-700' :
                              'bg-green-100 text-green-700'
                            }`}>
                              {kw.competition}
                            </span>
                          </td>
                          <td className="py-3 px-2">
                            <div className="flex items-center gap-2">
                              <div className="flex-1 bg-slate-100 rounded-full h-2 max-w-[80px]">
                                <div 
                                  className="bg-gradient-to-r from-orange-500 to-red-500 h-2 rounded-full" 
                                  style={{ width: `${kw.score}%` }}
                                ></div>
                              </div>
                              <span className="text-slate-700 font-medium text-xs">{kw.score}</span>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="bg-white rounded-xl border border-slate-200 p-6">
                <h3 className="font-semibold text-slate-800 mb-4">广告文案建议</h3>
                <div className="space-y-4">
                  {results.ad_copies.map((ad: any, idx: number) => (
                    <div key={idx} className="border border-slate-200 rounded-lg p-4 hover:border-orange-300 transition">
                      <div className="flex items-center justify-between mb-3">
                        <span className="px-2 py-1 bg-orange-100 text-orange-700 text-xs font-medium rounded">{ad.type}</span>
                        <span className="text-xs text-green-600 font-medium">预计CTR: {ad.estimated_ctr}</span>
                      </div>
                      <div className="mb-2">
                        <div className="text-xs text-slate-500 mb-1">标题</div>
                        <div className="text-base font-semibold text-slate-800">{ad.headline}</div>
                      </div>
                      <div className="mb-3">
                        <div className="text-xs text-slate-500 mb-1">描述</div>
                        <div className="text-sm text-slate-700">{ad.description}</div>
                      </div>
                      <div className="flex items-center justify-end">
                        <span className="px-4 py-2 bg-gradient-to-r from-orange-500 to-red-500 text-white text-sm font-medium rounded-lg cursor-pointer hover:from-orange-600 hover:to-red-600">
                          {ad.cta}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <div className="bg-white rounded-xl border border-slate-200 p-12 text-center">
              <div className="w-20 h-20 mx-auto rounded-full bg-gradient-to-br from-orange-500 to-red-500 flex items-center justify-center text-4xl mb-4">
                广告
              </div>
              <h3 className="text-lg font-semibold text-slate-700 mb-2">PPC智能广告生成器</h3>
              <p className="text-sm text-slate-500 mb-4">
                基于产品信息和目标受众，AI智能生成<br/>
                高转化率的关键词和广告文案
              </p>
              <div className="flex items-center justify-center gap-3 text-xs text-slate-400">
                <span className="px-3 py-1 bg-slate-100 rounded-full">关键词推荐</span>
                <span className="px-3 py-1 bg-slate-100 rounded-full">文案优化</span>
                <span className="px-3 py-1 bg-slate-100 rounded-full">ROI预测</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}