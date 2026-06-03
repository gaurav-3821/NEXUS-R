import React from 'react';
import { Sparkles } from 'lucide-react';
import clsx from 'clsx';
import { useAppearanceStore } from '../../store/appearanceStore';

export interface ChatLayoutProps {
  children: React.ReactNode;
  inputArea: React.ReactNode;
  showUpgradeBadge?: boolean;
  onUpgradeClick?: () => void;
}

export function ChatLayout({ children, inputArea, showUpgradeBadge = true, onUpgradeClick }: ChatLayoutProps) {
  const { compactMode } = useAppearanceStore();

  return (
    <div className="flex flex-col h-full relative w-full items-center">
      
      {/* Sticky Upgrade Pro Badge */}
      {showUpgradeBadge && (
        <div className="absolute right-0 top-1/2 -translate-y-1/2 z-50">
          <button 
            onClick={onUpgradeClick}
            className={clsx("bg-accent-600 text-white rounded-l-xl shadow-lg hover:bg-accent-600 transition-colors flex flex-col items-center gap-2 border border-accent-400/30 border-r-0 group cursor-pointer", compactMode ? "py-2 px-1" : "py-4 px-1.5")}
          >
            <Sparkles size={14} className="group-hover:scale-110 transition-transform text-yellow-300" />
            <span className="[writing-mode:vertical-lr] rotate-180 text-xs font-semibold tracking-wider">Upgrade Pro</span>
          </button>
        </div>
      )}

      {/* Messages Scroll Area */}
      <div className={clsx("flex-1 overflow-y-auto w-full px-4 scroll-smooth", compactMode ? "pt-4 pb-2" : "pt-8 pb-4")}>
        {children}
      </div>

      {/* Input Area */}
      <div className={clsx("shrink-0 w-full relative", compactMode ? "pt-1" : "pt-2")}>
        {inputArea}
      </div>
    </div>
  );
}
