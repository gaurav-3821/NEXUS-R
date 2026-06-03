import React from 'react';
import { Search } from 'lucide-react';
import clsx from 'clsx';

export interface SearchBarProps extends React.InputHTMLAttributes<HTMLInputElement> {
  shortcut?: string;
}

export function SearchBar({ shortcut, className, ...props }: SearchBarProps) {
  return (
    <div className={clsx("relative inline-block", className)}>
      <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
      <input 
        type="text" 
        className={clsx(
          "pl-9 py-2.5 bg-gray-50 dark:bg-slate-900 border border-gray-200 dark:border-slate-700 rounded-lg text-sm text-gray-900 dark:text-gray-100 outline-none transition-all",
          "focus:border-accent-300 dark:focus:border-accent-500 focus:ring-2 focus:ring-accent-100 dark:focus:ring-accent-500/20",
          shortcut ? "pr-12 w-64" : "pr-4 w-full"
        )}
        {...props}
      />
      {shortcut && (
        <div className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] font-semibold text-gray-400 dark:text-gray-500 dark:text-gray-400 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 px-1.5 py-0.5 rounded shadow-sm">
          {shortcut}
        </div>
      )}
    </div>
  );
}
