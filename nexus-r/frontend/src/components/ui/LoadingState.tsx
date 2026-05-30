import React from 'react';
import clsx from 'clsx';
import { Loader2 } from 'lucide-react';

export interface LoadingStateProps extends React.HTMLAttributes<HTMLDivElement> {
  text?: string;
  fullScreen?: boolean;
}

export function LoadingState({ text = 'Loading...', fullScreen = false, className, ...props }: LoadingStateProps) {
  return (
    <div 
      className={clsx(
        "flex flex-col items-center justify-center gap-3 text-gray-500",
        fullScreen ? "fixed inset-0 z-50 bg-white/80 backdrop-blur-sm" : "p-8",
        className
      )}
      {...props}
    >
      <Loader2 size={32} className="animate-spin text-indigo-600" />
      {text && <p className="text-sm font-medium animate-pulse">{text}</p>}
    </div>
  );
}
