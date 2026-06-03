import { useAppStore } from '../../store/useAppStore';
import { useAppearanceStore } from '../../store/appearanceStore';
import { APP_NAME } from '../../constants';
import { Plus, Search, Settings, MessageSquare, Trash2 } from 'lucide-react';
import clsx from 'clsx';
import { UserProfileCard } from './UserProfileCard';
import { useNavigate, useLocation } from 'react-router-dom';

export default function Sidebar() {
  const { conversations, currentConversationId, setCurrentConversation, loadConversationMessages, startNewChat } = useAppStore();
  const { sidebarTransparency, compactMode } = useAppearanceStore();
  const navigate = useNavigate();
  const location = useLocation();
  const isSettingsActive = location.pathname.startsWith('/settings');

  return (
    <div className={clsx(
      "flex flex-col h-full text-[#111827] dark:text-slate-100",
      sidebarTransparency ? "bg-white dark:bg-slate-900/70 backdrop-blur-md" : "bg-white dark:bg-slate-900"
    )}>
      {/* Header */}
      <div className={clsx("pb-2", compactMode ? "p-3" : "p-6")}>
        <h3 className={clsx("font-bold tracking-[0.2em] uppercase text-gray-900 dark:text-gray-100", compactMode ? "text-lg mb-3" : "text-xl mb-6")}>
          {APP_NAME}
        </h3>
        <div className={clsx("flex", compactMode ? "gap-1" : "gap-2")}>
          <button 
            className={clsx("flex-1 primary-button rounded-full flex items-center justify-center gap-2", compactMode ? "py-1.5 px-3" : "py-2.5 px-4")}
            onClick={() => {
              startNewChat();
              navigate('/');
            }}
          >
            <Plus size={18} />
            <span>New chat</span>
          </button>
          <button className={clsx("bg-gray-900 dark:bg-slate-700 text-white rounded-full hover:bg-gray-800 dark:hover:bg-slate-600 transition-colors flex items-center justify-center", compactMode ? "w-[36px] h-[36px] p-2" : "w-[42px] h-[42px] p-2.5")}>
            <Search size={18} />
          </button>
        </div>
      </div>

      {/* Conversations List */}
      <div className={clsx("flex-1 overflow-y-auto px-4 mt-4", compactMode ? "space-y-0.5" : "space-y-1")}>
        <div className="flex items-center justify-between px-2 mb-3">
          <span className="text-[11px] font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider">Your conversations</span>
          <button className="text-[11px] font-semibold text-accent-500 hover:text-accent-600 transition-colors">Clear All</button>
        </div>
        
        {conversations.length === 0 ? (
          <div className="text-sm text-gray-500 dark:text-gray-400 text-center py-6">No previous chats</div>
        ) : (
          conversations.map(conv => (
            <button
              key={conv.id}
              onClick={() => {
                setCurrentConversation(conv.id);
                loadConversationMessages(conv.id);
                navigate('/');
              }}
              className={clsx(
                "w-full text-left rounded-xl flex items-center gap-3 group transition-colors",
                compactMode ? "px-2 py-1.5" : "px-3 py-2.5",
                currentConversationId === conv.id && !isSettingsActive
                  ? "bg-accent-50 dark:bg-accent-500/20 text-accent-600 dark:text-accent-400" 
                  : "text-gray-600 dark:text-gray-100 hover:bg-gray-50 dark:hover:bg-slate-800 hover:text-gray-900 dark:hover:text-gray-100"
              )}
            >
              <MessageSquare size={16} className={currentConversationId === conv.id && !isSettingsActive ? "text-accent-600 dark:text-accent-400" : "text-gray-400 dark:text-gray-500"} />
              <span className="truncate flex-1 text-sm font-medium">{conv.title || "New Conversation"}</span>
              <Trash2 size={14} className="opacity-0 group-hover:opacity-100 hover:text-red-500 transition-opacity" />
            </button>
          ))
        )}
      </div>

      {/* Bottom Profile / Settings */}
      <div className={clsx("pt-2", compactMode ? "p-2" : "p-4")}>
        <button 
          onClick={() => navigate('/settings/general')}
          className={clsx(
            "w-full flex items-center gap-3 text-sm font-medium rounded-full transition-colors",
            compactMode ? "py-1.5 px-3 mb-2" : "py-2.5 px-4 mb-4",
            isSettingsActive ? "bg-accent-50 dark:bg-accent-500/20 text-accent-600 dark:text-accent-400 border border-accent-100 dark:border-accent-500/30" : "text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-800 border border-transparent"
          )}
        >
          <Settings size={18} className={isSettingsActive ? "text-accent-600 dark:text-accent-400" : "text-gray-400 dark:text-gray-500"} />
          <span>Settings</span>
        </button>
        
        <UserProfileCard />
      </div>
    </div>
  );
}
