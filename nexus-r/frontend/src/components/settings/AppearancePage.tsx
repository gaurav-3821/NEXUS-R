import { useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAppearanceStore } from '../../store/appearanceStore';
import { SettingsLayout } from '../layout/SettingsLayout';
import { PageHeader } from '../ui/PageHeader';
import { SearchBar } from '../ui/SearchBar';
import { SettingsNavigation } from './ui/SettingsNavigation';
import { SettingsCard } from './ui/SettingsCard';
import { ToggleRow } from './ui/ToggleRow';
import { 
  Settings, Box, Key, Palette, Wrench, Database, Shield, Zap, Code, Link, CloudOff, Info, 
  RefreshCw, Sun, Moon, Monitor, Sliders, Check, Download, Upload, ArrowRight, LayoutTemplate, 
  Palette as PaletteIcon, Type, MousePointer2
} from 'lucide-react';
import clsx from 'clsx';

const accentColors = [
  '#4f46e5', // Indigo (Default)
  '#0ea5e9', // Sky
  '#10b981', // Emerald
  '#84cc16', // Lime
  '#eab308', // Yellow
  '#f97316', // Orange
  '#ef4444', // Red
  '#ec4899', // Pink
  '#8b5cf6', // Violet
];

export default function AppearancePage() {
  const navigate = useNavigate();
  const location = useLocation();
  const activeTab = location.pathname.split('/').pop() || 'appearance';

  const { themeMode, accentColor, compactMode, highContrast, reduceAnimations, sidebarTransparency, showResponseMetadata, loadSettings, updateSetting, importTheme, exportTheme, resetToDefaults } = useAppearanceStore();

  useEffect(() => {
    loadSettings();
  }, [loadSettings]);

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
      onTabChange={(id) => navigate(`/settings/${id}`)} 
      footerAction={
        <button 
          onClick={resetToDefaults}
          className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl text-sm font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-slate-800 transition-colors"
        >
          <RefreshCw size={14} />
          Restore Defaults
        </button>
      }
    />
  );

  const rightPanel = (
    <div className="space-y-6">
      {/* Appearance Preview */}
      <SettingsCard title="Appearance Preview" subtitle="See how NEXUS-R will look with your settings.">
        <div className="rounded-xl overflow-hidden border border-gray-200 dark:border-slate-700 shadow-sm bg-gray-50 dark:bg-slate-900">
          <div className="h-6 bg-gray-100 dark:bg-slate-800 border-b border-gray-200 dark:border-slate-700 flex items-center px-3 gap-1.5">
            <div className="w-2.5 h-2.5 rounded-full bg-red-400"></div>
            <div className="w-2.5 h-2.5 rounded-full bg-amber-400"></div>
            <div className="w-2.5 h-2.5 rounded-full bg-green-400"></div>
          </div>
          <div className="flex h-40">
            {/* Sidebar Mockup */}
            <div className="w-16 bg-[#1a1b26] border-r border-gray-800 p-2 flex flex-col items-center gap-3">
              <div className="w-6 h-6 rounded-full bg-accent-500 mb-2"></div>
              <div className="w-5 h-1.5 rounded-full bg-gray-700"></div>
              <div className="w-8 h-1.5 rounded-full bg-gray-700"></div>
              <div className="w-6 h-1.5 rounded-full bg-gray-700"></div>
              <div className="w-7 h-1.5 rounded-full bg-gray-700"></div>
              <div className="w-5 h-1.5 rounded-full bg-gray-700"></div>
            </div>
            {/* Content Mockup */}
            <div className="flex-1 bg-white p-3 flex flex-col">
              <div className="flex gap-2 mb-3">
                <div className="w-5 h-5 rounded-full bg-gray-200 shrink-0"></div>
                <div className="w-24 h-12 rounded-lg bg-gray-100 rounded-tl-none"></div>
              </div>
              <div className="flex gap-2 mb-3 self-end">
                <div className="w-20 h-10 rounded-lg bg-accent-50 text-accent-600 flex items-center justify-center rounded-tr-none border border-accent-100">
                  <Code size={14} />
                </div>
                <div className="w-5 h-5 rounded-full bg-accent-500 shrink-0"></div>
              </div>
              <div className="mt-auto">
                <div className="h-8 rounded-full border border-gray-200 bg-gray-50 flex items-center px-3 justify-between">
                  <div className="w-16 h-1.5 rounded-full bg-gray-300"></div>
                  <div className="w-5 h-5 rounded-full bg-accent-500 flex items-center justify-center">
                    <ArrowRight size={10} className="text-white" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </SettingsCard>

      {/* Quick Actions */}
      <SettingsCard title="Quick Actions">
        <div className="space-y-2">
            <button 
              onClick={resetToDefaults}
              className="w-full py-2.5 px-4 bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl text-sm font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-slate-800 flex items-center gap-3 transition-colors text-left"
            >
              <RefreshCw size={16} /> Reset to Defaults
            </button>
            <button 
              onClick={importTheme}
              className="w-full py-2.5 px-4 bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl text-sm font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-slate-800 flex items-center gap-3 transition-colors text-left"
            >
              <Download size={16} /> Import Theme
            </button>
            <button 
              onClick={exportTheme}
              className="w-full py-2.5 px-4 bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl text-sm font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-slate-800 flex items-center gap-3 transition-colors text-left"
            >
              <Upload size={16} /> Export Theme
            </button>
            <button className="w-full py-2.5 px-4 bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl text-sm font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-slate-800 flex items-center gap-3 transition-colors text-left">
              <PaletteIcon size={16} /> Get More Themes
            </button>
        </div>
      </SettingsCard>

      {/* Current Theme Details */}
      <SettingsCard title="Current Theme Details">
        <div className="space-y-3">
          <DetailRow label="Mode" value={themeMode.charAt(0).toUpperCase() + themeMode.slice(1)} />
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600 dark:text-gray-400 font-medium">Accent Color</span>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full" style={{ backgroundColor: accentColor }}></div>
              <span className="font-bold text-gray-900 dark:text-gray-100">{accentColor.toUpperCase()}</span>
            </div>
          </div>
          <DetailRow label="Font" value="Inter" />
          <DetailRow label="Density" value={compactMode ? 'Compact' : 'Comfortable'} />
          <DetailRow label="Updated" value={new Date().toLocaleString([], { dateStyle: 'short', timeStyle: 'short' }).replace(',', '')} />
        </div>
      </SettingsCard>
    </div>
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
        className="px-8 py-2.5 rounded-full text-sm font-bold bg-accent-600 text-white hover:bg-accent-700 shadow-md flex items-center gap-2 transition-all"
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
      isOverlay={false}
    >
      <div className="animate-in fade-in slide-in-from-bottom-2 h-full flex flex-col w-full">
        
        {/* Main Content Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-accent-50 text-accent-600 flex items-center justify-center">
              <PaletteIcon size={20} />
            </div>
            <div>
              <h3 className="text-xl font-bold text-gray-900 dark:text-gray-100">Appearance</h3>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400 mt-0.5">Customize how NEXUS-R looks and feels.</p>
            </div>
          </div>
        </div>

        {/* Detail Tabs */}
        <div className="flex gap-6 border-b border-gray-100 dark:border-slate-800 mb-8 overflow-x-auto pb-1 scrollbar-hide">
          <button className="pb-2 text-sm font-bold text-accent-600 border-b-2 border-accent-600 whitespace-nowrap">Theme</button>
          <button className="pb-2 text-sm font-bold text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 whitespace-nowrap">Layout</button>
          <button className="pb-2 text-sm font-bold text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 whitespace-nowrap">Chat Interface</button>
          <button className="pb-2 text-sm font-bold text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 whitespace-nowrap">Typography</button>
          <button className="pb-2 text-sm font-bold text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 whitespace-nowrap">Colors</button>
          <button className="pb-2 text-sm font-bold text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 whitespace-nowrap">Icons & Logos</button>
        </div>

        {/* Theme Mode Section */}
        <div className="mb-8">
          <h4 className="text-[15px] font-bold text-gray-900 dark:text-gray-100 mb-1">Theme Mode</h4>
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-4">Choose your preferred theme for the application.</p>
          
          <div className="grid grid-cols-4 gap-4">
            <ThemeCard 
              title="Light" 
              description="Clean and bright light theme"
              icon={<Sun size={14} />}
              active={themeMode === 'light'}
              onClick={() => updateSetting('themeMode', 'light')}
              preview={
                <div className="w-full h-16 bg-white border border-gray-200 rounded-lg p-2 flex flex-col gap-1.5">
                  <div className="flex gap-1 items-center">
                    <div className="w-2 h-2 rounded-full bg-gray-200"></div>
                    <div className="w-2 h-2 rounded-full bg-gray-200"></div>
                    <div className="w-2 h-2 rounded-full bg-gray-200"></div>
                  </div>
                  <div className="flex-1 rounded border border-gray-100 bg-gray-50"></div>
                </div>
              }
            />
            <ThemeCard 
              title="Dark" 
              description="Easy on the eyes dark theme"
              icon={<Moon size={14} />}
              active={themeMode === 'dark'}
              onClick={() => updateSetting('themeMode', 'dark')}
              preview={
                <div className="w-full h-16 bg-[#1a1b26] border border-gray-700 rounded-lg p-2 flex flex-col gap-1.5">
                  <div className="flex gap-1 items-center">
                    <div className="w-2 h-2 rounded-full bg-gray-700"></div>
                    <div className="w-2 h-2 rounded-full bg-gray-700"></div>
                    <div className="w-2 h-2 rounded-full bg-gray-700"></div>
                  </div>
                  <div className="flex-1 rounded border border-gray-800 bg-[#24283b]"></div>
                </div>
              }
            />
            <ThemeCard 
              title="System" 
              description="Use system preference automatically"
              icon={<Monitor size={14} />}
              active={themeMode === 'system'}
              onClick={() => updateSetting('themeMode', 'system')}
              preview={
                <div className="w-full h-16 flex rounded-lg overflow-hidden border border-gray-200">
                  <div className="w-1/2 h-full bg-white p-2 flex flex-col gap-1.5 border-r border-gray-200">
                    <div className="flex gap-1 items-center">
                      <div className="w-2 h-2 rounded-full bg-gray-200"></div>
                      <div className="w-2 h-2 rounded-full bg-gray-200"></div>
                    </div>
                    <div className="flex-1 rounded border border-gray-100 bg-gray-50"></div>
                  </div>
                  <div className="w-1/2 h-full bg-[#1a1b26] p-2 flex flex-col gap-1.5 border-l border-gray-700">
                     <div className="flex gap-1 items-center justify-end">
                      <div className="w-2 h-2 rounded-full bg-gray-700"></div>
                      <div className="w-2 h-2 rounded-full bg-gray-700"></div>
                    </div>
                    <div className="flex-1 rounded border border-gray-800 bg-[#24283b]"></div>
                  </div>
                </div>
              }
            />
          </div>
        </div>

        {/* Accent Color Section */}
        <div className="mb-8">
          <h4 className="text-[15px] font-bold text-gray-900 dark:text-gray-100 mb-1">Accent Color</h4>
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-4">Choose the primary color used across NEXUS-R.</p>
          
          <div className="flex gap-3 items-center">
            {accentColors.map((color) => (
              <button
                key={color}
                onClick={() => updateSetting('accentColor', color)}
                className={clsx(
                  "w-8 h-8 rounded-full flex items-center justify-center transition-transform hover:scale-110",
                  accentColor === color ? "ring-2 ring-offset-2" : ""
                )}
                style={{ 
                  backgroundColor: color,
                  '--tw-ring-color': color
                } as any}
              >
                {accentColor === color && <Check size={14} className="text-white" />}
              </button>
            ))}
            <button className="w-8 h-8 rounded-full flex items-center justify-center border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 ml-2 hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors shadow-sm">
              <div className="w-4 h-4 rounded-full bg-gradient-to-br from-blue-500 via-purple-500 to-pink-500"></div>
            </button>
          </div>
        </div>

        {/* Theme Settings Section */}
        <div>
          <h4 className="text-[15px] font-bold text-gray-900 dark:text-gray-100 mb-1">Theme Settings</h4>
          
          <div className="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl shadow-sm overflow-hidden mt-4">
            <ToggleRow 
              label="Follow system theme" 
              description="Automatically switch between light and dark based on system settings." 
              checked={themeMode === 'system'} 
              onChange={(c) => updateSetting('themeMode', c ? 'system' : 'light')} 
              icon={<Monitor size={16} className="text-gray-500 dark:text-gray-400" />}
              className="border-b border-gray-100 dark:border-slate-800 last:border-0"
              variant="plane"
            />
            
            <ToggleRow 
              label="Sidebar translucent" 
              description="Apply a translucent effect to the sidebar." 
              checked={sidebarTransparency} 
              onChange={(c) => updateSetting('sidebarTransparency', c)} 
              icon={<LayoutTemplate size={16} className="text-gray-500 dark:text-gray-400" />}
              className="border-b border-gray-100 last:border-0"
            />
            
            <ToggleRow 
              label="Reduce animations" 
              description="Minimize animations for a smoother experience." 
              checked={reduceAnimations} 
              onChange={(c) => updateSetting('reduceAnimations', c)} 
              icon={<MousePointer2 size={16} className="text-gray-500 dark:text-gray-400" />}
              className="border-b border-gray-100 last:border-0"
            />

            <ToggleRow 
              label="Compact mode" 
              description="Reduce spacing and padding for a more compact interface." 
              checked={compactMode} 
              onChange={(c) => updateSetting('compactMode', c)} 
              icon={<Sliders size={16} className="text-gray-500 dark:text-gray-400" />}
              className="border-b border-gray-100 last:border-0"
            />

            <ToggleRow 
              label="High contrast" 
              description="Increase contrast for better readability." 
              checked={highContrast} 
              onChange={(c) => updateSetting('highContrast', c)} 
              icon={<Type size={16} className="text-gray-500 dark:text-gray-400" />}
              className="border-b border-gray-100 last:border-0"
            />

            <ToggleRow 
              label="Show Response Metadata" 
              description="Display actual model, route, provider, latency, and cost for every response." 
              checked={showResponseMetadata} 
              onChange={(c) => updateSetting('showResponseMetadata', c)} 
              icon={<Info size={16} className="text-gray-500 dark:text-gray-400" />}
              className="border-b border-gray-100 last:border-0"
            />
          </div>
        </div>

      </div>
    </SettingsLayout>
  );
}

