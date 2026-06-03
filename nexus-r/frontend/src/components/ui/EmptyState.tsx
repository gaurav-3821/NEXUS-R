import React from 'react';
import clsx from 'clsx';

export interface EmptyStateProps extends React.HTMLAttributes<HTMLDivElement> {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export function EmptyState({ icon, title, description, action, className, ...props }: EmptyStateProps) {
  return (
    <div 
      className={clsx(
        "flex flex-col items-center justify-center p-8 text-center rounded-2xl border border-dashed border-gray-300 bg-gray-50 dark:bg-[#0f172a]/50",
        className
      )}
      {...props}
    >
      {icon && (
        <div className="mb-4 text-gray-400 bg-white dark:bg-slate-900 p-4 rounded-full shadow-sm border border-gray-100">
          {icon}
        </div>
      )}
      <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100 mb-1">{title}</h3>
      {description && <p className="text-sm text-gray-500 dark:text-gray-400 max-w-sm mb-6">{description}</p>}
      {action && <div>{action}</div>}
    </div>
  );
}
