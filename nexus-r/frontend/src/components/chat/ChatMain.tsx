import { useEffect, useRef } from 'react';
import { useAppStore } from '../../store/useAppStore';
import { APP_NAME } from '../../constants';
import { RefreshCw, Sparkles, Bot } from 'lucide-react';
import ChatInput from './ChatInput';
import ChatToolbar from './ChatToolbar';
import WidgetDispatcher from './widgets';
import clsx from 'clsx';
import { useAppearanceStore } from '../../store/appearanceStore';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export default function ChatMain() {
  const { messages } = useAppStore();
  const { compactMode, showResponseMetadata } = useAppearanceStore();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);


  return (
    <div className="flex flex-col h-full relative w-full items-center">


      {/* Messages Scroll Area */}
      <div className={clsx("flex-1 overflow-y-auto w-full scroll-smooth", messages.length === 0 ? "pt-8 pb-8" : (compactMode ? "pt-4 pb-44" : "pt-8 pb-44"))}>
        <div className={clsx("max-w-4xl mx-auto px-4 flex flex-col", compactMode ? "gap-4" : "gap-10")}>
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center flex-1 min-h-[60vh] text-center pb-32 md:pb-40">
              <div className="flex items-start justify-center gap-1 md:gap-2">
                {[
                  {l:'N', w:'Neural'},
                  {l:'E', w:'Engine'},
                  {l:'X', w:'for eXecution'},
                  {l:'U', w:'Understanding'},
                  {l:'S', w:'Synthesis'},
                  {l:'–', w:'', small:true},
                  {l:'R', w:'Runtime'},
                ].map((it, i) => (
                  <div key={i} className="flex flex-col items-center w-12 md:w-16">
                    <div className="h-20 md:h-32 flex items-center justify-center">
                      <span className={clsx("font-bold text-accent-600 dark:text-accent-400 leading-none", it.small ? "text-5xl md:text-7xl" : "text-7xl md:text-9xl")}>{it.l}</span>
                    </div>
                    {it.w && <span className="text-[10px] md:text-xs text-gray-500 dark:text-gray-400 mt-2 leading-tight text-center">{it.w}</span>}
                  </div>
                ))}
              </div>
            </div>
          )}
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
                
                {msg.reasoning_content && (
                  <details 
                    open={msg.streaming}
                    className="mb-4 text-sm text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-slate-800/50 rounded-lg overflow-hidden border border-gray-100 dark:border-slate-700/50"
                  >
                    <summary className="cursor-pointer select-none font-medium px-4 py-2 hover:bg-gray-100 dark:hover:bg-slate-700/50 transition-colors flex items-center gap-2">
                      <Bot size={14} />
                      AI Reasoning Process
                    </summary>
                    <div className="p-4 pt-2 whitespace-pre-wrap font-mono text-xs overflow-x-auto opacity-80">
                      {msg.reasoning_content}
                    </div>
                  </details>
                )}
                
                <div className="msg-prose prose prose-sm md:prose-base dark:prose-invert max-w-none prose-p:leading-relaxed prose-pre:p-0">
                  {msg.streaming && !msg.content && !msg.reasoning_content ? (
                    <div className="flex flex-col gap-2 w-48 py-1 mt-2">
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

                {/* Widgets (weather, calculator, stock, citations, etc.) */}
                {msg.widgets && msg.widgets.length > 0 && (
                  <div className="mt-3 flex flex-col gap-2 not-prose">
                    {msg.widgets.map((w, i) => (
                      <WidgetDispatcher key={i} widget={w} />
                    ))}
                  </div>
                )}

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
                        {msg.metadata.reasoning_tokens !== undefined && msg.metadata.reasoning_tokens !== null && (
                          <div className="text-purple-500 dark:text-purple-400">
                            Reasoning: {msg.metadata.reasoning_tokens} tokens
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Toolbar + Input Area — centered in viewport for empty state, fixed at bottom when there are messages */}
      <div className={clsx(
        "fixed left-0 right-0 z-20 pointer-events-none",
        messages.length === 0 ? "top-1/2 -translate-y-[60%]" : "bottom-0"
      )}>
        <div className="pointer-events-auto">
          <div className="max-w-4xl mx-auto px-4">
            <ChatToolbar />
          </div>
          <ChatInput />
        </div>
      </div>
    </div>
  );
}
