import { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate, useLocation } from 'react-router-dom';
import { useModelsStore } from '../../store/modelsStore';
import { APP_NAME } from '../../constants';
import { SettingsLayout } from '../layout/SettingsLayout';
import { PageHeader } from '../ui/PageHeader';
import { SearchBar } from '../ui/SearchBar';
import { SettingsNavigation } from './ui/SettingsNavigation';
import { SettingsCard } from './ui/SettingsCard';
import ModelBadge from '../ui/ModelBadge';
import { 
  Settings, Box, Key, Palette, Wrench, Database, Shield, Zap, Code, Link, CloudOff, Info, 
  RefreshCw, ArrowLeft, Server, Globe, ChevronDown, AlertCircle, Bot
} from 'lucide-react';
import clsx from 'clsx';
import { ModelDiscoveryCenter } from './ModelDiscoveryCenter';
import { Download } from 'lucide-react';

export default function ModelsPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { 
    currentConfig, cloudOptions, localModels, routingProfile, isLoading, error, downloadJobs, providerModels,
    loadModels, updateConfig, updateRoutingProfile, startModelDownload, loadDownloadJobs, fetchProviderModels
  } = useModelsStore();
  const activeTab = location.pathname.split('/').pop() || 'models';
  const [isDownloadCenterOpen, setIsDownloadCenterOpen] = useState(false);

  useEffect(() => {
    loadModels();
    loadDownloadJobs();
    const interval = setInterval(loadDownloadJobs, 3000);
    return () => clearInterval(interval);
  }, [loadModels, loadDownloadJobs]);

  useEffect(() => {
    cloudOptions.forEach(opt => {
      if (opt.value !== 'none' && opt.api_key_configured && !providerModels[opt.value]) {
        fetchProviderModels(opt.value);
      }
    });
  }, [cloudOptions, fetchProviderModels, providerModels]);

  const allCloudModels = cloudOptions
    .filter(o => o.value !== 'none' && o.api_key_configured)
    .flatMap(o => (providerModels[o.value] || []).map(m => ({ 
      id: `${o.value}/${m.name}`, 
      label: `${m.name} (${o.label})`, 
      provider: o.value 
    })));

  const getCloudProviderForModel = (modelId: string) => {
    return allCloudModels.find(m => m.id === modelId)?.provider || null;
  };

  const getModelStatus = (modelId: string | undefined): 'available' | 'downloading' | 'unavailable' | 'none' => {
    if (!modelId) return 'none';
    if (localModels.some(m => m.name === modelId)) return 'available';
    const cloudProv = getCloudProviderForModel(modelId);
    if (cloudProv) {
      const opt = cloudOptions.find(o => o.value === cloudProv);
      return opt?.api_key_configured ? 'available' : 'unavailable';
    }
    if (downloadJobs?.find(j => j.model_name === modelId)) return 'downloading';
    return 'unavailable';
  };

  const getActionLabel = (modelId: string | undefined) => {
    if (!modelId) return undefined;
    const st = getModelStatus(modelId);
    if (st === 'available') return getCloudProviderForModel(modelId) ? 'Connected' : undefined;
    if (st === 'unavailable') return getCloudProviderForModel(modelId) ? 'Configure API Key' : 'Download';
    return undefined;
  };

  const handleAction = (modelId: string | undefined) => {
    if (!modelId) return;
    if (getCloudProviderForModel(modelId)) navigate('/settings/api-keys');
    else startModelDownload(modelId);
  };

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
      {/* Model Summary Card */}
      <SettingsCard title="Model Summary" subtitle="Your current model configuration">
        {isLoading && !currentConfig ? (
          <div className="p-4 flex justify-center">
            <div className="animate-pulse flex flex-col space-y-4 w-full">
              <div className="h-4 bg-gray-200 rounded w-1/2"></div>
              <div className="h-4 bg-gray-200 rounded w-1/3"></div>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <SummaryRow icon={<ModelBadge modelId={routingProfile?.reasoning || ''} size={14} />} label="Reasoning Model" value={routingProfile?.reasoning || 'Unknown'} />
            <SummaryRow icon={<ModelBadge modelId={routingProfile?.coding || ''} size={14} />} label="Coding Model" value={routingProfile?.coding || 'Unknown'} />
            <SummaryRow icon={<ModelBadge modelId={routingProfile?.general || ''} size={14} />} label="General Model" value={routingProfile?.general || 'Unknown'} />
            
            <div className="pt-3 mt-3 border-t border-gray-100 dark:border-slate-800 space-y-3">
              <SummaryRow icon={<Server size={14} className="text-emerald-500" />} label="Local Default" value={currentConfig?.local_model || 'Not configured'} />
              <SummaryRow icon={<Globe size={14} className="text-blue-500" />} label="Cloud Provider" value={currentConfig?.cloud_provider || 'Not configured'} />
            </div>
          </div>
        )}
      </SettingsCard>
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
      <div className="animate-in fade-in slide-in-from-bottom-2 h-full flex flex-col w-full relative">
        
        {/* Main Content Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <button className="text-gray-400 hover:text-gray-600 transition-colors">
              <ArrowLeft size={20} />
            </button>
            <div>
              <h3 className="text-xl font-bold text-gray-900 dark:text-gray-100">Models</h3>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400 mt-0.5">Configure local and cloud models</p>
            </div>
          </div>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl flex items-start gap-3">
            <AlertCircle size={20} className="text-red-500 mt-0.5 shrink-0" />
            <div>
              <h4 className="text-sm font-bold text-red-800 dark:text-red-400">Error</h4>
              <p className="text-sm text-red-600 dark:text-red-300 mt-1">{error}</p>
            </div>
          </div>
        )}

        {isLoading && !currentConfig ? (
          <div className="p-12 flex justify-center">
            <div className="w-10 h-10 border-4 border-gray-200 dark:border-slate-800 border-t-accent-500 rounded-full animate-spin"></div>
          </div>
        ) : (
          <>
            <div className="mb-8">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h4 className="text-[15px] font-bold text-gray-900 dark:text-gray-100 mb-1">Routing Pipeline</h4>
                  <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Configure models for different task categories.</p>
                </div>
              </div>
              
              <div className="space-y-3">
                <ModelSelectionRow 
                  title="Router Model" 
                  description="The model responsible for analyzing prompts and selecting the best pipeline." 
                  icon={<Bot size={18} />} 
                  iconColor="text-indigo-600"
                  iconBg="bg-indigo-100"
                  currentValue={routingProfile?.router || 'Semantic Router v1'}
                  options={[{id: 'Semantic Router v1', label: 'Semantic Router v1'}]}
                  emptyMessage="No routers available"
                  onSelect={(val) => updateRoutingProfile({ router: val })}
                  status="available"
                />
                
                <ModelSelectionRow 
                  title="Reasoning" 
                  description="Used for math, logic, and complex analytical tasks." 
                  icon={<Zap size={18} />} 
                  iconColor="text-purple-600"
                  iconBg="bg-purple-100"
                  currentValue={routingProfile?.reasoning || 'Unknown'}
                  options={[
                    ...localModels.map(m => ({ id: m.name, label: m.name })),
                    ...allCloudModels
                  ]}
                  emptyMessage="No models available"
                  onSelect={(val) => updateRoutingProfile({ reasoning: val })}
                  status={getModelStatus(routingProfile?.reasoning)}
                  actionInProgress={downloadJobs?.some(j => j.model_name === routingProfile?.reasoning)}
                  actionProgress={downloadJobs?.find(j => j.model_name === routingProfile?.reasoning)?.progress_percent}
                  actionLabel={getActionLabel(routingProfile?.reasoning)}
                  onAction={() => handleAction(routingProfile?.reasoning)}
                />

                <ModelSelectionRow 
                  title="Coding" 
                  description="Used for software development, debugging, and code generation." 
                  icon={<Code size={18} />} 
                  iconColor="text-blue-600"
                  iconBg="bg-blue-100"
                  currentValue={routingProfile?.coding || 'Unknown'}
                  options={[
                    ...localModels.map(m => ({ id: m.name, label: m.name })),
                    ...allCloudModels
                  ]}
                  emptyMessage="No models available"
                  onSelect={(val) => updateRoutingProfile({ coding: val })}
                  status={getModelStatus(routingProfile?.coding)}
                  actionInProgress={downloadJobs?.some(j => j.model_name === routingProfile?.coding)}
                  actionProgress={downloadJobs?.find(j => j.model_name === routingProfile?.coding)?.progress_percent}
                  actionLabel={getActionLabel(routingProfile?.coding)}
                  onAction={() => handleAction(routingProfile?.coding)}
                />

                <ModelSelectionRow 
                  title="General" 
                  description="Used for creative writing, chatting, and basic tasks." 
                  icon={<Palette size={18} />} 
                  iconColor="text-emerald-600"
                  iconBg="bg-emerald-100"
                  currentValue={routingProfile?.general || 'Unknown'}
                  options={[
                    ...localModels.map(m => ({ id: m.name, label: m.name })),
                    ...allCloudModels
                  ]}
                  emptyMessage="No models available"
                  onSelect={(val) => updateRoutingProfile({ general: val })}
                  status={getModelStatus(routingProfile?.general)}
                  actionInProgress={downloadJobs?.some(j => j.model_name === routingProfile?.general)}
                  actionProgress={downloadJobs?.find(j => j.model_name === routingProfile?.general)?.progress_percent}
                  actionLabel={getActionLabel(routingProfile?.general)}
                  onAction={() => handleAction(routingProfile?.general)}
                />
              </div>
            </div>

            <div className="mb-8 border-t border-gray-200 dark:border-slate-800 pt-8">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h4 className="text-[15px] font-bold text-gray-900 dark:text-gray-100 mb-1">Local Models</h4>
                  <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Choose a model to run locally on your machine for privacy and offline usage.</p>
                </div>
                <button 
                  onClick={() => setIsDownloadCenterOpen(true)}
                  className="px-4 py-2 bg-purple-50 text-purple-600 dark:bg-purple-900/20 dark:text-purple-400 rounded-lg text-sm font-bold hover:bg-purple-100 dark:hover:bg-purple-900/40 flex items-center gap-2 transition-colors shrink-0"
                >
                  <Download size={16} />
                  Download Models
                </button>
              </div>
              
              <div className="space-y-3">
                <ModelSelectionRow 
                  title="Local Model" 
                  description="Select a model available on your system via Ollama." 
                  icon={<Server size={18} />} 
                  iconColor="text-emerald-600"
                  iconBg="bg-emerald-100"
                  currentValue={currentConfig?.local_model || ''}
                  options={localModels.map(m => ({ id: m.name, label: m.name }))}
                  onSelect={(val) => updateConfig(val, currentConfig?.cloud_provider)}
                  emptyMessage="No local models found"
                />
              </div>
            </div>

            <div>
              <h4 className="text-[15px] font-bold text-gray-900 dark:text-gray-100 mb-1">Cloud Providers</h4>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-4">Select a cloud provider to use for remote inference.</p>
              
              <div className="space-y-3">
                <ModelSelectionRow 
                  title="Cloud Provider" 
                  description="Choose which provider handles remote requests." 
                  icon={<Globe size={18} />} 
                  iconColor="text-blue-600"
                  iconBg="bg-blue-100"
                  currentValue={currentConfig?.cloud_provider || ''}
                  options={cloudOptions.filter(o => o.value === 'none' || o.api_key_configured).map(o => ({ id: o.value, label: o.label }))}
                  onSelect={(val) => updateConfig(currentConfig?.local_model, val)}
                  emptyMessage="No cloud providers configured"
                />
              </div>
            </div>
          </>
        )}
      </div>
      {isDownloadCenterOpen && <ModelDiscoveryCenter onClose={() => setIsDownloadCenterOpen(false)} />}
    </SettingsLayout>
  );
}

// Subcomponents

function SummaryRow({ icon, label, value }: { icon: React.ReactNode, label: string, value: string }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <div className="flex items-center gap-2 font-medium text-gray-500 dark:text-gray-400">
        <div className="w-5 h-5 rounded flex items-center justify-center bg-gray-50 dark:bg-[#0f172a] border border-gray-200 dark:border-slate-800">
          {icon}
        </div>
        {label}
      </div>
      <span className="font-bold text-gray-600 dark:text-gray-400">{value}</span>
    </div>
  );
}

function ModelSelectionRow({ 
  title, description, icon, iconColor, iconBg, 
  currentValue, options, emptyMessage, onSelect,
  status = 'available', onAction, actionLabel, actionIcon, actionInProgress, actionProgress
}: {
  title: string, description: string, icon: React.ReactNode, iconColor: string, iconBg: string, 
  currentValue: string, options: {id: string, label: string}[], emptyMessage: string, onSelect: (val: string) => void,
  status?: 'available' | 'downloading' | 'unavailable' | 'none',
  onAction?: () => void,
  actionLabel?: string,
  actionIcon?: React.ReactNode,
  actionInProgress?: boolean,
  actionProgress?: number
}) {
  const [isOpen, setIsOpen] = useState(false);
  const activeLabel = options.find(o => o.id === currentValue)?.label || currentValue || 'None';
  const triggerRef = useRef<HTMLDivElement>(null);
  const portalRef = useRef<HTMLDivElement>(null);
  const [coords, setCoords] = useState({ top: 0, left: 0 });

  useEffect(() => {
    if (isOpen && triggerRef.current) {
      const rect = triggerRef.current.getBoundingClientRect();
      setCoords({
        top: rect.bottom + 8,
        left: rect.right - 300 // align right edge with right edge of button
      });
    }
  }, [isOpen]);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      const target = e.target as Node;
      if (
        triggerRef.current?.contains(target) ||
        portalRef.current?.contains(target)
      ) {
        return;
      }
      setIsOpen(false);
    };
    
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);
  return (
    <div className="flex flex-col p-4 bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl shadow-sm hover:border-gray-300 transition-colors relative z-20">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-start gap-4 flex-1">
          <div className={clsx("w-10 h-10 rounded-xl flex items-center justify-center shrink-0 mt-0.5", iconBg, iconColor)}>
            {icon}
          </div>
          <div>
            <div className="flex items-center gap-2 mb-0.5">
              <h5 className="font-bold text-gray-600 dark:text-gray-400 text-[15px]">{title}</h5>
            </div>
            <p className="text-[13px] font-medium text-gray-500 dark:text-gray-500">{description}</p>
          </div>
        </div>
        
        <div className="flex items-center gap-4 shrink-0 relative">
          {actionLabel && (
            <button 
              onClick={onAction}
              disabled={actionInProgress}
              className={clsx(
                "px-3 py-1.5 rounded-lg text-sm font-bold flex items-center gap-2 transition-colors border",
                actionInProgress 
                  ? "bg-gray-100 text-gray-500 border-gray-200 dark:bg-slate-800 dark:border-slate-700" 
                  : status === 'unavailable'
                    ? "bg-accent-50 text-accent-600 border-accent-100 hover:bg-accent-100 dark:bg-accent-900/20 dark:border-accent-800"
                    : "bg-emerald-50 text-emerald-600 border-emerald-100 hover:bg-emerald-100 dark:bg-emerald-900/20 dark:border-emerald-800"
              )}
            >
              {actionInProgress ? (
                <>
                  <div className="w-3.5 h-3.5 border-2 border-current border-t-transparent rounded-full animate-spin"></div>
                  {actionProgress !== undefined ? `${actionProgress}%` : 'Downloading...'}
                </>
              ) : (
                <>
                  {actionIcon}
                  {actionLabel}
                </>
              )}
            </button>
          )}

            <div className="flex flex-col items-end gap-1.5">
              <div 
                ref={triggerRef}
                onClick={() => setIsOpen(!isOpen)}
                className="flex items-center gap-3 px-3 py-1.5 border border-gray-200 dark:border-slate-800 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-800 cursor-pointer transition-colors"
              >
                <div className="flex items-center gap-2">
                  <ModelBadge modelId={currentValue} size={16} />
                  <span className="text-sm font-bold text-gray-600 dark:text-gray-400 max-w-[150px] truncate">{activeLabel}</span>
                </div>
                <ChevronDown size={14} className="text-gray-400 ml-2" />
              </div>
              
              {isOpen && createPortal(
                <div 
                  ref={portalRef}
                  className="fixed w-[300px] max-h-[300px] overflow-y-auto bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 shadow-xl rounded-xl z-[9999]"
                  style={{ top: coords.top, left: coords.left, pointerEvents: 'auto' }}
                >
                  <div className="p-2">
                    <div className="text-[10px] font-bold text-gray-400 uppercase tracking-wider px-2 py-1">Available Options</div>
                    {options.length === 0 ? (
                      <div className="text-xs text-gray-500 px-2 py-2">{emptyMessage}</div>
                    ) : (
                      options.map(opt => (
                        <button 
                          key={opt.id}
                          onClick={() => {
                            onSelect(opt.id);
                            setIsOpen(false);
                          }}
                          className={clsx(
                            "w-full text-left px-3 py-2 text-sm font-medium rounded-lg transition-colors flex items-center justify-between",
                            currentValue === opt.id
                              ? "bg-accent-50 text-accent-700" 
                              : "text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-slate-800"
                          )}
                        >
                          <span className="flex items-center gap-2 truncate">
                            <ModelBadge modelId={opt.id} size={14} />
                            {opt.label}
                          </span>
                        </button>
                      ))
                    )}
                  </div>
                </div>,
                document.body
              )}
              
            <div className="flex items-center gap-1.5 text-[11px] font-bold text-gray-500 dark:text-gray-400 pr-1 uppercase tracking-wider">
              {status === 'available' ? (
                <><div className="w-1.5 h-1.5 rounded-full bg-emerald-500"></div> Available</>
              ) : status === 'downloading' ? (
                <><div className="w-1.5 h-1.5 rounded-full bg-yellow-500"></div> Downloading</>
              ) : status === 'unavailable' ? (
                <><div className="w-1.5 h-1.5 rounded-full bg-red-500"></div> Unavailable</>
              ) : (
                <><div className="w-1.5 h-1.5 rounded-full bg-gray-300"></div> Inactive</>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

