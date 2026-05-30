import { useState, useRef } from 'react';
import { useAppStore } from '../../store/useAppStore';
import { Paperclip, Send, Square, Bot, ChevronDown, Check, Settings } from 'lucide-react';
import clsx from 'clsx';

export default function ChatInput() {
  const [input, setInput] = useState('');
  const [modelDropdownOpen, setModelDropdownOpen] = useState(false);
  const [selectedModel, setSelectedModel] = useState('GPT-4o');
  const { sendChatMessage, interruptChat, streamingMsgId, attachedImages } = useAppStore();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSend = () => {
    if (streamingMsgId) {
      interruptChat();
    } else {
      sendChatMessage(input);
      setInput('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const models = [
    { id: 'GPT-4o', name: 'GPT-4o', desc: 'Most capable model for complex tasks' },
    { id: 'GPT-4 Turbo', name: 'GPT-4 Turbo', desc: 'Balanced performance and speed' },
    { id: 'GPT-3.5 Turbo', name: 'GPT-3.5 Turbo', desc: 'Fast and efficient for everyday tasks' },
    { id: 'Claude 3 Opus', name: 'Claude 3 Opus', desc: 'Excellent for analysis and reasoning' }
  ];

  return (
    <div className="flex flex-col mx-auto w-full max-w-4xl px-8 pb-8 relative z-20">
      {/* Input Container */}
      <div className="relative flex items-center gap-2 bg-white border border-gray-200 rounded-full p-2 shadow-[0_8px_30px_rgb(0,0,0,0.04)] focus-within:ring-2 focus-within:ring-indigo-500/20 focus-within:border-indigo-300 transition-all">
        
        {/* Attachment Button */}
        <button 
          onClick={() => fileInputRef.current?.click()}
          className="p-2.5 text-gray-400 hover:text-gray-600 rounded-full hover:bg-gray-100 transition-colors ml-2"
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
          className="flex-1 max-h-32 bg-transparent resize-none outline-none py-3 px-2 text-sm text-gray-800 placeholder-gray-400"
          rows={1}
        />

        {/* Action Area (Model + Send) */}
        <div className="flex items-center gap-2 pr-1 relative">
          
          {/* Model Selector Button */}
          <button 
            onClick={() => setModelDropdownOpen(!modelDropdownOpen)}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-gray-50 hover:bg-gray-100 rounded-full border border-gray-200 transition-colors"
          >
            <Bot size={16} className="text-gray-500" />
            <span>{selectedModel}</span>
            <ChevronDown size={14} className="text-gray-400" />
          </button>

          {/* Model Selector Dropdown */}
          {modelDropdownOpen && (
            <div className="absolute bottom-14 right-14 w-72 bg-white border border-gray-100 shadow-xl rounded-2xl p-2 z-50">
              <div className="px-3 py-2 text-xs font-semibold text-gray-500">Select AI Model</div>
              <div className="space-y-1 mt-1">
                {models.map(m => (
                  <button
                    key={m.id}
                    onClick={() => {
                      setSelectedModel(m.id);
                      setModelDropdownOpen(false);
                    }}
                    className={clsx(
                      "w-full flex items-center justify-between p-3 rounded-xl transition-colors text-left",
                      selectedModel === m.id ? "bg-indigo-50" : "hover:bg-gray-50"
                    )}
                  >
                    <div className="flex gap-3">
                      <div className="mt-0.5"><Bot size={18} className={selectedModel === m.id ? "text-indigo-600" : "text-gray-400"} /></div>
                      <div>
                        <div className={clsx("text-sm font-semibold", selectedModel === m.id ? "text-indigo-900" : "text-gray-800")}>{m.name}</div>
                        <div className="text-xs text-gray-500">{m.desc}</div>
                      </div>
                    </div>
                    {selectedModel === m.id && <Check size={16} className="text-indigo-600" />}
                  </button>
                ))}
              </div>
              <div className="mt-2 pt-2 border-t border-gray-100">
                <button className="w-full flex items-center justify-between px-3 py-2 text-sm font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-50 rounded-lg">
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
                  ? "bg-[#4f46e5] text-white hover:bg-indigo-600 shadow-md"
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
