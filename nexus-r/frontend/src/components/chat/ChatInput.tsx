import { useState, useRef, useEffect } from 'react';
import { useAppStore } from '../../store/useAppStore';
import { useModelsStore } from '../../store/modelsStore';
import { Paperclip, Send, Square, Bot, ChevronDown, Check, Settings } from 'lucide-react';
import clsx from 'clsx';

import { useNavigate } from 'react-router-dom';

export default function ChatInput() {
  const navigate = useNavigate();
  const [input, setInput] = useState('');
  const [modelDropdownOpen, setModelDropdownOpen] = useState(false);
  const [selectedModel, setSelectedModel] = useState('Auto Router');
  const { sendChatMessage, interruptChat, streamingMsgId, attachedImages } = useAppStore();
  const { currentConfig, loadModels } = useModelsStore();
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadModels();
  }, [loadModels]);

  const handleSend = () => {
    if (streamingMsgId) {
      interruptChat();
    } else {
      const modelToSend = selectedModel === 'Auto Router' ? undefined : selectedModel;
      sendChatMessage(input, modelToSend);
      setInput('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col mx-auto w-full max-w-4xl px-8 pb-8 relative z-20">
      {/* Input Container */}
      <div className="relative flex items-center gap-2 bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-full p-2 shadow-[0_8px_30px_rgb(0,0,0,0.04)] focus-within:ring-2 focus-within:ring-accent-500/20 focus-within:border-accent-300 transition-all">
        
        {/* Attachment Button */}
        <button 
          onClick={() => fileInputRef.current?.click()}
          className="p-2.5 text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300 rounded-full hover:bg-gray-100 dark:hover:bg-slate-800 transition-colors ml-2"
        >
          <Paperclip size={20} />
        </button>
        <input 
          type="file" 
          ref={fileInputRef} 
          className="hidden" 
          accept=".txt,.md,.py,.js,.pdf,.png,.jpg,.jpeg,.webp"
        />

        {/* Text Area */}
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="What's in your mind?..."
          className="flex-1 max-h-32 bg-transparent resize-none outline-none py-3 px-2 text-sm text-gray-800 dark:text-gray-200 placeholder-gray-400 dark:placeholder-gray-500"
          rows={1}
        />

        {/* Action Area (Model + Send) */}
        <div className="flex items-center gap-2 pr-1 relative">
          
          {/* Model Selector Button */}
          <button 
            onClick={() => setModelDropdownOpen(!modelDropdownOpen)}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-[#0f172a] hover:bg-gray-100 rounded-full border border-gray-200 dark:border-slate-800 transition-colors"
          >
            <Bot size={16} className="text-gray-500 dark:text-gray-400" />
            <span>{selectedModel}</span>
            <ChevronDown size={14} className="text-gray-400" />
          </button>

          {/* Model Selector Dropdown */}
          {modelDropdownOpen && (
            <div className="absolute bottom-14 right-14 w-80 bg-white dark:bg-slate-900 border border-gray-100 shadow-xl rounded-2xl p-2 z-50">
              
              {/* Auto Router Selection */}
              <button
                onClick={() => {
                  setSelectedModel("Auto Router");
                  setModelDropdownOpen(false);
                }}
                className={clsx(
                  "w-full flex items-start justify-between p-3 rounded-xl transition-colors text-left",
                  selectedModel === "Auto Router" ? "bg-accent-50" : "hover:bg-gray-50 dark:hover:bg-slate-800"
                )}
              >
                <div className="flex gap-3 w-full">
                  <div className="mt-0.5"><Bot size={18} className={selectedModel === "Auto Router" ? "text-accent-600" : "text-gray-400"} /></div>
                  <div className="flex-1">
                    <div className={clsx("text-sm font-semibold", selectedModel === "Auto Router" ? "text-accent-900" : "text-gray-800")}>
                      Auto Router
                    </div>
                    <div className="mt-1 text-xs text-gray-500">
                      <div className="mb-1 text-gray-400 uppercase tracking-wider text-[10px] font-bold">Active Models</div>
                      <div className="flex justify-between"><span>Reasoning &rarr;</span> <span>{useModelsStore.getState().routingProfile?.reasoning || 'GPT-4o'}</span></div>
                      <div className="flex justify-between"><span>Coding &rarr;</span> <span>{useModelsStore.getState().routingProfile?.coding || 'Claude 3.5 Sonnet'}</span></div>
                      <div className="flex justify-between"><span>General &rarr;</span> <span>{useModelsStore.getState().routingProfile?.general || 'Llama 3 70B'}</span></div>
                    </div>
                  </div>
                </div>
                {selectedModel === "Auto Router" && <Check size={16} className="text-accent-600 ml-2" />}
              </button>

              {/* Manual Override */}
              <div className="px-3 py-2 mt-2 text-[10px] font-bold uppercase tracking-wider text-gray-400">Manual Override</div>
              <div className="space-y-1">
                {[
                  useModelsStore.getState().routingProfile?.reasoning || 'GPT-4o',
                  useModelsStore.getState().routingProfile?.coding || 'Claude 3.5 Sonnet',
                  useModelsStore.getState().routingProfile?.general || 'Llama 3 70B'
                ].map(m => (
                  <button
                    key={m}
                    onClick={() => {
                      setSelectedModel(m);
                      setModelDropdownOpen(false);
                    }}
                    className={clsx(
                      "w-full flex items-center justify-between p-3 rounded-xl transition-colors text-left",
                      selectedModel === m ? "bg-accent-50" : "hover:bg-gray-50 dark:hover:bg-slate-800"
                    )}
                  >
                    <div className="flex gap-3">
                      <div className="mt-0.5"><Bot size={18} className={selectedModel === m ? "text-accent-600" : "text-gray-400"} /></div>
                      <div className={clsx("text-sm font-semibold", selectedModel === m ? "text-accent-900" : "text-gray-800")}>{m}</div>
                    </div>
                    {selectedModel === m && <Check size={16} className="text-accent-600" />}
                  </button>
                ))}
              </div>

              {/* Current Routing Profile */}
              <div className="mt-3 pt-3 border-t border-gray-100 dark:border-slate-800">
                <div className="px-3 pb-1 text-[10px] font-bold uppercase tracking-wider text-gray-400">Current Routing Profile</div>
                <div className="px-3 space-y-1 text-xs text-gray-500">
                  <div className="flex justify-between"><span>Reasoning:</span> <span className="font-medium text-gray-700 dark:text-gray-300">{useModelsStore.getState().routingProfile?.reasoning || 'GPT-4o'}</span></div>
                  <div className="flex justify-between"><span>Coding:</span> <span className="font-medium text-gray-700 dark:text-gray-300">{useModelsStore.getState().routingProfile?.coding || 'Claude 3.5 Sonnet'}</span></div>
                  <div className="flex justify-between"><span>General:</span> <span className="font-medium text-gray-700 dark:text-gray-300">{useModelsStore.getState().routingProfile?.general || 'Llama 3 70B'}</span></div>
                  <div className="flex justify-between"><span>Embedding:</span> <span className="font-medium text-gray-700 dark:text-gray-300">{useModelsStore.getState().routingProfile?.embedding || 'text-embedding-3-small'}</span></div>
                </div>
              </div>

              {/* Manage Models */}
              <div className="mt-2 pt-2 border-t border-gray-100 dark:border-slate-800">
                <button 
                  onClick={() => { setModelDropdownOpen(false); navigate('/settings/models'); }}
                  className="w-full flex items-center justify-between px-3 py-2 text-sm font-medium text-gray-600 hover:text-gray-900 dark:text-gray-100 hover:bg-gray-50 dark:hover:bg-slate-800 rounded-lg">
                  <div className="flex items-center gap-2">
                    <Settings size={14} />
                    <span>Manage Models</span>
                  </div>
                  <ChevronDown size={14} className="-rotate-90" />
                </button>
              </div>
            </div>
          )}
          
          {/* Send Button */}
          <button 
            onClick={handleSend}
            disabled={!input.trim() && !streamingMsgId && attachedImages.length === 0}
            className={clsx(
              "p-3 rounded-full transition-all flex items-center justify-center w-11 h-11",
              streamingMsgId 
                ? "bg-red-50 text-red-500 hover:bg-red-100" 
                : input.trim() || attachedImages.length > 0
                  ? "bg-accent-600 text-white hover:bg-accent-600 shadow-md"
                  : "bg-gray-100 text-gray-400"
            )}
          >
            {streamingMsgId ? <Square size={16} className="fill-current" /> : <Send size={16} className="-translate-x-[1px] translate-y-[1px]" />}
          </button>
        </div>
      </div>
    </div>
  );
}
