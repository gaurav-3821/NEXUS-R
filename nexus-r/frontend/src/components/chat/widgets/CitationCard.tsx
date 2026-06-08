import { ExternalLink, BookOpen } from 'lucide-react';

interface CitationCardProps {
  data: {
    sources: Array<{ title: string; url: string; snippet: string }>;
  };
}

export default function CitationCard({ data }: CitationCardProps) {
  if (!data) return null;
  const sources = Array.isArray(data.sources) ? data.sources : [];
  if (sources.length === 0) return null;

  return (
    <div className="px-4 py-3 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-100 dark:border-emerald-800/40 rounded-xl">
      <div className="flex items-center gap-1.5 mb-2">
        <BookOpen size={14} className="text-emerald-600 dark:text-emerald-400" />
        <span className="text-xs font-semibold text-emerald-700 dark:text-emerald-300">
          Sources ({sources.length})
        </span>
      </div>
      <div className="flex flex-col gap-1.5">
        {sources.map((src, i) => (
          <a
            key={i}
            href={src.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-start gap-1.5 text-xs text-gray-600 dark:text-gray-400 hover:text-emerald-600 dark:hover:text-emerald-400 group"
          >
            <span className="text-[10px] font-bold text-emerald-500 shrink-0 mt-0.5">[{i + 1}]</span>
            <span className="flex-1 min-w-0 truncate">{src.title || src.url.replace(/^https?:\/\//, '').split('/')[0]}</span>
            <ExternalLink size={10} className="shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
          </a>
        ))}
      </div>
    </div>
  );
}
