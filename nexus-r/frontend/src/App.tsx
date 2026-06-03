import { useEffect, Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAppStore } from './store/useAppStore';
import { useAppearanceStore } from './store/appearanceStore';
import Sidebar from './components/sidebar/Sidebar';
import { WS_URL } from './api/client';

// Lazy load components
const ChatMain = lazy(() => import('./components/chat/ChatMain'));
const GeneralPage = lazy(() => import('./components/settings/GeneralPage'));
const ProvidersPage = lazy(() => import('./components/settings/ProvidersPage'));
const ModelsPage = lazy(() => import('./components/settings/ModelsPage'));
const MemoryPage = lazy(() => import('./components/settings/MemoryPage'));
const PerformancePage = lazy(() => import('./components/settings/PerformancePage'));
const AppearancePage = lazy(() => import('./components/settings/AppearancePage'));
const PlaceholderPage = lazy(() => import('./components/settings/PlaceholderPage'));

function App() {
  const { isSidebarOpen, loadConversations } = useAppStore();
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
      <div className="flex h-screen w-full bg-[#f8fafc] dark:bg-slate-950 overflow-hidden text-[#111827] dark:text-slate-100">
        {/* Sidebar */}
        {isSidebarOpen && (
          <div className="w-[280px] flex-shrink-0 border-r border-gray-100 dark:border-slate-800 z-10 hidden md:block">
            <Sidebar />
          </div>
        )}

        {/* Main Chat Area */}
        <div className="flex-1 flex flex-col min-w-0 bg-[#f8fafc] dark:bg-slate-950 relative">
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
