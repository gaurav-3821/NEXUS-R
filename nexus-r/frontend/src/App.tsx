import { useEffect, Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAppStore } from './store/useAppStore';
import { useAppearanceStore } from './store/appearanceStore';
import Sidebar from './components/sidebar/Sidebar';
import { AnimatedHamburger } from './components/ui/AnimatedHamburger';
import { WS_URL } from './api/client';
import clsx from 'clsx';

// Lazy load components
const ChatMain = lazy(() => import('./components/chat/ChatMain'));
const GeneralPage = lazy(() => import('./components/settings/GeneralPage'));
const ProvidersPage = lazy(() => import('./components/settings/ProvidersPage'));
const ModelsPage = lazy(() => import('./components/settings/ModelsPage'));
const MemoryPage = lazy(() => import('./components/settings/MemoryPage'));
const PerformancePage = lazy(() => import('./components/settings/PerformancePage'));
const AppearancePage = lazy(() => import('./components/settings/AppearancePage'));
const AboutPage = lazy(() => import('./components/settings/AboutPage'));
const AgentToolsPage = lazy(() => import('./components/settings/AgentToolsPage'));
const AdvancedPage = lazy(() => import('./components/settings/AdvancedPage'));
const PlaceholderPage = lazy(() => import('./components/settings/PlaceholderPage'));

function App() {
  const { isSidebarOpen, toggleSidebar, loadConversations } = useAppStore();
  const loadSettings = useAppearanceStore((s) => s.loadSettings);

  useEffect(() => {
    loadConversations();
    loadSettings();
  }, [loadConversations, loadSettings]);

  useEffect(() => {
    // Basic WebSocket connection setup mirroring the original app.js
    let ws: WebSocket | null = null;
    
    const connectWs = () => {
      try {
        ws = new WebSocket(WS_URL);
        
        ws.onopen = () => {
          ws?.send(JSON.stringify({ type: "subscribe", filter: "all" }));
        };

        ws.onmessage = (evt) => {
          try {
            const msg = JSON.parse(evt.data);
            if (msg.type === "cost_update") {
              useAppStore.setState({ totalSessionCost: msg.running_total });
            }
          } catch (e) {}
        };

        ws.onclose = () => {
          setTimeout(connectWs, 3000);
        };
      } catch (e) {
        setTimeout(connectWs, 3000);
      }
    };
    
    connectWs();
    return () => ws?.close();
  }, []);

  return (
    <BrowserRouter>
      <div className="flex h-screen w-full bg-[#f8fafc] dark:bg-slate-950 overflow-hidden text-[#111827] dark:text-slate-100 relative">
        {/* Mobile Sidebar Overlay */}
        {isSidebarOpen && (
          <div 
            className="fixed inset-0 bg-black/50 z-20 md:hidden transition-opacity"
            onClick={toggleSidebar}
          />
        )}

        {/* Sidebar - slides in/out */}
        <div className={clsx(
          "absolute inset-y-0 left-0 z-30 w-[280px] bg-[#f8fafc] dark:bg-slate-950 border-r border-gray-100 dark:border-slate-800 transition-transform duration-300 ease-in-out",
          isSidebarOpen ? "translate-x-0" : "-translate-x-full"
        )}>
          <Sidebar />
        </div>

        {/* Main Chat Area */}
        <div className={clsx(
          "flex-1 flex flex-col min-w-0 bg-[#f8fafc] dark:bg-slate-950 relative transition-[margin] duration-300 ease-in-out",
          isSidebarOpen && "md:ml-[280px]"
        )}>
          {/* Hamburger toggle — visible when sidebar is closed */}
          {!isSidebarOpen && (
            <div className="absolute top-3 left-3 z-30">
              <AnimatedHamburger isOpen={false} onClick={toggleSidebar} />
            </div>
          )}
          <Suspense fallback={<div className="flex-1 flex items-center justify-center text-gray-500">Loading...</div>}>
            <Routes>
              <Route path="/" element={<ChatMain />} />
              <Route path="/settings" element={<Navigate to="/settings/general" replace />} />
              <Route path="/settings/general" element={<GeneralPage />} />
              <Route path="/settings/api-keys" element={<ProvidersPage />} />
              <Route path="/settings/models" element={<ModelsPage />} />
              <Route path="/settings/memory" element={<MemoryPage />} />
              <Route path="/settings/performance" element={<PerformancePage />} />
              <Route path="/settings/appearance" element={<AppearancePage />} />
              <Route path="/settings/about" element={<AboutPage />} />
              <Route path="/settings/agent-tools" element={<AgentToolsPage />} />
              <Route path="/settings/advanced" element={<AdvancedPage />} />
              <Route path="/settings/:section" element={<PlaceholderPage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
        </div>
      </div>
    </BrowserRouter>
  );
}

export default App;
