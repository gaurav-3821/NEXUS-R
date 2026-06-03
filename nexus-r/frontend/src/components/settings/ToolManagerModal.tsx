import { useEffect } from 'react';
import { useToolStore } from '../../store/toolStore';
import { X, Wrench, Globe, Brain, Terminal, FileCode2, Calculator, CheckCircle2, ShieldAlert } from 'lucide-react';
import type { AgentTool } from '../../api/tools';

interface ToolManagerModalProps {
  onClose: () => void;
}

export function ToolManagerModal({ onClose }: ToolManagerModalProps) {
  const { tools, isLoading, error, loadTools } = useToolStore();

  useEffect(() => {
    loadTools();
  }, [loadTools]);

  const getToolIcon = (tool: AgentTool) => {
    switch (tool.id) {
      case 'playwright_search': return <Globe size={24} className="text-blue-500" />;
      case 'timesfm_forecaster': return <Brain size={24} className="text-purple-500" />;
      case 'safe_calculator': return <Calculator size={24} className="text-emerald-500" />;
      case 'memory_parser': return <Brain size={24} className="text-indigo-500" />;
      case 'file_operations': return <FileCode2 size={24} className="text-amber-500" />;
      case 'terminal_sandbox': return <Terminal size={24} className="text-slate-500" />;
      default: return <Wrench size={24} className="text-gray-500" />;
    }
  };

  const categories = Array.from(new Set(tools.map(t => t.category)));

  return (
    <div className="absolute inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-gray-50 dark:bg-[#0b1120] border border-gray-200 dark:border-slate-800 rounded-2xl shadow-2xl flex flex-col w-full max-w-5xl h-[85vh] overflow-hidden flex-shrink-0 animate-in zoom-in-95 duration-200">
        
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-slate-800 shrink-0 bg-white dark:bg-slate-900 z-10 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center text-white shadow-md">
              <Wrench size={24} />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 tracking-tight">Tool Manager</h2>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400 mt-0.5">
                Manage the capabilities available to the agent during execution.
              </p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="w-10 h-10 flex items-center justify-center rounded-full bg-gray-100 hover:bg-gray-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-gray-500 transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-8">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center h-full gap-4 text-gray-400">
              <div className="w-8 h-8 border-4 border-amber-500 border-t-transparent rounded-full animate-spin"></div>
              <p className="font-medium">Loading tools...</p>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center h-full gap-4">
              <div className="w-16 h-16 rounded-full bg-red-100 dark:bg-red-900/20 text-red-500 flex items-center justify-center">
                <ShieldAlert size={32} />
              </div>
              <p className="text-red-500 font-bold">{error}</p>
              <button 
                onClick={() => loadTools()}
                className="px-4 py-2 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 transition-colors text-sm font-bold"
              >
                Retry
              </button>
            </div>
          ) : (
            <div className="space-y-10">
              {categories.map(category => (
                <div key={category} className="space-y-4">
                  <h3 className="text-lg font-bold text-gray-800 dark:text-gray-200 border-b border-gray-200 dark:border-slate-800 pb-2">
                    {category} Tools
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {tools.filter(t => t.category === category).map(tool => (
                      <div 
                        key={tool.id} 
                        className="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-2xl p-5 hover:shadow-lg hover:border-amber-200 dark:hover:border-amber-900/50 transition-all group"
                      >
                        <div className="flex items-start justify-between mb-4">
                          <div className="w-12 h-12 rounded-xl bg-gray-50 dark:bg-slate-800 flex items-center justify-center group-hover:scale-110 transition-transform">
                            {getToolIcon(tool)}
                          </div>
                          {tool.status === 'Active' ? (
                            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-100 dark:border-emerald-800/30">
                              <CheckCircle2 size={12} className="text-emerald-600 dark:text-emerald-400" />
                              <span className="text-[10px] font-bold text-emerald-700 dark:text-emerald-400 uppercase tracking-wider">Active</span>
                            </div>
                          ) : (
                            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-gray-100 dark:bg-slate-800 border border-gray-200 dark:border-slate-700">
                              <span className="w-1.5 h-1.5 rounded-full bg-gray-400"></span>
                              <span className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Inactive</span>
                            </div>
                          )}
                        </div>
                        <h4 className="font-bold text-gray-900 dark:text-gray-100 mb-1.5">{tool.name}</h4>
                        <p className="text-sm text-gray-500 dark:text-gray-400 leading-relaxed">
                          {tool.description}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
