import React from 'react';
import clsx from 'clsx';

export interface PageHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
}

export function PageHeader({ title, subtitle, action, className, ...props }: PageHeaderProps) {
  return (
    <div 
      className={clsx(
        "flex items-center justify-between px-8 py-5 border-b border-gray-200 bg-white",
        className
      )}
      {...props}
    >
      <div>
        <h2 className="text-2xl font-bold text-gray-900">{title}</h2>
        {subtitle && <p className="text-sm text-gray-500 font-medium mt-1">{subtitle}</p>}
      </div>
      {action && (
        <div>
          {action}
        </div>
      )}
    </div>
  );
}
