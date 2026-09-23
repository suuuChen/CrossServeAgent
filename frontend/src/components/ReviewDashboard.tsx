import { useState } from 'react';

export default function ReviewDashboard() {
  const [reviewInput, setReviewInput] = useState('');
  const [productUrl, setProductUrl] = useState('');
  const [analysisType, setAnalysisType] = useState<'sentiment' | 'topics' | 'keywords'>('sentiment');
  const [analyzing, setAnalyzing] = useState(false);
  const [results, setResults] = useState<any>(null);

  const handleAnalyze = async (): Promise<void> => {
    if (!reviewInput && !productUrl) return;
    
    setAnalyzing(true);
    setTimeout(() => {
      setResults({
        total_reviews: 1247,
        avg_rating: 4.2,
        sentiment_distribution: {
          positive: 68,
          neutral: 22,
          negative: 10
        },
        top_topics: [
          { topic: '产品质量', percentage: 35, sentiment: 'positive' },
          { topic: '物流速度', percentage: 28, sentiment: 'mixed' },
          { topic: '客服服务', percentage: 18, sentiment: 'positive' },
          { topic: '价格合理性', percentage: 12, sentiment: 'neutral' },
          { topic: '包装完好', percentage: 7, sentiment: 'positive' }
        ],
        key_phrases: [
          '质量很好', '物流快', '性价比高', '客服态度好',
          '包装精美', '使用方便', '物超所值', '推荐购买'
        ],
        recent_reviews: [
          { rating: 5, text: '产品质量非常好，物流也很快！', date: '2024-01-15', sentiment: 'positive' },
          { rating: 4, text: '整体不错，就是包装可以再好一点', date: '2024-01-14', sentiment: 'positive' },
          { rating: 3, text: '一般般吧，没有想象中那么好', date: '2024-01-13', sentiment: 'neutral' },
          { rating: 2, text: '物流太慢了，等了很久', date: '2024-01-12', sentiment: 'negative' },
          { rating: 5, text: '超级满意，会再次购买！', date: '2024-01-11', sentiment: 'positive' }
        ]
      });
      setAnalyzing(false);
    }, 1500);
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
              <label className="text-xs text-slate-500 block mb-1.5">竞品ASIN或商品链接</label>
              <input
                type="text"
                value={productUrl}
                onChange={(e) => setProductUrl(e.target.value)}
                placeholder="B08N5WRWNW 或 https://..."
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="text-center text-xs text-slate-400">— 或者 —</div>

            <div>
              <label className="text-xs text-slate-500 block mb-1.5">直接粘贴评论内容</label>
              <textarea
                rows={5}
                value={reviewInput}
                onChange={(e) => setReviewInput(e.target.value)}
                placeholder="粘贴多条评论，每条一行..."
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="text-xs text-slate-500 block mb-2">分析类型</label>
              <div className="space-y-2">
                {[
                  { value: 'sentiment', label: '情感分析', desc: '正面/中性/负面比例' },
                  { value: 'topics', label: '主题聚类', desc: '自动识别讨论主题' },
                  { value: 'keywords', label: '关键词提取', desc: '高频词汇统计' }
                ].map(type => (
                  <button
                    key={type.value}
                    onClick={() => setAnalysisType(type.value as any)}
                    className={`w-full text-left px-4 py-3 rounded-lg border transition ${
                      analysisType === type.value
                        ? 'bg-blue-50 border-blue-400 text-blue-700'
                        : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                    }`}
                  >
                    <div className="font-medium text-sm">{type.label}</div>
                    <div className={`text-xs mt-0.5 ${analysisType === type.value ? 'text-blue-600' : 'text-slate-400'}`}>
                      {type.desc}
                    </div>
                  </button>
                ))}
              </div>
            </div>

            <button
              onClick={handleAnalyze}
              disabled={analyzing || (!reviewInput && !productUrl)}
              className="w-full py-3 bg-gradient-to-r from-blue-500 to-cyan-500 text-white text-sm font-medium rounded-lg hover:from-blue-600 hover:to-cyan-600 disabled:opacity-50 disabled:cursor-not-allowed transition shadow-md"
            >
              {analyzing ? '分析中...' : '开始分析'}
            </button>
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
                  {results.top_topics.map((topic: any, idx: number) => (
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
                  {results.key_phrases.map((phrase: string, idx: number) => (
                    <span key={idx} className="px-3 py-1.5 bg-gradient-to-r from-blue-50 to-cyan-50 text-blue-700 text-sm rounded-full border border-blue-200">
                      {phrase}
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