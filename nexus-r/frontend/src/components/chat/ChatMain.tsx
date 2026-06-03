import { useAppStore } from '../../store/useAppStore';
import { APP_NAME } from '../../constants';
import { RefreshCw, Sparkles, Bot } from 'lucide-react';
import ChatInput from './ChatInput';
import clsx from 'clsx';
import { useAppearanceStore } from '../../store/appearanceStore';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export default function ChatMain() {
  const { messages } = useAppStore();
  const { compactMode, showResponseMetadata } = useAppearanceStore();

  return (
    <div className="flex flex-col h-full relative w-full items-center">
      
      {/* Sticky Upgrade Pro Badge */}
      <div className="absolute right-0 top-1/2 -translate-y-1/2 z-50">
        <button className={clsx("bg-accent-600 text-white rounded-l-xl shadow-lg hover:bg-accent-600 transition-colors flex flex-col items-center gap-2 border border-accent-400/30 border-r-0 group cursor-pointer", compactMode ? "py-2 px-1" : "py-4 px-1.5")}>
          <Sparkles size={14} className="group-hover:scale-110 transition-transform text-yellow-300" />
          <span className="[writing-mode:vertical-lr] rotate-180 text-xs font-semibold tracking-wider">Upgrade Pro</span>
        </button>
      </div>

      {/* Messages Scroll Area */}
      <div className={clsx("flex-1 overflow-y-auto w-full px-4 scroll-smooth", compactMode ? "pt-4 pb-2" : "pt-8 pb-4")}>
        <div className={clsx("max-w-4xl mx-auto flex flex-col", compactMode ? "gap-4" : "gap-10")}>
          {messages.map((msg) => (
            <div 
              key={msg.id} 
              className={clsx(
                "flex w-full animate-in fade-in slide-in-from-bottom-2 duration-300",
                msg.role === 'user' ? "justify-end" : (compactMode ? "justify-start gap-2" : "justify-start gap-4")
              )}
            >
              {/* Assistant Avatar */}
              {msg.role === 'assistant' && msg.id !== 'welcome' && (
                <div className={clsx("rounded-full bg-accent-50 border border-accent-100 flex items-center justify-center shrink-0 mt-1", compactMode ? "w-6 h-6" : "w-8 h-8")}>
                  <img src="https://ui-avatars.com/api/?name=AI&background=e0e7ff&color=4f46e5" alt="AI" className={clsx("rounded-full", compactMode ? "w-6 h-6" : "w-8 h-8")} />
                </div>
              )}

              <div 
                className={clsx(
                  "max-w-[85%] rounded-2xl relative group",
                  msg.role === 'user' 
                    ? clsx("bg-[#f3f4f6] dark:bg-slate-800 text-gray-800 dark:text-gray-200 rounded-br-sm", compactMode ? "px-4 py-2" : "px-5 py-3.5") 
                    : clsx("text-gray-900 dark:text-gray-100 bg-transparent", compactMode ? "px-1 py-0.5" : "px-2 py-1")
                )}
              >
                {msg.role === 'assistant' && msg.id !== 'welcome' && (
                  <div className="flex items-center gap-2 mb-2 text-sm font-semibold text-accent-600">
                    <span>{APP_NAME}</span>
                    <Bot size={14} />
                  </div>
                )}
                
                <div className="msg-prose prose prose-sm md:prose-base dark:prose-invert max-w-none prose-p:leading-relaxed prose-pre:p-0">
                  {msg.streaming && msg.content === '...' ? (
                    <div className="flex flex-col gap-2 w-48 py-1">
                      <div className="h-2 bg-gray-200 dark:bg-slate-700 rounded-full w-full animate-pulse"></div>
                      <div className="h-2 bg-gray-200 dark:bg-slate-700 rounded-full w-5/6 animate-pulse" style={{ animationDelay: '150ms' }}></div>
                      <div className="h-2 bg-gray-200 dark:bg-slate-700 rounded-full w-4/6 animate-pulse" style={{ animationDelay: '300ms' }}></div>
                    </div>
                  ) : (
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {msg.content}
                    </ReactMarkdown>
                  )}
                </div>

                {/* Regenerate Button for Assistant */}
                {msg.role === 'assistant' && msg.id !== 'welcome' && !msg.streaming && (
                  <div className="mt-4 flex flex-col gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button className="flex items-center gap-1.5 text-xs font-semibold text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 transition-colors self-start">
                      <RefreshCw size={12} />
                      Regenerate
                    </button>
                    {showResponseMetadata && msg.metadata && (
                      <div className="mt-1 flex flex-col gap-1 text-[11px] font-mono text-gray-400 dark:text-slate-500 border-t border-gray-100 dark:border-slate-800 pt-2">
                        <div>Model: {msg.metadata.model}</div>
                        <div>Provider: {msg.metadata.provider}</div>
                        <div>Route: {msg.metadata.route}</div>
                        <div>Latency: {Math.round(msg.metadata.latency_ms)}ms</div>
                        <div>Cost: ${msg.metadata.cost.toFixed(6)}</div>
                      </div>
                    )}
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
