import { useAppStore } from '../../store/useAppStore';
import { RefreshCw, Sparkles, Bot } from 'lucide-react';
import ChatInput from './ChatInput';
import clsx from 'clsx';

export default function ChatMain() {
  const { messages } = useAppStore();

  return (
    <div className="flex flex-col h-full relative w-full items-center">
      
      {/* Sticky Upgrade Pro Badge */}
      <div className="absolute right-0 top-1/2 -translate-y-1/2 z-50">
        <button className="bg-[#4f46e5] text-white py-4 px-1.5 rounded-l-xl shadow-lg hover:bg-indigo-600 transition-colors flex flex-col items-center gap-2 border border-indigo-400/30 border-r-0 group cursor-pointer">
          <Sparkles size={14} className="group-hover:scale-110 transition-transform text-yellow-300" />
          <span className="[writing-mode:vertical-lr] rotate-180 text-xs font-semibold tracking-wider">Upgrade Pro</span>
        </button>
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto w-full pt-8 pb-4 px-4 scroll-smooth">
        <div className="max-w-4xl mx-auto flex flex-col gap-10">
          {messages.map((msg) => (
            <div 
              key={msg.id} 
              className={clsx(
                "flex w-full animate-in fade-in slide-in-from-bottom-2 duration-300",
                msg.role === 'user' ? "justify-end" : "justify-start gap-4"
              )}
            >
              {/* Assistant Avatar */}
              {msg.role === 'assistant' && msg.id !== 'welcome' && (
                <div className="w-8 h-8 rounded-full bg-indigo-50 border border-indigo-100 flex items-center justify-center shrink-0 mt-1">
                  <img src="https://ui-avatars.com/api/?name=AI&background=e0e7ff&color=4f46e5" alt="AI" className="w-8 h-8 rounded-full" />
                </div>
              )}

              <div 
                className={clsx(
                  "max-w-[85%] rounded-2xl relative group",
                  msg.role === 'user' 
                    ? "bg-[#f3f4f6] text-gray-800 px-5 py-3.5 rounded-br-sm" 
                    : "text-gray-900 bg-transparent px-2 py-1"
                )}
              >
                {msg.role === 'assistant' && msg.id !== 'welcome' && (
                  <div className="flex items-center gap-2 mb-2 text-sm font-semibold text-indigo-600">
                    <span>CHAT A.I+</span>
                    <Bot size={14} />
                  </div>
                )}
                
                <div className="msg-prose whitespace-pre-wrap text-[15px] leading-[1.7] font-medium text-gray-800">
                  {msg.streaming && msg.content === '...' ? (
                    <div className="flex flex-col gap-2 w-48 py-1">
                      <div className="h-2 bg-gray-200 rounded-full w-full animate-pulse"></div>
                      <div className="h-2 bg-gray-200 rounded-full w-5/6 animate-pulse" style={{ animationDelay: '150ms' }}></div>
                      <div className="h-2 bg-gray-200 rounded-full w-4/6 animate-pulse" style={{ animationDelay: '300ms' }}></div>
                    </div>
                  ) : (
                    msg.content
                  )}
                </div>

                {/* Regenerate Button for Assistant */}
                {msg.role === 'assistant' && msg.id !== 'welcome' && !msg.streaming && (
                  <div className="mt-4 flex items-center gap-4 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button className="flex items-center gap-1.5 text-xs font-semibold text-gray-500 hover:text-gray-800 transition-colors">
                      <RefreshCw size={12} />
                      Regenerate
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Input Area */}
      <div className="shrink-0 w-full relative pt-2">
        <ChatInput />
      </div>
    </div>
  );
}
