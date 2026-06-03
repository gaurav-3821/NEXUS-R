import { useEffect } from 'react';
import { useDashboardStore } from '../../store/dashboardStore';
import { X, Activity, DollarSign, Clock, Layers, Cpu, Hash } from 'lucide-react';
import { APP_NAME } from '../../constants';

interface AgentDashboardModalProps {
  onClose: () => void;
}

export function AgentDashboardModal({ onClose }: AgentDashboardModalProps) {
  const { summary, tasks, modelBreakdown, isLoading, error, loadDashboardData } = useDashboardStore();

  useEffect(() => {
    loadDashboardData();
    const interval = setInterval(() => {
      loadDashboardData();
    }, 5000); // refresh every 5s
    return () => clearInterval(interval);
  }, [loadDashboardData]);

  const formatDate = (dateStr: string) => {
    const d = new Date(dateStr);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const getModelModelsList = () => {
    if (!modelBreakdown) return [];
    return Object.entries(modelBreakdown)
      .map(([name, stats]) => ({ name, ...stats }))
      .sort((a, b) => b.cost - a.cost); // sort by highest cost
  };

  return (
    <div className="absolute inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-2xl shadow-2xl flex flex-col w-full max-w-6xl h-[90vh] overflow-hidden flex-shrink-0 animate-in zoom-in-95 duration-200">
        
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-100 dark:border-slate-800 shrink-0 bg-white dark:bg-slate-900">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-orange-50 dark:bg-orange-900/20 text-orange-600 dark:text-orange-400 flex items-center justify-center">
              <Activity size={20} />
            </div>
            <div>
              <div className="flex items-center gap-3">
                <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">Agent Live Dashboard</h2>
                <span className="px-2 py-0.5 text-[10px] font-bold tracking-wider uppercase bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 rounded-full flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></span>
                  Live
                </span>
              </div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400 mt-0.5">
                Real-time telemetry, operational costs, and performance of {APP_NAME}.
              </p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="w-10 h-10 flex items-center justify-center rounded-full hover:bg-gray-100 dark:hover:bg-slate-800 text-gray-500 transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6 bg-gray-50 dark:bg-[#0b1120]">
          {error && (
            <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-xl border border-red-200 dark:border-red-800 text-sm font-medium">
              Failed to load telemetry data: {error}
            </div>
          )}

          {isLoading && !summary ? (
            <div className="flex flex-col items-center justify-center h-64 space-y-4">
              <div className="w-8 h-8 border-4 border-orange-500 border-t-transparent rounded-full animate-spin"></div>
              <p className="text-sm font-medium text-gray-500">Connecting to telemetry stream...</p>
            </div>
          ) : (
            <div className="space-y-6">
              
              {/* Top Stats */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="bg-white dark:bg-slate-900 rounded-xl border border-gray-200 dark:border-slate-800 p-5 shadow-sm">
                  <div className="flex items-center gap-2 mb-2 text-gray-500 dark:text-gray-400 font-semibold text-xs uppercase tracking-wider">
                    <DollarSign size={14} /> Total Cost
                  </div>
                  <div className="text-3xl font-bold text-gray-900 dark:text-gray-100">
                    ${summary?.total_cost?.toFixed(5) || '0.00000'}
                  </div>
                </div>
                
                <div className="bg-white dark:bg-slate-900 rounded-xl border border-gray-200 dark:border-slate-800 p-5 shadow-sm">
                  <div className="flex items-center gap-2 mb-2 text-gray-500 dark:text-gray-400 font-semibold text-xs uppercase tracking-wider">
                    <Hash size={14} /> Total Tasks
                  </div>
                  <div className="text-3xl font-bold text-gray-900 dark:text-gray-100">
                    {summary?.total_tasks || 0}
                  </div>
                </div>

                <div className="bg-white dark:bg-slate-900 rounded-xl border border-gray-200 dark:border-slate-800 p-5 shadow-sm">
                  <div className="flex items-center gap-2 mb-2 text-gray-500 dark:text-gray-400 font-semibold text-xs uppercase tracking-wider">
                    <Clock size={14} /> Avg Latency
                  </div>
                  <div className="text-3xl font-bold text-gray-900 dark:text-gray-100">
                    {summary?.avg_latency_ms ? (summary.avg_latency_ms / 1000).toFixed(2) : '0'}s
                  </div>
                </div>

                <div className="bg-white dark:bg-slate-900 rounded-xl border border-gray-200 dark:border-slate-800 p-5 shadow-sm">
                  <div className="flex items-center gap-2 mb-2 text-gray-500 dark:text-gray-400 font-semibold text-xs uppercase tracking-wider">
                    <Layers size={14} /> Tokens Processed
                  </div>
                  <div className="text-3xl font-bold text-gray-900 dark:text-gray-100">
                    {summary?.total_tokens?.toLocaleString() || '0'}
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                
                {/* Model Breakdown */}
                <div className="bg-white dark:bg-slate-900 rounded-xl border border-gray-200 dark:border-slate-800 shadow-sm overflow-hidden flex flex-col">
                  <div className="p-4 border-b border-gray-100 dark:border-slate-800 bg-gray-50/50 dark:bg-slate-900/50">
                    <h3 className="font-bold text-gray-800 dark:text-gray-200 flex items-center gap-2">
                      <Cpu size={16} className="text-indigo-500" /> Model Utilization
                    </h3>
                  </div>
                  <div className="p-4 flex-1 overflow-y-auto">
                    {getModelModelsList().length === 0 ? (
                      <div className="text-center py-8 text-sm text-gray-500">No model usage recorded.</div>
                    ) : (
                      <div className="space-y-4">
                        {getModelModelsList().map((m) => (
                          <div key={m.name} className="flex flex-col gap-1.5">
                            <div className="flex items-center justify-between text-sm">
                              <span className="font-semibold text-gray-700 dark:text-gray-300">{m.name}</span>
                              <span className="font-mono text-xs text-gray-500">${m.cost.toFixed(5)}</span>
                            </div>
                            <div className="w-full h-2 bg-gray-100 dark:bg-slate-800 rounded-full overflow-hidden">
                              <div 
                                className="h-full bg-indigo-500 rounded-full" 
                                style={{ width: `${Math.min(100, Math.max(2, (m.cost / (summary?.total_cost || 1)) * 100))}%` }}
                              ></div>
                            </div>
                            <div className="text-[10px] text-gray-400 font-medium text-right uppercase tracking-wider">
                              {m.tasks} tasks &middot; {m.tokens || 0} tokens
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                {/* Recent Tasks */}
                <div className="lg:col-span-2 bg-white dark:bg-slate-900 rounded-xl border border-gray-200 dark:border-slate-800 shadow-sm overflow-hidden flex flex-col">
                  <div className="p-4 border-b border-gray-100 dark:border-slate-800 bg-gray-50/50 dark:bg-slate-900/50 flex items-center justify-between">
                    <h3 className="font-bold text-gray-800 dark:text-gray-200 flex items-center gap-2">
                      <Activity size={16} className="text-blue-500" /> Recent Operations
                    </h3>
                    <span className="text-xs font-semibold text-gray-400 bg-gray-100 dark:bg-slate-800 px-2 py-1 rounded-md">Last 50 tasks</span>
                  </div>
                  <div className="flex-1 overflow-y-auto">
                    {tasks.length === 0 ? (
                      <div className="text-center py-12 text-sm text-gray-500">No tasks recorded in this session.</div>
                    ) : (
                      <table className="w-full text-left border-collapse">
                        <thead className="sticky top-0 bg-white/95 dark:bg-slate-900/95 backdrop-blur-sm z-10">
                          <tr className="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider border-b border-gray-100 dark:border-slate-800">
                            <th className="py-3 px-4 font-semibold">Time</th>
                            <th className="py-3 px-4 font-semibold">Task ID</th>
                            <th className="py-3 px-4 font-semibold">Model</th>
                            <th className="py-3 px-4 font-semibold text-right">Cost</th>
                            <th className="py-3 px-4 font-semibold text-right">Latency</th>
                          </tr>
                        </thead>
                        <tbody className="text-sm font-medium">
                          {tasks.map((task) => (
                            <tr key={task.task_id} className="border-b border-gray-50 dark:border-slate-800/50 hover:bg-gray-50/50 dark:hover:bg-slate-800/50 transition-colors">
                              <td className="py-2.5 px-4 text-gray-500 dark:text-gray-400 whitespace-nowrap text-xs">
                                {formatDate(task.start_time)}
                              </td>
                              <td className="py-2.5 px-4 text-gray-900 dark:text-gray-200 font-mono text-xs">
                                {task.task_id.split('-')[0]}...
                              </td>
                              <td className="py-2.5 px-4">
                                <span className="px-2 py-0.5 bg-gray-100 dark:bg-slate-800 text-gray-600 dark:text-gray-300 rounded text-xs">
                                  {task.model}
                                </span>
                              </td>
                              <td className="py-2.5 px-4 text-right font-mono text-xs text-gray-600 dark:text-gray-300">
                                ${task.total_cost.toFixed(5)}
                              </td>
                              <td className="py-2.5 px-4 text-right text-gray-500 dark:text-gray-400 text-xs">
                                {(task.avg_latency_ms / 1000).toFixed(2)}s
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>
                </div>

              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
