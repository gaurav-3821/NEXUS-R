import { useState } from 'react';
import { useAppStore } from '../../store/useAppStore';
import { SettingsLayout } from '../layout/SettingsLayout';
import { PageHeader } from '../ui/PageHeader';
import { SearchBar } from '../ui/SearchBar';
import { SettingsNavigation } from './ui/SettingsNavigation';
import { 
  Settings, Box, Key, Palette, Wrench, Database, Shield, Zap, Code, Link, CloudOff, Info, 
  RefreshCw, Plus, ChevronRight, Eye, CheckCircle2, Trash2, DownloadCloud, Activity, Bot, Globe, Cpu, Network
} from 'lucide-react';
import clsx from 'clsx';

export default function ProvidersPage() {
  const { setSettingsOpen } = useAppStore();
  const [activeTab, setActiveTab] = useState('api-keys');
  const [selectedProvider, setSelectedProvider] = useState('openai');

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

  const providersList = [
    { id: 'openai', name: 'OpenAI', status: 'Active', keyPreview: 'sk-********************', icon: <Bot className="text-emerald-500" /> },
    { id: 'anthropic', name: 'Anthropic', status: 'Active', keyPreview: 'sk-ant-****************', icon: <Cpu className="text-orange-500" /> },
    { id: 'groq', name: 'Groq', status: 'Active', keyPreview: 'gsk_********************', icon: <Zap className="text-red-500" /> },
    { id: 'google', name: 'Google', status: 'Inactive', keyPreview: 'AIza********************', icon: <Globe className="text-blue-500" /> },
    { id: 'openrouter', name: 'OpenRouter', status: 'Inactive', keyPreview: 'sk-or-*****************', icon: <Network className="text-indigo-500" /> },
    { id: 'custom', name: 'Custom Provider', status: 'Inactive', keyPreview: 'Not configured', icon: <Code className="text-gray-500" /> },
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
      footer={footer}
      isOverlay={true}
    >
      <div className="animate-in fade-in slide-in-from-bottom-2 h-full flex flex-col w-[850px] max-w-full">
        {/* Page Title inside content */}
        <div className="mb-6 flex items-center gap-3 text-indigo-600">
          <Link size={24} className="text-indigo-500" />
          <div>
            <h3 className="text-xl font-bold text-gray-900">API Keys</h3>
            <p className="text-sm font-medium text-gray-500 mt-0.5">Manage your cloud provider credentials and model API keys securely.</p>
          </div>
          <div className="ml-auto text-sm font-semibold text-indigo-500 flex items-center gap-1.5 cursor-pointer hover:text-indigo-600 transition-colors">
            <Info size={14} /> How it works?
          </div>
        </div>

        {/* 2-Column Split View */}
        <div className="flex gap-6 items-start">
          
          {/* Left Column: Providers List */}
          <div className="w-[300px] shrink-0 space-y-4">
            {/* Top Sub-tabs */}
            <div className="flex gap-6 border-b border-gray-200">
              <button className="pb-2 text-sm font-bold text-indigo-600 border-b-2 border-indigo-600">Providers</button>
              <button className="pb-2 text-sm font-bold text-gray-500 hover:text-gray-700">Model API</button>
            </div>

            <div className="flex items-center justify-between mt-2">
              <div>
                <h4 className="font-bold text-gray-900">Providers</h4>
                <p className="text-xs font-medium text-gray-500">Add and manage your cloud providers.</p>
              </div>
              <button className="text-xs font-bold text-indigo-600 border border-indigo-100 bg-indigo-50 px-2 py-1.5 rounded-lg flex items-center gap-1 hover:bg-indigo-100 transition-colors">
                <Plus size={12} /> Add Provider
              </button>
            </div>

            <div className="space-y-2 mt-2">
              {providersList.map(provider => (
                <button
                  key={provider.id}
                  onClick={() => setSelectedProvider(provider.id)}
                  className={clsx(
                    "w-full flex items-center justify-between p-3 rounded-xl border transition-all text-left group",
                    selectedProvider === provider.id 
                      ? "border-indigo-200 bg-indigo-50/50 shadow-sm" 
                      : "border-gray-100 bg-white hover:border-gray-200 hover:bg-gray-50"
                  )}
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-white border border-gray-100 shadow-sm flex items-center justify-center shrink-0">
                      {provider.icon}
                    </div>
                    <div>
                      <div className="text-sm font-bold text-gray-900">{provider.name}</div>
                      <div className="text-xs font-medium text-gray-400 font-mono mt-0.5">{provider.keyPreview}</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={clsx(
                      "text-xs font-bold",
                      provider.status === 'Active' ? "text-emerald-500" : "text-orange-500"
                    )}>
                      {provider.status}
                    </span>
                    <ChevronRight size={14} className={clsx(
                      "transition-colors",
                      selectedProvider === provider.id ? "text-indigo-500" : "text-gray-300 group-hover:text-gray-400"
                    )} />
                  </div>
                </button>
              ))}
            </div>

            <div className="bg-indigo-50/50 border border-indigo-100 rounded-xl p-3 flex gap-3 items-start mt-4">
              <Shield size={16} className="text-indigo-500 shrink-0 mt-0.5" />
              <div>
                <p className="text-xs font-medium text-indigo-900 leading-relaxed">
                  Your API keys are encrypted and stored securely using AES-256 encryption.
                </p>
                <button className="text-xs font-bold text-indigo-600 mt-1 hover:underline">Learn more ↗</button>
              </div>
            </div>
          </div>

          {/* Right Column: Provider Details */}
          <div className="flex-1 bg-white border border-gray-200 rounded-2xl shadow-sm overflow-hidden">
            <div className="p-6">
              
              {/* Detail Header */}
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-emerald-50 border border-emerald-100 flex items-center justify-center text-emerald-600">
                    <Bot size={24} />
                  </div>
                  <h3 className="text-xl font-bold text-gray-900">OpenAI</h3>
                  <span className="bg-emerald-50 text-emerald-600 border border-emerald-200 text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider ml-1">Active</span>
                </div>
                <button className="text-sm font-semibold text-red-600 border border-red-100 bg-red-50 hover:bg-red-100 px-3 py-1.5 rounded-lg flex items-center gap-2 transition-colors">
                  <Trash2 size={14} /> Remove
                </button>
              </div>

              {/* Detail Tabs */}
              <div className="flex gap-6 border-b border-gray-100 mb-6">
                <button className="pb-2 text-sm font-bold text-indigo-600 border-b-2 border-indigo-600">Configuration</button>
                <button className="pb-2 text-sm font-bold text-gray-500 hover:text-gray-700">Models</button>
                <button className="pb-2 text-sm font-bold text-gray-500 hover:text-gray-700">Rate Limits</button>
                <button className="pb-2 text-sm font-bold text-gray-500 hover:text-gray-700">Usage</button>
              </div>

              {/* Form Inputs */}
              <div className="space-y-5">
                <div>
                  <label className="block text-sm font-bold text-gray-900 mb-1">API Key</label>
                  <p className="text-xs font-medium text-gray-500 mb-2">Enter your OpenAI API key to connect your account.</p>
                  <div className="flex gap-2">
                    <div className="relative flex-1">
                      <input 
                        type="password" 
                        defaultValue="sk-abc123def456ghi789jkl012mno345pqr" 
                        className="w-full bg-white border border-gray-200 rounded-lg pl-3 pr-10 py-2 text-sm font-medium outline-none focus:border-indigo-400 shadow-sm"
                      />
                      <button className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors">
                        <Eye size={16} />
                      </button>
                    </div>
                    <button className="px-4 py-2 bg-white border border-gray-200 text-gray-700 rounded-lg text-sm font-semibold hover:bg-gray-50 transition-colors shadow-sm whitespace-nowrap">
                      Update Key
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-bold text-gray-900 mb-1">Base URL (Optional)</label>
                  <p className="text-xs font-medium text-gray-500 mb-2">Leave as default unless you're using a custom endpoint.</p>
                  <input 
                    type="text" 
                    defaultValue="https://api.openai.com/v1" 
                    className="w-full bg-white border border-gray-200 rounded-lg px-3 py-2 text-sm font-medium outline-none focus:border-indigo-400 shadow-sm text-gray-600"
                  />
                </div>

                {/* Connection Status Box */}
                <div className="bg-emerald-50/30 border border-emerald-100 rounded-xl p-4 flex items-center justify-between">
                  <div className="flex gap-3">
                    <CheckCircle2 className="text-emerald-500 mt-0.5" size={20} />
                    <div>
                      <h4 className="text-sm font-bold text-gray-900">Connection Status</h4>
                      <p className="text-xs font-medium text-emerald-600 mt-0.5">Connected successfully</p>
                    </div>
                  </div>
                  <div className="flex flex-col items-end gap-2">
                    <button className="text-xs font-bold text-indigo-600 border border-indigo-100 bg-white hover:bg-indigo-50 px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-colors shadow-sm">
                      <RefreshCw size={12} /> Verify Connection
                    </button>
                    <div className="flex items-center gap-1.5 text-[10px] font-bold text-gray-400">
                      <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full"></div>
                      Last verified: 2 minutes ago
                    </div>
                  </div>
                </div>

                {/* Info Rows */}
                <div className="border border-gray-100 rounded-xl overflow-hidden shadow-sm">
                  <button className="w-full flex items-center justify-between p-4 bg-white hover:bg-gray-50 border-b border-gray-100 transition-colors">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-lg bg-indigo-50 flex items-center justify-center text-indigo-500">
                        <DownloadCloud size={16} />
                      </div>
                      <div className="text-left">
                        <div className="text-sm font-bold text-gray-900">Models Available</div>
                        <div className="text-xs font-medium text-gray-500">List of models you can access with this API key.</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-1 text-sm font-bold text-gray-700">
                      12 models <ChevronRight size={16} className="text-gray-400" />
                    </div>
                  </button>
                  <button className="w-full flex items-center justify-between p-4 bg-white hover:bg-gray-50 transition-colors">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-lg bg-indigo-50 flex items-center justify-center text-indigo-500">
                        <Activity size={16} />
                      </div>
                      <div className="text-left">
                        <div className="text-sm font-bold text-gray-900">Rate Limits</div>
                        <div className="text-xs font-medium text-gray-500">View your current usage and rate limit details.</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-1 text-sm font-bold text-gray-700">
                      500 RPM / 90,000 TPM <ChevronRight size={16} className="text-gray-400" />
                    </div>
                  </button>
                </div>

              </div>
            </div>
          </div>
        </div>
      </div>
    </SettingsLayout>
  );
}
