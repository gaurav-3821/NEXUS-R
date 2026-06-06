import { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { getMemories, clearAllMemories } from '../../api/memory';
import type { Memory, MemoryStats } from '../../api/memory';
import { SettingsLayout } from '../layout/SettingsLayout';
import { PageHeader } from '../ui/PageHeader';
import { SearchBar } from '../ui/SearchBar';
import { SettingsNavigation } from './ui/SettingsNavigation';
import { SettingsCard } from './ui/SettingsCard';
import { ToggleRow } from './ui/ToggleRow';
import { ActionRow } from './ui/ActionRow';
import { ComingSoonBadge } from '../ui/ComingSoonBadge';
import { 
  Settings, Box, Key, Palette, Wrench, Database, Shield, Zap, Code, Link, CloudOff, Info, 
  RefreshCw, Trash2, DatabaseBackup, Activity, Search, Server, Clock, MessageSquare, CheckCircle2, ChevronRight
} from 'lucide-react';

export default function MemoryPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const activeTab = location.pathname.split('/').pop() || 'memory';
  const [stats, setStats] = useState<MemoryStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchMemory = async () => {
    setIsLoading(true);
    try {
      const res = await getMemories();
      setStats(res.stats);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchMemory();
  }, []);

  const handleClear = async () => {
    try {
      await clearAllMemories();
      await fetchMemory();
    } catch (e) {
      console.error(e);
    }
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
      <SettingsCard title="Memory Summary">
        <div className="flex gap-4 items-center mb-6">
          <div className="relative w-16 h-16">
            <svg viewBox="0 0 36 36" className="w-full h-full rotate-[-90deg]">
              <circle cx="18" cy="18" r="16" fill="none" className="stroke-gray-100 dark:stroke-slate-700" strokeWidth="4"></circle>
              <circle cx="18" cy="18" r="16" fill="none" className="stroke-blue-600 dark:stroke-blue-400" strokeWidth="4" strokeDasharray="42 100" strokeDashoffset="0"></circle>
              <circle cx="18" cy="18" r="16" fill="none" className="stroke-emerald-500 dark:stroke-emerald-400" strokeWidth="4" strokeDasharray="25 100" strokeDashoffset="-42"></circle>
              <circle cx="18" cy="18" r="16" fill="none" className="stroke-orange-500 dark:stroke-orange-400" strokeWidth="4" strokeDasharray="18 100" strokeDashoffset="-67"></circle>
              <circle cx="18" cy="18" r="16" fill="none" className="stroke-gray-300 dark:stroke-gray-600" strokeWidth="4" strokeDasharray="15 100" strokeDashoffset="-85"></circle>
            </svg>
          </div>
          <div className="flex-1 space-y-2">
            <div className="flex items-center justify-between text-xs font-semibold">
              <div className="flex items-center gap-1.5 text-gray-600 dark:text-gray-400"><div className="w-1.5 h-1.5 rounded-full bg-blue-600 dark:bg-blue-400"></div> User Preferences</div>
              <span className="text-gray-900 dark:text-gray-100">42%</span>
            </div>
            <div className="flex items-center justify-between text-xs font-semibold">
              <div className="flex items-center gap-1.5 text-gray-600 dark:text-gray-400"><div className="w-1.5 h-1.5 rounded-full bg-emerald-500 dark:bg-emerald-400"></div> Project Context</div>
              <span className="text-gray-900 dark:text-gray-100">25%</span>
            </div>
            <div className="flex items-center justify-between text-xs font-semibold">
              <div className="flex items-center gap-1.5 text-gray-600 dark:text-gray-400"><div className="w-1.5 h-1.5 rounded-full bg-orange-500 dark:bg-orange-400"></div> Facts & Notes</div>
              <span className="text-gray-900 dark:text-gray-100">18%</span>
            </div>
            <div className="flex items-center justify-between text-xs font-semibold">
              <div className="flex items-center gap-1.5 text-gray-600 dark:text-gray-400"><div className="w-1.5 h-1.5 rounded-full bg-gray-300 dark:bg-gray-600"></div> Others</div>
              <span className="text-gray-900 dark:text-gray-100">15%</span>
            </div>
          </div>
        </div>
      </SettingsCard>

      <SettingsCard title="Memory Categories">
        <div className="space-y-3 mb-4">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600 dark:text-gray-400 font-medium">Total Memories</span>
            <span className="font-semibold text-gray-900 dark:text-gray-100">{stats?.total_memories || 0}</span>
          </div>
        </div>
      </SettingsCard>

      <SettingsCard title="Quick Actions">
        <div className="space-y-2">
          <button onClick={handleClear} className="w-full py-2.5 px-4 bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl text-sm font-semibold text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 flex items-center gap-3 transition-colors text-left">
            <Trash2 size={16} /> Clear All Memories
          </button>
          <button className="w-full py-2.5 px-4 bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl text-sm font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-slate-800 flex items-center gap-3 transition-colors text-left">
            <RefreshCw size={16} className="text-accent-500" /> Rebuild Memory Index
          </button>
          <button className="w-full py-2.5 px-4 bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl text-sm font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-slate-800 flex items-center gap-3 transition-colors text-left">
            <Activity size={16} className="text-emerald-500 dark:text-emerald-400" /> Optimize Memory
          </button>
          <button className="w-full py-2.5 px-4 bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl text-sm font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-slate-800 flex items-center gap-3 transition-colors text-left">
            <Search size={16} className="text-blue-500 dark:text-blue-400" /> View Memory Explorer
          </button>
        </div>
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
              <h4 className="text-xl font-bold text-gray-900 dark:text-gray-100 mb-1">{isLoading ? '...' : (stats?.total_memories || 0)}</h4>
            </div>
            
            <div className="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl p-4 shadow-sm dark:shadow-black/10">
              <div className="w-6 h-6 rounded-md bg-indigo-50 dark:bg-indigo-900/20 text-indigo-500 dark:text-indigo-400 flex items-center justify-center mb-3">
                <Server size={14} />
              </div>
              <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1">Memory Size</p>
              <h4 className="text-xl font-bold text-gray-900 dark:text-gray-100 mb-1">{isLoading ? '...' : `${((stats?.total_size_bytes || 0) / 1024 / 1024).toFixed(2)} MB`}</h4>
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
                <ComingSoonBadge /> <ChevronRight size={14} className="text-gray-400 dark:text-gray-500" />
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
            
            <ActionRow 
              label="Smart Memory" 
              description="Use AI to determine what to remember and what to forget." 
              action={<ComingSoonBadge />} 
              className="border-b border-gray-100 dark:border-slate-800 last:border-0 bg-gray-50/50 dark:bg-slate-800/50"
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
                  <ComingSoonBadge />
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
                <span className="text-[13px] font-bold text-gray-900 dark:text-gray-100">{((stats?.total_size_bytes || 0) / 1024 / 1024).toFixed(2)} MB <span className="text-gray-400 dark:text-gray-500 font-medium">/ 1.5 GB</span></span>
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
