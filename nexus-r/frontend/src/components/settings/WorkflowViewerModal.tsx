import { useEffect, useState } from 'react';
import { useWorkflowStore } from '../../store/workflowStore';
import { X, Network, MessageSquare, Clock, Cpu, RefreshCw } from 'lucide-react';
import clsx from 'clsx';

interface WorkflowViewerModalProps {
  onClose: () => void;
}

export function WorkflowViewerModal({ onClose }: WorkflowViewerModalProps) {
  const { 
    workflows, selectedWorkflowId, selectedWorkflowHistory, 
    isLoadingWorkflows, isLoadingHistory, 
    loadWorkflows, selectWorkflow 
  } = useWorkflowStore();

  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    loadWorkflows();
    return () => {
      selectWorkflow(null);
    };
  }, [loadWorkflows, selectWorkflow]);

  const formatDate = (dateStr: string) => {
    const d = new Date(dateStr);
    return d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  const filteredWorkflows = workflows.filter(w => 
    w.title.toLowerCase().includes(searchQuery.toLowerCase()) || 
    w.conversation_id.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="absolute inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-2xl shadow-2xl flex flex-col w-full max-w-7xl h-[92vh] overflow-hidden flex-shrink-0 animate-in zoom-in-95 duration-200">
        
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-100 dark:border-slate-800 shrink-0 bg-white dark:bg-slate-900 z-10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 flex items-center justify-center">
              <Network size={20} />
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">Workflow Viewer</h2>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400 mt-0.5">
                Inspect historical agent execution traces and conversation threads.
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
        <div className="flex-1 flex overflow-hidden bg-gray-50 dark:bg-[#0b1120]">
          
          {/* Left Sidebar - Workflow List */}
          <div className="w-1/3 min-w-[320px] max-w-[400px] border-r border-gray-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col z-0">
            <div className="p-4 border-b border-gray-100 dark:border-slate-800 shrink-0">
              <div className="relative">
                <input 
                  type="text" 
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search workflows..." 
                  className="w-full pl-4 pr-10 py-2.5 bg-gray-50 dark:bg-[#0f172a] border border-gray-200 dark:border-slate-800 rounded-xl text-sm outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100 transition-all dark:text-gray-200 dark:focus:ring-blue-900/20"
                />
                <button 
                  onClick={() => loadWorkflows()}
                  className="absolute right-2 top-1/2 -translate-y-1/2 w-7 h-7 flex items-center justify-center rounded-lg text-gray-400 hover:text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors"
                  title="Refresh workflows"
                >
                  <RefreshCw size={14} className={clsx(isLoadingWorkflows && "animate-spin")} />
                </button>
              </div>
            </div>
            
            <div className="flex-1 overflow-y-auto p-3 space-y-2">
              {isLoadingWorkflows && workflows.length === 0 ? (
                <div className="flex justify-center p-8">
                  <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                </div>
              ) : filteredWorkflows.length === 0 ? (
                <div className="text-center py-12 px-4 text-sm text-gray-500">
                  No workflows found.
                </div>
              ) : (
                filteredWorkflows.map(workflow => (
                  <button
                    key={workflow.conversation_id}
                    onClick={() => selectWorkflow(workflow.conversation_id)}
                    className={clsx(
                      "w-full text-left p-4 rounded-xl border transition-all duration-200",
                      selectedWorkflowId === workflow.conversation_id
                        ? "bg-blue-50 border-blue-200 dark:bg-blue-900/10 dark:border-blue-800 shadow-sm"
                        : "bg-white border-transparent hover:border-gray-200 hover:bg-gray-50 dark:bg-slate-900 dark:hover:bg-slate-800 dark:hover:border-slate-700"
                    )}
                  >
                    <div className="flex items-start justify-between gap-3 mb-2">
                      <h4 className={clsx(
                        "font-bold text-[14px] line-clamp-2 leading-snug",
                        selectedWorkflowId === workflow.conversation_id ? "text-blue-700 dark:text-blue-400" : "text-gray-800 dark:text-gray-200"
                      )}>
                        {workflow.title || "Untitled Workflow"}
                      </h4>
                    </div>
                    <div className="flex items-center gap-3 text-[11px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      <span className="flex items-center gap-1.5"><Clock size={12} /> {formatDate(workflow.created_at)}</span>
                      <span className="flex items-center gap-1.5"><MessageSquare size={12} /> {workflow.message_count} steps</span>
                    </div>
                  </button>
                ))
              )}
            </div>
          </div>

          {/* Right Content - Detailed History */}
          <div className="flex-1 flex flex-col overflow-hidden relative">
            {!selectedWorkflowId ? (
              <div className="flex-1 flex flex-col items-center justify-center text-center p-8">
                <div className="w-16 h-16 rounded-2xl bg-gray-100 dark:bg-slate-800 flex items-center justify-center text-gray-400 mb-4 shadow-sm border border-gray-200 dark:border-slate-700">
                  <Network size={28} />
                </div>
                <h3 className="text-xl font-bold text-gray-900 dark:text-gray-100 mb-2">Select a Workflow</h3>
                <p className="text-sm text-gray-500 dark:text-gray-400 max-w-sm">
                  Choose a workflow from the sidebar to inspect its execution trace, inputs, models, and cost.
                </p>
              </div>
            ) : isLoadingHistory && selectedWorkflowHistory.length === 0 ? (
              <div className="flex-1 flex items-center justify-center">
                <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
              </div>
            ) : (
              <div className="flex-1 overflow-y-auto p-6 space-y-6 scroll-smooth">
                {selectedWorkflowHistory.map((msg) => (
                  <div 
                    key={msg.message_id} 
                    className={clsx(
                      "flex flex-col max-w-3xl rounded-2xl border shadow-sm",
                      msg.role === 'user' 
                        ? "ml-auto bg-blue-600 text-white border-blue-700" 
                        : "mr-auto bg-white dark:bg-slate-900 border-gray-200 dark:border-slate-800"
                    )}
                  >
                    {/* Message Header */}
                    {msg.role === 'assistant' && (
                      <div className="px-4 py-2.5 border-b border-gray-100 dark:border-slate-800 flex items-center justify-between bg-gray-50/50 dark:bg-[#0b1120] rounded-t-2xl">
                        <div className="flex items-center gap-3">
                          <span className="flex items-center gap-1.5 text-xs font-bold text-gray-600 dark:text-gray-300">
                            <Cpu size={14} className="text-blue-500" /> {msg.model || 'Unknown Model'}
                          </span>
                        </div>
                        <div className="flex items-center gap-3 text-[11px] font-mono font-medium text-gray-500 dark:text-gray-400">
                          {msg.latency_ms ? <span>{(msg.latency_ms / 1000).toFixed(2)}s</span> : null}
                          {msg.cost ? <span>${msg.cost.toFixed(5)}</span> : null}
                        </div>
                      </div>
                    )}
                    
                    {/* Message Content */}
                    <div className="p-4 text-[14px] leading-relaxed whitespace-pre-wrap">
                      {msg.role === 'user' ? (
                        <div className="text-blue-50 font-medium">
                          {msg.content}
                        </div>
                      ) : (
                        <div className="text-gray-800 dark:text-gray-200">
                          {msg.content || (msg.blocked ? <span className="text-red-500 font-bold flex items-center gap-2"><X size={16}/> Blocked by Trust Layer</span> : <span className="italic text-gray-400">Empty response</span>)}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
