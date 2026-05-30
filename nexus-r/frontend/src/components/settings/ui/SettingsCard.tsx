import React from 'react';
import clsx from 'clsx';

export interface SettingsCardProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}

export function SettingsCard({ title, subtitle, children, className, ...props }: SettingsCardProps) {
  return (
    <div className={clsx("bg-white border border-gray-200 rounded-2xl p-5 shadow-sm", className)} {...props}>
      <h4 className="font-bold text-gray-900 mb-1">{title}</h4>
      {subtitle && <p className="text-xs text-gray-500 font-medium mb-4">{subtitle}</p>}
      <div className="space-y-3">
        {children}
      </div>
    </div>
  );
}
