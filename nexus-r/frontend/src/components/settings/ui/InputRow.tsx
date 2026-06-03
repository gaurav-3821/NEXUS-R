import React from 'react';
import clsx from 'clsx';

export interface InputRowProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label: string;
  description?: string;
}

export function InputRow({ label, description, className, ...props }: InputRowProps) {
  return (
    <div className={clsx("flex items-center justify-between py-2 border-b border-gray-100 last:border-0", className)}>
      <div>
        <div className="text-[15px] font-semibold text-gray-800">{label}</div>
        {description && <div className="text-[13px] text-gray-500 dark:text-gray-400 mt-0.5">{description}</div>}
      </div>
      <input 
        type="text"
        className="w-48 bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-lg px-3 py-2 text-sm font-medium outline-none focus:border-accent-400"
        {...props}
      />
    </div>
  );
}
