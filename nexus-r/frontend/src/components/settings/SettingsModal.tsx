import { useAppStore } from '../../store/useAppStore';
import { Settings, Box, Key, Palette, Wrench, Database, Shield, Zap, Code, Link, CloudOff, Info, RefreshCw, Upload, Download, Trash2, Search } from 'lucide-react';
import clsx from 'clsx';
import { useState } from 'react';

export default function SettingsModal() {
  const { setSettingsOpen } = useAppStore();
  const [activeTab, setActiveTab] = useState('general');

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

  return (
    <div className="absolute inset-0 bg-[#f8fafc] z-40 flex flex-col animate-in fade-in duration-200 text-[#111827]">
      {/* Header */}
      <div className="flex items-center justify-between px-8 py-5 border-b border-gray-200 bg-white">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Settings</h2>
          <p className="text-sm text-gray-500 font-medium mt-1">Manage NEXUS-R configuration and preferences</p>
        </div>
        <div className="relative">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input 
            type="text" 
            placeholder="Search settings..." 
            className="pl-9 pr-12 py-2.5 bg-gray-50 border border-gray-200 rounded-lg text-sm w-64 outline-none focus:border-indigo-300 focus:ring-2 focus:ring-indigo-100 transition-all"
          />
          <div className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] font-semibold text-gray-400 bg-white border border-gray-200 px-1.5 py-0.5 rounded shadow-sm">
            Ctrl /
          </div>
        </div>
      </div>

      {/* Body */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <div className="w-[280px] border-r border-gray-200 bg-white py-4 px-3 flex flex-col gap-1 overflow-y-auto">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={clsx(
                "flex items-center justify-between px-4 py-3 rounded-xl text-[15px] font-semibold transition-all group",
                activeTab === tab.id 
                  ? "bg-indigo-50 text-indigo-600" 
                  : "text-gray-700 hover:bg-gray-50"
              )}
            >
              <div className="flex items-center gap-4">
                <span className={activeTab === tab.id ? "text-indigo-600" : "text-gray-400 group-hover:text-gray-600"}>{tab.icon}</span>
                {tab.label}
              </div>
              {tab.badge && (
                <span className="bg-indigo-100 text-indigo-600 text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider">{tab.badge}</span>
              )}
              {activeTab === tab.id && !tab.badge && (
                <div className="w-1.5 h-1.5 rounded-full bg-indigo-600"></div>
              )}
            </button>
          ))}
          
          <div className="mt-auto pt-6 px-4">
            <button className="flex items-center gap-2 text-sm font-semibold text-gray-500 hover:text-gray-800 transition-colors">
              <RefreshCw size={14} />
              Restore Defaults
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 p-8 overflow-y-auto bg-[#f8fafc] flex gap-8">
          
          {/* Main Settings Form */}
          <div className="flex-1 max-w-3xl">
            {activeTab === 'general' && (
              <div className="space-y-8 animate-in fade-in slide-in-from-bottom-2">
                
                {/* General Section */}
                <div>
                  <h3 className="text-lg font-bold text-gray-900 mb-1">General</h3>
                  <p className="text-sm text-gray-500 font-medium mb-6">Basic application settings and preferences.</p>
                  
                  <div className="space-y-6">
                    <div className="flex items-center justify-between py-2 border-b border-gray-100">
                      <div>
                        <div className="text-[15px] font-semibold text-gray-800">App Name</div>
                        <div className="text-[13px] text-gray-500 mt-0.5">Customize your application name</div>
                      </div>
                      <input type="text" defaultValue="NEXUS-R" className="w-48 bg-white border border-gray-200 rounded-lg px-3 py-2 text-sm font-medium outline-none focus:border-indigo-400" />
                    </div>

                    <div className="flex items-center justify-between py-2 border-b border-gray-100">
                      <div>
                        <div className="text-[15px] font-semibold text-gray-800">Default Language</div>
                        <div className="text-[13px] text-gray-500 mt-0.5">Choose your preferred language</div>
                      </div>
                      <select className="w-48 bg-white border border-gray-200 rounded-lg px-3 py-2 text-sm font-medium outline-none focus:border-indigo-400 appearance-none">
                        <option>English</option>
                      </select>
                    </div>

                    <div className="flex items-center justify-between py-2 border-b border-gray-100">
                      <div>
                        <div className="text-[15px] font-semibold text-gray-800">Auto Save Conversations</div>
                        <div className="text-[13px] text-gray-500 mt-0.5">Automatically save your conversations</div>
                      </div>
                      <Toggle checked={true} />
                    </div>

                    <div className="flex items-center justify-between py-2 border-b border-gray-100">
                      <div>
                        <div className="text-[15px] font-semibold text-gray-800">Auto Generate Chat Titles</div>
                        <div className="text-[13px] text-gray-500 mt-0.5">Generate titles for new conversations automatically</div>
                      </div>
                      <Toggle checked={true} />
                    </div>

                    <div className="flex items-center justify-between py-2 border-b border-gray-100">
                      <div>
                        <div className="text-[15px] font-semibold text-gray-800">Auto Update Models List</div>
                        <div className="text-[13px] text-gray-500 mt-0.5">Automatically check for new models and updates</div>
                      </div>
                      <Toggle checked={true} />
                    </div>
                  </div>
                </div>

                {/* Chat Behavior Section */}
                <div className="pt-4">
                  <h3 className="text-lg font-bold text-gray-900 mb-6">Chat Behavior</h3>
                  
                  <div className="space-y-6">
                    <div className="flex items-center justify-between py-2 border-b border-gray-100">
                      <div>
                        <div className="text-[15px] font-semibold text-gray-800">Stream Responses</div>
                        <div className="text-[13px] text-gray-500 mt-0.5">Display responses in real-time</div>
                      </div>
                      <Toggle checked={true} />
                    </div>

                    <div className="flex items-center justify-between py-2 border-b border-gray-100">
                      <div>
                        <div className="text-[15px] font-semibold text-gray-800">Markdown Rendering</div>
                        <div className="text-[13px] text-gray-500 mt-0.5">Render markdown in messages</div>
                      </div>
                      <Toggle checked={true} />
                    </div>

                    <div className="flex items-center justify-between py-2 border-b border-gray-100">
                      <div>
                        <div className="text-[15px] font-semibold text-gray-800">Code Syntax Highlighting</div>
                        <div className="text-[13px] text-gray-500 mt-0.5">Highlight code blocks</div>
                      </div>
                      <Toggle checked={true} />
                    </div>

                    <div className="flex items-center justify-between py-2 border-b border-gray-100">
                      <div>
                        <div className="text-[15px] font-semibold text-gray-800">Show Token Usage</div>
                        <div className="text-[13px] text-gray-500 mt-0.5">Display token count for messages</div>
                      </div>
                      <Toggle checked={false} />
                    </div>
                  </div>
                </div>

              </div>
            )}
          </div>

          {/* Right Sidebar Widget Column */}
          <div className="w-[320px] shrink-0 space-y-6">
            
            {/* Model Status Card */}
            <div className="bg-white border border-gray-200 rounded-2xl p-5 shadow-sm">
              <h4 className="font-bold text-gray-900 mb-1">Model Status</h4>
              <p className="text-xs text-gray-500 font-medium mb-4">Providers and connection status</p>
              
              <div className="space-y-3">
                <StatusRow name="Ollama" status="Connected" />
                <StatusRow name="OpenAI" status="Connected" />
                <StatusRow name="Groq" status="Connected" />
                <StatusRow name="OpenRouter" status="Offline" />
                <StatusRow name="Anthropic" status="Connected" />
              </div>
            </div>

            {/* Session Overview Card */}
            <div className="bg-white border border-gray-200 rounded-2xl p-5 shadow-sm">
              <h4 className="font-bold text-gray-900 mb-1">Session Overview</h4>
              <p className="text-xs text-gray-500 font-medium mb-4">Live session statistics</p>
              
              <div className="space-y-3">
                <StatRow label="Total Messages" value="128" />
                <StatRow label="Total Tokens" value="45,231" />
                <StatRow label="Total Cost" value="$0.043" valueColor="text-green-600" />
                <StatRow label="Session Time" value="01:24:18" />
              </div>
            </div>

            {/* Quick Actions Card */}
            <div className="bg-white border border-gray-200 rounded-2xl p-5 shadow-sm">
              <h4 className="font-bold text-gray-900 mb-4">Quick Actions</h4>
              
              <div className="space-y-2">
                <button className="w-full py-2.5 px-4 bg-white border border-gray-200 rounded-xl text-sm font-semibold text-gray-700 hover:bg-gray-50 flex items-center justify-center gap-2 transition-colors">
                  <Upload size={16} /> Export Settings
                </button>
                <button className="w-full py-2.5 px-4 bg-white border border-gray-200 rounded-xl text-sm font-semibold text-gray-700 hover:bg-gray-50 flex items-center justify-center gap-2 transition-colors">
                  <Download size={16} /> Import Settings
                </button>
                <button className="w-full py-2.5 px-4 bg-red-50 border border-red-100 rounded-xl text-sm font-semibold text-red-600 hover:bg-red-100 flex items-center justify-center gap-2 transition-colors mt-2">
                  <Trash2 size={16} /> Reset All Settings
                </button>
              </div>
            </div>
            
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="bg-white border-t border-gray-200 px-8 py-4 flex items-center justify-end gap-4">
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
      </div>
    </div>
  );
}

function Toggle({ checked }: { checked?: boolean }) {
  return (
    <div className={clsx(
      "w-11 h-6 rounded-full p-1 cursor-pointer transition-colors shadow-inner flex items-center",
      checked ? "bg-[#4f46e5]" : "bg-gray-200"
    )}>
      <div className={clsx(
        "bg-white w-4 h-4 rounded-full shadow-sm transition-transform duration-300",
        checked ? "translate-x-5" : "translate-x-0"
      )} />
    </div>
  );
}

function StatusRow({ name, status }: { name: string, status: 'Connected' | 'Offline' }) {
  const isConnected = status === 'Connected';
  return (
    <div className="flex items-center justify-between text-sm">
      <div className="flex items-center gap-2 font-semibold text-gray-700">
        <span className="font-mono text-gray-400">⚡</span>
        {name}
      </div>
      <div className={clsx("font-semibold", isConnected ? "text-green-600" : "text-orange-500")}>
        {status}
      </div>
    </div>
  );
}

function StatRow({ label, value, valueColor = "text-gray-900" }: { label: string, value: string, valueColor?: string }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-gray-600 font-medium">{label}</span>
      <span className={clsx("font-bold", valueColor)}>{value}</span>
    </div>
  );
}
