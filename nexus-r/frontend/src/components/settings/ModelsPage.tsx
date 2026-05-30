import { useState } from 'react';
import { useAppStore } from '../../store/useAppStore';
import { SettingsLayout } from '../layout/SettingsLayout';
import { PageHeader } from '../ui/PageHeader';
import { SearchBar } from '../ui/SearchBar';
import { SettingsNavigation } from './ui/SettingsNavigation';
import { SettingsCard } from './ui/SettingsCard';
import { 
  Settings, Box, Key, Palette, Wrench, Database, Shield, Zap, Code, Link, CloudOff, Info, 
  RefreshCw, ArrowLeft, Download, Brain, Code2, MessageSquare, Layers, Network, ArrowDown, ChevronDown
} from 'lucide-react';
import clsx from 'clsx';

export default function ModelsPage() {
  const { setSettingsOpen } = useAppStore();
  const [activeTab, setActiveTab] = useState('default-model');

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
      onTabChange={setActiveTab} 
      footerAction={
        <button className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-white border border-gray-200 rounded-xl text-sm font-semibold text-gray-700 hover:bg-gray-50 transition-colors">
          <RefreshCw size={14} />
          Restore Defaults
        </button>
      }
    />
  );

  const rightPanel = (
    <div className="space-y-6">
      {/* Routing Preview Card */}
      <SettingsCard title="Routing Preview" subtitle="See how your message will be routed">
        <div className="bg-white border border-gray-100 rounded-xl p-4 shadow-sm text-sm font-medium text-gray-800 relative z-10">
          How do I implement authentication in React with TypeScript?
        </div>
        
        <div className="flex justify-center -mt-2 mb-2 relative z-0">
          <ArrowDown size={16} className="text-gray-300" />
        </div>

        <div className="bg-[#f0fdf4] border border-[#bbf7d0] rounded-xl p-4">
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-lg bg-emerald-500 text-white flex items-center justify-center shrink-0 shadow-sm">
              <Code2 size={16} />
            </div>
            <div>
              <div className="text-sm font-bold text-gray-900 leading-tight">Will route to Coding Model</div>
              <div className="text-sm font-bold text-gray-900 leading-tight">Claude 3.5 Sonnet</div>
              <p className="text-xs font-medium text-gray-600 mt-2 leading-relaxed">
                Best for coding and technical implementation tasks.
              </p>
            </div>
          </div>
        </div>

        <div className="mt-4 pt-4 border-t border-gray-100">
          <button className="text-sm font-bold text-indigo-600 hover:text-indigo-700 flex items-center gap-1.5 transition-colors">
            Test another message &rarr;
          </button>
        </div>
      </SettingsCard>

      {/* Model Summary Card */}
      <SettingsCard title="Model Summary" subtitle="Your current model configuration">
        <div className="space-y-3">
          <SummaryRow icon={<Network size={14} className="text-indigo-500" />} label="Router" value="all-MiniLM-L6-v2" />
          <SummaryRow icon={<Brain size={14} className="text-purple-500" />} label="Reasoning" value="GPT-4o" />
          <SummaryRow icon={<Code2 size={14} className="text-emerald-500" />} label="Coding" value="Claude 3.5 Sonnet" />
          <SummaryRow icon={<MessageSquare size={14} className="text-blue-500" />} label="General" value="Llama 3 70B" />
          <SummaryRow icon={<Layers size={14} className="text-orange-500" />} label="Embedding" value="text-embedding-3-small" />
        </div>
      </SettingsCard>
    </div>
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
      rightPanel={rightPanel}
      footer={footer}
      isOverlay={true}
    >
      <div className="animate-in fade-in slide-in-from-bottom-2 h-full flex flex-col w-full">
        
        {/* Main Content Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <button className="text-gray-400 hover:text-gray-600 transition-colors">
              <ArrowLeft size={20} />
            </button>
            <div>
              <h3 className="text-xl font-bold text-gray-900">Default Model</h3>
              <p className="text-sm font-medium text-gray-500 mt-0.5">Configure which models are used for different tasks</p>
            </div>
          </div>
          <button className="text-sm font-bold text-gray-700 hover:text-gray-900 flex items-center gap-2 transition-colors">
            <RefreshCw size={14} /> Reset to Recommended
          </button>
        </div>

        {/* Sentence Transformer Section */}
        <div className="mb-8">
          <div className="flex items-center gap-2 mb-1">
            <h4 className="text-[15px] font-bold text-gray-900">Sentence Transformer (Routing Engine)</h4>
            <span className="bg-emerald-50 text-emerald-600 border border-emerald-200 text-[10px] font-bold px-2 py-0.5 rounded-full">Recommended</span>
          </div>
          <p className="text-sm font-medium text-gray-500 mb-4">Analyzes the meaning of your message and intelligently switches to the best model for optimal results.</p>
          
          <div className="border border-gray-200 rounded-xl overflow-hidden bg-white shadow-sm">
            <div className="p-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center shrink-0">
                  <Network size={16} />
                </div>
                <span className="font-bold text-gray-900">all-MiniLM-L6-v2</span>
              </div>
              
              <div className="flex items-center gap-3">
                <button className="flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-gray-50 transition-colors text-sm font-semibold text-gray-700 border border-transparent hover:border-gray-200">
                  <div className="w-1.5 h-1.5 rounded-full bg-emerald-500"></div> Active <ChevronDown size={14} className="text-gray-400" />
                </button>
                <div className="w-px h-4 bg-gray-200"></div>
                <button className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-gray-200 bg-white hover:bg-gray-50 transition-colors text-sm font-semibold text-gray-700 shadow-sm">
                  <Download size={14} /> Download
                </button>
              </div>
            </div>
            <div className="bg-indigo-50/50 px-4 py-3 flex items-center justify-between border-t border-indigo-100">
              <p className="text-xs font-bold text-indigo-600">Lightweight, fast and accurate for semantic understanding and intent detection.</p>
              <button className="text-xs font-bold text-indigo-600 hover:text-indigo-800 transition-colors flex items-center gap-1">
                Learn more &rarr;
              </button>
            </div>
          </div>
        </div>

        {/* Task Specific Models Section */}
        <div>
          <h4 className="text-[15px] font-bold text-gray-900 mb-1">Task Specific Models</h4>
          <p className="text-sm font-medium text-gray-500 mb-4">Choose the best model for each type of task. The routing engine above will decide which one to use.</p>
          
          <div className="space-y-3">
            <ModelRow 
              title="Reasoning Model" 
              description="Best for complex reasoning, problem solving and logical tasks." 
              icon={<Brain size={18} />} 
              iconColor="text-purple-600"
              iconBg="bg-purple-100"
              modelName="GPT-4o"
              recommended={true}
            />
            <ModelRow 
              title="Coding Model" 
              description="Optimized for code generation, debugging and technical tasks." 
              icon={<Code2 size={18} />} 
              iconColor="text-emerald-600"
              iconBg="bg-emerald-100"
              modelName="Claude 3.5 Sonnet"
              recommended={true}
            />
            <ModelRow 
              title="General Model" 
              description="Best for general conversations, Q&A and everyday tasks." 
              icon={<MessageSquare size={18} />} 
              iconColor="text-blue-600"
              iconBg="bg-blue-100"
              modelName="Llama 3 70B"
              recommended={true}
            />
            <ModelRow 
              title="Embedding Model" 
              description="Used for knowledge retrieval, search and semantic similarity." 
              icon={<Layers size={18} />} 
              iconColor="text-orange-600"
              iconBg="bg-orange-100"
              modelName="text-embedding-3-small"
              recommended={true}
            />
          </div>

          <div className="mt-6 bg-indigo-50/50 border border-indigo-100 rounded-xl p-3 flex gap-3 items-start">
            <Info size={16} className="text-indigo-500 shrink-0 mt-0.5" />
            <p className="text-xs font-medium text-indigo-900 leading-relaxed">
              The sentence transformer will analyze each message and route it to the most appropriate model based on its meaning and intent.
            </p>
          </div>
        </div>

      </div>
    </SettingsLayout>
  );
}

