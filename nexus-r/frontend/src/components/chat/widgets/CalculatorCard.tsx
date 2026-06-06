import { Calculator } from 'lucide-react';

interface CalculatorCardProps {
  data: {
    expression: string;
    result: string;
  };
}

export default function CalculatorCard({ data }: CalculatorCardProps) {
  return (
    <div className="px-4 py-3 bg-purple-50 dark:bg-purple-900/20 border border-purple-100 dark:border-purple-800/40 rounded-xl flex items-center gap-3">
      <Calculator size={20} className="text-purple-500 dark:text-purple-400 shrink-0" />
      <div className="flex-1 min-w-0">
        <div className="text-xs text-gray-500 dark:text-gray-400 font-mono truncate">
          {data.expression}
        </div>
        <div className="text-lg font-bold text-gray-900 dark:text-gray-100 font-mono">
          = {data.result}
        </div>
      </div>
    </div>
  );
}
