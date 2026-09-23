import { useState } from 'react';
import { reviewApi } from '../api';

export default function ReviewDashboard() {
  const [reviewInput, setReviewInput] = useState('');
  const [productUrl, setProductUrl] = useState('');
  const [analysisType, setAnalysisType] = useState<'sentiment' | 'topics' | 'keywords'>('sentiment');
  const [analyzing, setAnalyzing] = useState(false);
  const [results, setResults] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [crawling, setCrawling] = useState(false);
  const [alerting, setAlerting] = useState(false);
  const [alerts, setAlerts] = useState<any>(null);

  const parsePastedReviews = () => {
    const lines = reviewInput.split('\n').map((l: string) => l.trim()).filter(Boolean);
    return lines.map((line: string) => {
      const m = line.match(/^(\d+(?:\.\d+)?)\s*[星\*]\s*(.+)$/);
      if (m) return { rating: parseFloat(m[1]), content: m[2].trim() };
      return { content: line };
    });
  };

  const handleCrawl = async (): Promise<void> => {
    if (!productUrl.trim()) return;
    setCrawling(true);
    setError(null);
    try {
      const data = await reviewApi.crawl('amazon', productUrl.trim(), 50);
      const crawled = (data.reviews || []).map((r: any) => ({ content: r.content, rating: r.rating || 0 }));
      setReviewInput(crawled.map((r: any) => `${r.rating}⭐ ${r.content}`).join('\n'));
      setError(null);
    } catch (e: any) {
      setError(e?.message || '爬取失败（无权限时后端自动降级 mock）');
    } finally {
      setCrawling(false);
    }
  };

  const handleMock = async (): Promise<void> => {
    setCrawling(true);
    setError(null);
    try {
      const data = await reviewApi.generateMock(50, 'earphone', 'neutral');
      const mocks = (data.reviews || []).map((r: any) => r.content);
      setReviewInput(mocks.join('\n'));
    } catch (e: any) {
      setError(e?.message || '生成模拟数据失败');
    } finally {
      setCrawling(false);
    }
  };

  const handleAnalyze = async (): Promise<void> => {
    const reviews = parsePastedReviews();
    if (reviews.length === 0) {
      setError('请先粘贴 / 爬取 / 生成一些评论');
      return;
    }
    setAnalyzing(true);
    setError(null);
    setAlerts(null);
    try {
      const data = await reviewApi.analyze(reviews);
      setResults(data.result);
    } catch (e: any) {
      setError(e?.message || '分析失败');
    } finally {
      setAnalyzing(false);
    }
  };

  const handleNegativeAlert = async (): Promise<void> => {
    const reviews = parsePastedReviews();
    if (reviews.length === 0) return;
    setAlerting(true);
    try {
      const data = await reviewApi.negativeAlert(reviews);
      setAlerts(data.result);
    } catch (e: any) {
      setError(e?.message || '差评告警失败');
    } finally {
      setAlerting(false);
    }
  };

  const handleRunAll = async () => {
    await handleAnalyze();
    await handleNegativeAlert();
  };

  return (
    <div className="p-8">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 bg-white rounded-xl border border-slate-200 p-6 h-fit">
          <h2 className="font-semibold text-slate-800 mb-4 flex items-center gap-2">
            <span className="w-1 h-4 bg-blue-500 rounded"></span> 评论分析设置
          </h2>

          <div className="space-y-4">
            <div>
              <label className="text-xs text-slate-500 block mb-1.5">竞品ASIN或商品链接（爬取用）</label>
              <input
                type="text"
                value={productUrl}
                onChange={(e) => setProductUrl(e.target.value)}
                placeholder="B08N5WRWNW 或 https://..."
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                onClick={handleCrawl}
                disabled={crawling || !productUrl.trim()}
                className="mt-2 w-full py-2 bg-blue-500 text-white text-xs font-medium rounded hover:bg-blue-600 disabled:opacity-50"
              >
                {crawling ? '爬取中...' : '🔍 从 Amazon 爬取评论'}
              </button>
            </div>

            <div className="text-center text-xs text-slate-400">— 或者 —</div>

            <div>
              <label className="text-xs text-slate-500 block mb-1.5">直接粘贴评论内容</label>
              <textarea
                rows={5}
                value={reviewInput}
                onChange={(e) => setReviewInput(e.target.value)}
                placeholder={'每条一行，可选评分前缀，例如：\n4⭐ 质量很好\nThis is great\n2⭐ 包装破损'}
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono"
              />
              <div className="mt-1 text-[10px] text-slate-400">已粘贴 {reviewInput.split('\n').filter(l => l.trim()).length} 行</div>
            </div>

            <button
              onClick={handleMock}
              disabled={crawling}
              className="w-full py-2 bg-emerald-500 text-white text-xs font-medium rounded hover:bg-emerald-600 disabled:opacity-50"
            >
              {crawling ? '生成中...' : '🎲 生成 50 条模拟评论（无需输入）'}
            </button>

            {error && (
              <div className="p-2 bg-red-50 border border-red-200 text-red-600 text-xs rounded">⚠️ {error}</div>
            )}

            <div className="space-y-2 pt-2 border-t border-slate-100">
              <div className="text-[11px] text-slate-500 font-semibold">分析操作</div>
              <button
                onClick={handleRunAll}
                disabled={analyzing || alerting}
                className="w-full py-2 bg-gradient-to-r from-blue-500 to-cyan-500 text-white text-sm font-medium rounded-lg hover:from-blue-600 hover:to-cyan-600 disabled:opacity-50 disabled:cursor-not-allowed transition shadow-md"
              >
                {analyzing ? '分析中...' : '🚀 一键分析 + 差评告警'}
              </button>
              <div className="flex gap-2">
                <button
                  onClick={handleAnalyze}
                  disabled={analyzing}
                  className="flex-1 py-2 bg-blue-500 text-white text-xs rounded-lg hover:bg-blue-600 disabled:opacity-50"
                >
                  {analyzing ? '分析中' : '仅情感/主题'}
                </button>
                <button
                  onClick={handleNegativeAlert}
                  disabled={alerting}
                  className="flex-1 py-2 bg-red-500 text-white text-xs rounded-lg hover:bg-red-600 disabled:opacity-50"
                >
                  {alerting ? '告警中' : '差评告警'}
                </button>
              </div>
            </div>
          </div>
        </div>

        <div className="lg:col-span-2 space-y-6">
          {results ? (
            <>
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-white rounded-xl border border-slate-200 p-5">
                  <div className="text-xs text-slate-500 mb-1">总评论数</div>
                  <div className="text-2xl font-bold text-slate-800">{results.total_reviews.toLocaleString()}</div>
                </div>
                <div className="bg-white rounded-xl border border-slate-200 p-5">
                  <div className="text-xs text-slate-500 mb-1">平均评分</div>
                  <div className="text-2xl font-bold text-yellow-600">{results.avg_rating}</div>
                </div>
                <div className="bg-white rounded-xl border border-slate-200 p-5">
                  <div className="text-xs text-slate-500 mb-1">好评率</div>
                  <div className="text-2xl font-bold text-green-600">{results.sentiment_distribution.positive}%</div>
                </div>
              </div>

              <div className="bg-white rounded-xl border border-slate-200 p-6">
                <h3 className="font-semibold text-slate-800 mb-4">情感分布</h3>
                <div className="space-y-3">
                  {[
                    { label: '正面评价', value: results.sentiment_distribution.positive, color: 'bg-green-500' },
                    { label: '中性评价', value: results.sentiment_distribution.neutral, color: 'bg-yellow-500' },
                    { label: '负面评价', value: results.sentiment_distribution.negative, color: 'bg-red-500' }
                  ].map(item => (
                    <div key={item.label}>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-slate-600">{item.label}</span>
                        <span className="font-medium text-slate-800">{item.value}%</span>
                      </div>
                      <div className="w-full bg-slate-100 rounded-full h-2.5">
                        <div className={`${item.color} h-2.5 rounded-full transition-all`} style={{ width: `${item.value}%` }}></div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-white rounded-xl border border-slate-200 p-6">
                <h3 className="font-semibold text-slate-800 mb-4">热门话题</h3>
                <div className="space-y-3">
                  {(results.top_themes || results.top_topics || []).map((topic: any, idx: number) => (
                    <div key={idx} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                      <div className="flex items-center gap-3">
                        <span className="text-lg font-bold text-slate-300">#{idx + 1}</span>
                        <span className="font-medium text-slate-700">{topic.topic}</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className={`px-2 py-1 text-xs font-medium rounded ${
                          topic.sentiment === 'positive' ? 'bg-green-100 text-green-700' :
                          topic.sentiment === 'negative' ? 'bg-red-100 text-red-700' :
                          'bg-yellow-100 text-yellow-700'
                        }`}>
                          {topic.sentiment === 'positive' ? '正面' : topic.sentiment === 'negative' ? '负面' : '混合'}
                        </span>
                        <span className="text-sm font-semibold text-slate-700 w-12 text-right">{topic.percentage}%</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-white rounded-xl border border-slate-200 p-6">
                <h3 className="font-semibold text-slate-800 mb-4">高频关键词</h3>
                <div className="flex flex-wrap gap-2">
                  {(results.keywords || results.key_phrases || []).map((phrase: any, idx: number) => (
                    <span key={idx} className="px-3 py-1.5 bg-gradient-to-r from-blue-50 to-cyan-50 text-blue-700 text-sm rounded-full border border-blue-200">
                      {typeof phrase === 'string' ? phrase : `${phrase.word || phrase.keyword || ''}${phrase.count ? ` ×${phrase.count}` : ''}`}
                    </span>
                  ))}
                </div>
              </div>

              <div className="bg-white rounded-xl border border-slate-200 p-6">
                <h3 className="font-semibold text-slate-800 mb-4">最近评论</h3>
                <div className="space-y-3">
                  {results.recent_reviews.map((review: any, idx: number) => (
                    <div key={idx} className="border-b border-slate-100 pb-3 last:border-0">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className="text-yellow-500">{review.rating}分</span>
                          <span className={`px-2 py-0.5 text-xs font-medium rounded ${
                            review.sentiment === 'positive' ? 'bg-green-100 text-green-700' :
                            review.sentiment === 'negative' ? 'bg-red-100 text-red-700' :
                            'bg-gray-100 text-gray-700'
                          }`}>
                            {review.sentiment === 'positive' ? '正面' : review.sentiment === 'negative' ? '负面' : '中性'}
                          </span>
                        </div>
                        <span className="text-xs text-slate-400">{review.date}</span>
                      </div>
                      <p className="text-sm text-slate-700">{review.text}</p>
                    </div>
                  ))}
                </div>
              </div>

              {alerts && (
                <div className="bg-gradient-to-br from-red-50 to-orange-50 rounded-xl border border-red-200 p-6">
                  <h3 className="font-semibold text-red-800 mb-4 flex items-center gap-2">
                    ⚠️ 差评告警
                    {alerts.negative_count !== undefined && (
                      <span className="px-2 py-0.5 bg-red-500 text-white text-xs rounded-full">
                        {alerts.negative_count} 条 / {alerts.total_checked || ''}
                      </span>
                    )}
                  </h3>
                  <div className="space-y-4">
                    {alerts.high_risk_keywords?.length > 0 && (
                      <div>
                        <div className="text-xs font-semibold text-red-700 mb-2">🔴 高风险关键词</div>
                        <div className="flex flex-wrap gap-2">
                          {alerts.high_risk_keywords.map((k: any, i: number) => (
                            <span key={i} className="px-2 py-1 bg-red-500 text-white text-xs rounded-full">
                              {typeof k === 'string' ? k : `${k.keyword || k.word || ''} ×${k.count || 1}`}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    {alerts.alerts?.length > 0 && (
                      <div>
                        <div className="text-xs font-semibold text-red-700 mb-2">📋 告警详情</div>
                        <div className="space-y-2">
                          {alerts.alerts.slice(0, 8).map((a: any, i: number) => (
                            <div key={i} className="bg-white p-2 rounded border border-red-100 text-xs">
                              <div className="text-red-600 font-medium">{a.category || a.topic || '问题'}</div>
                              <div className="text-slate-600 mt-0.5">{a.message || a.summary || a.suggestion || ''}</div>
                              {a.recommendations?.length > 0 && (
                                <div className="mt-1 text-emerald-600">💡 {a.recommendations.join('；')}</div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    {alerts.improvement_suggestions?.length > 0 && (
                      <div>
                        <div className="text-xs font-semibold text-emerald-700 mb-2">💡 改进建议</div>
                        <ul className="list-disc list-inside text-xs text-slate-700 space-y-1">
                          {alerts.improvement_suggestions.map((s: string, i: number) => (
                            <li key={i}>{s}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="bg-white rounded-xl border border-slate-200 p-12 text-center">
              <div className="w-20 h-20 mx-auto rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center text-4xl mb-4">
                评论
              </div>
              <h3 className="text-lg font-semibold text-slate-700 mb-2">竞品评论智能分析</h3>
              <p className="text-sm text-slate-500 mb-4">
                上传或粘贴竞品评论，AI自动进行<br/>
                情感分析、主题聚类、关键词提取
              </p>
              <div className="flex items-center justify-center gap-3 text-xs text-slate-400">
                <span className="px-3 py-1 bg-slate-100 rounded-full">情感识别</span>
                <span className="px-3 py-1 bg-slate-100 rounded-full">主题聚类</span>
                <span className="px-3 py-1 bg-slate-100 rounded-full">关键词云</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}