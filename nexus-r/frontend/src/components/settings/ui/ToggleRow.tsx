import React from 'react';
import clsx from 'clsx';

export interface ToggleRowProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'onChange'> {
  label: string;
  description?: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  icon?: React.ReactNode;
  variant?: 'default' | 'plane';
}

function PlaneIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor">
      <path d="M2.5 3.5l19 8.5-19 8.5v-7l14-1.5-14-1.5v-7z" />
    </svg>
  );
}

export function ToggleRow({ label, description, checked, onChange, className, icon, variant = 'default', ...props }: ToggleRowProps) {
  if (variant === 'plane') {
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
        <label className="plane-switch shrink-0" onClick={(e) => e.stopPropagation()}>
          <input 
            type="checkbox"
            checked={checked}
            onChange={(e) => onChange(e.target.checked)}
          />
          <div>
            <span className="street-middle"></span>
            <span className="cloud"></span>
            <span className="cloud two"></span>
            <div>
              <PlaneIcon />
            </div>
          </div>
        </label>
      </div>
    );
  }

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
      <label className="toggle-switch shrink-0" onClick={(e) => e.stopPropagation()}>
        <input 
          type="checkbox"
          className="toggle-input"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
        />
        <div className="toggle-label"></div>
      </label>
    </div>
  );
}
