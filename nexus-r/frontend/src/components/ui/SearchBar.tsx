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
          "pl-9 py-2.5 bg-gray-50 border border-gray-200 rounded-lg text-sm outline-none transition-all",
          "focus:border-indigo-300 focus:ring-2 focus:ring-indigo-100",
          shortcut ? "pr-12 w-64" : "pr-4 w-full"
        )}
        {...props}
      />
      {shortcut && (
        <div className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] font-semibold text-gray-400 bg-white border border-gray-200 px-1.5 py-0.5 rounded shadow-sm">
          {shortcut}
        </div>
      )}
    </div>
  );
}
