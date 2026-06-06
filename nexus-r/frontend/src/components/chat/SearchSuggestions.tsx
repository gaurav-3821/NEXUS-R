import { useState, useEffect, useRef } from 'react';
import { fetchSuggestions } from '../../api/chat';
import clsx from 'clsx';

interface SearchSuggestionsProps {
  prefix: string;
  onSelect: (suggestion: string) => void;
  visible: boolean;
}

export default function SearchSuggestions({ prefix, onSelect, visible }: SearchSuggestionsProps) {
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const mountedRef = useRef(false);

  useEffect(() => {
    mountedRef.current = true;
    if (timerRef.current) clearTimeout(timerRef.current);
    if (abortRef.current) abortRef.current.abort();

    const trimmed = prefix.trim();
    if (!visible || !trimmed || trimmed.length < 1) {
      setSuggestions([]);
      return;
    }

    timerRef.current = setTimeout(async () => {
      abortRef.current = new AbortController();
      try {
        const results = await fetchSuggestions(trimmed, 5, abortRef.current.signal);
        if (mountedRef.current) {
          setSuggestions(results);
        }
      } catch {
        if (mountedRef.current) setSuggestions([]);
      }
    }, 300);

    return () => {
      mountedRef.current = false;
      if (timerRef.current) clearTimeout(timerRef.current);
      if (abortRef.current) abortRef.current.abort();
    };
  }, [prefix, visible]);

  if (suggestions.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-1.5 px-1 py-1">
      {suggestions.map((s) => (
        <button
          key={s}
          onClick={() => onSelect(s)}
          className={clsx(
            "px-2.5 py-1 rounded-full text-xs font-medium transition-all",
            "bg-gray-100 dark:bg-slate-800 text-gray-600 dark:text-gray-400",
            "hover:bg-gray-200 dark:hover:bg-slate-700 hover:text-gray-800 dark:hover:text-gray-200"
          )}
        >
          {s}
        </button>
      ))}
    </div>
  );
}
