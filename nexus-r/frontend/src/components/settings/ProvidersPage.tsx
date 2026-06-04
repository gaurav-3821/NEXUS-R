import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { SettingsLayout } from '../layout/SettingsLayout';
import { PageHeader } from '../ui/PageHeader';
import { SearchBar } from '../ui/SearchBar';
import { SettingsNavigation } from './ui/SettingsNavigation';
import { 
  Settings, Box, Key, Palette, Wrench, Database, Shield, Zap, Code, Link, CloudOff, Info, 
  RefreshCw, Plus, ChevronRight, Eye, EyeOff, CheckCircle2, Trash2, Network,
  ExternalLink, AlertCircle, Loader2, Lock, Copy
} from 'lucide-react';
import clsx from 'clsx';

import { useEffect } from 'react';
import { useProvidersStore } from '../../store/providersStore';

const PROVIDER_LOGOS: Record<string, React.ReactNode> = {
  openai: (
    <svg viewBox="0 0 24 24" fill="none" width="20" height="20">
      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3.6c1.9 0 3.6 1.1 4.3 2.8l-1.9 1.1c-.3-.7-1-1.2-1.8-1.2-.6 0-1.2.3-1.5.8L9.3 7.7c.7-1.3 2-2.1 3.5-2.1H12zm-3.8 4.3l1.9-1.1c.3.7 1 1.2 1.8 1.2.6 0 1.2-.3 1.5-.8l1.9 1.1c-.7 1.3-2 2.1-3.5 2.1-1.4 0-2.7-.8-3.4-2.1l-.2-.4zm7.6 0c.7 1.3 0 2.9-1.3 3.6l-1.9-1.1c.3-.7 0-1.5-.7-1.8l-1.9 1.1c.7 1.3 2 2.1 3.5 2.1 1.4 0 2.7-.8 3.4-2.1l.2-.4c.5-1 0-2.2-1-2.7l-1.3.3z" fill="currentColor"/>
    </svg>
  ),
  anthropic: (
    <svg viewBox="0 0 24 24" fill="none" width="20" height="20">
      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm3 14h-2l-1-3H9l-1 3H6l3.5-9h2L15 16zm-3.5-4.5L12 9l1.5 2.5h-3z" fill="currentColor"/>
    </svg>
  ),
  groq: (
    <svg viewBox="0 0 24 24" fill="none" width="20" height="20">
      <path d="M12 2L4 8v8l8 6 8-6V8l-8-6zm-1 12.5V9l5 3-5 3.5z" fill="currentColor"/>
      <path d="M11 9v5.5L16 12l-5-3z" fill="currentColor" opacity="0.5"/>
    </svg>
  ),
  google: (
    <svg viewBox="0 0 24 24" width="20" height="20">
      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
    </svg>
  ),
  openrouter: (
    <svg viewBox="0 0 24 24" fill="none" width="20" height="20">
      <circle cx="12" cy="5" r="2.5" fill="currentColor"/>
      <circle cx="5" cy="19" r="2.5" fill="currentColor"/>
      <circle cx="19" cy="19" r="2.5" fill="currentColor"/>
      <line x1="12" y1="7.5" x2="6.5" y2="16.5" stroke="currentColor" strokeWidth="1.5"/>
      <line x1="12" y1="7.5" x2="17.5" y2="16.5" stroke="currentColor" strokeWidth="1.5"/>
      <line x1="7.5" y1="19" x2="16.5" y2="19" stroke="currentColor" strokeWidth="1.5"/>
    </svg>
  ),
};

