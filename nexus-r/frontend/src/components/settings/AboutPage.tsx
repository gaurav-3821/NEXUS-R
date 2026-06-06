import { useNavigate, useLocation } from 'react-router-dom';
import { APP_NAME } from '../../constants';
import { SettingsLayout } from '../layout/SettingsLayout';
import { PageHeader } from '../ui/PageHeader';
import { SearchBar } from '../ui/SearchBar';
import { SettingsNavigation } from './ui/SettingsNavigation';
import {
  Settings, Box, Key, Palette, Wrench, Database, Shield, Zap, Code, Link, CloudOff, Info,
  RefreshCw, Bot, Search, Brain, MessageSquare, Globe, Lightbulb, Cpu, LayoutDashboard,
  ExternalLink,
} from 'lucide-react';

const VERSION = '0.1.0';
const COMMIT_HASH = '2f6c38c';
const GITHUB_URL = 'https://github.com/gaurav-3821/NEXUS-R';

function InfoCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="flex items-center gap-3 p-3 bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl">
      <div className="w-8 h-8 rounded-lg bg-indigo-50 dark:bg-indigo-900/20 text-indigo-500 dark:text-indigo-400 flex items-center justify-center shrink-0">
        {icon}
      </div>
      <div>
        <p className="text-xs font-semibold text-gray-500 dark:text-gray-400">{label}</p>
        <p className="text-sm font-bold text-gray-900 dark:text-gray-100">{value}</p>
      </div>
    </div>
  );
}

function CapabilityCard({ icon, title, description }: { icon: React.ReactNode; title: string; description: string }) {
  return (
    <div className="flex gap-3 p-4 bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl hover:border-gray-300 dark:hover:border-slate-600 transition-colors">
      <div className="w-8 h-8 rounded-lg bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0 mt-0.5">
        {icon}
      </div>
      <div>
        <h5 className="font-bold text-gray-900 dark:text-gray-100 text-sm mb-0.5">{title}</h5>
        <p className="text-xs font-medium text-gray-500 dark:text-gray-400 leading-relaxed">{description}</p>
      </div>
    </div>
  );
}

export default function AboutPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const activeTab = location.pathname.split('/').pop() || 'about';

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
      subtitle={`Manage ${APP_NAME} configuration and preferences`}
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
      <div className="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl p-5 shadow-sm">
        <h5 className="font-bold text-gray-900 dark:text-gray-100 text-sm mb-3">Version Info</h5>
        <div className="space-y-2">
          <InfoCard icon={<Bot size={16} />} label="App Version" value={`v${VERSION}`} />
          <InfoCard icon={<Cpu size={16} />} label="Frontend" value="React 19 + Vite 8" />
          <InfoCard icon={<Cpu size={16} />} label="Backend" value="Python 3.11+ / FastAPI" />
          <InfoCard icon={<Code size={16} />} label="Commit" value={COMMIT_HASH} />
        </div>
      </div>

      <div className="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl p-5 shadow-sm">
        <h5 className="font-bold text-gray-900 dark:text-gray-100 text-sm mb-3">Links</h5>
        <div className="space-y-2">
          <a href={GITHUB_URL} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 p-2.5 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-800 transition-colors text-sm font-semibold text-gray-700 dark:text-gray-300">
            <Code size={16} /> GitHub Repository <ExternalLink size={12} className="text-gray-400 ml-auto" />
          </a>
        </div>
      </div>
    </div>
  );

  return (
    <SettingsLayout
      header={header}
      sidebar={sidebar}
      rightPanel={rightPanel}
      isOverlay={false}
    >
      <div className="animate-in fade-in slide-in-from-bottom-2 h-full flex flex-col w-full pb-8">
        <div className="flex items-center gap-3 mb-8">
          <div className="w-10 h-10 rounded-xl bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400 flex items-center justify-center">
            <Info size={20} />
          </div>
          <div>
            <h3 className="text-xl font-bold text-gray-900 dark:text-gray-100">About {APP_NAME}</h3>
            <p className="text-sm font-medium text-gray-500 dark:text-gray-400 mt-0.5">What this application is and what it can do.</p>
          </div>
        </div>

        <div className="mb-8">
          <h4 className="text-[15px] font-bold text-gray-900 dark:text-gray-100 mb-1">What is {APP_NAME}?</h4>
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400 leading-relaxed">
            {APP_NAME} is an intelligent agent runtime that connects large language models to your tools, data, and workflows.
            It provides a unified chat interface backed by a pluggable architecture for search, memory, suggestions, widgets,
            and multi-model routing — enabling context-aware assistance that adapts to how you work.
          </p>
        </div>

        <div className="mb-8">
          <h4 className="text-[15px] font-bold text-gray-900 dark:text-gray-100 mb-3">Capabilities</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <CapabilityCard
              icon={<MessageSquare size={16} />}
              title="Multi-Model Chat"
              description="Chat with any supported LLM — OpenAI, Anthropic, Google, Ollama, OpenRouter, and more. Switch models mid-conversation."
            />
            <CapabilityCard
              icon={<Search size={16} />}
              title="Web Research"
              description="Search the web in real-time using SearxNG or Playwright. Research results are injected as context for informed responses."
            />
            <CapabilityCard
              icon={<Brain size={16} />}
              title="Persistent Memory"
              description="Remembers user preferences, project context, and facts across conversations using SQLite-backed semantic memory with embedding-based retrieval."
            />
            <CapabilityCard
              icon={<Lightbulb size={16} />}
              title="Smart Suggestions"
              description="Provides context-aware input suggestions based on conversation history to speed up your workflow."
            />
            <CapabilityCard
              icon={<LayoutDashboard size={16} />}
              title="Live Widgets"
              description="Displays weather, stock prices, calculator results, router decisions, model status, and cost analytics as interactive inline cards."
            />
            <CapabilityCard
              icon={<Globe size={16} />}
              title="Browser Automation"
              description="Agents can navigate web pages, fill forms, and extract data using Playwright — useful for login workflows, data scraping, and web research."
            />
            <CapabilityCard
              icon={<Cpu size={16} />}
              title="Model Routing"
              description="Automatically routes requests to the most cost-effective model tier based on task complexity, with configurable fallback chains."
            />
            <CapabilityCard
              icon={<Shield size={16} />}
              title="Cost & Usage Tracking"
              description="Tracks token usage, latency, and cost per conversation. Dashboard provides visibility into spending across models and providers."
            />
          </div>
        </div>
      </div>
    </SettingsLayout>
  );
}
