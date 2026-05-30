import { useEffect } from 'react';
import { useAppStore } from './store/useAppStore';
import Sidebar from './components/sidebar/Sidebar';
import ChatMain from './components/chat/ChatMain';
import SettingsModal from './components/settings/SettingsModal';
import { WS_URL } from './api/client';

function App() {
  const { isSidebarOpen, isSettingsOpen } = useAppStore();

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
    <div className="flex h-screen w-full bg-[#f8fafc] overflow-hidden text-[#111827]">
      {/* Sidebar */}
      {isSidebarOpen && (
        <div className="w-[280px] flex-shrink-0 bg-white border-r border-gray-100 z-10 hidden md:block">
          <Sidebar />
        </div>
      )}

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-w-0 bg-[#f8fafc] relative">
        {!isSettingsOpen ? (
          <ChatMain />
        ) : (
          <SettingsModal />
        )}
      </div>
    </div>
  );
}

export default App;
