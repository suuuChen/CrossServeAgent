import { useState } from 'react';
import { listingApi } from '../api';
import type { ListingProduct, ListingResult } from '../types';

const PLATFORMS = [
  { code: 'amazon', label: 'Amazon', color: 'amber' },
  { code: 'temu', label: 'Temu', color: 'orange' },
  { code: 'tiktok_shop', label: 'TikTok Shop', color: 'slate' },
];

const LANGUAGES = [
  { code: 'en', label: '英语' },
  { code: 'es', label: '西班牙语' },
  { code: 'fr', label: '法语' },
  { code: 'de', label: '德语' },
  { code: 'zh', label: '中文' },
];

export default function ListingGenerator() {
  const [product, setProduct] = useState<ListingProduct>({
    name: 'Air Max Pro 跑步鞋',
    brand: 'Nike',
    category: '跑步鞋',
    description: '轻便透气的跑步鞋，配备响应式缓震系统',
    key_features: ['轻量化设计', '透气网面', '响应式缓震', '耐用橡胶外底', '时尚外观'],
    target_audience: '跑步爱好者和健身人士',
  });
  const [platform, setPlatform] = useState('amazon');
  const [targetLanguage, setTargetLanguage] = useState('zh');
  const [variants, setVariants] = useState(1);
  const [result, setResult] = useState<ListingResult | null>(null);
  const [loading, setLoading] = useState(false);

  const handleGenerate = async (): Promise<void> => {
    setLoading(true);
    try {
      const data = await listingApi.generate(product, platform, variants, targetLanguage);
      setResult(data.result);
    } catch (error) {
      alert('生成失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  const getPlatformColor = (p: string): string => {
    const colors: Record<string, string> = {
      amazon: 'bg-amber-100 text-amber-700',
      temu: 'bg-orange-100 text-orange-700',
      tiktok_shop: 'bg-slate-800 text-white',
    };
    return colors[p] || 'bg-slate-100 text-slate-700';
  };

  return (
    <div className="p-8">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 bg-white rounded-xl border border-slate-200 p-6 h-fit">
          <h2 className="font-semibold text-slate-800 mb-4 flex items-center gap-2">
            <span className="w-1 h-4 bg-purple-500 rounded"></span> 产品信息
          </h2>

          <div className="space-y-4">
            <div>
              <label className="text-xs text-slate-500 block mb-1.5">产品名称 *</label>
              <input
                type="text"
                value={product.name}
                onChange={(e) => setProduct({ ...product, name: e.target.value })}
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-slate-500 block mb-1.5">品牌</label>
                <input
                  type="text"
                  value={product.brand}
                  onChange={(e) => setProduct({ ...product, brand: e.target.value })}
                  className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              </div>
              <div>
                <label className="text-xs text-slate-500 block mb-1.5">类目</label>
                <input
                  type="text"
                  value={product.category}
                  onChange={(e) => setProduct({ ...product, category: e.target.value })}
                  className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              </div>
            </div>

            <div>
              <label className="text-xs text-slate-500 block mb-1.5">产品描述</label>
              <textarea
                rows={2}
                value={product.description}
                onChange={(e) => setProduct({ ...product, description: e.target.value })}
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>

            <div>
              <label className="text-xs text-slate-500 block mb-1.5">核心卖点 (逗号分隔)</label>
              <textarea
                rows={2}
                value={product.key_features.join(', ')}
                onChange={(e) => setProduct({ ...product, key_features: e.target.value.split(',').map(s => s.trim()) })}
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>

            <div>
              <label className="text-xs text-slate-500 block mb-1.5">目标人群</label>
              <input
                type="text"
                value={product.target_audience}
                onChange={(e) => setProduct({ ...product, target_audience: e.target.value })}
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>

            <div className="border-t border-slate-100 pt-4">
              <label className="text-xs text-slate-500 block mb-2">目标平台</label>
              <div className="flex gap-2">
                {PLATFORMS.map(p => (
                  <button
                    key={p.code}
                    onClick={() => setPlatform(p.code)}
                    className={`flex-1 py-2 text-xs rounded-lg border transition ${
                      platform === p.code
                        ? `bg-${p.color}-50 border-${p.color}-400 text-${p.color}-700 font-medium`
                        : 'border-slate-200 text-slate-500 hover:bg-slate-50'
                    }`}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="border-t border-slate-100 pt-4">
              <label className="text-xs text-slate-500 block mb-2">
                目标语言: <span className="text-purple-600 font-semibold">{LANGUAGES.find(l => l.code === targetLanguage)?.label}</span>
              </label>
              <div className="grid grid-cols-3 gap-2">
                {LANGUAGES.map(lang => (
                  <button
                    key={lang.code}
                    onClick={() => setTargetLanguage(lang.code)}
                    className={`px-3 py-2 text-xs rounded-lg border transition ${
                      targetLanguage === lang.code
                        ? 'bg-purple-50 border-purple-400 text-purple-700 font-medium'
                        : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                    }`}
                  >
                    {lang.label}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="text-xs text-slate-500 block mb-1.5">
                变体数量: <span className="text-blue-600 font-semibold">{variants}</span>
              </label>
              <input
                type="range"
                min="1"
                max="5"
                value={variants}
                onChange={(e) => setVariants(parseInt(e.target.value))}
                className="w-full accent-purple-500"
              />
            </div>

            <button
              onClick={handleGenerate}
              disabled={loading || !product.name}
              className="w-full py-3 bg-gradient-to-r from-purple-500 to-pink-500 text-white text-sm font-medium rounded-lg hover:from-purple-600 hover:to-pink-600 disabled:opacity-50 disabled:cursor-not-allowed transition shadow-md"
            >
              {loading ? '生成中...' : '生成多语言Listing'}
            </button>
          </div>
        </div>

        <div className="lg:col-span-2 space-y-6">
          {result ? (
            <>
              <div className="bg-white rounded-xl border border-slate-200 p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-semibold text-slate-800 flex items-center gap-2">
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${getPlatformColor(platform)}`}>
                      {PLATFORMS.find(p => p.code === platform)?.label}
                    </span>
                    生成结果
                  </h3>
                  <span className="text-xs text-slate-400">
                    语言: {LANGUAGES.find(l => l.code === targetLanguage)?.label} | 变体: {variants}个版本
                  </span>
                </div>

                {result.variants && result.variants.length > 0 && (
                  <div className="space-y-6">
                    {result.variants.map((variant: any, idx: number) => (
                      <div key={idx} className="border border-slate-200 rounded-lg p-4">
                        <div className="text-xs text-slate-500 mb-3 font-medium">
                          版本 {idx + 1}
                        </div>
                        
                        <div className="space-y-4">
                          <div>
                            <div className="text-xs text-slate-500 font-medium mb-1">标题 (Title)</div>
                            <div className="text-sm text-slate-800 bg-slate-50 p-3 rounded">{variant.title}</div>
                          </div>

                          {variant.bullet_points && (
                            <div>
                              <div className="text-xs text-slate-500 font-medium mb-2">五点描述 (Bullet Points)</div>
                              <div className="space-y-2">
                                {variant.bullet_points.map((bullet: string, bidx: number) => (
                                  <div key={bidx} className="text-sm text-slate-700 bg-slate-50 p-2 rounded">{bullet}</div>
                                ))}
                              </div>
                            </div>
                          )}

                          {variant.description && (
                            <div>
                              <div className="text-xs text-slate-500 font-medium mb-1">详细描述 (Description)</div>
                              <div className="text-sm text-slate-700 bg-slate-50 p-3 rounded whitespace-pre-wrap">{variant.description}</div>
                            </div>
                          )}

                          {variant.a_plus_content && (
                            <div>
                              <div className="text-xs text-slate-500 font-medium mb-2">A+ 页面内容</div>
                              <div className="grid grid-cols-2 gap-3">
                                {variant.a_plus_content.brand_story && (
                                  <div className="bg-purple-50 p-3 rounded">
                                    <div className="text-xs text-purple-600 font-medium mb-1">品牌故事</div>
                                    <div className="text-xs text-slate-700">{variant.a_plus_content.brand_story}</div>
                                  </div>
                                )}
                                {variant.a_plus_content.product_highlights && (
                                  <div className="bg-blue-50 p-3 rounded">
                                    <div className="text-xs text-blue-600 font-medium mb-1">产品亮点</div>
                                    <ul className="text-xs text-slate-700 list-disc list-inside">
                                      {variant.a_plus_content.product_highlights.map((h: string, hidx: number) => (
                                        <li key={hidx}>{h}</li>
                                      ))}
                                    </ul>
                                  </div>
                                )}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="bg-white rounded-xl border border-slate-200 p-12 text-center">
              <div className="w-20 h-20 mx-auto rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-4xl mb-4">
                Listing
              </div>
              <h3 className="text-lg font-semibold text-slate-700 mb-2">多语言商品Listing生成器</h3>
              <p className="text-sm text-slate-500 mb-4">
                自动生成符合 Amazon / Temu / TikTok Shop 平台规范的<br/>
                多语言商品Listing（标题/五点/描述/A+文案）
              </p>
              <div className="flex items-center justify-center gap-3 text-xs text-slate-400">
                <span className="px-3 py-1 bg-slate-100 rounded-full">支持5种语言</span>
                <span className="px-3 py-1 bg-slate-100 rounded-full">3大平台</span>
                <span className="px-3 py-1 bg-slate-100 rounded-full">A/B变体测试</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}