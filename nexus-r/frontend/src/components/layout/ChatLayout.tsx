import React from 'react';
import { Sparkles } from 'lucide-react';
import clsx from 'clsx';
import { useAppearanceStore } from '../../store/appearanceStore';

export interface ChatLayoutProps {
  children: React.ReactNode;
  inputArea: React.ReactNode;
}

export function ChatLayout({ children, inputArea }: ChatLayoutProps) {
  const { compactMode } = useAppearanceStore();

  return (
    <div className="flex flex-col h-full relative w-full items-center">
      

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
