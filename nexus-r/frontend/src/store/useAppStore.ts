import { create } from 'zustand';
import { apiPost, apiUrl } from '../api/client';

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  streaming?: boolean;
  cost?: number;
  latency?: number;
  time?: number;
  model?: string;
  auto_model?: string;
  auto_model_reason?: string;
}

export interface Conversation {
  id: string;
  title: string;
  updated_at: string;
}

interface AppState {
  currentConversationId: string | null;
  conversations: Conversation[];
  messages: Message[];
  attachedImages: string[];
  streamingMsgId: string | null;
  isMonitorOpen: boolean;
  isSidebarOpen: boolean;
  isSettingsOpen: boolean;
  
  // Dev Monitor Metrics
  workflowState: string;
  workflowStage: string;
  tokenSpeed: string;
  executionTime: string;
  activeTools: string;
  totalSessionCost: number;
  reasoningTrace: string;

  // Actions
  setCurrentConversation: (id: string | null) => void;
  addMessage: (msg: Message) => void;
  updateMessage: (id: string, updates: Partial<Message>) => void;
  setAttachedImages: (images: string[]) => void;
  setConversations: (convs: Conversation[]) => void;
  setStreamingMsgId: (id: string | null) => void;
  toggleMonitor: () => void;
  toggleSidebar: () => void;
  setSettingsOpen: (isOpen: boolean) => void;
  
  // Domain actions
  sendChatMessage: (content: string) => Promise<void>;
  interruptChat: () => Promise<void>;
}

export const useAppStore = create<AppState>((set, get) => ({
  currentConversationId: null,
  conversations: [],
  messages: [{
    id: 'welcome',
    role: 'assistant',
    content: 'Select a conversation or start a new chat.'
  }],
  attachedImages: [],
  streamingMsgId: null,
  isMonitorOpen: true,
  isSidebarOpen: true,
  isSettingsOpen: false,
  
  workflowState: 'idle',
  workflowStage: 'Ready',
  tokenSpeed: '0.0 tok/s',
  executionTime: '0.0s',
  activeTools: 'None',
  totalSessionCost: 0,
  reasoningTrace: 'No active reasoning trace.',

  setCurrentConversation: (id) => set({ currentConversationId: id }),
  addMessage: (msg) => set((state) => ({ messages: [...state.messages, msg] })),
  updateMessage: (id, updates) => set((state) => ({
    messages: state.messages.map(m => m.id === id ? { ...m, ...updates } : m)
  })),
  setAttachedImages: (images) => set({ attachedImages: images }),
  setConversations: (convs) => set({ conversations: convs }),
  setStreamingMsgId: (id) => set({ streamingMsgId: id }),
  toggleMonitor: () => set((state) => ({ isMonitorOpen: !state.isMonitorOpen })),
  toggleSidebar: () => set((state) => ({ isSidebarOpen: !state.isSidebarOpen })),
  setSettingsOpen: (isOpen) => set({ isSettingsOpen: isOpen }),

  sendChatMessage: async (content: string) => {
    const state = get();
    if (!content.trim()) return;
    
    // Clear initial welcome message if present
    if (state.messages.length === 1 && state.messages[0].id === 'welcome') {
      set({ messages: [] });
    }

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
      time: Date.now()
    };
    
    set((s) => ({
      messages: [...s.messages, userMsg],
      workflowState: 'reasoning',
      workflowStage: 'thinking',
      tokenSpeed: '0.0 tok/s',
      executionTime: '0.0s',
      activeTools: 'None',
      reasoningTrace: 'No active reasoning trace.',
    }));

    try {
      const body: any = { message: content };
      if (state.currentConversationId) body.conversation_id = state.currentConversationId;
      if (state.attachedImages.length > 0) body.images = state.attachedImages;
      
      set({ attachedImages: [] });

      const response = await fetch(apiUrl("/chat"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });
      
      if (!response.ok) {
        throw new Error(await response.text());
      }
      
      const data = await response.json();
      
      if (!state.currentConversationId && data.conversation_id) {
        set({ currentConversationId: data.conversation_id });
        // Fetch conversations again or dispatch event
      }
      
      if (data.status === "processing") {
        set({ streamingMsgId: data.message_id });
        
        const skeletonMsg: Message = {
          id: data.message_id,
          role: 'assistant',
          content: '...', // Handled by UI to show skeleton loader
          streaming: true,
        };
        set((s) => ({ messages: [...s.messages, skeletonMsg] }));
      }
    } catch (e: any) {
      const errorMsg: Message = {
        id: Date.now().toString(),
        role: 'assistant',
        content: `Error: ${e.message}`
      };
      set((s) => ({ messages: [...s.messages, errorMsg] }));
    }
  },

  interruptChat: async () => {
    const state = get();
    if (!state.streamingMsgId) return;
    try {
      set((s) => ({
        messages: s.messages.map(m => m.id === state.streamingMsgId ? {
          ...m,
          streaming: false,
          content: m.content + '\n\n*Generation interrupted by user.*'
        } : m),
        streamingMsgId: null,
        workflowState: 'idle',
        workflowStage: 'Finalized'
      }));
      await apiPost("/chat/interrupt", { message_id: state.streamingMsgId });
    } catch (e) {
      console.error(e);
    }
  }
}));
