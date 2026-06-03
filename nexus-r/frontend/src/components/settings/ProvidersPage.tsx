import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { SettingsLayout } from '../layout/SettingsLayout';
import { PageHeader } from '../ui/PageHeader';
import { SearchBar } from '../ui/SearchBar';
import { SettingsNavigation } from './ui/SettingsNavigation';
import { 
  Settings, Box, Key, Palette, Wrench, Database, Shield, Zap, Code, Link, CloudOff, Info, 
  RefreshCw, Plus, ChevronRight, Eye, CheckCircle2, Trash2, DownloadCloud, Activity, Bot, Globe, Cpu, Network
} from 'lucide-react';
import clsx from 'clsx';

import { useEffect } from 'react';
import { useProvidersStore } from '../../store/providersStore';

export default function ProvidersPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const activeTab = location.pathname.split('/').pop() || 'api-keys';
  const { providers, isLoading, loadProviders, updateKey, removeProvider } = useProvidersStore();
  const [selectedProvider, setSelectedProvider] = useState<string | null>(null);
  const [apiKeyInput, setApiKeyInput] = useState('');

  useEffect(() => {
    loadProviders();
  }, [loadProviders]);

  useEffect(() => {
    if (providers.length > 0 && !selectedProvider) {
      setSelectedProvider(providers[0].id);
    }
  }, [providers, selectedProvider]);

  const handleUpdateKey = async () => {
    if (selectedProvider && apiKeyInput) {
      const success = await updateKey(selectedProvider, apiKeyInput);
      if (success) {
        setApiKeyInput('');
      }
    }
  };

  const handleRemoveProvider = async () => {
    if (selectedProvider) {
      await removeProvider(selectedProvider);
    }
  };

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

  const getProviderIcon = (id: string) => {
    switch (id) {
      case 'openai': return <Bot className="text-emerald-500" />;
      case 'anthropic': return <Cpu className="text-orange-500" />;
      case 'groq': return <Zap className="text-red-500" />;
      case 'google': return <Globe className="text-blue-500" />;
      case 'openrouter': return <Network className="text-indigo-500" />;
      default: return <Code className="text-gray-500" />;
    }
  };

  const activeProvider = providers.find(p => p.id === selectedProvider);

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
      footer={footer}
      isOverlay={false}
    >
      <div className="animate-in fade-in slide-in-from-bottom-2 h-full flex flex-col w-[850px] max-w-full">
        <div className="mb-6 flex items-center gap-3">
          <Link size={24} className="text-indigo-500 dark:text-indigo-400" />
          <div>
            <h3 className="text-xl font-bold text-gray-900 dark:text-gray-100">API Keys</h3>
            <p className="text-sm font-medium text-gray-500 dark:text-gray-400 mt-0.5">Manage your cloud provider credentials and model API keys securely.</p>
          </div>
          <div className="ml-auto text-sm font-semibold text-indigo-500 dark:text-indigo-400 flex items-center gap-1.5 cursor-pointer hover:text-indigo-600 dark:hover:text-indigo-300 transition-colors">
            <Info size={14} /> How it works?
          </div>
        </div>

        <div className="flex gap-6 items-start">
          
          <div className="w-[300px] shrink-0 space-y-4">
            <div className="flex gap-6 border-b border-gray-200 dark:border-slate-800">
              <button className="pb-2 text-sm font-bold text-indigo-600 dark:text-indigo-400 border-b-2 border-indigo-600 dark:border-indigo-400">Providers</button>
              <button className="pb-2 text-sm font-bold text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300">Model API</button>
            </div>

            <div className="flex items-center justify-between mt-2">
              <div>
                <h4 className="font-bold text-gray-900 dark:text-gray-100">Providers</h4>
                <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Add and manage your cloud providers.</p>
              </div>
              <button className="text-xs font-bold text-indigo-600 dark:text-indigo-400 border border-indigo-100 dark:border-indigo-800 bg-indigo-50 dark:bg-indigo-900/20 px-2 py-1.5 rounded-lg flex items-center gap-1 hover:bg-indigo-100 dark:hover:bg-indigo-900/40 transition-colors">
                <Plus size={12} /> Add Provider
              </button>
            </div>

            <div className="space-y-2 mt-2">
              {isLoading && providers.length === 0 ? (
                <div className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">Loading providers...</div>
              ) : providers.map(provider => (
                <button
                  key={provider.id}
                  onClick={() => setSelectedProvider(provider.id)}
                  className={clsx(
                    "w-full flex items-center justify-between p-3 rounded-xl border transition-all text-left group",
                    selectedProvider === provider.id 
                      ? "border-indigo-200 dark:border-indigo-700 bg-indigo-50/50 dark:bg-indigo-900/10 shadow-sm" 
                      : "border-gray-100 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-gray-200 dark:hover:border-slate-700 hover:bg-gray-50 dark:hover:bg-slate-800"
                  )}
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 shadow-sm flex items-center justify-center shrink-0">
                      {getProviderIcon(provider.id)}
                    </div>
                    <div>
                      <div className="text-sm font-bold text-gray-900 dark:text-gray-100">{provider.name}</div>
                      <div className="text-xs font-medium text-gray-400 dark:text-gray-500 font-mono mt-0.5">
                        {provider.has_key ? `${provider.key_prefix}****************` : 'Not configured'}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={clsx(
                      "text-xs font-bold",
                      provider.status === 'Active' ? "text-emerald-500 dark:text-emerald-400" : "text-orange-500 dark:text-orange-400"
                    )}>
                      {provider.status}
                    </span>
                    <ChevronRight size={14} className={clsx(
                      "transition-colors",
                      selectedProvider === provider.id ? "text-indigo-500 dark:text-indigo-400" : "text-gray-300 dark:text-gray-600 group-hover:text-gray-400 dark:group-hover:text-gray-500"
                    )} />
                  </div>
                </button>
              ))}
            </div>

            <div className="bg-indigo-50/50 dark:bg-indigo-900/10 border border-indigo-100 dark:border-indigo-800 rounded-xl p-3 flex gap-3 items-start mt-4">
              <Shield size={16} className="text-indigo-500 dark:text-indigo-400 shrink-0 mt-0.5" />
              <div>
                <p className="text-xs font-medium text-indigo-900 dark:text-indigo-200 leading-relaxed">
                  Your API keys are encrypted and stored securely using AES-256 encryption.
                </p>
                <button className="text-xs font-bold text-indigo-600 dark:text-indigo-400 mt-1 hover:underline">Learn more ↗</button>
              </div>
            </div>
          </div>

          <div className="flex-1 bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-2xl shadow-sm dark:shadow-black/10 overflow-hidden">
            {activeProvider ? (
              <div className="p-6">
                
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-100 dark:border-indigo-800 flex items-center justify-center text-indigo-600 dark:text-indigo-400">
                      {getProviderIcon(activeProvider.id)}
                    </div>
                    <h3 className="text-xl font-bold text-gray-900 dark:text-gray-100">{activeProvider.name}</h3>
                    {activeProvider.has_key && (
                      <span className="bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800 text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider ml-1">Active</span>
                    )}
                  </div>
                  {activeProvider.has_key && (
                    <button 
                      onClick={handleRemoveProvider}
                      className="text-sm font-semibold text-red-600 dark:text-red-400 border border-red-100 dark:border-red-800 bg-red-50 dark:bg-red-900/20 hover:bg-red-100 dark:hover:bg-red-900/40 px-3 py-1.5 rounded-lg flex items-center gap-2 transition-colors"
                    >
                      <Trash2 size={14} /> Remove
                    </button>
                  )}
                </div>

                <div className="flex gap-6 border-b border-gray-100 dark:border-slate-800 mb-6">
                  <button className="pb-2 text-sm font-bold text-indigo-600 dark:text-indigo-400 border-b-2 border-indigo-600 dark:border-indigo-400">Configuration</button>
                </div>

                <div className="space-y-5">
                  <div>
                    <label className="block text-sm font-bold text-gray-900 dark:text-gray-100 mb-1">API Key</label>
                    <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">Enter your {activeProvider.name} API key to connect your account.</p>
                    <div className="flex gap-2">
                      <div className="relative flex-1">
                        <input 
                          type="password" 
                          value={apiKeyInput}
                          onChange={(e) => setApiKeyInput(e.target.value)}
                          placeholder={activeProvider.has_key ? `${activeProvider.key_prefix}****************` : "Enter new API key..."}
                          className="w-full bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-lg pl-3 pr-10 py-2 text-sm font-medium outline-none focus:border-indigo-400 dark:focus:border-indigo-500 shadow-sm dark:shadow-black/10 placeholder:text-gray-400 dark:placeholder:text-gray-500"
                        />
                        <button className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 transition-colors">
                          <Eye size={16} />
                        </button>
                      </div>
                      <button 
                        onClick={handleUpdateKey}
                        disabled={!apiKeyInput}
                        className="px-4 py-2 bg-indigo-600 dark:bg-indigo-500 text-white rounded-lg text-sm font-semibold hover:bg-indigo-700 dark:hover:bg-indigo-600 transition-colors shadow-sm whitespace-nowrap disabled:opacity-50"
                      >
                        {activeProvider.has_key ? 'Update Key' : 'Save Key'}
                      </button>
                    </div>
                  </div>

                  {activeProvider.has_key ? (
                    <div className="bg-emerald-50/30 dark:bg-emerald-900/10 border border-emerald-100 dark:border-emerald-800 rounded-xl p-4 flex items-center justify-between">
                      <div className="flex gap-3">
                        <CheckCircle2 className="text-emerald-500 dark:text-emerald-400 mt-0.5" size={20} />
                        <div>
                          <h4 className="text-sm font-bold text-gray-900 dark:text-gray-100">Connection Status</h4>
                          <p className="text-xs font-medium text-emerald-600 dark:text-emerald-400 mt-0.5">Key stored securely.</p>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="bg-gray-50 dark:bg-slate-800/50 border border-gray-200 dark:border-slate-700 rounded-xl p-4 flex items-center gap-3">
                      <Info className="text-gray-400 dark:text-gray-500 mt-0.5" size={20} />
                      <div>
                        <h4 className="text-sm font-bold text-gray-900 dark:text-gray-100">Not Configured</h4>
                        <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mt-0.5">Please provide an API key to enable {activeProvider.name} models.</p>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="p-12 text-center text-gray-500 dark:text-gray-400">
                <p>Select a provider to view its configuration.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </SettingsLayout>
  );
}
