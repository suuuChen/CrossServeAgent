import axios from 'axios';

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

export default api;