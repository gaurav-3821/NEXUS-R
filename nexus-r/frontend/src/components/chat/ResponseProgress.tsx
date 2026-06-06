import { useState, useEffect, useRef } from 'react';
import { useAppStore } from '../../store/useAppStore';
import clsx from 'clsx';

export function ResponseProgress() {
  const { workflowSteps, streamingMsgId } = useAppStore();
  const [stallSeconds, setStallSeconds] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!streamingMsgId) {
      setStallSeconds(0);
      if (intervalRef.current) clearInterval(intervalRef.current);
      intervalRef.current = null;
      return;
    }

    const activeStep = workflowSteps.find(s => s.status === 'active');
    if (activeStep && activeStep.step !== 'generating') {
      setStallSeconds(0);
      intervalRef.current = setInterval(() => setStallSeconds(v => v + 1), 1000);
    } else {
      setStallSeconds(0);
      if (intervalRef.current) clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [workflowSteps, streamingMsgId]);

  if (!streamingMsgId || workflowSteps.length === 0) return null;

  return (
    <div className="flex flex-col gap-3 py-1 w-full max-w-sm">
      {workflowSteps.map((step) => {
        const isActive = step.status === 'active';
        const isCompleted = step.status === 'completed';
        const isPending = step.status === 'pending';
        const stalled = isActive && stallSeconds >= 3;

        return (
          <div key={step.step} className="flex items-center gap-2.5 text-sm leading-none">
            <svg className="w-[18px] h-[18px] shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              {isCompleted && (
                <path d="M20 6L9 17l-5-5" className="text-emerald-500" />
              )}
              {isActive && (
                <>
                  <circle cx="12" cy="12" r="10" className={clsx(stalled ? "text-amber-500" : "text-indigo-500", "opacity-25")} />
                  <path d="M12 6v6l4 2" className={clsx(stalled ? "text-amber-500" : "text-indigo-500")}>
                    <animateTransform attributeName="transform" type="rotate" from="0 12 12" to="360 12 12" dur="1s" repeatCount="indefinite" />
                  </path>
                </>
              )}
              {isPending && (
                <circle cx="12" cy="12" r="8" className="text-gray-300 dark:text-gray-600" />
              )}
            </svg>
            <span className={clsx(
              "font-medium",
              isCompleted && "text-emerald-600 dark:text-emerald-400",
              isActive && (stalled ? "text-amber-600 dark:text-amber-400" : "text-indigo-600 dark:text-indigo-400"),
              isPending && "text-gray-400 dark:text-gray-500",
            )}>
              {step.message}
              {stalled && (
                <span className="text-gray-400 dark:text-gray-500 font-normal ml-1.5 animate-pulse">Still working...</span>
              )}
            </span>
          </div>
        );
      })}
    </div>
  );
}
