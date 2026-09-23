export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface ConversationSummary {
  turn_count: number;
  emotion: string;
  emotion_label: string;
  order_no?: string;
  order_text?: string;
  queries_text?: string;
  summary: string;
  translated_summary?: string;
  summary_language?: string;
}

export interface ChatResponse {
  success: boolean;
  response: string;
  session_id?: string;
  intent: string;
  confidence: number;
  language: string;
  should_transfer: boolean;
  compliance_blocked: boolean;
  rag_confidence?: number;
  context_used?: Record<string, number>;
  processing_time_ms?: number;
  transfer_reason?: string;
  conversation_summary?: ConversationSummary;
  session_status?: string;
  compliance_details?: Record<string, any>;
  error?: string;
}

export interface PendingHumanSession {
  session_id: string;
  status: string;
  transfer_reason: string;
  intent: string;
  turn_count: number;
  language_detected: string;
  transfer_timestamp: string;
  conversation_summary: ConversationSummary;
  last_activity: string;
}

export interface PendingSessionsResponse {
  success: boolean;
  total: number;
  sessions: PendingHumanSession[];
}

export interface HumanTakeoverResponse {
  success: boolean;
  session_id: string;
  new_status: string;
  agent_name: string;
  message: string;
}

export interface ReviewItem {
  content: string;
  rating?: number;
  title?: string;
  date?: string;
}

export interface ThemeResult {
  theme: string;
  percentage: number;
  sentiment: string;
}

export interface AnalyzeResult {
  total_reviews: number;
  avg_rating: number;
  sentiment_distribution: {
    positive: number;
    neutral: number;
    negative: number;
  };
  top_themes: ThemeResult[];
  key_phrases: string[];
  cluster_labels?: Record<number, string>;
  recommendations?: string[];
  negative_alerts?: {
    high_risk_keywords: string[];
    negative_sentiment_topics: string[];
    product_label?: string;
  };
  recent_reviews?: Array<{
    text: string;
    rating?: number;
    sentiment: string;
    date?: string;
  }>;
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