import React from 'react';

export interface AppLayoutProps {
  sidebar: React.ReactNode;
  children: React.ReactNode;
  isSidebarOpen?: boolean;
}

export function AppLayout({ sidebar, children, isSidebarOpen = true }: AppLayoutProps) {
  return (
    <div className="flex h-screen w-full bg-[#f8fafc] dark:bg-slate-950 overflow-hidden text-[#111827] dark:text-slate-100">
      {/* Sidebar */}
      {isSidebarOpen && (
        <div className="w-[280px] flex-shrink-0 bg-white dark:bg-slate-900 border-r border-gray-100 dark:border-slate-800 z-10 hidden md:block">
          {sidebar}
        </div>
      )}

      {/* Main Area */}
      <div className="flex-1 flex flex-col min-w-0 bg-[#f8fafc] dark:bg-slate-950 relative overflow-hidden">
        {children}
      </div>
    </div>
  );
}
