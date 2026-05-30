import { useState } from 'react';
import { useAppStore } from '../../store/useAppStore';
import { SettingsLayout } from '../layout/SettingsLayout';
import { PageHeader } from '../ui/PageHeader';
import { SearchBar } from '../ui/SearchBar';
import { SettingsNavigation } from './ui/SettingsNavigation';
import { SettingsCard } from './ui/SettingsCard';
import { SelectRow } from './ui/SelectRow';
import { ToggleRow } from './ui/ToggleRow';
import { ActionRow } from './ui/ActionRow';
import { ComingSoonBadge } from '../ui/ComingSoonBadge';
import { 
  Settings, Box, Key, Palette, Wrench, Database, Shield, Zap, Code, Link, CloudOff, Info, 
  RefreshCw, Cpu, HardDrive, Monitor, Activity, Trash2, Clock, Play, RotateCcw, Sliders, Leaf
} from 'lucide-react';
import clsx from 'clsx';

export default function PerformancePage() {
  const { setSettingsOpen } = useAppStore();
  const [activeTab, setActiveTab] = useState('performance');
  const [activeProfile, setActiveProfile] = useState('balanced');

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
      {/* System Resources */}
      <SettingsCard title="System Resources">
        <div className="space-y-4 mt-2">
          <ResourceProgress icon={<Cpu size={14} />} label="CPU" value="32%" progress={32} />
          <ResourceProgress icon={<Database size={14} />} label="RAM" value="7.6 GB / 16 GB" progress={47.5} />
          <ResourceProgress icon={<Monitor size={14} />} label="GPU" value="2.1 GB / 6 GB" progress={35} />
          <ResourceProgress icon={<HardDrive size={14} />} label="Disk" value="128 GB / 512 GB" progress={25} />
        </div>
      </SettingsCard>

      {/* Performance Statistics */}
      <SettingsCard 
        title="Performance Statistics" 
        headerAction={
          <select className="text-xs font-semibold text-gray-500 bg-transparent outline-none cursor-pointer hover:text-gray-700">
            <option>This Session</option>
            <option>Today</option>
            <option>All Time</option>
          </select>
        }
      >
        <div className="space-y-3 mb-4">
          <StatRow label="Total Inferences" value="1,248" />
          <StatRow label="Average Response Time" value="2.34s" />
          <StatRow label="Tokens / Second" value="38.6" />
          <StatRow label="Cache Hit Rate" value="87%" />
          <StatRow label="GPU Utilization" value="34%" />
        </div>
        <button className="text-sm font-bold text-indigo-600 flex items-center gap-1 hover:text-indigo-700 transition-colors">
          View Detailed Stats &rarr;
        </button>
      </SettingsCard>

      {/* Quick Actions */}
      <SettingsCard title="Quick Actions">
        <div className="space-y-2">
          <button className="w-full py-2.5 px-4 bg-white border border-gray-200 rounded-xl text-sm font-semibold text-gray-700 hover:bg-gray-50 flex items-center gap-3 transition-colors text-left">
            <Trash2 size={16} className="text-indigo-500" /> Clear Caches
          </button>
          <button className="w-full py-2.5 px-4 bg-white border border-gray-200 rounded-xl text-sm font-semibold text-gray-700 hover:bg-gray-50 flex items-center gap-3 transition-colors text-left">
            <Activity size={16} className="text-indigo-500" /> Optimize Now
          </button>
          <button className="w-full py-2.5 px-4 bg-white border border-gray-200 rounded-xl text-sm font-semibold text-gray-700 hover:bg-gray-50 flex items-center gap-3 transition-colors text-left">
            <Play size={16} className="text-indigo-500" /> Run Benchmark
          </button>
          <button className="w-full py-2.5 px-4 bg-white border border-gray-200 rounded-xl text-sm font-semibold text-gray-700 hover:bg-gray-50 flex items-center gap-3 transition-colors text-left">
            <RotateCcw size={16} className="text-gray-400" /> Reset to Defaults
          </button>
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
              <Activity size={20} />
            </div>
            <div>
              <h3 className="text-xl font-bold text-gray-900">Performance</h3>
              <p className="text-sm font-medium text-gray-500 mt-0.5">Optimize NEXUS-R performance and resource usage.</p>
            </div>
          </div>
          <button className="text-sm font-bold text-indigo-600 hover:text-indigo-800 transition-colors flex items-center gap-1.5">
            Learn more &rarr;
          </button>
        </div>

        {/* Detail Tabs */}
        <div className="flex gap-6 border-b border-gray-100 mb-8">
          <button className="pb-2 text-sm font-bold text-indigo-600 border-b-2 border-indigo-600">Resource Usage</button>
          <button className="pb-2 text-sm font-bold text-gray-500 hover:text-gray-700">Inference</button>
          <button className="pb-2 text-sm font-bold text-gray-500 hover:text-gray-700">Caching</button>
          <button className="pb-2 text-sm font-bold text-gray-500 hover:text-gray-700">Background Tasks</button>
          <button className="pb-2 text-sm font-bold text-gray-500 hover:text-gray-700">Monitoring</button>
        </div>

        {/* Resource Management Section */}
        <div className="mb-10">
          <h4 className="text-[15px] font-bold text-gray-900 mb-1">Resource Management</h4>
          <p className="text-sm font-medium text-gray-500 mb-4">Configure how NEXUS-R uses system resources.</p>
          
          <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
            <SelectRow 
              label="CPU Usage Limit" 
              description="Limit the maximum CPU usage for NEXUS-R processes." 
              options={[{ label: '80%', value: '80' }, { label: '100%', value: '100' }]} 
              className="border-b border-gray-100 last:border-0"
              icon={<Cpu size={16} className="text-gray-500" />}
            />
            
            <SelectRow 
              label="RAM Usage Limit" 
              description="Limit the maximum RAM usage for NEXUS-R." 
              options={[{ label: '12 GB', value: '12' }, { label: '16 GB', value: '16' }]} 
              className="border-b border-gray-100 last:border-0"
              icon={<Database size={16} className="text-gray-500" />}
            />
            
            {/* Unimplemented Features utilizing ComingSoonBadge */}
            <ActionRow 
              label="Hardware Acceleration" 
              description="Enable hardware acceleration for supported models." 
              action={<ComingSoonBadge />} 
              className="border-b border-gray-100 last:border-0 bg-gray-50/50"
              icon={<Monitor size={16} className="text-gray-500" />}
            />
            
            <ActionRow 
              label="GPU Mode" 
              description="Force strict GPU processing for local models." 
              action={<ComingSoonBadge />} 
              className="border-b border-gray-100 last:border-0 bg-gray-50/50"
              icon={<Zap size={16} className="text-gray-500" />}
            />

            <SelectRow 
              label="Disk Cache Limit" 
              description="Maximum disk space used for caching models and data." 
              options={[{ label: '20 GB', value: '20' }, { label: '50 GB', value: '50' }]} 
              className="border-b border-gray-100 last:border-0"
              icon={<HardDrive size={16} className="text-gray-500" />}
            />
          </div>
        </div>

        {/* Performance Profiles Section */}
        <div>
          <h4 className="text-[15px] font-bold text-gray-900 mb-1">Performance Profiles</h4>
          <p className="text-sm font-medium text-gray-500 mb-4">Choose a predefined profile or customize settings for your needs.</p>
          
          <div className="grid grid-cols-4 gap-4 mb-6">
            <ProfileCard 
              title="Balanced"
              description="Best balance between speed and resource usage."
              icon={<Sliders size={16} className="text-indigo-500" />}
              active={activeProfile === 'balanced'}
              recommended={true}
              onClick={() => setActiveProfile('balanced')}
            />
            <ProfileCard 
              title="Speed"
              description="Maximize speed and throughput."
              icon={<Zap size={16} className="text-blue-500" />}
              active={activeProfile === 'speed'}
              onClick={() => setActiveProfile('speed')}
            />
            <ProfileCard 
              title="Efficiency"
              description="Minimize resource usage."
              icon={<Leaf size={16} className="text-emerald-500" />}
              active={activeProfile === 'efficiency'}
              onClick={() => setActiveProfile('efficiency')}
            />
            <ProfileCard 
              title="Custom"
              description="Customize all performance settings."
              icon={<Settings size={16} className="text-gray-500" />}
              active={activeProfile === 'custom'}
              onClick={() => setActiveProfile('custom')}
            />
          </div>

          <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
            <ToggleRow 
              label="Automatic Resource Management" 
              description="Automatically adjust resource usage based on system load." 
              checked={true} 
              onChange={() => {}} 
              icon={<Clock size={16} className="text-indigo-500" />}
            />
          </div>
        </div>

      </div>
    </SettingsLayout>
  );
}

