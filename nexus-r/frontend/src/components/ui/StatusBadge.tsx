import React from 'react';
import clsx from 'clsx';

export interface StatusBadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  status: 'online' | 'offline' | 'pending' | 'error';
  label?: string;
}

export function StatusBadge({ status, label, className, ...props }: StatusBadgeProps) {
  const statusColors = {
    online: "bg-green-500",
    offline: "bg-gray-400",
    pending: "bg-amber-500 animate-pulse",
    error: "bg-red-500"
  };

  const statusText = {
    online: "text-green-600",
    offline: "text-gray-500 dark:text-gray-400",
    pending: "text-amber-600",
    error: "text-red-600"
  };

  const defaultLabels = {
    online: "Connected",
    offline: "Offline",
    pending: "Connecting...",
    error: "Error"
  };

  const displayLabel = label || defaultLabels[status];

  return (
    <div className={clsx("flex items-center gap-2", className)} {...props}>
      <div className={clsx("w-2 h-2 rounded-full", statusColors[status])} />
      <span className={clsx("text-sm font-semibold", statusText[status])}>
        {displayLabel}
      </span>
    </div>
  );
}
