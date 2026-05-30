import React from 'react';
import clsx from 'clsx';

export interface SettingsLayoutProps {
  header: React.ReactNode;
  sidebar: React.ReactNode;
  children: React.ReactNode; // The main form content
  rightPanel?: React.ReactNode;
  footer?: React.ReactNode;
  isOverlay?: boolean;
}

export function SettingsLayout({ header, sidebar, children, rightPanel, footer, isOverlay = true }: SettingsLayoutProps) {
  return (
    <div 
      className={clsx(
        "flex flex-col text-[#111827] bg-[#f8fafc]",
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
        <div className="w-[280px] shrink-0 border-r border-gray-200 bg-white py-4 px-3 flex flex-col gap-1 overflow-y-auto">
          {sidebar}
        </div>

        {/* Content Area */}
        <div className={clsx(
          "flex-1 overflow-y-auto bg-[#f8fafc] p-8",
          rightPanel ? "flex gap-8" : ""
        )}>
          {/* Main Settings Form */}
          <div className="flex-1 max-w-3xl">
            {children}
          </div>

          {/* Right Sidebar Widget Column */}
          {rightPanel && (
            <div className="w-[320px] shrink-0 space-y-6">
              {rightPanel}
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      {footer && (
        <div className="shrink-0 bg-white border-t border-gray-200 px-8 py-4 flex items-center justify-end gap-4">
          {footer}
        </div>
      )}
    </div>
  );
}
