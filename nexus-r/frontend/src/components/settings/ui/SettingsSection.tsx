import React from 'react';
import clsx from 'clsx';

export interface SettingsSectionProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string;
  description?: string;
  children: React.ReactNode;
}

export function SettingsSection({ title, description, children, className, ...props }: SettingsSectionProps) {
  return (
    <div className={clsx("space-y-6", className)} {...props}>
      <div>
        <h3 className="text-lg font-bold text-gray-900 mb-1">{title}</h3>
        {description && <p className="text-sm text-gray-500 font-medium mb-6">{description}</p>}
      </div>
      <div className="space-y-6">
        {children}
      </div>
    </div>
  );
}
