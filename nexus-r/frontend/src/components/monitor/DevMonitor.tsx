import { useAppStore } from '../../store/useAppStore';
import { Activity, Zap, Clock, Wrench, ShieldAlert } from 'lucide-react';
import clsx from 'clsx';

export default function DevMonitor() {
  const { 
    workflowState, 
    workflowStage, 
    tokenSpeed, 
    executionTime, 
    activeTools, 
    reasoningTrace,
    totalSessionCost
  } = useAppStore();

  return (
    <div className="flex flex-col h-full bg-black/40 backdrop-blur-xl border-l border-white/5">
      <div className="p-4 border-b border-white/10 flex items-center justify-between bg-white dark:bg-slate-900/5">
        <div className="flex items-center gap-2">
          <Activity size={18} className="text-accent-400" />
          <h3 className="font-semibold text-sm uppercase tracking-wider text-gray-300">Dev Pipeline</h3>
        </div>
        <div className="flex items-center gap-2">
          <div className={clsx(
            "w-2 h-2 rounded-full",
            workflowState === 'reasoning' ? "bg-accent-500 animate-pulse-glow" : "bg-gray-50 dark:bg-[#0f172a]0"
          )} />
        </div>
      </div>

      <div className="p-4 space-y-6 overflow-y-auto">
        {/* State Widget */}
        <div className="glass-panel p-4 rounded-xl relative overflow-hidden group">
          <div className="absolute inset-0 bg-gradient-to-br from-accent-500/10 to-purple-500/10 opacity-0 group-hover:opacity-100 transition-opacity" />
          <div className="text-xs text-gray-500 dark:text-gray-400 font-medium uppercase tracking-wider mb-1">Status</div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white capitalize">{workflowStage}</span>
            <span className="text-xs text-accent-400 font-mono">[{workflowState}]</span>
          </div>
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-2 gap-3">
          <MetricCard icon={<Zap size={14} />} label="Speed" value={tokenSpeed} />
          <MetricCard icon={<Clock size={14} />} label="Time" value={executionTime} />
          <MetricCard icon={<Wrench size={14} />} label="Tools" value={activeTools} className="col-span-2" />
          <MetricCard icon={<ShieldAlert size={14} />} label="Session Cost" value={`$${totalSessionCost.toFixed(4)}`} className="col-span-2 border-accent-500/30 bg-accent-500/5 text-accent-200" />
        </div>

        {/* Reasoning Trace */}
        <div className="mt-4">
          <div className="text-xs text-gray-500 dark:text-gray-400 font-medium uppercase tracking-wider mb-2 flex justify-between">
            <span>Live Reasoning</span>
            <span className="font-mono text-[10px] bg-white dark:bg-slate-900/10 px-1.5 py-0.5 rounded text-gray-400">TRACE</span>
          </div>
          <div className="glass-panel p-3 rounded-xl min-h-[200px] text-xs font-mono text-gray-300 whitespace-pre-wrap leading-relaxed shadow-inner">
            {reasoningTrace}
          </div>
        </div>
      </div>
    </div>
  );
}

function MetricCard({ icon, label, value, className = "" }: { icon: React.ReactNode, label: string, value: string, className?: string }) {
  return (
    <div className={`glass-panel p-3 rounded-xl flex flex-col gap-1 border border-white/5 ${className}`}>
      <div className="flex items-center gap-1.5 text-gray-400">
        {icon}
        <span className="text-[10px] uppercase font-semibold tracking-wider">{label}</span>
      </div>
      <div className="text-sm font-mono font-medium text-gray-200">
        {value}
      </div>
    </div>
  );
}
