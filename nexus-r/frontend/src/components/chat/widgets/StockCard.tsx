import { TrendingUp, TrendingDown, DollarSign } from 'lucide-react';

interface StockCardProps {
  data: {
    symbol: string;
    price?: number;
    change?: number;
    change_percent?: number;
    volume?: number;
    error?: string;
  };
}

export default function StockCard({ data }: StockCardProps) {
  if (data.error) {
    return (
      <div className="px-3 py-2 bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg text-xs text-orange-700 dark:text-orange-300">
        {data.error}
      </div>
    );
  }

  const change = data.change_percent ?? 0;
  const isUp = change >= 0;
  const TrendIcon = isUp ? TrendingUp : TrendingDown;

  return (
    <div className="px-4 py-3 bg-green-50 dark:bg-green-900/20 border border-green-100 dark:border-green-800/40 rounded-xl min-w-[180px]">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-bold text-gray-600 dark:text-gray-400 uppercase tracking-wide">
          {data.symbol}
        </span>
        <DollarSign size={14} className="text-green-600 dark:text-green-400" />
      </div>
      <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
        ${data.price?.toFixed(2) ?? '—'}
      </div>
      <div className={`flex items-center gap-1 text-xs font-medium mt-0.5 ${isUp ? 'text-green-600 dark:text-green-400' : 'text-red-500 dark:text-red-400'}`}>
        <TrendIcon size={12} />
        <span>{change >= 0 ? '+' : ''}{change.toFixed(2)}%</span>
      </div>
      {data.volume && (
        <div className="text-[10px] text-gray-400 dark:text-gray-500 mt-1">
          Vol: {(data.volume / 1000000).toFixed(1)}M
        </div>
      )}
    </div>
  );
}