// Subcomponents

function ResourceProgress({ icon, label, value, progress }: { icon: React.ReactNode, label: string, value: string, progress: number }) {
  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2 text-sm font-semibold text-gray-700">
          <div className="w-5 h-5 rounded bg-gray-50 border border-gray-200 flex items-center justify-center text-gray-500">
            {icon}
          </div>
          {label}
        </div>
        <span className="text-xs font-bold text-indigo-600">{value}</span>
      </div>
      <div className="w-full h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div className="h-full bg-indigo-500 rounded-full" style={{ width: `${progress}%` }}></div>
      </div>
    </div>
  );
}

function StatRow({ label, value }: { label: string, value: string }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-gray-600 font-medium">{label}</span>
      <span className="font-bold text-gray-900">{value}</span>
    </div>
  );
}

function ProfileCard({ title, description, icon, active, recommended, onClick }: {
  title: string, description: string, icon: React.ReactNode, active: boolean, recommended?: boolean, onClick: () => void
}) {
  return (
    <div 
      onClick={onClick}
      className={clsx(
        "relative p-4 rounded-xl border transition-all cursor-pointer flex flex-col h-full",
        active ? "bg-indigo-50/30 border-indigo-300 shadow-sm" : "bg-white border-gray-200 hover:border-gray-300 hover:bg-gray-50 shadow-sm"
      )}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {icon}
          <h5 className={clsx("font-bold text-sm", active ? "text-indigo-900" : "text-gray-900")}>{title}</h5>
        </div>
        <div className={clsx(
          "w-4 h-4 rounded-full border-2 flex items-center justify-center",
          active ? "border-indigo-600" : "border-gray-300"
        )}>
          {active && <div className="w-2 h-2 rounded-full bg-indigo-600"></div>}
        </div>
      </div>
      <p className="text-xs font-medium text-gray-500 leading-relaxed mb-3 flex-1">{description}</p>
      
      {recommended && (
        <div className="mt-auto">
          <span className="bg-indigo-100 text-indigo-700 border border-indigo-200 text-[9px] font-bold px-2 py-0.5 rounded-full">Recommended</span>
        </div>
      )}
    </div>
  );
}
