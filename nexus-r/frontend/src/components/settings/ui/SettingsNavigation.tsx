import React from 'react';
import clsx from 'clsx';

export interface SettingsTab {
  id: string;
  label: string;
  icon: React.ReactNode;
  badge?: string;
}

export interface SettingsNavigationProps {
  tabs: SettingsTab[];
  activeTab: string;
  onTabChange: (tabId: string) => void;
  footerAction?: React.ReactNode;
}

export function SettingsNavigation({ tabs, activeTab, onTabChange, footerAction }: SettingsNavigationProps) {
  return (
    <div className="flex flex-col h-full">
      {tabs.map(tab => (
        <button
          key={tab.id}
          onClick={() => onTabChange(tab.id)}
          className={clsx(
            "flex items-center justify-between px-4 py-3 mb-1 rounded-xl text-[15px] font-semibold transition-all group",
            activeTab === tab.id 
              ? "bg-indigo-50 text-indigo-600" 
              : "text-gray-700 hover:bg-gray-50"
          )}
        >
          <div className="flex items-center gap-4">
            <span className={activeTab === tab.id ? "text-indigo-600" : "text-gray-400 group-hover:text-gray-600"}>
              {tab.icon}
            </span>
            {tab.label}
          </div>
          {tab.badge && (
            <span className="bg-indigo-100 text-indigo-600 text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider">
              {tab.badge}
            </span>
          )}
          {activeTab === tab.id && !tab.badge && (
            <div className="w-1.5 h-1.5 rounded-full bg-indigo-600 shrink-0"></div>
          )}
        </button>
      ))}
      
      {footerAction && (
        <div className="mt-auto pt-6 px-4">
          {footerAction}
        </div>
      )}
    </div>
  );
}
