import { Brain } from 'lucide-react';

interface MemoryCardProps {
  data: {
    facts: Array<Record<string, any>>;
    fact_count: number;
  };
}

export default function MemoryCard({ data }: MemoryCardProps) {
  const facts = data.facts ?? [];
  if (facts.length === 0) return null;

  return (
    <div className="px-4 py-3 bg-pink-50 dark:bg-pink-900/20 border border-pink-100 dark:border-pink-800/40 rounded-xl min-w-[160px]">
      <div className="flex items-center gap-1.5 mb-1">
        <Brain size={14} className="text-pink-500 dark:text-pink-400" />
        <span className="text-xs font-semibold text-pink-700 dark:text-pink-300">Memory ({data.fact_count})</span>
      </div>
      <div className="flex flex-col gap-0.5">
        {facts.slice(0, 3).map((f, i) => (
          <div key={i} className="text-[10px] text-gray-600 dark:text-gray-400 truncate">
            {typeof f === 'string' ? f : f.content || f.text || JSON.stringify(f).slice(0, 60)}
          </div>
        ))}
        {facts.length > 3 && (
          <div className="text-[10px] text-gray-400 dark:text-gray-500">+{facts.length - 3} more</div>
        )}
      </div>
    </div>
  );
}
