import React from 'react';
import clsx from 'clsx';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: string;
  subtitle?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
}

export function Card({ title, subtitle, children, footer, className, ...props }: CardProps) {
  return (
    <div 
      className={clsx(
        "bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-2xl shadow-sm overflow-hidden",
        className
      )} 
      {...props}
    >
      {(title || subtitle) && (
        <div className="px-5 py-4 border-b border-gray-100">
          {title && <h3 className="font-bold text-gray-900 dark:text-gray-100">{title}</h3>}
          {subtitle && <p className="text-xs text-gray-500 dark:text-gray-400 font-medium mt-1">{subtitle}</p>}
        </div>
      )}
      <div className="p-5">
        {children}
      </div>
      {footer && (
        <div className="px-5 py-4 border-t border-gray-100 bg-gray-50 dark:bg-[#0f172a]/50">
          {footer}
        </div>
      )}
    </div>
  );
}