// Subcomponents

function ThemeCard({ title, description, icon, active, onClick, preview }: {
  title: string, description: string, icon: React.ReactNode, active: boolean, onClick: () => void, preview: React.ReactNode
}) {
  return (
    <div 
      onClick={onClick}
      className={clsx(
        "relative p-4 rounded-xl border transition-all cursor-pointer flex flex-col h-full",
        active ? "bg-accent-50/30 border-accent-500 shadow-sm ring-1 ring-accent-500" : "bg-white dark:bg-slate-900 border-gray-200 dark:border-slate-800 hover:border-gray-300 dark:hover:border-slate-600 hover:bg-gray-50 dark:hover:bg-slate-800 shadow-sm"
      )}
    >
      <div className="flex items-center gap-2 mb-3 text-gray-700 dark:text-gray-300">
        {icon}
        <h5 className="font-bold text-sm text-gray-900 dark:text-gray-100">{title}</h5>
      </div>
      
      <div className="mb-4">
        {preview}
      </div>

      <p className="text-xs font-medium text-gray-500 dark:text-gray-400 leading-relaxed mb-4 flex-1">{description}</p>
      
      <div className="flex items-center justify-end mt-auto">
        <div className={clsx(
          "w-4 h-4 rounded-full border-2 flex items-center justify-center",
          active ? "border-accent-600" : "border-gray-300 dark:border-slate-600"
        )}>
          {active && <div className="w-2 h-2 rounded-full bg-accent-600"></div>}
        </div>
      </div>
    </div>
  );
}

function DetailRow({ label, value }: { label: string, value: string }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-gray-600 dark:text-gray-400 font-medium">{label}</span>
      <span className="font-bold text-gray-900 dark:text-gray-100">{value}</span>
    </div>
  );
}
