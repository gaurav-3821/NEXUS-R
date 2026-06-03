import React from 'react';
import clsx from 'clsx';

export interface ActionRowProps extends React.HTMLAttributes<HTMLDivElement> {
  label: string;
  description?: string;
  action: React.ReactNode;
  icon?: React.ReactNode;
}

export function ActionRow({ label, description, action, className, icon, ...props }: ActionRowProps) {
  return (
    <div className={clsx("flex items-center justify-between p-4 hover:bg-gray-50 dark:hover:bg-slate-800 transition-colors", className)} {...props}>
      <div className="flex items-center gap-3">
        {icon && <div className="w-8 h-8 rounded-lg bg-gray-50 dark:bg-[#0f172a] border border-gray-100 flex items-center justify-center shrink-0">{icon}</div>}
        <div>
          <div className="text-sm font-bold text-gray-900 dark:text-gray-100">{label}</div>
          {description && <div className="text-[13px] font-medium text-gray-500 dark:text-gray-400 mt-0.5">{description}</div>}
        </div>
      </div>
      <div>
        {action}
      </div>
    </div>
  );
}