// Subcomponents

function SummaryRow({ icon, label, value }: { icon: React.ReactNode, label: string, value: string }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <div className="flex items-center gap-2 font-medium text-gray-600">
        <div className="w-5 h-5 rounded flex items-center justify-center bg-gray-50 border border-gray-100">
          {icon}
        </div>
        {label}
      </div>
      <span className="font-bold text-gray-900">{value}</span>
    </div>
  );
}

function ModelRow({ title, description, icon, iconColor, iconBg, modelName, recommended }: {
  title: string, description: string, icon: React.ReactNode, iconColor: string, iconBg: string, modelName: string, recommended?: boolean
}) {
  return (
    <div className="flex items-center justify-between p-4 bg-white border border-gray-200 rounded-xl shadow-sm hover:border-gray-300 transition-colors">
      <div className="flex items-start gap-4">
        <div className={clsx("w-10 h-10 rounded-xl flex items-center justify-center shrink-0 mt-0.5", iconBg, iconColor)}>
          {icon}
        </div>
        <div>
          <div className="flex items-center gap-2 mb-0.5">
            <h5 className="font-bold text-gray-900 text-[15px]">{title}</h5>
            {recommended && <span className="bg-emerald-50 text-emerald-600 border border-emerald-200 text-[9px] font-bold px-2 py-0.5 rounded-full tracking-wider">RECOMMENDED</span>}
          </div>
          <p className="text-[13px] font-medium text-gray-500">{description}</p>
        </div>
      </div>
      
      <div className="flex items-center gap-4 shrink-0">
        <div className="flex items-center gap-3 px-3 py-1.5 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors">
          <div className="flex items-center gap-2">
            <BotIcon />
            <span className="text-sm font-bold text-gray-900">{modelName}</span>
          </div>
          <ChevronDown size={14} className="text-gray-400 ml-2" />
        </div>
        <div className="flex items-center gap-1.5 text-xs font-bold text-gray-700 w-[70px] justify-end">
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-500"></div> Active
        </div>
        <button className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-gray-200 bg-white hover:bg-gray-50 transition-colors text-sm font-semibold text-gray-700 shadow-sm">
          <Download size={14} /> <span className="hidden xl:inline">Download</span>
        </button>
      </div>
    </div>
  );
}

// Simple fallback icon for the model dropdown
function BotIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-gray-500">
      <path d="M12 8V4H8" />
      <rect width="16" height="12" x="4" y="8" rx="2" />
      <path d="M2 14h2" />
      <path d="M20 14h2" />
      <path d="M15 13v2" />
      <path d="M9 13v2" />
    </svg>
  );
}
