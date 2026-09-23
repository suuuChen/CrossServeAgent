import axios from 'axios';
import type {
  PendingSessionsResponse,
  HumanTakeoverResponse,
  AnalyzeResult,
  ReviewItem,
} from '../types';

const api = axios.create({
  baseURL: 'http://localhost:8000/api/v1',
  timeout: 30000,
});

export const chatApi = {
  sendMessage: async (message: string, language: string, sessionId?: string) => {
    const response = await api.post('/chat', {
      message,
      language,
      session_id: sessionId,
    });
    return response.data;
  },
};

export const listingApi = {
  generate: async (product: any, platform: string, variants: number, language: string = 'en') => {
    const response = await api.post('/listing/generate', {
      product,
      platform,
      variants,
      language,
    });
    return response.data;
  },
};

export const humanTransferApi = {
  listPending: async (): Promise<PendingSessionsResponse> => {
    const response = await api.get('/sessions/pending-human');
    return response.data;
  },

  takeover: async (sessionId: string, agentName: string): Promise<HumanTakeoverResponse> => {
    const response = await api.post(`/sessions/${sessionId}/human-takeover`, null, {
      params: { agent_name: agentName },
    });
    return response.data;
  },
};

export const reviewApi = {
  crawl: async (platform: string, productId: string, maxReviews: number = 50) => {
    const response = await api.post('/reviews/crawl', {
      platform,
      product_id: productId,
      max_reviews: maxReviews,
    });
    return response.data;
  },

  analyze: async (reviews: ReviewItem[]): Promise<{ success: boolean; result: AnalyzeResult }> => {
    const response = await api.post('/reviews/analyze', {
      reviews: reviews.map(r => ({
        content: r.content,
        rating: r.rating ?? 0,
      })),
    });
    return response.data;
  },

  negativeAlert: async (
    reviews: ReviewItem[],
    productLabel?: string,
    alertThresholdPct: number = 15,
    keywordFreqThreshold: number = 3
  ) => {
    const response = await api.post('/reviews/negative-alert', {
      reviews: reviews.map(r => ({
        content: r.content,
        rating: r.rating ?? 0,
      })),
      product_label: productLabel,
      alert_threshold_pct: alertThresholdPct,
      keyword_freq_threshold: keywordFreqThreshold,
    });
    return response.data;
  },

  compareCrawl: async (products: Array<{ platform: string; product_id: string; label?: string }>, maxReviews: number = 50) => {
    const response = await api.post('/reviews/compare-crawl', {
      products,
      max_reviews: maxReviews,
    });
    return response.data;
  },

  generateMock: async (count: number = 50, productCategory?: string, sentimentBias: string = 'neutral') => {
    const response = await api.post('/reviews/generate-mock', {
      count,
      product_category: productCategory,
      sentiment_bias: sentimentBias,
    });
    return response.data;
  },
};

export default api;