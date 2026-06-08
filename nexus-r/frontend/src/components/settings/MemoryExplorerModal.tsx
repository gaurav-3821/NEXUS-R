import { useState, useMemo } from 'react';
import { useMemoryStore } from '../../store/memoryStore';
import { X, Search, Trash2, Database, AlertCircle, Calendar } from 'lucide-react';
import { APP_NAME } from '../../constants';

interface MemoryExplorerModalProps {
  onClose: () => void;
}

export function MemoryExplorerModal({ onClose }: MemoryExplorerModalProps) {
  const { memories, removeMemory, isLoading, error } = useMemoryStore();
  const [searchQuery, setSearchQuery] = useState('');

  const filteredMemories = useMemo(() => {
    if (!searchQuery.trim()) return memories;
    const lowerQ = searchQuery.toLowerCase();
    return memories.filter(m => 
      m.fact_text.toLowerCase().includes(lowerQ) || 
      m.type.toLowerCase().includes(lowerQ)
    );
  }, [memories, searchQuery]);

  const handleDelete = async (id: string) => {
    if (confirm('Are you sure you want to delete this memory?')) {
      await removeMemory(id);
    }
  };

  const formatDate = (isoStr: string) => {
    if (!isoStr) return 'Unknown date';
    const d = new Date(isoStr);
    return d.toLocaleDateString() + ' ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="absolute inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-2xl shadow-2xl flex flex-col w-full max-w-5xl h-[85vh] overflow-hidden flex-shrink-0 animate-in zoom-in-95 duration-200">
        
        {/* Header */}
        <div className="flex flex-col gap-4 p-6 border-b border-gray-100 dark:border-slate-800 shrink-0">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 flex items-center justify-center">
                <Database size={20} />
              </div>
              <div>
                <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">Memory Explorer</h2>
                <p className="text-sm font-medium text-gray-500 dark:text-gray-400 mt-0.5">
                  View and manage specific details {APP_NAME} has remembered.
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
          
          <div className="relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input 
              type="text" 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search memories..." 
              className="w-full pl-9 pr-4 py-2.5 bg-gray-50 dark:bg-[#0f172a] border border-gray-200 dark:border-slate-800 rounded-xl text-sm outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100 transition-all dark:text-gray-200 dark:focus:ring-blue-900/20"
            />
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6 bg-gray-50 dark:bg-[#0b1120]">
          {error && (
            <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl flex items-start gap-3">
              <AlertCircle size={20} className="text-red-500 mt-0.5 shrink-0" />
              <div>
                <h4 className="text-sm font-bold text-red-800 dark:text-red-400">Error</h4>
                <p className="text-sm text-red-600 dark:text-red-300 mt-1">{error}</p>
              </div>
            </div>
          )}

          {isLoading && memories.length === 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {[1, 2, 3, 4].map(i => (
                <div key={i} className="bg-white dark:bg-slate-900 rounded-xl p-5 border border-gray-200 dark:border-slate-800 shadow-sm animate-pulse h-32">
                  <div className="flex gap-2 mb-3">
                    <div className="h-4 w-16 bg-gray-200 dark:bg-slate-800 rounded-full"></div>
                    <div className="h-4 w-24 bg-gray-200 dark:bg-slate-800 rounded-full"></div>
                  </div>
                  <div className="h-4 w-3/4 bg-gray-200 dark:bg-slate-800 rounded mb-2"></div>
                  <div className="h-4 w-1/2 bg-gray-200 dark:bg-slate-800 rounded"></div>
                </div>
              ))}
            </div>
          ) : filteredMemories.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center">
              <div className="w-16 h-16 rounded-full bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 flex items-center justify-center text-gray-400 mb-4 shadow-sm">
                <Search size={24} />
              </div>
              <h4 className="text-lg font-bold text-gray-900 dark:text-gray-100 mb-2">No memories found</h4>
              <p className="text-sm text-gray-500 dark:text-gray-400 max-w-sm">
                {searchQuery ? "We couldn't find any memories matching your search." : "No memories have been recorded yet."}
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {filteredMemories.map(memory => (
                <div 
                  key={memory.id} 
                  className="bg-white dark:bg-slate-900 rounded-xl p-5 border border-gray-200 dark:border-slate-800 shadow-sm hover:shadow-md transition-shadow flex flex-col relative group"
                >
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <span className="px-2.5 py-1 text-[11px] font-bold uppercase tracking-wider text-blue-700 bg-blue-100 dark:text-blue-300 dark:bg-blue-900/30 rounded-full">
                        {memory.type}
                      </span>
                      <span className="flex items-center gap-1.5 text-xs font-medium text-gray-500 dark:text-gray-400">
                        <Calendar size={12} />
                        {formatDate(memory.created_at)}
                      </span>
                    </div>
                    <button 
                      onClick={() => handleDelete(memory.id)}
                      className="opacity-0 group-hover:opacity-100 p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-all focus:opacity-100"
                      title="Delete memory"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                  <p className="text-sm text-gray-700 dark:text-gray-200 leading-relaxed font-medium line-clamp-4">
                    {memory.fact_text}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
