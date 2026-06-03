import React from 'react';
import clsx from 'clsx';

import { useAppearanceStore } from '../../../store/appearanceStore';

export interface SettingsCardProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  headerAction?: React.ReactNode;
}

export function SettingsCard({ title, subtitle, children, headerAction, className, ...props }: SettingsCardProps) {
  const { compactMode } = useAppearanceStore();

  return (
    <div className={clsx("bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 shadow-sm transition-colors", compactMode ? "rounded-xl p-3" : "rounded-2xl p-5", className)} {...props}>
      <div className={clsx("flex items-center justify-between", compactMode ? "mb-2" : "mb-4")}>
        <div>
          <h4 className="font-bold text-gray-900 dark:text-gray-100">{title}</h4>
          {subtitle && <p className="text-xs text-gray-500 dark:text-gray-400 font-medium mt-1">{subtitle}</p>}
        </div>
        {headerAction && <div>{headerAction}</div>}
      </div>
      <div className={clsx(compactMode ? "space-y-1.5" : "space-y-3")}>
        {children}
      </div>
    </div>
  );
}
