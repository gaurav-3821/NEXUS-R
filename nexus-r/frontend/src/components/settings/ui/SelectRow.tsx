import React from 'react';
import clsx from 'clsx';

export interface SelectRowProps extends Omit<React.SelectHTMLAttributes<HTMLSelectElement>, 'onChange'> {
  label: string;
  description?: string;
  options: { label: string; value: string }[];
  defaultValue?: string;
  onChange?: (value: string) => void;
  icon?: React.ReactNode;
}

export function SelectRow({ label, description, options, className, defaultValue, onChange, icon, ...props }: SelectRowProps) {
  return (
    <div className={clsx("flex items-center justify-between py-2 border-b border-gray-100 last:border-0", className)}>
      <div className="flex items-center gap-3">
        {icon && <div className="text-gray-400">{icon}</div>}
        <div>
          <div className="text-[15px] font-semibold text-gray-800">{label}</div>
          {description && <div className="text-[13px] text-gray-500 mt-0.5">{description}</div>}
        </div>
      </div>
      <select 
        className="w-48 bg-white border border-gray-200 rounded-lg px-3 py-2 text-sm font-medium outline-none focus:border-indigo-400 cursor-pointer"
        defaultValue={defaultValue}
        onChange={(e) => onChange?.(e.target.value)}
        {...props}
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </select>
    </div>
  );
}