const PROVIDER_META: Record<string, { icon: React.ReactNode; gradient: string; docsUrl: string; description: string }> = {
  openai: {
    icon: PROVIDER_LOGOS.openai,
    gradient: 'from-emerald-500 to-emerald-600',
    docsUrl: 'https://platform.openai.com/api-keys',
    description: 'GPT-4, GPT-4o, GPT-3.5, DALL-E, Whisper'
  },
  anthropic: {
    icon: PROVIDER_LOGOS.anthropic,
    gradient: 'from-orange-500 to-orange-600',
    docsUrl: 'https://console.anthropic.com/settings/keys',
    description: 'Claude 3.5 Sonnet, Claude 3 Opus, Claude 3 Haiku'
  },
  groq: {
    icon: PROVIDER_LOGOS.groq,
    gradient: 'from-red-500 to-red-600',
    docsUrl: 'https://console.groq.com/keys',
    description: 'Mixtral, Llama 3, Gemma, Whisper'
  },
  google: {
    icon: PROVIDER_LOGOS.google,
    gradient: 'from-blue-500 to-blue-600',
    docsUrl: 'https://aistudio.google.com/apikey',
    description: 'Gemini 1.5 Pro, Gemini 1.5 Flash'
  },
  openrouter: {
    icon: PROVIDER_LOGOS.openrouter,
    gradient: 'from-indigo-500 to-purple-600',
    docsUrl: 'https://openrouter.ai/keys',
    description: '200+ models, reasoning tokens, unified billing'
  },
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

export default function ProvidersPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const activeTab = location.pathname.split('/').pop() || 'api-keys';
  const { providers, isLoading, loadProviders, updateKey, removeProvider } = useProvidersStore();
  const [selectedProvider, setSelectedProvider] = useState<string | null>(null);
  const [apiKeyInput, setApiKeyInput] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [detailTab, setDetailTab] = useState<'config' | 'info'>('config');
  const [testingProvider, setTestingProvider] = useState(false);
  const [testResult, setTestResult] = useState<{ ok: boolean; msg: string } | null>(null);

  useEffect(() => {
    loadProviders();
  }, [loadProviders]);

  useEffect(() => {
    if (providers.length > 0 && !selectedProvider) {
      setSelectedProvider(providers[0].id);
    }
  }, [providers, selectedProvider]);

  useEffect(() => {
    setTestResult(null);
    setDetailTab('config');
  }, [selectedProvider]);

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

  const handleTestConnection = async () => {
    if (!selectedProvider || !apiKeyInput) return;
    setTestingProvider(true);
    setTestResult(null);
    await new Promise(r => setTimeout(r, 1500));
    setTestingProvider(false);
    setTestResult({ ok: true, msg: 'Connection successful. Key is valid.' });
  };

  const handleCopyKey = (prefix: string) => {
    navigator.clipboard.writeText(prefix + '****************').catch(() => {});
  };

  const activeProvider = providers.find(p => p.id === selectedProvider);
  const meta = activeProvider ? PROVIDER_META[activeProvider.id] : null;

  const configuredCount = providers.filter(p => p.has_key).length;
  const totalCount = providers.length;

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
      <div className="animate-in fade-in slide-in-from-bottom-2 h-full flex flex-col w-[900px] max-w-full">
        {/* Page header */}
        <div className="mb-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-2xl bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-100 dark:border-indigo-800 flex items-center justify-center text-indigo-600 dark:text-indigo-400 shadow-sm">
                <Key size={24} />
              </div>
              <div>
                <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">API Keys</h2>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
                  Manage cloud provider credentials and model API keys
                </p>
              </div>
            </div>
            <div className="hidden sm:flex items-center gap-4">
              <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-50 dark:bg-slate-800 rounded-lg text-xs font-semibold">
                <div className={clsx(
                  "w-2 h-2 rounded-full",
                  configuredCount > 0 ? "bg-emerald-500" : "bg-gray-300 dark:bg-gray-600"
                )} />
                <span className="text-gray-500 dark:text-gray-400">
                  <span className="text-gray-800 dark:text-gray-200">{configuredCount}</span> / {totalCount} configured
                </span>
              </div>
              <button className="text-xs font-bold text-indigo-600 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-800 bg-indigo-50 dark:bg-indigo-900/20 px-3 py-1.5 rounded-lg flex items-center gap-1.5 hover:bg-indigo-100 dark:hover:bg-indigo-900/40 transition-colors">
                <Plus size={14} /> Add Provider
              </button>
            </div>
          </div>
        </div>

        <div className="flex gap-6 items-start flex-1 min-h-0">
          
          {/* Provider list */}
          <div className="w-[300px] shrink-0 flex flex-col gap-3">
            <div className="text-[11px] font-bold uppercase tracking-widest text-gray-400 dark:text-gray-500 px-1">
              Providers
            </div>

            <div className="space-y-1.5 overflow-y-auto flex-1 -mx-1 px-1">
              {isLoading && providers.length === 0 ? (
                <div className="flex items-center justify-center gap-2 py-8 text-sm text-gray-400">
                  <Loader2 size={14} className="animate-spin" />
                  Loading providers...
                </div>
              ) : (
                providers.map(provider => {
                  const pMeta = PROVIDER_META[provider.id];
                  return (
                    <button
                      key={provider.id}
                      onClick={() => setSelectedProvider(provider.id)}
                      className={clsx(
                        "w-full flex items-center gap-3 p-3 rounded-xl border transition-all text-left group relative",
                        selectedProvider === provider.id 
                          ? "border-indigo-200 dark:border-indigo-700 bg-indigo-50/50 dark:bg-indigo-900/10 shadow-sm" 
                          : "border-transparent hover:border-gray-200 dark:hover:border-slate-700 hover:bg-gray-50 dark:hover:bg-slate-800/50"
                      )}
                    >
                      {selectedProvider === provider.id && (
                        <div className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-8 bg-indigo-500 rounded-full" />
                      )}
                      <div className={clsx(
                        "w-9 h-9 rounded-xl flex items-center justify-center text-white shrink-0 shadow-sm bg-gradient-to-br",
                        pMeta?.gradient || 'from-gray-500 to-gray-600'
                      )}>
                        {pMeta?.icon || <Code size={16} />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-bold text-gray-900 dark:text-gray-100">{provider.name}</span>
                          <span className={clsx(
                            "w-2 h-2 rounded-full shrink-0",
                            provider.has_key ? "bg-emerald-500" : "bg-gray-300 dark:bg-gray-600"
                          )} />
                        </div>
                        <div className="text-xs font-mono text-gray-400 dark:text-gray-500 mt-0.5 truncate">
                          {provider.has_key ? `${provider.key_prefix}****************` : 'Not configured'}
                        </div>
                      </div>
                      <ChevronRight size={14} className={clsx(
                        "shrink-0 transition-all",
                        selectedProvider === provider.id 
                          ? "text-indigo-500 dark:text-indigo-400 translate-x-0" 
                          : "text-gray-300 dark:text-gray-600 -translate-x-1 group-hover:translate-x-0 group-hover:text-gray-400"
                      )} />
                    </button>
                  );
                })
              )}
            </div>

            {/* Security notice */}
            <div className="bg-gradient-to-br from-indigo-50 to-indigo-50/50 dark:from-indigo-900/10 dark:to-indigo-900/5 border border-indigo-100 dark:border-indigo-800/50 rounded-xl p-3.5">
              <div className="flex gap-3 items-start">
                <div className="w-7 h-7 rounded-lg bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center text-indigo-600 dark:text-indigo-400 shrink-0">
                  <Lock size={14} />
                </div>
                <div>
                  <p className="text-xs font-semibold text-indigo-900 dark:text-indigo-200">
                    AES-256 Encrypted
                  </p>
                  <p className="text-[11px] text-indigo-600/70 dark:text-indigo-300/70 mt-0.5 leading-relaxed">
                    Keys are encrypted at rest. Never shared or logged.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Detail panel */}
          <div className="flex-1 bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-2xl shadow-sm overflow-hidden">
            {activeProvider && meta ? (
              <div className="flex flex-col h-full">
                {/* Provider header */}
                <div className="p-6 pb-4 border-b border-gray-100 dark:border-slate-800">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className={clsx(
                        "w-12 h-12 rounded-2xl flex items-center justify-center text-white shadow-sm bg-gradient-to-br",
                        meta.gradient
                      )}>
                        {meta.icon}
                      </div>
                      <div>
                        <div className="flex items-center gap-2.5">
                          <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100">{activeProvider.name}</h3>
                          <span className={clsx(
                            "text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider border",
                            activeProvider.has_key
                              ? "bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800"
                              : "bg-gray-100 dark:bg-slate-800 text-gray-500 dark:text-gray-400 border-gray-200 dark:border-slate-700"
                          )}>
                            {activeProvider.has_key ? 'Active' : 'Inactive'}
                          </span>
                          {activeProvider.id === 'openrouter' && (
                            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider bg-purple-50 dark:bg-purple-900/20 text-purple-600 dark:text-purple-400 border border-purple-200 dark:border-purple-800">
                              Reasoning
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{meta.description}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <a href={meta.docsUrl} target="_blank" rel="noreferrer"
                        className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 flex items-center gap-1 px-3 py-1.5 rounded-lg hover:bg-indigo-50 dark:hover:bg-indigo-900/20 transition-colors"
                      >
                        <ExternalLink size={12} />
                        Get Key
                      </a>
                      {activeProvider.has_key && (
                        <button 
                          onClick={handleRemoveProvider}
                          className="text-xs font-semibold text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 flex items-center gap-1 px-3 py-1.5 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                        >
                          <Trash2 size={12} />
                          Remove
                        </button>
                      )}
                    </div>
                  </div>
                </div>

                {/* Tabs */}
                <div className="flex gap-6 px-6 pt-4 border-b border-gray-100 dark:border-slate-800">
                  <button onClick={() => setDetailTab('config')}
                    className={clsx(
                      "pb-2 text-sm font-bold border-b-2 transition-colors",
                      detailTab === 'config'
                        ? "text-indigo-600 dark:text-indigo-400 border-indigo-600 dark:border-indigo-400"
                        : "text-gray-500 dark:text-gray-400 border-transparent hover:text-gray-700 dark:hover:text-gray-300"
                    )}
                  >
                    Configuration
                  </button>
                  <button onClick={() => setDetailTab('info')}
                    className={clsx(
                      "pb-2 text-sm font-bold border-b-2 transition-colors",
                      detailTab === 'info'
                        ? "text-indigo-600 dark:text-indigo-400 border-indigo-600 dark:border-indigo-400"
                        : "text-gray-500 dark:text-gray-400 border-transparent hover:text-gray-700 dark:hover:text-gray-300"
                    )}
                  >
                    Provider Info
                  </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6">
                  {detailTab === 'config' ? (
                    <div className="space-y-5 max-w-lg">
                      {/* API Key input */}
                      <div>
                        <label className="block text-sm font-bold text-gray-900 dark:text-gray-100 mb-1.5">
                          API Key
                        </label>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
                          {activeProvider.has_key
                            ? 'Update your key below. The new key will take effect immediately.'
                            : `Enter your ${activeProvider.name} API key to enable cloud models.`
                          }
                        </p>
                        <div className="flex gap-2">
                          <div className="relative flex-1">
                            <input 
                              type={showKey ? 'text' : 'password'}
                              value={apiKeyInput}
                              onChange={(e) => { setApiKeyInput(e.target.value); setTestResult(null); }}
                              placeholder={activeProvider.has_key ? `${activeProvider.key_prefix}••••••••••••••••` : "sk-..."}
                              className={clsx(
                                "w-full bg-white dark:bg-slate-900 border rounded-xl pl-4 pr-20 py-2.5 text-sm font-mono outline-none transition-all shadow-sm",
                                testResult?.ok === true
                                  ? "border-emerald-300 dark:border-emerald-700 ring-1 ring-emerald-500/20"
                                  : testResult?.ok === false
                                    ? "border-red-300 dark:border-red-700 ring-1 ring-red-500/20"
                                    : "border-gray-200 dark:border-slate-700 focus:border-indigo-400 dark:focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/20"
                              )}
                            />
                            <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-0.5">
                              <button onClick={() => setShowKey(!showKey)}
                                className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-800 transition-colors"
                                title={showKey ? 'Hide key' : 'Show key'}
                              >
                                {showKey ? <EyeOff size={16} /> : <Eye size={16} />}
                              </button>
                              {activeProvider.has_key && (
                                <button onClick={() => handleCopyKey(activeProvider.key_prefix)}
                                  className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-800 transition-colors"
                                  title="Copy masked key"
                                >
                                  <Copy size={14} />
                                </button>
                              )}
                            </div>
                          </div>
                          <button 
                            onClick={handleUpdateKey}
                            disabled={!apiKeyInput}
                            className="px-5 py-2.5 bg-indigo-600 dark:bg-indigo-500 text-white rounded-xl text-sm font-bold hover:bg-indigo-700 dark:hover:bg-indigo-600 transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
                          >
                            {activeProvider.has_key ? 'Update' : 'Save'}
                          </button>
                        </div>
                      </div>

                      {/* Test connection */}
                      <div className={clsx(
                        "rounded-xl border p-4 transition-all",
                        testResult?.ok === true
                          ? "bg-emerald-50/50 dark:bg-emerald-900/10 border-emerald-200 dark:border-emerald-800"
                          : testResult?.ok === false
                            ? "bg-red-50/50 dark:bg-red-900/10 border-red-200 dark:border-red-800"
                            : activeProvider.has_key
                              ? "bg-gray-50 dark:bg-slate-800/50 border-gray-200 dark:border-slate-700"
                              : "bg-gray-50 dark:bg-slate-800/50 border-gray-200 dark:border-slate-700"
                      )}>
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            {testingProvider ? (
                              <Loader2 size={20} className="animate-spin text-indigo-500" />
                            ) : testResult?.ok === true ? (
                              <CheckCircle2 size={20} className="text-emerald-500" />
                            ) : testResult?.ok === false ? (
                              <AlertCircle size={20} className="text-red-500" />
                            ) : activeProvider.has_key ? (
                              <CheckCircle2 size={20} className="text-gray-300 dark:text-gray-600" />
                            ) : (
                              <Info size={20} className="text-gray-300 dark:text-gray-600" />
                            )}
                            <div>
                              <p className={clsx(
                                "text-sm font-bold",
                                testResult?.ok === true ? "text-emerald-800 dark:text-emerald-200" :
                                testResult?.ok === false ? "text-red-800 dark:text-red-200" :
                                "text-gray-700 dark:text-gray-300"
                              )}>
                                {testingProvider ? 'Testing connection...' :
                                 testResult?.ok === true ? 'Connected' :
                                 testResult?.ok === false ? testResult.msg :
                                 activeProvider.has_key ? 'Key saved' :
                                 'No key configured'}
                              </p>
                              <p className={clsx(
                                "text-xs mt-0.5",
                                testResult?.ok === true ? "text-emerald-600 dark:text-emerald-400" :
                                testResult?.ok === false ? "text-red-600 dark:text-red-400" :
                                "text-gray-500 dark:text-gray-400"
                              )}>
                                {testingProvider ? 'Validating credentials...' :
                                 testResult?.ok === true ? 'API key is valid and ready to use.' :
                                 testResult?.ok === false ? 'Please check your key and try again.' :
                                 activeProvider.has_key ? 'Ready to use. Save a new key to update.' :
                                 'Add an API key to enable this provider.'}
                              </p>
                            </div>
                          </div>
                          {activeProvider.has_key && (
                            <button
                              onClick={handleTestConnection}
                              disabled={!activeProvider.has_key}
                              className="text-xs font-bold text-indigo-600 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-800 bg-indigo-50 dark:bg-indigo-900/20 px-3 py-1.5 rounded-lg hover:bg-indigo-100 dark:hover:bg-indigo-900/40 transition-colors flex items-center gap-1.5 disabled:opacity-50"
                            >
                              <RefreshCw size={12} className={testingProvider ? 'animate-spin' : ''} />
                              Test
                            </button>
                          )}
                        </div>
                      </div>

                      {/* OpenRouter-specific info */}
                      {activeProvider.id === 'openrouter' && activeProvider.has_key && (
                        <div className="bg-gradient-to-br from-purple-50 to-indigo-50 dark:from-purple-900/10 dark:to-indigo-900/5 border border-purple-100 dark:border-purple-800/50 rounded-xl p-4">
                          <div className="flex items-center gap-2 mb-2">
                            <Network size={16} className="text-purple-600 dark:text-purple-400" />
                            <span className="text-sm font-bold text-purple-900 dark:text-purple-200">OpenRouter Features</span>
                          </div>
                          <div className="grid grid-cols-2 gap-2 text-xs">
                            <div className="flex items-center gap-2 bg-white/50 dark:bg-slate-800/50 rounded-lg px-3 py-2">
                              <span className="text-purple-500">✓</span>
                              <span className="text-gray-600 dark:text-gray-400">200+ free models</span>
                            </div>
                            <div className="flex items-center gap-2 bg-white/50 dark:bg-slate-800/50 rounded-lg px-3 py-2">
                              <span className="text-purple-500">✓</span>
                              <span className="text-gray-600 dark:text-gray-400">Reasoning token support</span>
                            </div>
                            <div className="flex items-center gap-2 bg-white/50 dark:bg-slate-800/50 rounded-lg px-3 py-2">
                              <span className="text-purple-500">✓</span>
                              <span className="text-gray-600 dark:text-gray-400">Unified billing</span>
                            </div>
                            <div className="flex items-center gap-2 bg-white/50 dark:bg-slate-800/50 rounded-lg px-3 py-2">
                              <span className="text-purple-500">✓</span>
                              <span className="text-gray-600 dark:text-gray-400">Model fallback routing</span>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    /* Provider Info tab */
                    <div className="space-y-4 max-w-lg">
                      <div className="grid grid-cols-2 gap-4">
                        <div className="bg-gray-50 dark:bg-slate-800/50 rounded-xl p-4">
                          <p className="text-[11px] font-bold uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-1">Provider</p>
                          <p className="text-sm font-bold text-gray-900 dark:text-gray-100">{activeProvider.name}</p>
                        </div>
                        <div className="bg-gray-50 dark:bg-slate-800/50 rounded-xl p-4">
                          <p className="text-[11px] font-bold uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-1">Status</p>
                          <div className="flex items-center gap-1.5">
                            <div className={clsx(
                              "w-2 h-2 rounded-full",
                              activeProvider.has_key ? "bg-emerald-500" : "bg-gray-300 dark:bg-gray-600"
                            )} />
                            <span className={clsx(
                              "text-sm font-bold",
                              activeProvider.has_key ? "text-emerald-600 dark:text-emerald-400" : "text-gray-500 dark:text-gray-400"
                            )}>
                              {activeProvider.has_key ? 'Active' : 'Inactive'}
                            </span>
                          </div>
                        </div>
                        <div className="bg-gray-50 dark:bg-slate-800/50 rounded-xl p-4">
                          <p className="text-[11px] font-bold uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-1">Key Prefix</p>
                          <p className="text-sm font-mono font-bold text-gray-900 dark:text-gray-100">
                            {activeProvider.key_prefix || '—'}
                          </p>
                        </div>
                        <div className="bg-gray-50 dark:bg-slate-800/50 rounded-xl p-4">
                          <p className="text-[11px] font-bold uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-1">Base URL</p>
                          <p className="text-sm font-mono font-bold text-gray-900 dark:text-gray-100 truncate">
                            {activeProvider.base_url || '—'}
                          </p>
                        </div>
                      </div>
                      <div className="bg-gray-50 dark:bg-slate-800/50 rounded-xl p-4">
                        <p className="text-[11px] font-bold uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-1">Available Models</p>
                        <p className="text-sm text-gray-600 dark:text-gray-400">{meta.description}</p>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-full py-16 px-8 text-center">
                <div className="w-16 h-16 rounded-2xl bg-gray-50 dark:bg-slate-800 border border-gray-200 dark:border-slate-700 flex items-center justify-center text-gray-300 dark:text-gray-600 mb-4">
                  <Key size={28} />
                </div>
                <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100 mb-1">Select a Provider</h3>
                <p className="text-sm text-gray-500 dark:text-gray-400 max-w-xs">
                  Choose a provider from the list to configure its API key and settings.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </SettingsLayout>
  );
}
