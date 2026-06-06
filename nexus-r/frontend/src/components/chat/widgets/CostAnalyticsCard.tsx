import { Receipt } from 'lucide-react';

interface CostAnalyticsCardProps {
  data: {
    estimated_cost: number;
    model: string;
    tier: string;
    currency: string;
  };
}

export default function CostAnalyticsCard({ data }: CostAnalyticsCardProps) {
  return (
    <div className="px-4 py-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-100 dark:border-amber-800/40 rounded-xl min-w-[140px]">
      <div className="flex items-center gap-1.5 mb-1">
        <Receipt size={14} className="text-amber-600 dark:text-amber-400" />
        <span className="text-xs font-semibold text-amber-700 dark:text-amber-300">Cost</span>
      </div>
      <div className="text-lg font-bold text-gray-900 dark:text-gray-100 font-mono">
        ${data.estimated_cost?.toFixed(6) ?? '0'}
      </div>
      <div className="text-[10px] text-gray-400 dark:text-gray-500 mt-0.5 truncate">
        {data.model} · {data.tier}
      </div>
    </div>
  );
}
