import { useState } from 'react';
import { useAppStore } from '../../store/useAppStore';
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
  const { setSettingsOpen } = useAppStore();
  const [activeTab, setActiveTab] = useState('memory');

  const tabs = [
    { id: 'general', label: 'General', icon: <Settings size={18} /> },
    { id: 'models', label: 'Models', icon: <Box size={18} /> },
    { id: 'default-model', label: 'Default Model', icon: <Box size={18} />, badge: 'NEW' },
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
      onTabChange={setActiveTab} 
      footerAction={
        <button className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-white border border-gray-200 rounded-xl text-sm font-semibold text-gray-700 hover:bg-gray-50 transition-colors">
          <RefreshCw size={14} />
          Restore Defaults
        </button>
      }
    />
  );

  const rightPanel = (
    <div className="space-y-6">
      {/* Memory Summary */}
      <SettingsCard title="Memory Summary">
        <div className="flex gap-4 items-center mb-6">
          <div className="relative w-16 h-16">
            <svg viewBox="0 0 36 36" className="w-full h-full rotate-[-90deg]">
              <circle cx="18" cy="18" r="16" fill="none" className="stroke-gray-100" strokeWidth="4"></circle>
              {/* User Preferences: 42% (blue) */}
              <circle cx="18" cy="18" r="16" fill="none" className="stroke-blue-600" strokeWidth="4" strokeDasharray="42 100" strokeDashoffset="0"></circle>
              {/* Project Context: 25% (green) */}
              <circle cx="18" cy="18" r="16" fill="none" className="stroke-emerald-500" strokeWidth="4" strokeDasharray="25 100" strokeDashoffset="-42"></circle>
              {/* Facts & Notes: 18% (orange) */}
              <circle cx="18" cy="18" r="16" fill="none" className="stroke-orange-500" strokeWidth="4" strokeDasharray="18 100" strokeDashoffset="-67"></circle>
              {/* Others: 15% (gray) */}
              <circle cx="18" cy="18" r="16" fill="none" className="stroke-gray-300" strokeWidth="4" strokeDasharray="15 100" strokeDashoffset="-85"></circle>
            </svg>
          </div>
          <div className="flex-1 space-y-2">
            <div className="flex items-center justify-between text-xs font-semibold">
              <div className="flex items-center gap-1.5 text-gray-600"><div className="w-1.5 h-1.5 rounded-full bg-blue-600"></div> User Preferences</div>
              <span className="text-gray-900">42%</span>
            </div>
            <div className="flex items-center justify-between text-xs font-semibold">
              <div className="flex items-center gap-1.5 text-gray-600"><div className="w-1.5 h-1.5 rounded-full bg-emerald-500"></div> Project Context</div>
              <span className="text-gray-900">25%</span>
            </div>
            <div className="flex items-center justify-between text-xs font-semibold">
              <div className="flex items-center gap-1.5 text-gray-600"><div className="w-1.5 h-1.5 rounded-full bg-orange-500"></div> Facts & Notes</div>
              <span className="text-gray-900">18%</span>
            </div>
            <div className="flex items-center justify-between text-xs font-semibold">
              <div className="flex items-center gap-1.5 text-gray-600"><div className="w-1.5 h-1.5 rounded-full bg-gray-300"></div> Others</div>
              <span className="text-gray-900">15%</span>
            </div>
          </div>
        </div>
      </SettingsCard>

      {/* Top Memory Categories */}
      <SettingsCard title="Top Memory Categories">
        <div className="space-y-3 mb-4">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600 font-medium">Coding Preferences</span>
            <span className="font-semibold text-gray-900">560 memories</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600 font-medium">Project Information</span>
            <span className="font-semibold text-gray-900">420 memories</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600 font-medium">User Preferences</span>
            <span className="font-semibold text-gray-900">380 memories</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600 font-medium">Key Decisions</span>
            <span className="font-semibold text-gray-900">210 memories</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600 font-medium">Facts & Notes</span>
            <span className="font-semibold text-gray-900">180 memories</span>
          </div>
        </div>
        <button className="text-sm font-bold text-indigo-600 flex items-center gap-1 hover:text-indigo-700 transition-colors">
          View all <ChevronRight size={14} />
        </button>
      </SettingsCard>

      {/* Quick Actions */}
      <SettingsCard title="Quick Actions">
        <div className="space-y-2">
          <button className="w-full py-2.5 px-4 bg-white border border-gray-200 rounded-xl text-sm font-semibold text-red-600 hover:bg-red-50 flex items-center gap-3 transition-colors text-left">
            <Trash2 size={16} /> Clear All Memories
          </button>
          <button className="w-full py-2.5 px-4 bg-white border border-gray-200 rounded-xl text-sm font-semibold text-gray-700 hover:bg-gray-50 flex items-center gap-3 transition-colors text-left">
            <RefreshCw size={16} className="text-indigo-500" /> Rebuild Memory Index
          </button>
          <button className="w-full py-2.5 px-4 bg-white border border-gray-200 rounded-xl text-sm font-semibold text-gray-700 hover:bg-gray-50 flex items-center gap-3 transition-colors text-left">
            <Activity size={16} className="text-emerald-500" /> Optimize Memory
          </button>
          <button className="w-full py-2.5 px-4 bg-white border border-gray-200 rounded-xl text-sm font-semibold text-gray-700 hover:bg-gray-50 flex items-center gap-3 transition-colors text-left">
            <Search size={16} className="text-blue-500" /> View Memory Explorer
          </button>
        </div>
      </SettingsCard>

      {/* Memory Health */}
      <SettingsCard title="Memory Health">
        <div className="flex gap-3">
          <div className="w-10 h-10 rounded-full bg-emerald-50 border border-emerald-100 flex items-center justify-center text-emerald-500 shrink-0">
            <CheckCircle2 size={24} />
          </div>
          <div>
            <h4 className="text-sm font-bold text-gray-900">Good</h4>
            <p className="text-xs font-medium text-gray-500 mt-0.5">Your memory is optimized and working well.</p>
          </div>
        </div>
      </SettingsCard>
    </div>
  );

  const footer = (
    <>
      <button 
        onClick={() => setSettingsOpen(false)}
        className="px-6 py-2.5 rounded-full text-sm font-semibold text-gray-700 hover:bg-gray-100 transition-colors"
      >
        Cancel
      </button>
      <button 
        onClick={() => setSettingsOpen(false)}
        className="px-8 py-2.5 rounded-full text-sm font-semibold text-white bg-[#4f46e5] hover:bg-indigo-600 shadow-md flex items-center gap-2 transition-all"
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
      isOverlay={true}
    >
      <div className="animate-in fade-in slide-in-from-bottom-2 h-full flex flex-col w-full">
        
        {/* Main Content Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
              <Database size={20} />
            </div>
            <div>
              <h3 className="text-xl font-bold text-gray-900">Memory</h3>
              <p className="text-sm font-medium text-gray-500 mt-0.5">Configure how NEXUS-R remembers and uses information across conversations.</p>
            </div>
          </div>
          <button className="text-sm font-bold text-indigo-600 hover:text-indigo-800 transition-colors flex items-center gap-1.5">
            Learn more &rarr;
          </button>
        </div>

        {/* Detail Tabs */}
        <div className="flex gap-6 border-b border-gray-100 mb-8">
          <button className="pb-2 text-sm font-bold text-indigo-600 border-b-2 border-indigo-600">Overview</button>
          <button className="pb-2 text-sm font-bold text-gray-500 hover:text-gray-700">Memory Types</button>
          <button className="pb-2 text-sm font-bold text-gray-500 hover:text-gray-700">Retention & Limits</button>
          <button className="pb-2 text-sm font-bold text-gray-500 hover:text-gray-700">Knowledge Base</button>
          <button className="pb-2 text-sm font-bold text-gray-500 hover:text-gray-700">Import / Export</button>
        </div>

        {/* Memory Overview Section */}
        <div className="mb-10">
          <h4 className="text-[15px] font-bold text-gray-900 mb-1">Memory Overview</h4>
          <p className="text-sm font-medium text-gray-500 mb-4">NEXUS-R uses memory to provide more relevant and personalized responses.</p>
          
          {/* 4 Stat Cards */}
          <div className="grid grid-cols-4 gap-4 mb-4">
            <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm">
              <div className="w-6 h-6 rounded-md bg-indigo-50 text-indigo-500 flex items-center justify-center mb-3">
                <DatabaseBackup size={14} />
              </div>
              <p className="text-xs font-semibold text-gray-500 mb-1">Total Memories</p>
              <h4 className="text-xl font-bold text-gray-900 mb-1">3,248</h4>
              <p className="text-[11px] font-bold text-emerald-500">+128 this week</p>
            </div>
            
            <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm">
              <div className="w-6 h-6 rounded-md bg-indigo-50 text-indigo-500 flex items-center justify-center mb-3">
                <Server size={14} />
              </div>
              <p className="text-xs font-semibold text-gray-500 mb-1">Memory Size</p>
              <h4 className="text-xl font-bold text-gray-900 mb-1">128 MB</h4>
              <p className="text-[11px] font-bold text-gray-500">8% of limit used</p>
            </div>

            <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm">
              <div className="w-6 h-6 rounded-md bg-indigo-50 text-indigo-500 flex items-center justify-center mb-3">
                <MessageSquare size={14} />
              </div>
              <p className="text-xs font-semibold text-gray-500 mb-1">Conversations</p>
              <h4 className="text-xl font-bold text-gray-900 mb-1">512</h4>
              <p className="text-[11px] font-bold text-emerald-500">+23 this week</p>
            </div>

            <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm">
              <div className="w-6 h-6 rounded-md bg-indigo-50 text-indigo-500 flex items-center justify-center mb-3">
                <Clock size={14} />
              </div>
              <p className="text-xs font-semibold text-gray-500 mb-1">Last Updated</p>
              <h4 className="text-xl font-bold text-gray-900 mb-1">2 min ago</h4>
              <p className="text-[11px] font-bold text-gray-500">Manual sync</p>
            </div>
          </div>

          {/* 2 Wide Action Cards */}
          <div className="grid grid-cols-2 gap-4">
            <div className="flex items-center justify-between p-4 bg-white border border-gray-200 rounded-xl shadow-sm hover:border-gray-300 transition-colors cursor-pointer">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0">
                  <Database size={16} />
                </div>
                <div>
                  <h5 className="font-bold text-gray-900 text-sm">Memory Saved</h5>
                  <p className="text-xs font-medium text-gray-500">All important information is captured and stored.</p>
                </div>
              </div>
              <div className="flex items-center gap-1.5 text-xs font-bold text-emerald-600">
                Active <ChevronRight size={14} className="text-gray-400" />
              </div>
            </div>

            <div className="flex items-center justify-between p-4 bg-white border border-gray-200 rounded-xl shadow-sm hover:border-gray-300 transition-colors cursor-pointer">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center shrink-0">
                  <DatabaseBackup size={16} />
                </div>
                <div>
                  <h5 className="font-bold text-gray-900 text-sm">Persistent Memory</h5>
                  <p className="text-xs font-medium text-gray-500">Memory is retained across sessions and restarts.</p>
                </div>
              </div>
              <div className="flex items-center gap-1.5 text-xs font-bold text-emerald-600">
                <ComingSoonBadge /> <ChevronRight size={14} className="text-gray-400" />
              </div>
            </div>
          </div>
        </div>

        {/* Memory Controls Section */}
        <div>
          <h4 className="text-[15px] font-bold text-gray-900 mb-1">Memory Controls</h4>
          <p className="text-sm font-medium text-gray-500 mb-4">Customize how memory works in NEXUS-R.</p>
          
          <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
            <ToggleRow 
              label="Enable Memory" 
              description="Allow NEXUS-R to remember information from conversations." 
              checked={true} 
              onChange={() => {}} 
              className="border-b border-gray-100 last:border-0"
            />
            <ToggleRow 
              label="Auto Save Memories" 
              description="Automatically save useful information from conversations." 
              checked={true} 
              onChange={() => {}} 
              className="border-b border-gray-100 last:border-0"
            />
            
            {/* Smart Memory - unsupported so coming soon */}
            <ActionRow 
              label="Smart Memory" 
              description="Use AI to determine what to remember and what to forget." 
              action={<ComingSoonBadge />} 
              className="border-b border-gray-100 last:border-0 bg-gray-50/50"
            />

            {/* Memory Sync Row */}
            <ActionRow 
              label="Memory Sync" 
              description="Sync memory across devices and instances." 
              action={
                <div className="flex items-center gap-4">
                  <span className="text-xs font-medium text-gray-500">Last synced: 2 min ago</span>
                  <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-200 bg-white hover:bg-gray-50 transition-colors text-sm font-semibold text-gray-700 shadow-sm disabled:opacity-50 disabled:cursor-not-allowed">
                    <RefreshCw size={14} /> Sync Now
                  </button>
                  <ComingSoonBadge />
                </div>
              }
              className="border-b border-gray-100 last:border-0 bg-gray-50/50"
            />

            {/* Current Memory Usage Row */}
            <div className="flex items-center justify-between p-5 border-b border-gray-100 last:border-0">
              <div className="flex-1 max-w-sm mr-8">
                <h5 className="font-bold text-gray-900 text-[15px] mb-1">Current Memory Usage</h5>
                <div className="w-full h-2 bg-gray-100 rounded-full mt-3 overflow-hidden">
                  <div className="h-full bg-indigo-500 rounded-full w-[8%]"></div>
                </div>
                <p className="text-xs font-medium text-gray-500 mt-2">1.37 GB available</p>
              </div>
              <div className="flex flex-col items-end gap-2 shrink-0">
                <span className="text-[13px] font-bold text-gray-900">128 MB <span className="text-gray-400 font-medium">/ 1.5 GB (8%)</span></span>
                <button className="px-4 py-2 border border-indigo-200 text-indigo-700 rounded-lg text-sm font-semibold hover:bg-indigo-50 transition-colors shadow-sm whitespace-nowrap">
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
