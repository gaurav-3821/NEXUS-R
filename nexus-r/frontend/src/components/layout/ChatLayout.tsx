import React from 'react';
import { Sparkles } from 'lucide-react';

export interface ChatLayoutProps {
  children: React.ReactNode;
  inputArea: React.ReactNode;
  showUpgradeBadge?: boolean;
  onUpgradeClick?: () => void;
}

export function ChatLayout({ children, inputArea, showUpgradeBadge = true, onUpgradeClick }: ChatLayoutProps) {
  return (
    <div className="flex flex-col h-full relative w-full items-center">
      
      {/* Sticky Upgrade Pro Badge */}
      {showUpgradeBadge && (
        <div className="absolute right-0 top-1/2 -translate-y-1/2 z-50">
          <button 
            onClick={onUpgradeClick}
            className="bg-[#4f46e5] text-white py-4 px-1.5 rounded-l-xl shadow-lg hover:bg-indigo-600 transition-colors flex flex-col items-center gap-2 border border-indigo-400/30 border-r-0 group cursor-pointer"
          >
            <Sparkles size={14} className="group-hover:scale-110 transition-transform text-yellow-300" />
            <span className="[writing-mode:vertical-lr] rotate-180 text-xs font-semibold tracking-wider">Upgrade Pro</span>
          </button>
        </div>
      )}

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto w-full pt-8 pb-4 px-4 scroll-smooth">
        {children}
      </div>

      {/* Input Area */}
      <div className="shrink-0 w-full relative pt-2">
        {inputArea}
      </div>
    </div>
  );
}
