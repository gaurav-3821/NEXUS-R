import React from 'react';
import clsx from 'clsx';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'primary' | 'secondary' | 'success' | 'warning' | 'danger' | 'outline';
  children: React.ReactNode;
}

export function Badge({ variant = 'primary', className, children, ...props }: BadgeProps) {
  const variants = {
    primary: "bg-accent-100 text-accent-700",
    secondary: "bg-gray-100 text-gray-700 dark:text-gray-300",
    success: "bg-green-100 text-green-700",
    warning: "bg-amber-100 text-amber-700",
    danger: "bg-red-100 text-red-700",
    outline: "bg-transparent border border-gray-200 dark:border-slate-800 text-gray-600"
  };

  return (
    <span 
      className={clsx(
        "px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase tracking-wider",
        variants[variant],
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
}
