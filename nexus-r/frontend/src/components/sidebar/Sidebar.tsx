import { useAppStore } from '../../store/useAppStore';
import { Plus, Search, Settings, MessageSquare, Trash2 } from 'lucide-react';
import clsx from 'clsx';

export default function Sidebar() {
  const { conversations, currentConversationId, setCurrentConversation, setSettingsOpen, isSettingsOpen } = useAppStore();

  return (
    <div className="flex flex-col h-full bg-white text-[#111827]">
      {/* Header */}
      <div className="p-6 pb-2">
        <h3 className="text-xl font-bold tracking-[0.2em] mb-6 uppercase text-black">
          CHAT A.I+
        </h3>
        <div className="flex gap-2">
          <button 
            className="flex-1 primary-button rounded-full py-2.5 px-4 flex items-center justify-center gap-2"
            onClick={() => {
              setCurrentConversation(null);
              setSettingsOpen(false);
            }}
          >
            <Plus size={18} />
            <span>New chat</span>
          </button>
          <button className="bg-black text-white rounded-full p-2.5 hover:bg-gray-800 transition-colors w-[42px] h-[42px] flex items-center justify-center">
            <Search size={18} />
          </button>
        </div>
      </div>

      {/* Conversations List */}
      <div className="flex-1 overflow-y-auto px-4 mt-4 space-y-1">
        <div className="flex items-center justify-between px-2 mb-3">
          <span className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider">Your conversations</span>
          <button className="text-[11px] font-semibold text-indigo-500 hover:text-indigo-600 transition-colors">Clear All</button>
        </div>
        
        {conversations.length === 0 ? (
          <div className="text-sm text-gray-500 text-center py-6">No previous chats</div>
        ) : (
          conversations.map(conv => (
            <button
              key={conv.id}
              onClick={() => {
                setCurrentConversation(conv.id);
                setSettingsOpen(false);
              }}
              className={clsx(
                "w-full text-left px-3 py-2.5 rounded-xl flex items-center gap-3 group transition-colors",
                currentConversationId === conv.id && !isSettingsOpen
                  ? "bg-indigo-50 text-indigo-600" 
                  : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
              )}
            >
              <MessageSquare size={16} className={currentConversationId === conv.id && !isSettingsOpen ? "text-indigo-600" : "text-gray-400"} />
              <span className="truncate flex-1 text-sm font-medium">{conv.title || "New Conversation"}</span>
              <Trash2 size={14} className="opacity-0 group-hover:opacity-100 hover:text-red-500 transition-opacity" />
            </button>
          ))
        )}
      </div>

      {/* Bottom Profile / Settings */}
      <div className="p-4 pt-2">
        <button 
          onClick={() => setSettingsOpen(true)}
          className={clsx(
            "w-full py-2.5 px-4 mb-4 flex items-center gap-3 text-sm font-medium rounded-full transition-colors",
            isSettingsOpen ? "bg-indigo-50 text-indigo-600 border border-indigo-100" : "text-gray-600 hover:bg-gray-50 border border-transparent"
          )}
        >
          <Settings size={18} className={isSettingsOpen ? "text-indigo-600" : "text-gray-400"} />
          <span>Settings</span>
        </button>
        
        <div className="flex items-center gap-3 px-2 py-2 border border-gray-100 rounded-full shadow-sm">
          <img 
            src="https://ui-avatars.com/api/?name=Andrew+Neilson&background=111827&color=fff" 
            alt="User" 
            className="w-8 h-8 rounded-full"
          />
          <div className="flex flex-col">
            <span className="text-sm font-semibold text-gray-900">Andrew Neilson</span>
          </div>
        </div>
      </div>
    </div>
  );
}
