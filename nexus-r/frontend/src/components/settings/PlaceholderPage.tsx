import { useNavigate, useLocation } from 'react-router-dom';
import { SettingsLayout } from '../layout/SettingsLayout';
import { PageHeader } from '../ui/PageHeader';
import { SearchBar } from '../ui/SearchBar';
import { SettingsNavigation } from './ui/SettingsNavigation';
import { ComingSoonBadge } from '../ui/ComingSoonBadge';
import { 
  Settings, Box, Key, Palette, Wrench, Database, Shield, Zap, Code, Link, CloudOff, Info, RefreshCw 
} from 'lucide-react';
import { APP_NAME } from '../../constants';

export default function PlaceholderPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const activeTab = location.pathname.split('/').pop() || '';

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

  const currentTab = tabs.find(t => t.id === activeTab) || tabs[0];

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
    <div className="flex flex-col items-center justify-center h-[50vh] text-center max-w-md mx-auto">
      <div className="w-16 h-16 bg-gray-100 dark:bg-slate-800 rounded-2xl flex items-center justify-center text-gray-400 dark:text-gray-500 mb-6 shadow-sm border border-gray-200 dark:border-slate-700">
        {currentTab.icon}
      </div>
      <h3 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">{currentTab.label}</h3>
      <p className="text-gray-500 dark:text-gray-400 mb-6 leading-relaxed">
        This section is currently under development. Soon you'll be able to manage your {currentTab.label.toLowerCase()} preferences right here.
      </p>
      <ComingSoonBadge />
    </div>
  );

  const footer = (
    <>
      <button 
        onClick={() => navigate('/')}
        className="px-6 py-2.5 rounded-full text-sm font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
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
      <></>
    </SettingsLayout>
  );
}
