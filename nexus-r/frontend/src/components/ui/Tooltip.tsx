import React, { useState } from 'react';
import clsx from 'clsx';

export interface TooltipProps {
  content: React.ReactNode;
  children: React.ReactElement;
  position?: 'top' | 'bottom' | 'left' | 'right';
  delay?: number;
}

export function Tooltip({ content, children, position = 'top', delay = 200 }: TooltipProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [timeoutId, setTimeoutId] = useState<NodeJS.Timeout | null>(null);

  const handleMouseEnter = () => {
    const id = setTimeout(() => setIsVisible(true), delay);
    setTimeoutId(id);
  };

  const handleMouseLeave = () => {
    if (timeoutId) clearTimeout(timeoutId);
    setIsVisible(false);
  };

  const positionClasses = {
    top: "bottom-full left-1/2 -translate-x-1/2 mb-2",
    bottom: "top-full left-1/2 -translate-x-1/2 mt-2",
    left: "right-full top-1/2 -translate-y-1/2 mr-2",
    right: "left-full top-1/2 -translate-y-1/2 ml-2"
  };

  return (
    <div 
      className="relative inline-flex"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onFocus={handleMouseEnter}
      onBlur={handleMouseLeave}
    >
      {children}
      
      {isVisible && (
        <div 
          className={clsx(
            "absolute z-50 px-2.5 py-1.5 text-xs font-medium text-white bg-gray-900 rounded-md shadow-sm whitespace-nowrap animate-in fade-in zoom-in-95 duration-100",
            positionClasses[position]
          )}
          role="tooltip"
        >
          {content}
          {/* Simple Arrow */}
          <div className={clsx(
            "absolute w-2 h-2 bg-gray-900 rotate-45",
            position === 'top' && "bottom-[-4px] left-1/2 -translate-x-1/2",
            position === 'bottom' && "top-[-4px] left-1/2 -translate-x-1/2",
            position === 'left' && "right-[-4px] top-1/2 -translate-y-1/2",
            position === 'right' && "left-[-4px] top-1/2 -translate-y-1/2"
          )} />
        </div>
      )}
    </div>
  );
}
