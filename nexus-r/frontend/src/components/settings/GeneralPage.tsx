import { useState } from 'react';
import { useAppStore } from '../../store/useAppStore';
import { SettingsLayout } from '../layout/SettingsLayout';
import { PageHeader } from '../ui/PageHeader';
import { SearchBar } from '../ui/SearchBar';
import { SettingsSection } from './ui/SettingsSection';
import { InputRow } from './ui/InputRow';
import { SelectRow } from './ui/SelectRow';
import { ToggleRow } from './ui/ToggleRow';
import { ActionRow } from './ui/ActionRow';
import { SettingsCard } from './ui/SettingsCard';
import { SettingsNavigation } from './ui/SettingsNavigation';
import { ComingSoonBadge } from '../ui/ComingSoonBadge';
import { StatusBadge } from '../ui/StatusBadge';
import { Upload, Download, Trash2, RefreshCw, Settings, Box, Key, Palette, Wrench, Database, Shield, Zap, Code, Link, CloudOff, Info } from 'lucide-react';

export default function GeneralPage() {
  const { setSettingsOpen } = useAppStore();
  const [activeTab, setActiveTab] = useState('general');

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
    <>
      <SettingsCard title="Model Status" subtitle="Providers and connection status">
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-2 font-semibold text-gray-700">
            <span className="font-mono text-gray-400">⚡</span> Ollama
          </div>
          <StatusBadge status="online" />
        </div>
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-2 font-semibold text-gray-700">
            <span className="font-mono text-gray-400">⚡</span> OpenAI
          </div>
          <StatusBadge status="online" />
        </div>
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-2 font-semibold text-gray-700">
            <span className="font-mono text-gray-400">⚡</span> Groq
          </div>
          <StatusBadge status="online" />
        </div>
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-2 font-semibold text-gray-700">
            <span className="font-mono text-gray-400">⚡</span> OpenRouter
          </div>
          <StatusBadge status="offline" />
        </div>
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-2 font-semibold text-gray-700">
            <span className="font-mono text-gray-400">⚡</span> Anthropic
          </div>
          <StatusBadge status="online" />
        </div>
      </SettingsCard>

      <SettingsCard title="Session Overview" subtitle="Live session statistics">
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-600 font-medium">Total Messages</span>
          <span className="font-bold text-gray-900">128</span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-600 font-medium">Total Tokens</span>
          <span className="font-bold text-gray-900">45,231</span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-600 font-medium">Total Cost</span>
          <span className="font-bold text-green-600">$0.043</span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-600 font-medium">Session Time</span>
          <span className="font-bold text-gray-900">01:24:18</span>
        </div>
      </SettingsCard>

      <SettingsCard title="Quick Actions">
        <button className="w-full py-2.5 px-4 bg-white border border-gray-200 rounded-xl text-sm font-semibold text-gray-700 hover:bg-gray-50 flex items-center justify-center gap-2 transition-colors">
          <Upload size={16} /> Export Settings
        </button>
        <button className="w-full py-2.5 px-4 bg-white border border-gray-200 rounded-xl text-sm font-semibold text-gray-700 hover:bg-gray-50 flex items-center justify-center gap-2 transition-colors">
          <Download size={16} /> Import Settings
        </button>
        <button className="w-full py-2.5 px-4 bg-red-50 border border-red-100 rounded-xl text-sm font-semibold text-red-600 hover:bg-red-100 flex items-center justify-center gap-2 transition-colors mt-2">
          <Trash2 size={16} /> Reset All Settings
        </button>
      </SettingsCard>
    </>
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
      {activeTab === 'general' && (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-2">
          <SettingsSection title="General" description="Basic application settings and preferences.">
            <InputRow label="App Name" description="Customize your application name" defaultValue="NEXUS-R" />
            <SelectRow label="Default Language" description="Choose your preferred language" options={[{ label: 'English', value: 'en' }]} />
            <ToggleRow label="Auto Save Conversations" description="Automatically save your conversations" checked={true} onChange={() => {}} />
            <ToggleRow label="Auto Generate Chat Titles" description="Generate titles for new conversations automatically" checked={true} onChange={() => {}} />
            <ToggleRow label="Auto Update Models List" description="Automatically check for new models and updates" checked={true} onChange={() => {}} />
            
            <ActionRow label="Auto Startup" description="Launch the application on system boot" action={<ComingSoonBadge />} />
          </SettingsSection>

          <SettingsSection title="Chat Behavior" description="Customize how the chat interface behaves.">
            <ToggleRow label="Stream Responses" description="Display responses in real-time" checked={true} onChange={() => {}} />
            <ToggleRow label="Markdown Rendering" description="Render markdown in messages" checked={true} onChange={() => {}} />
            <ToggleRow label="Code Syntax Highlighting" description="Highlight code blocks" checked={true} onChange={() => {}} />
            <ToggleRow label="Show Token Usage" description="Display token count for messages" checked={false} onChange={() => {}} />
          </SettingsSection>
        </div>
      )}

      {/* Placeholders for other tabs for navigation feel */}
      {activeTab === 'performance' && (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-2">
          <SettingsSection title="Performance Options" description="Optimize application performance.">
            <ActionRow label="Hardware Acceleration" description="Offload rendering and computations to the GPU" action={<ComingSoonBadge />} />
            <ActionRow label="GPU Mode" description="Force strict GPU processing for local models" action={<ComingSoonBadge />} />
          </SettingsSection>
        </div>
      )}

      {activeTab === 'memory' && (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-2">
          <SettingsSection title="Memory Management" description="Configure how the agent remembers data.">
            <ActionRow label="Persistent Memory" description="Keep long-term context stored securely" action={<ComingSoonBadge />} />
            <ActionRow label="Advanced Caching" description="Cache frequent embeddings for faster recall" action={<ComingSoonBadge />} />
          </SettingsSection>
        </div>
      )}

      {/* Empty state placeholder for unpopulated tabs */}
      {['models', 'default-model', 'api-keys', 'appearance', 'agent-tools', 'privacy', 'advanced', 'integrations', 'backup', 'about'].includes(activeTab) && (
        <div className="flex flex-col items-center justify-center h-full text-center text-gray-500 pt-20">
          <Settings size={48} className="mb-4 text-gray-300" />
          <h3 className="text-xl font-bold text-gray-800">Section Under Construction</h3>
          <p className="mt-2 text-sm text-gray-500">This settings area is not yet implemented.</p>
        </div>
      )}
    </SettingsLayout>
  );
}
