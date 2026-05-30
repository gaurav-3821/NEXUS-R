import React from 'react';
import clsx from 'clsx';

export interface ToggleRowProps extends React.HTMLAttributes<HTMLDivElement> {
  label: string;
  description?: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}

export function ToggleRow({ label, description, checked, onChange, className, ...props }: ToggleRowProps) {
  return (
    <div className={clsx("flex items-center justify-between py-2 border-b border-gray-100 last:border-0", className)} {...props}>
      <div>
        <div className="text-[15px] font-semibold text-gray-800">{label}</div>
        {description && <div className="text-[13px] text-gray-500 mt-0.5">{description}</div>}
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
