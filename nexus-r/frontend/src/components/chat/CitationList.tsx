import { useState } from 'react';
import type { Source } from '../../store/useAppStore';
import { ExternalLink, ChevronDown } from 'lucide-react';
import clsx from 'clsx';

interface CitationListProps {
  sources: Source[];
}

export default function CitationList({ sources }: CitationListProps) {
  const [expanded, setExpanded] = useState(false);

  if (!sources || sources.length === 0) return null;

  const visible = expanded ? sources : sources.slice(0, 3);

  return (
    <div className="mt-4 pt-3 border-t border-gray-100 dark:border-slate-800">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1.5 text-xs font-semibold text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 transition-colors mb-2"
      >
        <span>Sources ({sources.length})</span>
        <ChevronDown
          size={12}
          className={clsx(
            "transition-transform",
            expanded && "rotate-180"
          )}
        />
      </button>
      <div className="flex flex-wrap gap-2">
        {visible.map((src, i) => (
          <a
            key={i}
            href={src.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-start gap-2 px-3 py-2 bg-gray-50 dark:bg-slate-800/60 border border-gray-100 dark:border-slate-700 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors max-w-xs group"
          >
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1">
                <span className="text-[11px] font-bold text-accent-600 dark:text-accent-400 shrink-0">
                  [{i + 1}]
                </span>
                <span className="text-xs font-medium text-gray-700 dark:text-gray-300 truncate">
                  {src.title || src.url.replace(/^https?:\/\//, '').split('/')[0]}
                </span>
              </div>
              <div className="text-[10px] text-gray-400 dark:text-gray-500 truncate mt-0.5">
                {src.url.replace(/^https?:\/\//, '').split('?')[0]}
              </div>
              {src.content && (
                <div className="text-[10px] text-gray-500 dark:text-gray-400 line-clamp-2 mt-0.5 italic">
                  {src.content}
                </div>
              )}
            </div>
            <ExternalLink
              size={12}
              className="text-gray-300 dark:text-gray-600 group-hover:text-accent-500 transition-colors shrink-0 mt-0.5"
            />
          </a>
        ))}
        {!expanded && sources.length > 3 && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-[11px] font-medium text-accent-600 dark:text-accent-400 hover:underline self-center px-2"
          >
            +{sources.length - 3} more
          </button>
        )}
      </div>
    </div>
  );
}