import { useState, useEffect, useRef } from 'react';
import { chatApi } from '../api';
import type { ChatMessage, ChatResponse } from '../types';

interface ChatPanelProps {
  sessionId: string | null;
  onSessionChange: (sessionId: string) => void;
  onTransfer: () => void;
}

export default function ChatPanel({ sessionId, onSessionChange, onTransfer }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // 买家发送消息
  const handleSend = async (): Promise<void> => {
    const msg = input.trim();
    if (!msg || loading) return;

    // 添加买家消息（左侧）
    setMessages(prev => [...prev, { role: 'user', content: msg }]);
    setInput('');
    setLoading(true);

    try {
      // 调用后端AI客服接口
      const response: ChatResponse = await chatApi.sendMessage(msg, 'auto', sessionId || undefined);
      
      // 显示AI客服回复（右侧）
      setMessages(prev => [...prev, { role: 'assistant', content: response.response }]);
      
      // 保存会话ID
      if (!sessionId && response.session_id) {
        onSessionChange(response.session_id);
      }

      // 如果需要转人工
      if (response.should_transfer) {
        // 显示转人工提示
        setTimeout(() => {
          setMessages(prev => [...prev, { 
            role: 'assistant', 
            content: '您的问题需要人工客服处理，正在为您转接，请稍候...' 
          }]);
          onTransfer();
        }, 500);
      }
    } catch (error) {
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: '抱歉，系统暂时繁忙，请稍后再试或直接联系我们的人工客服。' 
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent): void => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-50">
      
      {/* 欢迎区域 / 空状态 */}
      <div className="flex-1 overflow-y-auto p-6">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center">
            
            {/* 客服头像 */}
            <div className="w-20 h-20 mb-4 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-3xl shadow-lg">
              客服
            </div>

            {/* 欢迎语 */}
            <h2 className="text-xl font-bold text-slate-800 mb-2">
              您好！我是智能客服助手
            </h2>
            <p className="text-sm text-slate-600 max-w-md mb-6">
              我可以帮您查询订单、物流信息、退换货政策等问题。<br />
              请用您熟悉的语言提问，我支持中文、英语、西班牙语、法语、德语。
            </p>

            {/* 常见问题快捷入口 */}
            <div className="w-full max-w-lg space-y-2">
              <div className="text-xs text-slate-500 font-medium mb-2 text-left">常见问题：</div>
              
              {[
                { text: '我的订单什么时候发货？', msg: '我的订单什么时候发货？' },
                { text: '物流查询：我的包裹到哪了？', msg: '我的包裹到哪了？' },
                { text: '如何申请退换货？', msg: '我想退货，怎么操作？' },
                { text: '客服工作时间是几点？', msg: '你们客服工作时间是几点？' },
              ].map((item, index) => (
                <button
                  key={index}
                  onClick={() => {
                    setInput(item.msg);
                    // 自动聚焦输入框
                    document.querySelector('textarea')?.focus();
                  }}
                  className="w-full text-left px-4 py-3 bg-white rounded-xl border border-slate-200 hover:border-blue-300 hover:bg-blue-50 transition-all text-sm text-slate-700 shadow-sm hover:shadow-md"
                >
                  {item.text}
                </button>
              ))}
            </div>

          </div>
        ) : (
          /* 消息列表 */
          <div className="space-y-4 pb-4">
            {messages.map((msg, index) => (
              <div key={index} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`flex items-end gap-2 max-w-[75%] ${
                  msg.role === 'user' ? 'flex-row-reverse' : ''
                }`}>
                  
                  {/* 头像 */}
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm shrink-0 ${
                    msg.role === 'user'
                      ? 'bg-gradient-to-br from-green-400 to-green-600 text-white'
                      : 'bg-gradient-to-br from-blue-500 to-purple-600 text-white'
                  }`}>
                    {msg.role === 'user' ? '我' : '客服'}
                  </div>

                  {/* 消息气泡 */}
                  <div className={`px-4 py-2.5 rounded-2xl text-sm leading-relaxed ${
                    msg.role === 'user'
                      ? 'bg-gradient-to-br from-green-500 to-green-600 text-white rounded-br-none shadow-md'
                      : 'bg-white text-slate-800 rounded-bl-none shadow-sm border border-slate-200'
                  }`}>
                    {msg.content}
                  </div>
                </div>
              </div>
            ))}
            
            {/* 加载中指示器 */}
            {loading && (
              <div className="flex justify-start">
                <div className="flex items-end gap-2">
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-sm">
                    客服
                  </div>
                  <div className="px-4 py-3 bg-white rounded-2xl rounded-bl-none shadow-sm border border-slate-200">
                    <div className="flex items-center gap-1 text-slate-500">
                      <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce"></div>
                      <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                      <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                    </div>
                  </div>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* 底部输入框 */}
      <div className="border-t border-slate-200 bg-white p-4 shadow-lg">
        <div className="max-w-4xl mx-auto">
          <div className="flex gap-3 items-end">
            <div className="flex-1 relative">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="输入您的问题... (支持中/英/西/法/德)"
                rows={1}
                className="w-full px-4 py-3 pr-12 text-sm border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none shadow-sm"
                disabled={loading}
                style={{ minHeight: '48px', maxHeight: '120px' }}
                onInput={(e) => {
                  const target = e.target as HTMLTextAreaElement;
                  target.style.height = 'auto';
                  target.style.height = Math.min(target.scrollHeight, 120) + 'px';
                }}
              />
              
              {/* 表情/附件按钮（可选） */}
              <button className="absolute right-3 bottom-3 text-slate-400 hover:text-slate-600 transition">
                +
              </button>
            </div>
            
            <button
              onClick={handleSend}
              disabled={loading || !input.trim()}
              className="px-6 py-3 bg-gradient-to-r from-blue-500 to-blue-600 text-white text-sm font-medium rounded-xl hover:from-blue-600 hover:to-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-md hover:shadow-lg flex items-center gap-2"
            >
              {loading ? (
                <>
                  处理中
                </>
              ) : (
                <>
                  发送
                </>
              )}
            </button>
          </div>
          
          {/* 提示文字 */}
          <div className="mt-2 text-[10px] text-slate-400 text-center">
            提示：按 Enter 发送，Shift+Enter 换行 · 支持多语言自动识别 · 7x24小时在线服务
          </div>
        </div>
      </div>
    </div>
  );
}