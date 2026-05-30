import { useAppStore } from '../../store/useAppStore';
import { Settings, Box, Key, Palette, Wrench, Database, Shield, Zap, Code, Link, CloudOff, Info, RefreshCw, Upload, Download, Trash2, Search } from 'lucide-react';
import clsx from 'clsx';
import { useState } from 'react';
import { SettingsSection } from './ui/SettingsSection';
import { ToggleRow } from './ui/ToggleRow';
import { InputRow } from './ui/InputRow';
import { SelectRow } from './ui/SelectRow';
import { ActionRow } from './ui/ActionRow';
import { SettingsCard } from './ui/SettingsCard';
import { SettingsNavigation } from './ui/SettingsNavigation';
import { ComingSoonBadge } from '../ui/ComingSoonBadge';

export default function SettingsModal() {
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

  return (
    <div className="absolute inset-0 bg-[#f8fafc] z-40 flex flex-col animate-in fade-in duration-200 text-[#111827]">
      {/* Header */}
      <div className="flex items-center justify-between px-8 py-5 border-b border-gray-200 bg-white">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Settings</h2>
          <p className="text-sm text-gray-500 font-medium mt-1">Manage NEXUS-R configuration and preferences</p>
        </div>
        <div className="relative">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input 
            type="text" 
            placeholder="Search settings..." 
            className="pl-9 pr-12 py-2.5 bg-gray-50 border border-gray-200 rounded-lg text-sm w-64 outline-none focus:border-indigo-300 focus:ring-2 focus:ring-indigo-100 transition-all"
          />
          <div className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] font-semibold text-gray-400 bg-white border border-gray-200 px-1.5 py-0.5 rounded shadow-sm">
            Ctrl /
          </div>
        </div>
      </div>

      {/* Body */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <div className="w-[280px] border-r border-gray-200 bg-white py-4 px-3 flex flex-col gap-1 overflow-y-auto">
          <SettingsNavigation 
            tabs={tabs} 
            activeTab={activeTab} 
            onTabChange={setActiveTab} 
            footerAction={
              <button className="flex items-center gap-2 text-sm font-semibold text-gray-500 hover:text-gray-800 transition-colors w-full justify-center">
                <RefreshCw size={14} />
                Restore Defaults
              </button>
            }
          />
        </div>

        {/* Content */}
        <div className="flex-1 p-8 overflow-y-auto bg-[#f8fafc] flex gap-8">
          
          {/* Main Settings Form */}
          <div className="flex-1 max-w-3xl">
            {activeTab === 'general' && (
              <div className="space-y-8 animate-in fade-in slide-in-from-bottom-2">
                <SettingsSection title="General" description="Basic application settings and preferences.">
                  <InputRow label="App Name" description="Customize your application name" defaultValue="NEXUS-R" />
                  <SelectRow label="Default Language" description="Choose your preferred language" options={[{ label: 'English', value: 'en' }]} />
                  <ToggleRow label="Auto Save Conversations" description="Automatically save your conversations" checked={true} onChange={() => {}} />
                  <ToggleRow label="Auto Generate Chat Titles" description="Generate titles for new conversations automatically" checked={true} onChange={() => {}} />
                  <ToggleRow label="Auto Update Models List" description="Automatically check for new models and updates" checked={true} onChange={() => {}} />
                  
                  {/* Coming Soon Example */}
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
              <div className="flex flex-col items-center justify-center h-full text-center text-gray-500">
                <Settings size={48} className="mb-4 text-gray-300" />
                <h3 className="text-xl font-bold text-gray-800">Section Under Construction</h3>
                <p className="mt-2 text-sm text-gray-500">This settings area is not yet implemented.</p>
              </div>
            )}
          </div>

          {/* Right Sidebar Widget Column */}
          <div className="w-[320px] shrink-0 space-y-6">
            <SettingsCard title="Model Status" subtitle="Providers and connection status">
              <StatusRow name="Ollama" status="Connected" />
              <StatusRow name="OpenAI" status="Connected" />
              <StatusRow name="Groq" status="Connected" />
              <StatusRow name="OpenRouter" status="Offline" />
              <StatusRow name="Anthropic" status="Connected" />
            </SettingsCard>

            <SettingsCard title="Session Overview" subtitle="Live session statistics">
              <StatRow label="Total Messages" value="128" />
              <StatRow label="Total Tokens" value="45,231" />
              <StatRow label="Total Cost" value="$0.043" valueColor="text-green-600" />
              <StatRow label="Session Time" value="01:24:18" />
            </SettingsCard>

            <SettingsCard title="Quick Actions">
              <div className="space-y-2">
                <button className="w-full py-2.5 px-4 bg-white border border-gray-200 rounded-xl text-sm font-semibold text-gray-700 hover:bg-gray-50 flex items-center justify-center gap-2 transition-colors">
                  <Upload size={16} /> Export Settings
                </button>
                <button className="w-full py-2.5 px-4 bg-white border border-gray-200 rounded-xl text-sm font-semibold text-gray-700 hover:bg-gray-50 flex items-center justify-center gap-2 transition-colors">
                  <Download size={16} /> Import Settings
                </button>
                <button className="w-full py-2.5 px-4 bg-red-50 border border-red-100 rounded-xl text-sm font-semibold text-red-600 hover:bg-red-100 flex items-center justify-center gap-2 transition-colors mt-2">
                  <Trash2 size={16} /> Reset All Settings
                </button>
              </div>
            </SettingsCard>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="bg-white border-t border-gray-200 px-8 py-4 flex items-center justify-end gap-4">
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
      </div>
    </div>
  );
}

function StatusRow({ name, status }: { name: string, status: 'Connected' | 'Offline' }) {
  const isConnected = status === 'Connected';
  return (
    <div className="flex items-center justify-between text-sm">
      <div className="flex items-center gap-2 font-semibold text-gray-700">
        <span className="font-mono text-gray-400">⚡</span>
        {name}
      </div>
      <div className={clsx("font-semibold", isConnected ? "text-green-600" : "text-orange-500")}>
        {status}
      </div>
    </div>
  );
}

function StatRow({ label, value, valueColor = "text-gray-900" }: { label: string, value: string, valueColor?: string }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-gray-600 font-medium">{label}</span>
      <span className={clsx("font-bold", valueColor)}>{value}</span>
    </div>
  );
}
