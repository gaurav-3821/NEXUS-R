import { GitBranch } from 'lucide-react';

interface RouterDecisionCardProps {
  data: {
    model: string;
    tier: string;
    estimated_cost: number;
  };
}

export default function RouterDecisionCard({ data }: RouterDecisionCardProps) {
  return (
    <div className="px-4 py-3 bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-100 dark:border-indigo-800/40 rounded-xl min-w-[160px]">
      <div className="flex items-center gap-1.5 mb-1">
        <GitBranch size={14} className="text-indigo-500 dark:text-indigo-400" />
        <span className="text-xs font-semibold text-indigo-700 dark:text-indigo-300">Router</span>
      </div>
      <div className="text-xs font-mono text-gray-800 dark:text-gray-200 truncate">{data.model}</div>
      <div className="flex justify-between mt-1 text-[10px] text-gray-500 dark:text-gray-400">
        <span>Tier: {data.tier}</span>
        <span>${data.estimated_cost?.toFixed(6) ?? '0'}</span>
      </div>
    </div>
  );
}
