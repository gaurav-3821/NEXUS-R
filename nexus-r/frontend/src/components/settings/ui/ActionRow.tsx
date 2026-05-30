import React from 'react';
import clsx from 'clsx';

export interface ActionRowProps extends React.HTMLAttributes<HTMLDivElement> {
  label: string;
  description?: string;
  action: React.ReactNode;
}

export function ActionRow({ label, description, action, className, ...props }: ActionRowProps) {
  return (
    <div className={clsx("flex items-center justify-between py-2 border-b border-gray-100 last:border-0", className)} {...props}>
      <div>
        <div className="text-[15px] font-semibold text-gray-800">{label}</div>
        {description && <div className="text-[13px] text-gray-500 mt-0.5">{description}</div>}
      </div>
      <div>
        {action}
      </div>
    </div>
  );
}
