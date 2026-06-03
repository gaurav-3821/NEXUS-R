import React from 'react';
import clsx from 'clsx';

import { useAppearanceStore } from '../../store/appearanceStore';

export interface SettingsLayoutProps {
  header: React.ReactNode;
  sidebar: React.ReactNode;
  children: React.ReactNode; // The main form content
  rightPanel?: React.ReactNode;
  footer?: React.ReactNode;
  isOverlay?: boolean;
}

export function SettingsLayout({ header, sidebar, children, rightPanel, footer, isOverlay = true }: SettingsLayoutProps) {
  const { compactMode } = useAppearanceStore();

  return (
    <div 
      className={clsx(
        "flex flex-col text-gray-900 dark:text-gray-100 bg-gray-50 dark:bg-[#0f172a] transition-colors",
        isOverlay ? "absolute inset-0 z-40 animate-in fade-in duration-200" : "h-full w-full"
      )}
    >
      {/* Header */}
      <div className="shrink-0">
        {header}
      </div>

      {/* Body */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar Nav */}
        <div className={clsx(
          "w-[280px] shrink-0 border-r border-gray-200 dark:border-slate-800 bg-white dark:bg-slate-900 overflow-y-auto flex flex-col transition-colors", 
          compactMode ? "py-2 px-2 gap-0.5" : "py-4 px-3 gap-1"
        )}>
          {sidebar}
        </div>

        {/* Content Area */}
        <div className={clsx(
          "flex-1 min-w-0 overflow-y-auto bg-gray-50 dark:bg-[#0f172a] transition-colors",
          compactMode ? "p-4" : "p-8",
          rightPanel ? (compactMode ? "flex gap-4" : "flex gap-8") : ""
        )}>
          {/* Main Settings Form */}
          <div className="flex-1 min-w-0 max-w-3xl">
            {children}
          </div>

          {/* Right Sidebar Widget Column */}
          {rightPanel && (
            <div className={clsx("w-[320px] shrink-0", compactMode ? "space-y-4" : "space-y-6")}>
              {rightPanel}
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      {footer && (
        <div className={clsx(
          "shrink-0 bg-white dark:bg-slate-900 border-t border-gray-200 dark:border-slate-800 flex items-center justify-end gap-4 transition-colors", 
          compactMode ? "px-4 py-2" : "px-8 py-4"
        )}>
          {footer}
        </div>
      )}
    </div>
  );
}
