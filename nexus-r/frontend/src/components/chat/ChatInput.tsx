import { useState, useRef, useEffect } from 'react';
import { useAppStore } from '../../store/useAppStore';
import { useModelsStore } from '../../store/modelsStore';
import { Paperclip, Send, Square, ChevronDown, Check, Settings, Star, X, Search, Bot } from 'lucide-react';
import ModelBadge from '../ui/ModelBadge';
import clsx from 'clsx';

import { useNavigate } from 'react-router-dom';

export default function ChatInput() {
  const navigate = useNavigate();
  const [input, setInput] = useState('');
  const [modelDropdownOpen, setModelDropdownOpen] = useState(false);
  const [selectedModel, setSelectedModel] = useState('Auto Router');
  const [searchFilter, setSearchFilter] = useState('');
  const { sendChatMessage, interruptChat, streamingMsgId, attachedImages } = useAppStore();
  const { loadModels, openrouterModels, pinnedCloudModels, togglePinnedModel, listOpenRouter, routingProfile } = useModelsStore();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const autoResize = () => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = 'auto';
    ta.style.height = Math.min(ta.scrollHeight, 128) + 'px';
  };

  useEffect(() => {
    loadModels();
  }, [loadModels]);

  useEffect(() => {
    if (!modelDropdownOpen) setSearchFilter('');
  }, [modelDropdownOpen]);

  useEffect(() => {
    if (modelDropdownOpen && openrouterModels.length === 0) {
      listOpenRouter();
    }
  }, [modelDropdownOpen, openrouterModels.length, listOpenRouter]);

  useEffect(() => {
    if (!modelDropdownOpen) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setModelDropdownOpen(false);
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [modelDropdownOpen]);

  const filteredModels = openrouterModels.filter((m: any) =>
    !searchFilter
    || m.id?.toLowerCase().includes(searchFilter.toLowerCase())
    || m.name?.toLowerCase().includes(searchFilter.toLowerCase())
  );

  const handleSend = () => {
    if (streamingMsgId) {
      interruptChat();
    } else {
      const modelToSend = selectedModel === 'Auto Router' ? undefined : selectedModel;
      sendChatMessage(input, modelToSend);
      setInput('');
      if (textareaRef.current) { textareaRef.current.style.height = 'auto'; }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const profileItems = [
    { key: 'reasoning', label: 'Reasoning', model: routingProfile?.reasoning || 'Auto-Router' },
    { key: 'coding', label: 'Coding', model: routingProfile?.coding || 'Auto-Router' },
    { key: 'general', label: 'General', model: routingProfile?.general || 'Auto-Router' },
  ];

  return (
    <div className="flex flex-col mx-auto w-full max-w-4xl px-4 pb-8 relative z-20">
      {/* Input Container */}
      <div className="relative flex items-end gap-2 bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-2xl p-2 shadow-[0_8px_30px_rgb(0,0,0,0.04)] focus-within:ring-2 focus-within:ring-accent-500/20 focus-within:border-accent-300 transition-all">
        
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
          ref={textareaRef}
          value={input}
          onChange={(e) => { setInput(e.target.value); autoResize(); }}
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
            <ModelBadge modelId={selectedModel} size={16} />
            <span>{selectedModel}</span>
            <ChevronDown size={14} className="text-gray-400" />
          </button>

          {/* Model Selector Dropdown */}
          {modelDropdownOpen && (
            <div className="absolute top-full right-0 mt-2 w-96 bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 shadow-xl rounded-2xl z-50 flex flex-col max-h-[min(60vh,420px)]">
              
              <div className="flex-1 min-h-0 overflow-y-auto p-2">
                {/* Section 1: Auto-Router Profiles */}
                <div className="px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-gray-400">
                  Auto-Router Profiles
                </div>

                {/* Auto Router */}
                <button
                  onClick={() => { setSelectedModel("Auto Router"); setModelDropdownOpen(false); }}
                  className={clsx(
                    "w-full flex items-center gap-3 p-3 rounded-xl transition-colors text-left",
                    selectedModel === "Auto Router" ? "bg-accent-50 dark:bg-accent-900/20" : "hover:bg-gray-50 dark:hover:bg-slate-800"
                  )}
                >
                  <Bot size={18} className={selectedModel === "Auto Router" ? "text-accent-600" : "text-gray-400"} />
                  <div className="flex-1">
                    <div className={clsx("text-sm font-semibold", selectedModel === "Auto Router" ? "text-accent-900 dark:text-accent-300" : "text-gray-800 dark:text-gray-200")}>
                      Auto Router
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">Automatic model routing by task</div>
                  </div>
                  {selectedModel === "Auto Router" && <Check size={16} className="text-accent-600 shrink-0" />}
                </button>

                {/* Profile override items */}
                {profileItems.map(item => (
                  <button
                    key={item.key}
                    onClick={() => { setSelectedModel(item.model); setModelDropdownOpen(false); }}
                    className={clsx(
                      "w-full flex items-center gap-3 p-3 rounded-xl transition-colors text-left",
                      selectedModel === item.model ? "bg-accent-50 dark:bg-accent-900/20" : "hover:bg-gray-50 dark:hover:bg-slate-800"
                    )}
                  >
                    <ModelBadge modelId={item.model} size={18} />
                    <div className="flex-1 min-w-0">
                      <div className={clsx("text-sm font-semibold truncate", selectedModel === item.model ? "text-accent-900 dark:text-accent-300" : "text-gray-800 dark:text-gray-200")}>
                        {item.label}
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400 truncate">{item.model}</div>
                    </div>
                    {selectedModel === item.model && <Check size={16} className="text-accent-600 shrink-0" />}
                  </button>
                ))}

                {/* Divider */}
                <div className="my-2 border-t border-gray-100 dark:border-slate-800" />

                {/* Section 2: Pinned Cloud Models */}
                <div className="px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-gray-400">
                  Pinned Cloud Models
                </div>
                {pinnedCloudModels.length === 0 ? (
                  <div className="px-3 py-3 text-xs text-gray-400 dark:text-gray-500 italic">
                    Pin models from the list below
                  </div>
                ) : (
                  pinnedCloudModels.map(id => {
                    const model = openrouterModels.find((m: any) => m.id === id);
                    const displayName = model?.name || id.split('/').pop() || id;
                    return (
                      <button
                        key={id}
                        onClick={() => { setSelectedModel(id); setModelDropdownOpen(false); }}
                        className={clsx(
                          "w-full flex items-center gap-3 p-3 rounded-xl transition-colors text-left",
                          selectedModel === id ? "bg-accent-50 dark:bg-accent-900/20" : "hover:bg-gray-50 dark:hover:bg-slate-800"
                        )}
                      >
                        <ModelBadge modelId={id} size={18} />
                        <div className="flex-1 min-w-0">
                          <div className={clsx("text-sm font-semibold truncate", selectedModel === id ? "text-accent-900 dark:text-accent-300" : "text-gray-800 dark:text-gray-200")}>
                            {displayName}
                          </div>
                          <div className="text-xs text-gray-500 dark:text-gray-400 truncate">{id}</div>
                        </div>
                        {selectedModel === id && <Check size={16} className="text-accent-600 shrink-0" />}
                      </button>
                    );
                  })
                )}

                {/* Divider */}
                <div className="my-2 border-t border-gray-100 dark:border-slate-800" />

                {/* Section 3: All OpenRouter Models */}
                <div className="px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-gray-400">
                  All OpenRouter Models
                </div>

                {/* Search filter — only show when models are loaded */}
                {openrouterModels.length > 0 && (
                  <div className="relative px-3 mb-2">
                    <Search size={14} className="absolute left-[19px] top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
                    <input
                      type="text"
                      value={searchFilter}
                      onChange={(e) => setSearchFilter(e.target.value)}
                      placeholder="Search models..."
                      className="w-full pl-8 pr-8 py-1.5 text-xs bg-gray-50 dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg outline-none focus:ring-1 focus:ring-accent-500 text-gray-800 dark:text-gray-200 placeholder-gray-400"
                    />
                    {searchFilter && (
                      <button onClick={() => setSearchFilter('')} className="absolute right-[19px] top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
                        <X size={14} />
                      </button>
                    )}
                  </div>
                )}

                {/* Model list */}
                {openrouterModels.length === 0 ? (
                  <div className="px-3 py-3 text-xs text-gray-400 dark:text-gray-500 italic">
                    Loading models...
                  </div>
                ) : filteredModels.length === 0 && searchFilter ? (
                  <div className="px-3 py-3 text-xs text-gray-400 dark:text-gray-500 italic">
                    No models match "{searchFilter}"
                  </div>
                ) : (
                  filteredModels.map((model: any) => {
                    const isPinned = pinnedCloudModels.includes(model.id);
                    return (
                      <div key={model.id} className="flex items-center gap-1 group">
                        <button
                          onClick={() => { setSelectedModel(model.id); setModelDropdownOpen(false); }}
                          className={clsx(
                            "flex-1 flex items-center gap-3 p-3 rounded-xl transition-colors text-left min-w-0",
                            selectedModel === model.id ? "bg-accent-50 dark:bg-accent-900/20" : "hover:bg-gray-50 dark:hover:bg-slate-800"
                          )}
                        >
                          <ModelBadge modelId={model.id} size={18} />
                          <div className="flex-1 min-w-0">
                            <div className={clsx("text-sm font-semibold truncate", selectedModel === model.id ? "text-accent-900 dark:text-accent-300" : "text-gray-800 dark:text-gray-200")}>
                              {model.name || model.id.split('/').pop()}
                            </div>
                            <div className="text-xs text-gray-400 dark:text-gray-500 truncate">{model.id}</div>
                          </div>
                          {selectedModel === model.id && <Check size={16} className="text-accent-600 shrink-0" />}
                        </button>
                        <button
                          onClick={() => togglePinnedModel(model.id)}
                          className="p-2 text-gray-400 hover:text-yellow-500 dark:hover:text-yellow-400 opacity-0 group-hover:opacity-100 transition-all shrink-0"
                          title={isPinned ? "Unpin model" : "Pin model"}
                          aria-label={isPinned ? "Unpin model" : "Pin model"}
                        >
                          <Star size={14} className={isPinned ? "fill-yellow-400 text-yellow-400 opacity-100" : ""} />
                        </button>
                      </div>
                    );
                  })
                )}
              </div>

              {/* Sticky Manage Models footer */}
              <div className="sticky bottom-0 border-t border-gray-100 dark:border-slate-800 bg-white dark:bg-slate-900 p-2 rounded-b-2xl">
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
