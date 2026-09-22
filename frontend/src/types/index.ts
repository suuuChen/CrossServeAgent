export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatResponse {
  message: string;
  session_id?: string;
  intent: string;
  confidence: number;
  language: string;
  should_transfer: boolean;
  compliance_blocked: boolean;
  rag_confidence?: number;
}

export interface ListingProduct {
  name: string;
  brand: string;
  category: string;
  description: string;
  key_features: string[];
  target_audience: string;
}

export interface ListingResult {
  variants: Array<{
    title: string;
    bullet_points: string[];
    description: string;
    a_plus_content?: {
      brand_story: string;
      product_highlights: string[];
      use_cases: string[];
      specs: string[];
    };
  }>;
}