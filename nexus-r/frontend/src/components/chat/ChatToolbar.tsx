import { useLayoutEffect, useRef, useState } from 'react';
import { useAppStore } from '../../store/useAppStore';
import { Zap, Gauge, Target, Globe, Search, X, AlertTriangle } from 'lucide-react';
import { Tooltip } from '../ui/Tooltip';
import clsx from 'clsx';

const MODES = [
  { key: 'speed' as const, label: 'Speed', icon: Zap },
  { key: 'balanced' as const, label: 'Balanced', icon: Gauge },
  { key: 'quality' as const, label: 'Quality', icon: Target },
];

const SOURCE_OPTIONS = [
  { key: 'web', label: 'Web' },
  { key: 'news', label: 'News' },
  { key: 'academic', label: 'Academic' },
  { key: 'social', label: 'Social' },
];

export default function ChatToolbar() {
  const {
    optimizationMode,
    searchEnabled,
    searchSources,
    setOptimizationMode,
    setSearchEnabled,
    setSearchSources,
  } = useAppStore();

  const toggleSource = (key: string) => {
    if (searchSources.includes(key)) {
      const next = searchSources.filter(s => s !== key);
      setSearchSources(next.length > 0 ? next : ['web']);
    } else {
      setSearchSources([...searchSources, key]);
    }
  };

  // Sliding indicator for mode buttons
  const modeIdx = MODES.findIndex(m => m.key === optimizationMode);
  const modeRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const modeContainerRef = useRef<HTMLDivElement>(null);
  const [modeSlider, setModeSlider] = useState({ left: 0, width: 0 });

  useLayoutEffect(() => {
    const btn = modeRefs.current[modeIdx];
    const ctr = modeContainerRef.current;
    if (btn && ctr) {
      const cr = ctr.getBoundingClientRect();
      const br = btn.getBoundingClientRect();
      setModeSlider({ left: br.left - cr.left, width: br.width });
    }
  }, [modeIdx, optimizationMode]);



  return (
    <div className="flex flex-col gap-1">
    <div className="flex items-center gap-3 px-1 py-1.5">
      {/* Mode Selector with sliding highlight */}
      <div ref={modeContainerRef} className="relative flex items-center gap-0.5 bg-gray-100 dark:bg-slate-800/60 rounded-lg p-0.5">
        <div
          className="absolute top-0.5 bottom-0.5 bg-white dark:bg-slate-700 rounded-md shadow-sm transition-[left,width] duration-300 ease-in-out"
          style={{ left: modeSlider.left, width: modeSlider.width }}
        />
        {MODES.map((m, i) => {
          const Icon = m.icon;
          const active = optimizationMode === m.key;
          return (
            <button
              key={m.key}
              ref={el => { modeRefs.current[i] = el; }}
              onClick={() => setOptimizationMode(m.key)}
              className={clsx(
                "relative z-10 flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium transition-all",
                active
                  ? "text-gray-900 dark:text-gray-100"
                  : "text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
              )}
            >
              <Icon size={12} className={clsx("transition-transform duration-300", active && "scale-110")} />
              {m.label}
            </button>
          );
        })}
      </div>

      <div className="w-px h-5 bg-gray-200 dark:bg-slate-700" />

      {/* Search Toggle */}
      <Tooltip
        content={
          optimizationMode === 'speed'
            ? 'Search is only available in Balanced or Quality mode. Switch mode to enable web research.'
            : 'Enable web search. The model will use retrieved sources to answer your question.'
        }
        position="bottom"
      >
        <button
          onClick={() => {
            if (optimizationMode === 'speed') {
              setOptimizationMode('balanced');
              setSearchEnabled(true);
              return;
            }
            setSearchEnabled(!searchEnabled);
          }}
          className={clsx(
            "flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium transition-all duration-300 ease-in-out",
            searchEnabled
              ? "bg-accent-50 dark:bg-accent-900/20 text-accent-700 dark:text-accent-300 shadow-[0_0_8px_rgba(99,102,241,0.4)] dark:shadow-[0_0_8px_rgba(129,140,248,0.3)]"
              : "text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
          )}
        >
          <Search size={12} className={clsx("transition-transform duration-300", searchEnabled && "scale-110")} />
          Search
          {searchEnabled && optimizationMode === 'speed' && (
            <AlertTriangle size={10} className="ml-0.5 text-amber-500" />
          )}
        </button>
      </Tooltip>

      {/* Source Pills with sliding highlight — visible when search is enabled */}
      {searchEnabled && (
        <>
          <div className="w-px h-5 bg-gray-200 dark:bg-slate-700" />
          <div className="flex items-center gap-1">
            {SOURCE_OPTIONS.map(opt => {
              const active = (searchSources || []).includes(opt.key);
              return (
                <button
                  key={opt.key}
                  onClick={() => toggleSource(opt.key)}
                  className={clsx(
                    "flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium transition-all",
                    active
                      ? "bg-gray-200 dark:bg-slate-700 text-gray-800 dark:text-gray-200"
                      : "text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-400"
                  )}
                >
                  <Globe size={10} />
                  {opt.label}
                  {active && (
                    <X size={10} className="ml-0.5" />
                  )}
                </button>
              );
            })}
          </div>
        </>
      )}
    </div>

      {searchEnabled && optimizationMode === 'speed' && (
        <div className="flex items-start gap-2 mx-1 px-2.5 py-1.5 rounded-md bg-amber-50/70 dark:bg-amber-900/15 border border-amber-200/60 dark:border-amber-800/40 text-[11px] text-amber-800 dark:text-amber-200">
          <AlertTriangle size={12} className="shrink-0 mt-0.5 text-amber-500" />
          <div className="flex-1 leading-snug">
            <span className="font-semibold">Search disabled:</span> Speed mode skips web research to keep responses fast.
            <button
              onClick={() => setOptimizationMode('balanced')}
              className="ml-1 underline font-medium hover:text-amber-900 dark:hover:text-amber-100"
            >
              Switch to Balanced
            </button>
          </div>
        </div>
      )}
    </div>
  );
}