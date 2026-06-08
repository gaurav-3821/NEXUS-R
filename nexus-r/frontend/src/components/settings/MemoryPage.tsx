import { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useMemoryStore } from '../../store/memoryStore';
import { SettingsLayout } from '../layout/SettingsLayout';
import { PageHeader } from '../ui/PageHeader';
import { SearchBar } from '../ui/SearchBar';
import { SettingsNavigation } from './ui/SettingsNavigation';
import { SettingsCard } from './ui/SettingsCard';
import { ToggleRow } from './ui/ToggleRow';
import { ActionRow } from './ui/ActionRow';
import { MemoryExplorerModal } from './MemoryExplorerModal';
import { 
  Settings, Box, Key, Palette, Wrench, Database, Shield, Zap, Code, Link, CloudOff, Info, 
  RefreshCw, Trash2, DatabaseBackup, Activity, Search, Server, Clock, MessageSquare, CheckCircle2, ChevronRight, Brain
} from 'lucide-react';

export default function MemoryPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const activeTab = location.pathname.split('/').pop() || 'memory';
  const { stats, detailStats, memories, loadMemories, loadDetailStats, clearAll, rebuild, optimize, setPersistent, setSmart, persistentEnabled, smartEnabled, isLoading, saveMemory } = useMemoryStore();
  const [showExplorer, setShowExplorer] = useState(false);

  useEffect(() => {
    loadMemories();
    loadDetailStats();
  }, [loadMemories, loadDetailStats]);

  const handleClear = async () => {
    const ok = await clearAll();
    showToast(ok ? 'All memories cleared.' : 'Failed to clear memories.', ok ? 'success' : 'error');
  };
  const handleRebuild = async () => {
    const ok = await rebuild();
    showToast(ok ? 'Memory index rebuilt.' : 'Failed to rebuild index.', ok ? 'success' : 'error');
  };
  const handleOptimize = async () => {
    const ok = await optimize();
    showToast(ok ? 'Memory optimized.' : 'Failed to optimize.', ok ? 'success' : 'error');
  };

  const handleSaveMemory = async () => {
    if (!saveInput.trim()) return;
    const ok = await saveMemory(saveInput.trim(), 'golden', 0.9, 0.9);
    showToast(ok ? 'Memory Saved!' : 'Failed to save memory.', ok ? 'success' : 'error');
    if (ok) setSaveInput('');
  };

  const cats = detailStats?.categories || {};
  const semantic = cats.semantic || 0;
  const golden = cats.golden || 0;
  const persistent = cats.persistent || 0;
  const smart = cats.smart || 0;
  const totalMem = detailStats?.total_memories || (semantic + golden + persistent + smart);
  const nonZeroTotal = Math.max(totalMem, 1);
  const semanticPct = Math.round((semantic / nonZeroTotal) * 100);
  const goldenPct = Math.round((golden / nonZeroTotal) * 100);
  const persistentPct = Math.round((persistent / nonZeroTotal) * 100);
  const smartPct = Math.round((smart / nonZeroTotal) * 100);
  const otherPct = Math.max(0, 100 - semanticPct - goldenPct - persistentPct - smartPct);

  const [saveInput, setSaveInput] = useState('');
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  const showToast = (message: string, type: 'success' | 'error' = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 2500);
  };

  const tabs = [
    { id: 'general', label: 'General', icon: <Settings size={18} /> },
    { id: 'models', label: 'Models', icon: <Box size={18} /> },
    { id: 'api-keys', label: 'API Keys', icon: <Key size={18} /> },
    { id: 'appearance', label: 'Appearance', icon: <Palette size={18} /> },
    { id: 'agent-tools', label: 'Agent Tools', icon: <Wrench size={18} /> },
    { id: 'memory', label: 'Memory', icon: <Database size={18} /> },
    { id: 'privacy', label: 'Privacy & Security', icon: <Shield size={18} /> },
    { id: 'performance', label: 'Performance', icon: <Zap size={18} /> },
    { id: 'advanced', label: 'Advanced', icon: <Code size={18} /> },
    { id: 'integrations', label: 'Integrations', icon: <Link size={18} /> },
    { id: 'backup', label: 'Backup & Sync', icon: <CloudOff size={18} /> },
    { id: 'about', label: 'About', icon: <Info size={18} /> },
  ];

  const header = (
    <PageHeader 
      title="Settings" 
      subtitle="Manage NEXUS-R configuration and preferences" 
      action={<SearchBar placeholder="Search settings..." shortcut="Ctrl /" />} 
    />
  );

  const sidebar = (
    <SettingsNavigation 
      tabs={tabs} 
      activeTab={activeTab} 
      onTabChange={(id) => navigate(`/settings/${id}`)} 
      footerAction={
        <button className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl text-sm font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-slate-800 transition-colors">
          <RefreshCw size={14} />
          Restore Defaults
        </button>
      }
    />
  );

  const rightPanel = (
    <div className="space-y-6">
      {toast && (
        <div className={`px-4 py-3 rounded-xl text-sm font-semibold shadow-lg animate-in slide-in-from-top-2 fade-in duration-200 ${
          toast.type === 'success'
            ? 'bg-emerald-50 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800'
            : 'bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-300 border border-red-200 dark:border-red-800'
        }`}>
          {toast.message}
        </div>
      )}
      <SettingsCard title="Memory Summary">
        <div className="flex gap-4 items-center mb-6">
          <div className="relative w-16 h-16">
            <svg viewBox="0 0 36 36" className="w-full h-full rotate-[-90deg]">
              <circle cx="18" cy="18" r="16" fill="none" className="stroke-gray-100 dark:stroke-slate-700" strokeWidth="4"></circle>
              {semanticPct > 0 && (
                <circle cx="18" cy="18" r="16" fill="none" className="stroke-blue-600 dark:stroke-blue-400" strokeWidth="4" strokeDasharray={`${semanticPct} 100`} strokeDashoffset="0"></circle>
              )}
              {goldenPct > 0 && (
                <circle cx="18" cy="18" r="16" fill="none" className="stroke-emerald-500 dark:stroke-emerald-400" strokeWidth="4" strokeDasharray={`${goldenPct} 100`} strokeDashoffset={`-${semanticPct}`}></circle>
              )}
              {persistentPct > 0 && (
                <circle cx="18" cy="18" r="16" fill="none" className="stroke-orange-500 dark:stroke-orange-400" strokeWidth="4" strokeDasharray={`${persistentPct} 100`} strokeDashoffset={`-${semanticPct + goldenPct}`}></circle>
              )}
              {smartPct > 0 && (
                <circle cx="18" cy="18" r="16" fill="none" className="stroke-purple-500 dark:stroke-purple-400" strokeWidth="4" strokeDasharray={`${smartPct} 100`} strokeDashoffset={`-${semanticPct + goldenPct + persistentPct}`}></circle>
              )}
              {otherPct > 0 && (
                <circle cx="18" cy="18" r="16" fill="none" className="stroke-gray-300 dark:stroke-gray-600" strokeWidth="4" strokeDasharray={`${otherPct} 100`} strokeDashoffset={`-${semanticPct + goldenPct + persistentPct + smartPct}`}></circle>
              )}
            </svg>
          </div>
          <div className="flex-1 space-y-2">
            <div className="flex items-center justify-between text-xs font-semibold">
              <div className="flex items-center gap-1.5 text-gray-600 dark:text-gray-400"><div className="w-1.5 h-1.5 rounded-full bg-blue-600 dark:bg-blue-400"></div> Semantic Memory</div>
              <span className="text-gray-900 dark:text-gray-100">{semanticPct}%</span>
            </div>
            <div className="flex items-center justify-between text-xs font-semibold">
              <div className="flex items-center gap-1.5 text-gray-600 dark:text-gray-400"><div className="w-1.5 h-1.5 rounded-full bg-emerald-500 dark:bg-emerald-400"></div> Golden Memory</div>
              <span className="text-gray-900 dark:text-gray-100">{goldenPct}%</span>
            </div>
            <div className="flex items-center justify-between text-xs font-semibold">
              <div className="flex items-center gap-1.5 text-gray-600 dark:text-gray-400"><div className="w-1.5 h-1.5 rounded-full bg-orange-500 dark:bg-orange-400"></div> Persistent Memory</div>
              <span className="text-gray-900 dark:text-gray-100">{persistentPct}%</span>
            </div>
            {smartPct > 0 && (
              <div className="flex items-center justify-between text-xs font-semibold">
                <div className="flex items-center gap-1.5 text-gray-600 dark:text-gray-400"><div className="w-1.5 h-1.5 rounded-full bg-purple-500 dark:bg-purple-400"></div> Smart Memory</div>
                <span className="text-gray-900 dark:text-gray-100">{smartPct}%</span>
              </div>
            )}
            {otherPct > 0 && (
              <div className="flex items-center justify-between text-xs font-semibold">
                <div className="flex items-center gap-1.5 text-gray-600 dark:text-gray-400"><div className="w-1.5 h-1.5 rounded-full bg-gray-300 dark:bg-gray-600"></div> Others</div>
                <span className="text-gray-900 dark:text-gray-100">{otherPct}%</span>
              </div>
            )}
          </div>
        </div>
      </SettingsCard>

      <SettingsCard title="Memory Categories">
        <div className="space-y-3 mb-4">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600 dark:text-gray-400 font-medium">Total Memories</span>
            <span className="font-semibold text-gray-900 dark:text-gray-100">{totalMem}</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600 dark:text-gray-400 font-medium">Semantic</span>
            <span className="font-semibold text-gray-900 dark:text-gray-100">{semantic}</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600 dark:text-gray-400 font-medium">Golden</span>
            <span className="font-semibold text-gray-900 dark:text-gray-100">{golden}</span>
          </div>
        </div>
      </SettingsCard>

      <SettingsCard title="Quick Actions">
        <div className="space-y-2">
          <div className="flex gap-2">
            <input
              type="text"
              value={saveInput}
              onChange={(e) => setSaveInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') handleSaveMemory(); }}
              placeholder="Type a fact to save as golden memory..."
              className="flex-1 px-4 py-2.5 bg-gray-50 dark:bg-[#0f172a] border border-gray-200 dark:border-slate-800 rounded-xl text-sm outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100 dark:text-gray-200 dark:focus:ring-blue-900/20"
            />
            <button
              onClick={handleSaveMemory}
              disabled={!saveInput.trim() || isLoading}
              className="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-300 dark:disabled:bg-slate-700 text-white rounded-xl text-sm font-semibold transition-colors shadow-sm flex items-center gap-2"
            >
              Save Memory
            </button>
          </div>
          <hr className="border-gray-100 dark:border-slate-800" />
          <button onClick={handleClear} className="w-full py-2.5 px-4 bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl text-sm font-semibold text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 flex items-center gap-3 transition-colors text-left">
            <Trash2 size={16} /> Clear All Memories
          </button>
          <button onClick={handleRebuild} className="w-full py-2.5 px-4 bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl text-sm font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-slate-800 flex items-center gap-3 transition-colors text-left">
            <RefreshCw size={16} className="text-accent-500" /> Rebuild Memory Index
          </button>
          <button onClick={handleOptimize} className="w-full py-2.5 px-4 bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl text-sm font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-slate-800 flex items-center gap-3 transition-colors text-left">
            <Activity size={16} className="text-emerald-500 dark:text-emerald-400" /> Optimize Memory
          </button>
          <button onClick={() => setShowExplorer(true)} className="w-full py-2.5 px-4 bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl text-sm font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-slate-800 flex items-center gap-3 transition-colors text-left">
            <Search size={16} className="text-blue-500 dark:text-blue-400" /> View Memory Explorer
          </button>
        </div>
      </SettingsCard>

      <SettingsCard title="Recent Memories">
        {isLoading && memories.length === 0 ? (
          <p className="text-sm text-gray-400">Loading...</p>
        ) : memories.length === 0 ? (
          <p className="text-sm text-gray-500 dark:text-gray-400">No memories recorded yet.</p>
        ) : (
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {[...memories].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()).slice(0, 5).map(m => (
              <div key={m.id} className="flex items-start gap-3 p-3 bg-gray-50 dark:bg-slate-800/50 rounded-xl border border-gray-100 dark:border-slate-800">
                <div>
                  <span className="inline-block px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-blue-700 bg-blue-100 dark:text-blue-300 dark:bg-blue-900/30 rounded-full">
                    {m.type}
                  </span>
                  <p className="text-sm text-gray-700 dark:text-gray-200 mt-1 leading-relaxed">{m.fact_text}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </SettingsCard>

      <SettingsCard title="Memory Health">
        <div className="flex gap-3">
          <div className="w-10 h-10 rounded-full bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-100 dark:border-emerald-800 flex items-center justify-center text-emerald-500 dark:text-emerald-400 shrink-0">
            <CheckCircle2 size={24} />
          </div>
          <div>
            <h4 className="text-sm font-bold text-gray-900 dark:text-gray-100">Good</h4>
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mt-0.5">Your memory is optimized and working well.</p>
          </div>
        </div>
      </SettingsCard>
    </div>
  );

  const footer = (
    <>
      <button 
        onClick={() => navigate('/')}
        className="px-6 py-2.5 rounded-full text-sm font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-800 transition-colors"
      >
        Cancel
      </button>
      <button 
        onClick={() => navigate('/')}
        className="px-8 py-2.5 rounded-full text-sm font-semibold text-white bg-accent-600 hover:bg-accent-700 shadow-md flex items-center gap-2 transition-all"
      >
        <Settings size={16} />
        Save Changes
      </button>
    </>
  );

  return (
    <SettingsLayout 
      header={header}
      sidebar={sidebar}
      rightPanel={rightPanel}
      footer={footer}
      isOverlay={false}
    >
      {showExplorer && <MemoryExplorerModal onClose={() => setShowExplorer(false)} />}
      <div className="animate-in fade-in slide-in-from-bottom-2 h-full flex flex-col w-full">
        
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400 flex items-center justify-center">
              <Database size={20} />
            </div>
            <div>
              <h3 className="text-xl font-bold text-gray-900 dark:text-gray-100">Memory</h3>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400 mt-0.5">Configure how NEXUS-R remembers and uses information across conversations.</p>
            </div>
          </div>
          <button className="text-sm font-bold text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-300 transition-colors flex items-center gap-1.5">
            Learn more &rarr;
          </button>
        </div>

        <div className="flex gap-6 border-b border-gray-100 dark:border-slate-800 mb-8">
          <button className="pb-2 text-sm font-bold text-indigo-600 dark:text-indigo-400 border-b-2 border-indigo-600 dark:border-indigo-400">Overview</button>
          <button className="pb-2 text-sm font-bold text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300">Memory Types</button>
          <button className="pb-2 text-sm font-bold text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300">Retention & Limits</button>
          <button className="pb-2 text-sm font-bold text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300">Knowledge Base</button>
          <button className="pb-2 text-sm font-bold text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300">Import / Export</button>
        </div>

        <div className="mb-10">
          <h4 className="text-[15px] font-bold text-gray-900 dark:text-gray-100 mb-1">Memory Overview</h4>
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-4">NEXUS-R uses memory to provide more relevant and personalized responses.</p>
          
          <div className="grid grid-cols-4 gap-4 mb-4">
            <div className="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl p-4 shadow-sm dark:shadow-black/10">
              <div className="w-6 h-6 rounded-md bg-indigo-50 dark:bg-indigo-900/20 text-indigo-500 dark:text-indigo-400 flex items-center justify-center mb-3">
                <DatabaseBackup size={14} />
              </div>
              <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1">Total Memories</p>
              <h4 className="text-xl font-bold text-gray-900 dark:text-gray-100 mb-1">{isLoading ? '...' : totalMem}</h4>
            </div>
            
            <div className="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl p-4 shadow-sm dark:shadow-black/10">
              <div className="w-6 h-6 rounded-md bg-indigo-50 dark:bg-indigo-900/20 text-indigo-500 dark:text-indigo-400 flex items-center justify-center mb-3">
                <Server size={14} />
              </div>
              <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1">Memory Size</p>
              <h4 className="text-xl font-bold text-gray-900 dark:text-gray-100 mb-1">{isLoading ? '...' : `${((detailStats?.total_size_bytes || 0) / 1024 / 1024).toFixed(2)} MB`}</h4>
            </div>

            <div className="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl p-4 shadow-sm dark:shadow-black/10">
              <div className="w-6 h-6 rounded-md bg-indigo-50 dark:bg-indigo-900/20 text-indigo-500 dark:text-indigo-400 flex items-center justify-center mb-3">
                <Clock size={14} />
              </div>
              <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1">Last Updated</p>
              <h4 className="text-[13px] font-bold text-gray-900 dark:text-gray-100 mb-1">{isLoading ? '...' : (stats?.newest_memory_date ? new Date(stats.newest_memory_date).toLocaleDateString() : 'Never')}</h4>
            </div>
            
            <div className="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl p-4 shadow-sm dark:shadow-black/10">
              <div className="w-6 h-6 rounded-md bg-indigo-50 dark:bg-indigo-900/20 text-indigo-500 dark:text-indigo-400 flex items-center justify-center mb-3">
                <Clock size={14} />
              </div>
              <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1">Oldest Memory</p>
              <h4 className="text-[13px] font-bold text-gray-900 dark:text-gray-100 mb-1">{isLoading ? '...' : (stats?.oldest_memory_date ? new Date(stats.oldest_memory_date).toLocaleDateString() : 'Never')}</h4>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="flex items-center justify-between p-4 bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl shadow-sm dark:shadow-black/10 hover:border-gray-300 dark:hover:border-slate-600 transition-colors cursor-pointer">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400 flex items-center justify-center shrink-0">
                  <Database size={16} />
                </div>
                <div>
                  <h5 className="font-bold text-gray-900 dark:text-gray-100 text-sm">Memory Saved</h5>
                  <p className="text-xs font-medium text-gray-500 dark:text-gray-400">All important information is captured and stored.</p>
                </div>
              </div>
              <div className="flex items-center gap-1.5 text-xs font-bold text-emerald-600 dark:text-emerald-400">
                Active <ChevronRight size={14} className="text-gray-400 dark:text-gray-500" />
              </div>
            </div>

            <div className="flex items-center justify-between p-4 bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl shadow-sm dark:shadow-black/10 hover:border-gray-300 dark:hover:border-slate-600 transition-colors cursor-pointer">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400 flex items-center justify-center shrink-0">
                  <DatabaseBackup size={16} />
                </div>
                <div>
                  <h5 className="font-bold text-gray-900 dark:text-gray-100 text-sm">Persistent Memory</h5>
                  <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Memory is retained across sessions and restarts.</p>
                </div>
              </div>
              <div className="flex items-center gap-1.5 text-xs font-bold text-emerald-600 dark:text-emerald-400">
                <span className="text-emerald-600 dark:text-emerald-400">{persistentEnabled ? 'Active' : 'Disabled'}</span> <ChevronRight size={14} className="text-gray-400 dark:text-gray-500" />
              </div>
            </div>
          </div>
        </div>

        <div>
          <h4 className="text-[15px] font-bold text-gray-900 dark:text-gray-100 mb-1">Memory Controls</h4>
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-4">Customize how memory works in NEXUS-R.</p>
          
          <div className="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl shadow-sm dark:shadow-black/10 overflow-hidden">
            <ToggleRow 
              label="Enable Memory" 
              description="Allow NEXUS-R to remember information from conversations." 
              checked={true} 
              onChange={() => {}} 
              className="border-b border-gray-100 dark:border-slate-800 last:border-0"
            />
            <ToggleRow 
              label="Auto Save Memories" 
              description="Automatically save useful information from conversations." 
              checked={true} 
              onChange={() => {}} 
              className="border-b border-gray-100 dark:border-slate-800 last:border-0"
            />
            
            <ToggleRow 
              label="Persistent Memory" 
              description="Retain golden examples and key information across sessions and restarts." 
              checked={persistentEnabled} 
              onChange={async (val) => { await setPersistent(val); }} 
              className="border-b border-gray-100 dark:border-slate-800 last:border-0"
            />

            <ToggleRow 
              label="Smart Memory" 
              description="Use AI to determine what to remember and what to forget based on relevance." 
              checked={smartEnabled} 
              onChange={async (val) => { await setSmart(val); }} 
              className="border-b border-gray-100 dark:border-slate-800 last:border-0"
            />

            <ActionRow 
              label="Memory Sync" 
              description="Sync memory across devices and instances." 
              action={
                <div className="flex items-center gap-4">
                  <span className="text-xs font-medium text-gray-500 dark:text-gray-400">Last synced: 2 min ago</span>
                  <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-900 hover:bg-gray-50 dark:hover:bg-slate-800 transition-colors text-sm font-semibold text-gray-700 dark:text-gray-300 shadow-sm">
                    <RefreshCw size={14} /> Sync Now
                  </button>
                </div>
              }
              className="border-b border-gray-100 dark:border-slate-800 last:border-0 bg-gray-50/50 dark:bg-slate-800/50"
            />

            <div className="flex items-center justify-between p-5 border-b border-gray-100 dark:border-slate-800 last:border-0">
              <div className="flex-1 max-w-sm mr-8">
                <h5 className="font-bold text-gray-900 dark:text-gray-100 text-[15px] mb-1">Current Memory Usage</h5>
                <div className="w-full h-2 bg-gray-100 dark:bg-slate-800 rounded-full mt-3 overflow-hidden">
                  <div className="h-full bg-indigo-500 dark:bg-indigo-400 rounded-full w-[8%]"></div>
                </div>
                <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mt-2">1.37 GB available</p>
              </div>
              <div className="flex flex-col items-end gap-2 shrink-0">
                <span className="text-[13px] font-bold text-gray-900 dark:text-gray-100">{((detailStats?.total_size_bytes || 0) / 1024 / 1024).toFixed(2)} MB <span className="text-gray-400 dark:text-gray-500 font-medium">/ 1.5 GB</span></span>
                <button className="px-4 py-2 border border-indigo-200 dark:border-indigo-800 text-indigo-700 dark:text-indigo-300 rounded-lg text-sm font-semibold hover:bg-indigo-50 dark:hover:bg-indigo-900/20 transition-colors shadow-sm">
                  Manage Storage
                </button>
              </div>
            </div>
          </div>
        </div>

      </div>
    </SettingsLayout>
  );
}