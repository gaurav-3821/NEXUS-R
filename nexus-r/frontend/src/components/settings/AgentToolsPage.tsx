import { useEffect, useState, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  getBrowserStatus, startBrowser, stopBrowser,
  getBrowserPageText, takeBrowserScreenshot, switchBrowserHeaded,
  saveBrowserSession, loadBrowserSession, getBrowserNetworkData,
} from '../../api/tools';
import type { BrowserStatus, NetworkDataEntry } from '../../api/tools';
import { SettingsLayout } from '../layout/SettingsLayout';
import { PageHeader } from '../ui/PageHeader';
import { SearchBar } from '../ui/SearchBar';
import { SettingsNavigation } from './ui/SettingsNavigation';
import { SettingsCard } from './ui/SettingsCard';
import {
  Settings, Box, Key, Palette, Wrench, Database, Shield, Zap, Code, Link, CloudOff, Info,
  RefreshCw, Play, Square, Monitor, FileText, Camera, ExternalLink, CheckCircle2,
  XCircle, ChevronRight, AlertCircle, Loader2, Activity, Save, Download,
  Globe, Network,
} from 'lucide-react';

export default function AgentToolsPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const activeTab = location.pathname.split('/').pop() || 'agent-tools';
  const [status, setStatus] = useState<BrowserStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [pageText, setPageText] = useState<string | null>(null);
  const [screenshotB64, setScreenshotB64] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [networkData, setNetworkData] = useState<NetworkDataEntry[] | null>(null);
  const [sessionResult, setSessionResult] = useState<string | null>(null);
  const [activeSubTab, setActiveSubTab] = useState<'sandbox' | 'actions' | 'guardrails'>('sandbox');

  const fetchStatus = useCallback(async () => {
    try {
      const s = await getBrowserStatus();
      setStatus(s);
      setError(null);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  const doAction = async (key: string, fn: () => Promise<any>) => {
    setActionLoading(key);
    setError(null);
    try {
      const res = await fn();
      if (res && res.success === false) setError(`Action failed`);
      await fetchStatus();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setActionLoading(null);
    }
  };

  const handleStart = () => doAction('start', startBrowser);
  const handleStop = () => doAction('stop', stopBrowser);

  const handleScreenshot = async () => {
    setActionLoading('screenshot');
    setError(null);
    try {
      const res = await takeBrowserScreenshot();
      setScreenshotB64(res.image_base64);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setActionLoading(null);
    }
  };

  const handlePageText = async () => {
    setActionLoading('page-text');
    setError(null);
    try {
      const res = await getBrowserPageText();
      setPageText(res.text);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setActionLoading(null);
    }
  };

  const handleSwitchHeaded = () => doAction('switch-headed', switchBrowserHeaded);

  const handleNetworkData = async () => {
    setActionLoading('network-data');
    setError(null);
    try {
      const res = await getBrowserNetworkData();
      setNetworkData(res.entries);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setActionLoading(null);
    }
  };

  const handleSaveSession = async () => {
    setActionLoading('save-session');
    setError(null);
    setSessionResult(null);
    try {
      const res = await saveBrowserSession();
      setSessionResult(res.success ? `Session saved to ${res.path}` : 'Failed to save session');
    } catch (e: any) {
      setError(e.message);
    } finally {
      setActionLoading(null);
    }
  };

  const handleLoadSession = async () => {
    setActionLoading('load-session');
    setError(null);
    setSessionResult(null);
    try {
      const res = await loadBrowserSession();
      setSessionResult(res.success ? 'Session loaded successfully' : 'No session file found');
    } catch (e: any) {
      setError(e.message);
    } finally {
      setActionLoading(null);
    }
  };

  const tabs = [
    { id: 'general', label: 'General', icon: <Settings size={18} /> },
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

  const btnClass = "w-full py-2.5 px-4 bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl text-sm font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-slate-800 disabled:opacity-50 flex items-center gap-3 transition-colors text-left";

  const rightPanel = (
    <div className="space-y-6">
      <SettingsCard title="Browser Status">
        <div className="flex items-center gap-3 mb-2">
          {status?.started
            ? <CheckCircle2 size={20} className="text-emerald-500 dark:text-emerald-400 shrink-0" />
            : <XCircle size={20} className="text-gray-300 dark:text-gray-600 shrink-0" />
          }
          <div>
            <h4 className="text-sm font-bold text-gray-900 dark:text-gray-100">
              {status?.started ? 'Running' : 'Stopped'}
            </h4>
            {status?.current_url && (
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mt-0.5 truncate max-w-[180px]">{status.current_url}</p>
            )}
          </div>
        </div>
        <div className="space-y-1.5 text-xs font-medium text-gray-500 dark:text-gray-400">
          <div className="flex justify-between"><span>Headless</span><span className="text-gray-700 dark:text-gray-300">{status?.headless ? 'Yes' : 'No'}</span></div>
        </div>
      </SettingsCard>

      <SettingsCard title="Quick Actions">
        <button onClick={handleStart} disabled={actionLoading === 'start' || status?.started} className={btnClass}>
          {actionLoading === 'start' ? <Loader2 size={16} className="animate-spin text-accent-500" /> : <Play size={16} className="text-emerald-500 dark:text-emerald-400" />}
          Start Browser
        </button>
        <button onClick={handleStop} disabled={actionLoading === 'stop' || !status?.started} className={btnClass}>
          {actionLoading === 'stop' ? <Loader2 size={16} className="animate-spin text-accent-500" /> : <Square size={16} className="text-red-500 dark:text-red-400" />}
          Stop Browser
        </button>
        <button onClick={handleScreenshot} disabled={actionLoading === 'screenshot' || !status?.started} className={btnClass}>
          {actionLoading === 'screenshot' ? <Loader2 size={16} className="animate-spin text-accent-500" /> : <Camera size={16} className="text-blue-500 dark:text-blue-400" />}
          Take Screenshot
        </button>
        <button onClick={handlePageText} disabled={actionLoading === 'page-text' || !status?.started} className={btnClass}>
          {actionLoading === 'page-text' ? <Loader2 size={16} className="animate-spin text-accent-500" /> : <FileText size={16} className="text-indigo-500 dark:text-indigo-400" />}
          Get Page Text
        </button>
        <button onClick={handleSwitchHeaded} disabled={actionLoading === 'switch-headed' || !status?.started || !status?.headless} className={btnClass}>
          {actionLoading === 'switch-headed' ? <Loader2 size={16} className="animate-spin text-accent-500" /> : <Monitor size={16} className="text-orange-500 dark:text-orange-400" />}
          Switch to Headed
        </button>
        <button onClick={handleSaveSession} disabled={actionLoading === 'save-session' || !status?.started} className={btnClass}>
          {actionLoading === 'save-session' ? <Loader2 size={16} className="animate-spin text-accent-500" /> : <Save size={16} className="text-green-500 dark:text-green-400" />}
          Save Session
        </button>
        <button onClick={handleLoadSession} disabled={actionLoading === 'load-session'} className={btnClass}>
          {actionLoading === 'load-session' ? <Loader2 size={16} className="animate-spin text-accent-500" /> : <Download size={16} className="text-amber-500 dark:text-amber-400" />}
          Load Session
        </button>
        <button onClick={handleNetworkData} disabled={actionLoading === 'network-data' || !status?.started} className={btnClass}>
          {actionLoading === 'network-data' ? <Loader2 size={16} className="animate-spin text-accent-500" /> : <Network size={16} className="text-cyan-500 dark:text-cyan-400" />}
          View Network Data
        </button>
        {sessionResult && (
          <div className="text-xs font-medium text-gray-500 dark:text-gray-400 px-1">{sessionResult}</div>
        )}
      </SettingsCard>
    </div>
  );

  const footer = (
    <>
      <button
        onClick={() => navigate('/')}
        className="px-6 py-2.5 rounded-full text-sm font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-800 transition-colors"
      >
        Close
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
            <div className="w-10 h-10 rounded-xl bg-orange-50 dark:bg-orange-900/20 text-orange-600 dark:text-orange-400 flex items-center justify-center">
              <Wrench size={20} />
            </div>
            <div>
              <h3 className="text-xl font-bold text-gray-900 dark:text-gray-100">Agent Tools</h3>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400 mt-0.5">Manage NEXUS-R agent capabilities — browser, calculator, memory, and more.</p>
            </div>
          </div>
        </div>

        {error && (
          <div className="flex items-center gap-2 p-3 mb-6 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl text-sm font-semibold text-red-700 dark:text-red-400">
            <AlertCircle size={16} />
            {error}
          </div>
        )}

        <div className="flex gap-6 border-b border-gray-100 dark:border-slate-800 mb-8">
          <button onClick={() => setActiveSubTab('sandbox')} className={`pb-2 text-sm font-bold transition-colors ${activeSubTab === 'sandbox' ? 'text-orange-600 dark:text-orange-400 border-b-2 border-orange-600 dark:border-orange-400' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}`}>Browser Sandbox</button>
          <button onClick={() => setActiveSubTab('actions')} className={`pb-2 text-sm font-bold transition-colors ${activeSubTab === 'actions' ? 'text-orange-600 dark:text-orange-400 border-b-2 border-orange-600 dark:border-orange-400' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}`}>Available Actions</button>
          <button onClick={() => setActiveSubTab('guardrails')} className={`pb-2 text-sm font-bold transition-colors ${activeSubTab === 'guardrails' ? 'text-orange-600 dark:text-orange-400 border-b-2 border-orange-600 dark:border-orange-400' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}`}>Guardrails</button>
        </div>

        {activeSubTab === 'sandbox' && (
        <div className="mb-10">
          <h4 className="text-[15px] font-bold text-gray-900 dark:text-gray-100 mb-1">Browser Sandbox</h4>
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-4">Headless Chromium browser with full navigation, interaction, search, and screenshot capabilities. Protected by concurrency lock and automatic error recovery.</p>

          <div className="grid grid-cols-4 gap-4 mb-4">
            <div className="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl p-4 shadow-sm dark:shadow-black/10">
              <div className="w-6 h-6 rounded-md bg-emerald-50 dark:bg-emerald-900/20 text-emerald-500 dark:text-emerald-400 flex items-center justify-center mb-3">
                <Activity size={14} />
              </div>
              <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1">Status</p>
              <h4 className="text-sm font-bold text-gray-900 dark:text-gray-100">{isLoading ? '...' : (status?.started ? 'Running' : 'Stopped')}</h4>
            </div>
            <div className="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl p-4 shadow-sm dark:shadow-black/10">
              <div className="w-6 h-6 rounded-md bg-indigo-50 dark:bg-indigo-900/20 text-indigo-500 dark:text-indigo-400 flex items-center justify-center mb-3">
                <Monitor size={14} />
              </div>
              <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1">Mode</p>
              <h4 className="text-sm font-bold text-gray-900 dark:text-gray-100">{isLoading ? '...' : (status?.headless ? 'Headless' : 'Headed')}</h4>
            </div>
            <div className="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl p-4 shadow-sm dark:shadow-black/10 col-span-2">
              <div className="w-6 h-6 rounded-md bg-blue-50 dark:bg-blue-900/20 text-blue-500 dark:text-blue-400 flex items-center justify-center mb-3">
                <ExternalLink size={14} />
              </div>
              <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1">Current URL</p>
              <h4 className="text-[13px] font-bold text-gray-900 dark:text-gray-100 truncate">{isLoading ? '...' : (status?.current_url || 'N/A')}</h4>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 mb-8">
            <div className="flex items-center justify-between p-4 bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl shadow-sm dark:shadow-black/10">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400 flex items-center justify-center shrink-0">
                  <CheckCircle2 size={16} />
                </div>
                <div>
                  <h5 className="font-bold text-gray-900 dark:text-gray-100 text-sm">Concurrency Lock</h5>
                  <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Async-safe with asyncio.Lock on all 15 action methods.</p>
                </div>
              </div>
              <ChevronRight size={14} className="text-gray-400 dark:text-gray-500 shrink-0" />
            </div>
            <div className="flex items-center justify-between p-4 bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl shadow-sm dark:shadow-black/10">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
                  <RefreshCw size={16} />
                </div>
                <div>
                  <h5 className="font-bold text-gray-900 dark:text-gray-100 text-sm">Error Recovery</h5>
                  <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Auto-retry on fatal errors with context recreation.</p>
                </div>
              </div>
              <ChevronRight size={14} className="text-gray-400 dark:text-gray-500 shrink-0" />
            </div>
            <div className="flex items-center justify-between p-4 bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl shadow-sm dark:shadow-black/10">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-purple-50 dark:bg-purple-900/20 text-purple-600 dark:text-purple-400 flex items-center justify-center shrink-0">
                  <Shield size={16} />
                </div>
                <div>
                  <h5 className="font-bold text-gray-900 dark:text-gray-100 text-sm">Stealth / Anti-Bot</h5>
                  <p className="text-xs font-medium text-gray-500 dark:text-gray-400">navigator.webdriver hidden, realistic UA + fingerprinting protection.</p>
                </div>
              </div>
              <ChevronRight size={14} className="text-gray-400 dark:text-gray-500 shrink-0" />
            </div>
            <div className="flex items-center justify-between p-4 bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl shadow-sm dark:shadow-black/10">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-cyan-50 dark:bg-cyan-900/20 text-cyan-600 dark:text-cyan-400 flex items-center justify-center shrink-0">
                  <Activity size={16} />
                </div>
                <div>
                  <h5 className="font-bold text-gray-900 dark:text-gray-100 text-sm">Network Capture</h5>
                  <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Captures XHR/Fetch JSON responses for LLM inspection.</p>
                </div>
              </div>
              <ChevronRight size={14} className="text-gray-400 dark:text-gray-500 shrink-0" />
            </div>
          </div>

          <h4 className="text-[15px] font-bold text-gray-900 dark:text-gray-100 mb-1">Captured Data</h4>
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-4">
            Browser actions can capture screenshots and page text for review.
          </p>
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl p-4 shadow-sm dark:shadow-black/10">
              <div className="flex items-center justify-between mb-3">
                <h5 className="font-bold text-gray-900 dark:text-gray-100 text-sm">Screenshot</h5>
                <button onClick={handleScreenshot} disabled={actionLoading === 'screenshot' || !status?.started} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-900 hover:bg-gray-50 dark:hover:bg-slate-800 transition-colors text-xs font-semibold text-gray-700 dark:text-gray-300 shadow-sm disabled:opacity-50">
                  {actionLoading === 'screenshot' ? <Loader2 size={12} className="animate-spin" /> : <Camera size={12} />}
                  Capture
                </button>
              </div>
              {screenshotB64 ? (
                <img src={`data:image/png;base64,${screenshotB64}`} alt="Browser screenshot" className="w-full rounded-lg border border-gray-200 dark:border-slate-700" />
              ) : (
                <div className="h-32 flex items-center justify-center bg-gray-50 dark:bg-slate-800 rounded-lg text-xs font-medium text-gray-400 dark:text-gray-500">No screenshot captured</div>
              )}
            </div>
            <div className="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl p-4 shadow-sm dark:shadow-black/10">
              <div className="flex items-center justify-between mb-3">
                <h5 className="font-bold text-gray-900 dark:text-gray-100 text-sm">Page Text</h5>
                <button onClick={handlePageText} disabled={actionLoading === 'page-text' || !status?.started} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-900 hover:bg-gray-50 dark:hover:bg-slate-800 transition-colors text-xs font-semibold text-gray-700 dark:text-gray-300 shadow-sm disabled:opacity-50">
                  {actionLoading === 'page-text' ? <Loader2 size={12} className="animate-spin" /> : <FileText size={12} />}
                  Refresh
                </button>
              </div>
              {pageText ? (
                <pre className="h-32 overflow-y-auto text-xs font-mono text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-slate-800 rounded-lg p-3 whitespace-pre-wrap break-words">{pageText.length > 2000 ? pageText.slice(0, 2000) + '...' : pageText}</pre>
              ) : (
                <div className="h-32 flex items-center justify-center bg-gray-50 dark:bg-slate-800 rounded-lg text-xs font-medium text-gray-400 dark:text-gray-500">No page text captured</div>
              )}
            </div>
          </div>

          <div className="mt-6">
            <div className="flex items-center justify-between mb-3">
              <h5 className="font-bold text-gray-900 dark:text-gray-100 text-sm">Captured API Data</h5>
              <button onClick={handleNetworkData} disabled={actionLoading === 'network-data' || !status?.started} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-900 hover:bg-gray-50 dark:hover:bg-slate-800 transition-colors text-xs font-semibold text-gray-700 dark:text-gray-300 shadow-sm disabled:opacity-50">
                {actionLoading === 'network-data' ? <Loader2 size={12} className="animate-spin" /> : <Network size={12} />}
                Fetch Network Data
              </button>
            </div>
            {networkData ? (
              networkData.length === 0 ? (
                <div className="h-20 flex items-center justify-center bg-gray-50 dark:bg-slate-800 rounded-lg text-xs font-medium text-gray-400 dark:text-gray-500">No API data captured yet</div>
              ) : (
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {networkData.map((entry, i) => (
                    <div key={i} className="p-3 bg-gray-50 dark:bg-slate-800 rounded-lg border border-gray-100 dark:border-slate-700">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${entry.status < 300 ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400' : 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400'}`}>{entry.status}</span>
                        <span className="text-[10px] font-mono font-medium text-gray-500 dark:text-gray-400">{entry.method}</span>
                        <span className="text-[10px] font-mono text-gray-600 dark:text-gray-300 truncate flex-1">{entry.url}</span>
                      </div>
                      <pre className="text-[10px] font-mono text-gray-500 dark:text-gray-400 truncate">{JSON.stringify(entry.data).slice(0, 200)}</pre>
                    </div>
                  ))}
                </div>
              )
            ) : (
              <div className="h-20 flex items-center justify-center bg-gray-50 dark:bg-slate-800 rounded-lg text-xs font-medium text-gray-400 dark:text-gray-500">Press "Fetch Network Data" to view captured API responses</div>
            )}
          </div>
        </div>
        )}

        {activeSubTab === 'actions' && (
        <div>
          <h4 className="text-[15px] font-bold text-gray-900 dark:text-gray-100 mb-1">Available Actions</h4>
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-4">The browser sandbox exposes these actions to the agent.</p>

          <div className="grid grid-cols-3 gap-3">
            {[
              { label: 'Navigate to URL', action: 'goto(url)', desc: 'Navigate to any URL with domcontentloaded + networkidle fallback.' },
              { label: 'Click Element', action: 'click(selector)', desc: 'Click an element by CSS selector.' },
              { label: 'Type Text', action: 'type_text(selector, text)', desc: 'Fill an input field.' },
              { label: 'Evaluate JavaScript', action: 'evaluate(code)', desc: 'Execute arbitrary JS in the page context.' },
              { label: 'Extract Text', action: 'extract_text(max_chars)', desc: 'Scrape visible text, stripping scripts/styles.' },
              { label: 'Screenshot', action: 'screenshot()', desc: 'Capture current page as PNG.' },
              { label: 'Get Links', action: 'get_links()', desc: 'Extract all linked URLs from the page.' },
              { label: 'Wait for Element', action: 'wait_for_element(selector)', desc: 'Wait for a CSS selector to appear.' },
              { label: 'Web Search', action: 'search_web(query)', desc: 'Search Brave Search and return results.' },
              { label: 'Image Search', action: 'search_images(query)', desc: 'Search Google Images for thumbnails.' },
              { label: 'Detect CAPTCHA / MFA', action: 'detect_interception_wall()', desc: 'Scan DOM for challenge walls.' },
              { label: 'Fill OTP Code', action: 'fill_otp_code(selector, code)', desc: 'Enter a verification code into an MFA field.' },
              { label: 'Switch to Headed', action: 'switch_to_headed()', desc: 'Open headed browser for HITL interaction.' },
              { label: 'Read Network Data', action: 'read_network_data(max_entries)', desc: 'Return captured API/JSON responses from page requests.' },
              { label: 'Stealth Browsing', action: '(automatic)', desc: 'Anti-bot fingerprinting protection applied on every new page.' },
            ].map((item, i) => (
              <div key={i} className="flex flex-col p-4 bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl hover:bg-gray-50 dark:hover:bg-slate-800 transition-colors overflow-hidden">
                <h5 className="font-bold text-gray-900 dark:text-gray-100 text-sm mb-1 truncate">{item.label}</h5>
                <code className="text-xs font-mono text-orange-600 dark:text-orange-400 bg-orange-50 dark:bg-orange-900/20 px-1.5 py-0.5 rounded self-start mb-1.5 max-w-full break-all">{item.action}</code>
                <p className="text-xs font-medium text-gray-500 dark:text-gray-400 break-words">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
        )}

        {activeSubTab === 'guardrails' && (
        <div>
          <h4 className="text-[15px] font-bold text-gray-900 dark:text-gray-100 mb-1">Guardrails & Safety</h4>
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-4">Safety mechanisms that protect the agent from runaway behavior, blocked access, and data loss.</p>

          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl shadow-sm dark:shadow-black/10">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-8 h-8 rounded-lg bg-amber-50 dark:bg-amber-900/20 text-amber-600 dark:text-amber-400 flex items-center justify-center shrink-0">
                  <Clock size={16} />
                </div>
                <div>
                  <h5 className="font-bold text-gray-900 dark:text-gray-100 text-sm">Time Guardrail</h5>
                  <p className="text-xs font-medium text-gray-500 dark:text-gray-400">60-second max per action loop</p>
                </div>
              </div>
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400 leading-relaxed">The browser action loop enforces a 60-second hard limit. When exceeded, the loop breaks cleanly, a system message is appended to the intent, and a WebSocket broadcast notifies the UI. Final metrics are still computed after the break.</p>
            </div>

            <div className="p-4 bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl shadow-sm dark:shadow-black/10">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-8 h-8 rounded-lg bg-purple-50 dark:bg-purple-900/20 text-purple-600 dark:text-purple-400 flex items-center justify-center shrink-0">
                  <Shield size={16} />
                </div>
                <div>
                  <h5 className="font-bold text-gray-900 dark:text-gray-100 text-sm">Stealth / Anti-Bot</h5>
                  <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Fingerprinting protection on every page</p>
                </div>
              </div>
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400 leading-relaxed">A JavaScript init script overrides navigator.webdriver, sets realistic plugins, languages, and chrome objects, and patches permissions.query to avoid automated detection. Applied via context.add_init_script() on every new context creation.</p>
            </div>

            <div className="p-4 bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl shadow-sm dark:shadow-black/10">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-8 h-8 rounded-lg bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400 flex items-center justify-center shrink-0">
                  <Save size={16} />
                </div>
                <div>
                  <h5 className="font-bold text-gray-900 dark:text-gray-100 text-sm">Session Persistence</h5>
                  <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Cookies + storage saved to JSON</p>
                </div>
              </div>
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400 leading-relaxed">save_session_state() writes cookies and localStorage to a JSON file via context.storage_state(). load_session_state() reads it back. The session file path is tracked in self._session_file and auto-loaded during _do_start() via the storage_state parameter to new_context().</p>
            </div>

            <div className="p-4 bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl shadow-sm dark:shadow-black/10">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-8 h-8 rounded-lg bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
                  <RefreshCw size={16} />
                </div>
                <div>
                  <h5 className="font-bold text-gray-900 dark:text-gray-100 text-sm">Error Recovery</h5>
                  <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Auto-retry with context recreation</p>
                </div>
              </div>
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400 leading-relaxed">The _call_with_retry wrapper catches fatal browser errors and triggers _recreate_context, which fully resets _playwright to None then calls _do_start() for a clean restart. This enables automatic recovery from crashed pages or lost connections.</p>
            </div>

            <div className="p-4 bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl shadow-sm dark:shadow-black/10">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-8 h-8 rounded-lg bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400 flex items-center justify-center shrink-0">
                  <CheckCircle2 size={16} />
                </div>
                <div>
                  <h5 className="font-bold text-gray-900 dark:text-gray-100 text-sm">Concurrency Lock</h5>
                  <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Async-safe with asyncio.Lock</p>
                </div>
              </div>
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400 leading-relaxed">All 15 public browser methods acquire self._lock before execution. This prevents race conditions when multiple agents or UI commands try to control the browser simultaneously.</p>
            </div>

            <div className="p-4 bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl shadow-sm dark:shadow-black/10">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-8 h-8 rounded-lg bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400 flex items-center justify-center shrink-0">
                  <Globe size={16} />
                </div>
                <div>
                  <h5 className="font-bold text-gray-900 dark:text-gray-100 text-sm">Memory Push</h5>
                  <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Scraped content sent to semantic memory</p>
                </div>
              </div>
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400 leading-relaxed">After every browser extract_text() action, the scraped content is automatically pushed to the semantic memory system via extract_memories(updated_text, ""). This allows the LLM to recall previously visited page content across sessions.</p>
            </div>
          </div>
        </div>
        )}

      </div>
    </SettingsLayout>
  );
}
