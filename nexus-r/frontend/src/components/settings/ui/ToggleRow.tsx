import React from 'react';
import clsx from 'clsx';

export interface ToggleRowProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'onChange'> {
  label: string;
  description?: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  icon?: React.ReactNode;
}

export function ToggleRow({ label, description, checked, onChange, className, icon, ...props }: ToggleRowProps) {
  return (
    <div 
      className={clsx("flex items-center justify-between p-4 hover:bg-gray-50 dark:hover:bg-slate-800/50 transition-colors cursor-pointer", className)} 
      onClick={() => onChange(!checked)}
      {...props}
    >
      <div className="flex items-center gap-3">
        {icon && <div className="w-8 h-8 rounded-lg bg-gray-50 dark:bg-gray-800 border border-gray-100 dark:border-gray-700 flex items-center justify-center shrink-0 text-gray-700 dark:text-gray-300 transition-colors">{icon}</div>}
        <div>
          <div className="text-sm font-bold text-gray-900 dark:text-gray-100 transition-colors">{label}</div>
          {description && <div className="text-[13px] font-medium text-gray-500 dark:text-gray-400 mt-0.5 transition-colors">{description}</div>}
        </div>
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={(e) => {
          e.stopPropagation();
          onChange(!checked);
        }}
        className={clsx(
          "relative w-14 h-8 rounded-full cursor-pointer shrink-0 transition-colors duration-400 ease-in-out border overflow-hidden",
          checked 
            ? "bg-accent-500 border-accent-500 shadow-sm" 
            : "bg-gray-300 dark:bg-slate-700 border-gray-400 dark:border-slate-600"
        )}
      >
        {/* Stars (visible when OFF) */}
        <div className={clsx("absolute w-[3px] h-[3px] bg-white rounded-full transition-all duration-400 right-3 top-2", checked ? "opacity-0 translate-y-2" : "opacity-100 translate-y-0")} />
        <div className={clsx("absolute w-[4px] h-[4px] bg-white rounded-full transition-all duration-400 right-5 top-4", checked ? "opacity-0 translate-y-2" : "opacity-100 translate-y-0")} />
        <div className={clsx("absolute w-[2px] h-[2px] bg-white rounded-full transition-all duration-400 right-2 top-5", checked ? "opacity-0 translate-y-2" : "opacity-100 translate-y-0")} />

        {/* Clouds (visible when ON) */}
        <svg 
          viewBox="0 0 24 24" 
          fill="white" 
          className={clsx("absolute bottom-[-2px] left-1 w-6 h-6 transition-all duration-400", checked ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4")}
        >
          <path d="M17.5 19C19.9853 19 22 16.9853 22 14.5C22 12.1325 20.177 10.2053 17.8576 10.0152C17.3871 6.6433 14.4828 4 11 4C7.13401 4 4 7.13401 4 11C4 11.2335 4.0114 11.4645 4.03362 11.6922C2.29871 12.2241 1 13.8617 1 15.8284C1 18.132 2.86802 20 5.17157 20H17.5V19Z" />
        </svg>

        {/* Thumb (Moon to Sun) */}
        <div 
          className={clsx(
            "absolute top-[3px] left-[3px] w-[24px] h-[24px] rounded-full transition-all duration-400",
            checked 
              ? "translate-x-6 shadow-[inset_15px_-4px_0_15px_#ffcf48]" 
              : "translate-x-0 shadow-[inset_8px_-4px_0_0_#fff]"
          )}
          style={{ transitionTimingFunction: 'cubic-bezier(0.81, -0.04, 0.38, 1.5)' }}
        />
      </button>
    </div>
  );
}
