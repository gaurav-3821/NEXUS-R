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
      className={clsx("flex items-center justify-between p-4 hover:bg-gray-50 transition-colors cursor-pointer", className)} 
      onClick={() => onChange(!checked)}
      {...props}
    >
      <div className="flex items-center gap-3">
        {icon && <div className="w-8 h-8 rounded-lg bg-gray-50 border border-gray-100 flex items-center justify-center shrink-0">{icon}</div>}
        <div>
          <div className="text-sm font-bold text-gray-900">{label}</div>
          {description && <div className="text-[13px] font-medium text-gray-500 mt-0.5">{description}</div>}
        </div>
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={clsx(
          "w-11 h-6 rounded-full p-1 cursor-pointer transition-colors shadow-inner flex items-center shrink-0",
          checked ? "bg-[#4f46e5]" : "bg-gray-200"
        )}
      >
        <div className={clsx(
          "bg-white w-4 h-4 rounded-full shadow-sm transition-transform duration-300",
          checked ? "translate-x-5" : "translate-x-0"
        )} />
      </button>
    </div>
  );
}
