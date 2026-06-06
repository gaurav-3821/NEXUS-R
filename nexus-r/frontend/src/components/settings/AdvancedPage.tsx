import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { SettingsLayout } from '../layout/SettingsLayout';
import { PageHeader } from '../ui/PageHeader';
import { SearchBar } from '../ui/SearchBar';
import { SettingsSection } from './ui/SettingsSection';
import { InputRow } from './ui/InputRow';
import { ToggleRow } from './ui/ToggleRow';
import { ActionRow } from './ui/ActionRow';
import { SettingsNavigation } from './ui/SettingsNavigation';
import {
  Settings, Box, Key, Palette, Wrench, Database, Shield, Zap, Code, Link, CloudOff, Info,
  RefreshCw, TerminalSquare, FlaskConical, Braces, Cpu
} from 'lucide-react';

export default function AdvancedPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const activeTab = location.pathname.split('/').pop() || 'advanced';

  // Local state for advanced settings since they are UI-only mocks for now
  const [developerMode, setDeveloperMode] = useState(false);
  const [experimentalFeatures, setExperimentalFeatures] = useState(false);
  const [verboseLogging, setVerboseLogging] = useState(false);
  const [hardwareAcceleration, setHardwareAcceleration] = useState(true);

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
      title="Advanced Settings" 
      subtitle="Configure developer tools, experimental features, and core system overrides" 
      action={<SearchBar placeholder="Search advanced..." shortcut="Ctrl /" />} 
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
          Reset Advanced
        </button>
      }
    />
  );

  const rightPanel = (
    <div className="space-y-6">
      <div className="bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-xl p-6 flex items-start gap-4">
        <div className="p-2 bg-orange-100 dark:bg-orange-900/40 text-orange-600 dark:text-orange-400 rounded-lg shrink-0">
          <TerminalSquare size={24} />
        </div>
        <div>
          <h4 className="text-[15px] font-bold text-orange-900 dark:text-orange-300 mb-1">Proceed with Caution</h4>
          <p className="text-sm font-medium text-orange-800/80 dark:text-orange-400/80">
            These settings are intended for developers and advanced users. Modifying these values may cause system instability or unexpected behavior in the agent context.
          </p>
        </div>
      </div>
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
      <div className="space-y-8 animate-in fade-in slide-in-from-bottom-2">
        <SettingsSection title="Developer Options" description="Expose additional debugging and telemetry tools.">
          <ToggleRow 
            label="Developer Mode" 
            description="Enable advanced debugging tools, inspector overlays, and full system logs" 
            checked={developerMode} 
            onChange={() => setDeveloperMode(!developerMode)} 
          />
          <ToggleRow 
            label="Verbose Logging" 
            description="Write full prompt/response payloads and trace data to disk" 
            checked={verboseLogging} 
            onChange={() => setVerboseLogging(!verboseLogging)} 
          />
          <ActionRow 
            label="Export System Logs" 
            description="Download all local system logs as a compressed archive" 
            action={
              <button className="px-4 py-2 bg-gray-100 hover:bg-gray-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-gray-800 dark:text-gray-200 rounded-lg text-sm font-semibold transition-colors">
                Export Logs
              </button>
            } 
          />
        </SettingsSection>

        <SettingsSection title="System Overrides" description="Directly modify core operational parameters.">
          <ToggleRow 
            label="Hardware Acceleration" 
            description="Utilize GPU processing for local embedding generation and parsing" 
            checked={hardwareAcceleration} 
            onChange={() => setHardwareAcceleration(!hardwareAcceleration)} 
          />
          <InputRow 
            label="API Base URL Override" 
            description="Redirect all local proxy traffic to a custom backend endpoint" 
            defaultValue=""
            placeholder="e.g. http://localhost:8000"
            onChange={() => {}}
          />
          <InputRow 
            label="Custom System Prompt Prefix" 
            description="Prepend a master instruction to all agent interactions" 
            defaultValue=""
            placeholder="e.g. You are an expert code reviewer..."
            onChange={() => {}}
          />
        </SettingsSection>

        <SettingsSection title="Experimental" description="Opt-in to beta features still in active development.">
          <ToggleRow 
            label="Enable Experimental Features" 
            description="Unlock work-in-progress tools like the semantic local filesystem search agent" 
            checked={experimentalFeatures} 
            onChange={() => setExperimentalFeatures(!experimentalFeatures)} 
          />
          <ActionRow 
            label="Clear Local Cache" 
            description="Purge all temporary files, embedding vectors, and artifact caches" 
            action={
              <button className="px-4 py-2 bg-red-50 hover:bg-red-100 dark:bg-red-900/20 dark:hover:bg-red-900/40 text-red-600 dark:text-red-400 rounded-lg text-sm font-semibold transition-colors">
                Purge Cache
              </button>
            } 
          />
        </SettingsSection>
      </div>
    </SettingsLayout>
  );
}
