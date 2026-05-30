import React from 'react';
import clsx from 'clsx';

export interface AppLayoutProps {
  sidebar: React.ReactNode;
  children: React.ReactNode;
  isSidebarOpen?: boolean;
}

export function AppLayout({ sidebar, children, isSidebarOpen = true }: AppLayoutProps) {
  return (
    <div className="flex h-screen w-full bg-[#f8fafc] overflow-hidden text-[#111827]">
      {/* Sidebar */}
      {isSidebarOpen && (
        <div className="w-[280px] flex-shrink-0 bg-white border-r border-gray-100 z-10 hidden md:block">
          {sidebar}
        </div>
      )}

      {/* Main Area */}
      <div className="flex-1 flex flex-col min-w-0 bg-[#f8fafc] relative overflow-hidden">
        {children}
      </div>
    </div>
  );
}
