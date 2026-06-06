import { Cpu, WifiOff } from 'lucide-react';

interface ModelStatusCardProps {
  data: {
    local_available: boolean;
    local_models: string[];
    ollama_running: boolean;
  };
}

export default function ModelStatusCard({ data }: ModelStatusCardProps) {
  return (
    <div className="px-4 py-3 bg-cyan-50 dark:bg-cyan-900/20 border border-cyan-100 dark:border-cyan-800/40 rounded-xl min-w-[160px]">
      <div className="flex items-center gap-1.5 mb-1">
        {data.ollama_running ? (
          <Cpu size={14} className="text-cyan-600 dark:text-cyan-400" />
        ) : (
          <WifiOff size={14} className="text-gray-400" />
        )}
        <span className="text-xs font-semibold text-cyan-700 dark:text-cyan-300">Models</span>
      </div>
      <div className="text-xs text-gray-600 dark:text-gray-400">
        {data.ollama_running ? (
          <>Ollama: {data.local_models?.length ?? 0} models</>
        ) : (
          <>Ollama: Offline</>
        )}
      </div>
      {data.local_models && data.local_models.length > 0 && (
        <div className="text-[10px] text-gray-400 dark:text-gray-500 mt-0.5 truncate" title={data.local_models.join(', ')}>
          {data.local_models.slice(0, 3).join(', ')}{data.local_models.length > 3 ? '...' : ''}
        </div>
      )}
    </div>
  );
}
