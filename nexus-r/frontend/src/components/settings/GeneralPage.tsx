import { useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useGeneralStore } from '../../store/generalStore';
import { APP_NAME } from '../../constants';
import { SettingsLayout } from '../layout/SettingsLayout';
import { PageHeader } from '../ui/PageHeader';
import { SearchBar } from '../ui/SearchBar';
import { SettingsSection } from './ui/SettingsSection';
import { InputRow } from './ui/InputRow';
import { SelectRow } from './ui/SelectRow';
import { ToggleRow } from './ui/ToggleRow';
import { ActionRow } from './ui/ActionRow';
import { SettingsNavigation } from './ui/SettingsNavigation';
import { ComingSoonBadge } from '../ui/ComingSoonBadge';
import { Settings, Box, Key, Palette, Wrench, Database, Shield, Zap, Code, Link, CloudOff, Info, RefreshCw, AlertCircle } from 'lucide-react';

export default function GeneralPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { settings, isLoading, error, loadSettings, updateSetting } = useGeneralStore();
  const activeTab = location.pathname.split('/').pop() || 'general';

  useEffect(() => {
    loadSettings();
  }, [loadSettings]);

  const tabs = [
    { id: 'general', label: 'General', icon: <Settings size={18} /> },
    { id: 'models', label: 'Models', icon: <Box size={18} /> },
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
      <div className="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl p-6 text-center text-gray-500 dark:text-gray-400">
        No active session statistics available in General settings.
      </div>
    </div>
  );

  const footer = (
    <>
      <button 
        onClick={() => navigate('/')}
        className="px-6 py-2.5 rounded-full text-sm font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-100 transition-colors"
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
      {error && (
        <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl flex items-start gap-3">
          <AlertCircle size={20} className="text-red-500 mt-0.5 shrink-0" />
          <div>
            <h4 className="text-sm font-bold text-red-800 dark:text-red-400">Error</h4>
            <p className="text-sm text-red-600 dark:text-red-300 mt-1">{error}</p>
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="p-12 flex justify-center">
          <div className="w-10 h-10 border-4 border-gray-200 dark:border-slate-800 border-t-accent-500 rounded-full animate-spin"></div>
        </div>
      ) : (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-2">
          <SettingsSection title="General Settings" description="Basic application preferences and local system configuration.">
            <SelectRow 
              label="Language" 
              description="Choose your preferred language for the application UI" 
              options={[{ label: 'English', value: 'en' }, { label: 'Spanish', value: 'es' }, { label: 'French', value: 'fr' }]} 
              value={settings.language}
              onChange={(val) => updateSetting('language', val)}
            />
            
            <ToggleRow 
              label="Auto Update" 
              description="Automatically install updates when available" 
              checked={settings.autoUpdate} 
              onChange={() => updateSetting('autoUpdate', !settings.autoUpdate)} 
            />

            <ToggleRow 
              label="Allow Telemetry" 
              description="Send anonymous usage statistics to improve the application" 
              checked={settings.telemetryEnabled} 
              onChange={() => updateSetting('telemetryEnabled', !settings.telemetryEnabled)} 
            />

            <InputRow 
              label="Default Workspace Directory" 
              description="Location where persistent files, documents, and backups are saved" 
              defaultValue={settings.defaultDirectory}
              onChange={(e) => updateSetting('defaultDirectory', e.target.value)}
              placeholder="e.g. C:\Users\Nexus\Workspace"
            />
            
            <ActionRow label="Auto Startup" description="Launch the application on system boot" action={<ComingSoonBadge />} />
          </SettingsSection>
        </div>
      )}

    </SettingsLayout>
  );
}
