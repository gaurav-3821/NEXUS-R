import React from 'react';
import clsx from 'clsx';

export interface SettingsCardProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  headerAction?: React.ReactNode;
}

export function SettingsCard({ title, subtitle, children, headerAction, className, ...props }: SettingsCardProps) {
  return (
    <div className={clsx("bg-white border border-gray-200 rounded-2xl p-5 shadow-sm", className)} {...props}>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h4 className="font-bold text-gray-900">{title}</h4>
          {subtitle && <p className="text-xs text-gray-500 font-medium mt-1">{subtitle}</p>}
        </div>
        {headerAction && <div>{headerAction}</div>}
      </div>
      <div className="space-y-3">
        {children}
      </div>
    </div>
  );
}
