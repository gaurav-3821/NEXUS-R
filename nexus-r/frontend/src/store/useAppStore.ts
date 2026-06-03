import { create } from 'zustand';
import { sendChat, streamChat, interruptChat, getConversations, getHistory, deleteConversation as apiDeleteConversation, clearAllConversations as apiClearAll } from '../api/chat';

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
  metadata?: {
    model: string;
    provider: string;
    route: string;
    latency_ms: number;
    cost: number;
  };
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
  
  // Domain actions
  sendChatMessage: (content: string, model?: string) => Promise<void>;
  interruptChat: () => Promise<void>;
  loadConversations: () => Promise<void>;
  loadConversationMessages: (conversationId: string) => Promise<void>;
  deleteConversation: (conversationId: string) => Promise<void>;
  clearAllConversations: () => Promise<void>;
  startNewChat: () => void;
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
  isMonitorOpen: false,
  isSidebarOpen: true,
  
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

  sendChatMessage: async (content: string, model?: string) => {
    const state = get();
    if (!content.trim() && state.attachedImages.length === 0) return;
    
    // Clear initial welcome message if present
    if (state.messages.length === 1 && state.messages[0].id === 'welcome') {
      set({ messages: [] });
    }

    const userMsg: Message = {
      id: crypto.randomUUID(),
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
      const params: any = { message: content };
      if (state.currentConversationId) params.conversation_id = state.currentConversationId;
      if (state.attachedImages.length > 0) params.images = state.attachedImages;
      if (model) params.model = model;
      
      set({ attachedImages: [] });

      // Create a skeleton message first
      const msgId = crypto.randomUUID();
      const skeletonMsg: Message = {
        id: msgId,
        role: 'assistant',
        content: '',
        streaming: true,
      };
      
      set((s) => ({
        messages: [...s.messages, skeletonMsg],
        streamingMsgId: msgId,
      }));

      await streamChat(params, (event) => {
        if (event.type === 'status') {
          set({ workflowState: event.value, workflowStage: event.value });
        } else if (event.type === 'token') {
          set((s) => {
            const updatedMsgs = s.messages.map(m => {
              if (m.id === msgId) {
                return { ...m, content: m.content + event.value };
              }
              return m;
            });
            return { messages: updatedMsgs };
          });
        } else if (event.type === 'done') {
          if (!get().currentConversationId && event.conversation_id) {
            set({ currentConversationId: event.conversation_id });
            get().loadConversations();
          }
          set((s) => {
            const updatedMsgs = s.messages.map(m => {
              if (m.id === msgId) {
                return { ...m, streaming: false, model: event.model, metadata: event.metadata };
              }
              return m;
            });
            return { 
              messages: updatedMsgs,
              streamingMsgId: null,
              workflowState: 'idle',
            };
          });
        } else if (event.type === 'error') {
          set((s) => {
            const updatedMsgs = s.messages.map(m => {
              if (m.id === msgId) {
                return { ...m, content: m.content + `\n\n[Error: ${event.value}]`, streaming: false };
              }
              return m;
            });
            return { messages: updatedMsgs, streamingMsgId: null, workflowState: 'idle' };
          });
        }
      });

    } catch (e: any) {
      const errorMsg: Message = {
        id: Date.now().toString(),
        role: 'assistant',
        content: `Error: ${e.message}`
      };
      set((s) => ({ messages: [...s.messages, errorMsg], streamingMsgId: null, workflowState: 'idle' }));
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
      await interruptChat(state.streamingMsgId);
    } catch (e) {
      console.error(e);
    }
  },

  loadConversations: async () => {
    try {
      const data = await getConversations();
      set({ conversations: data.conversations || [] });
    } catch (e) {
      console.error('Failed to load conversations:', e);
    }
  },

  loadConversationMessages: async (conversationId: string) => {
    try {
      const data = await getHistory(conversationId);
      const msgs: Message[] = (data.messages || []).map((m: any) => ({
        id: m.message_id || crypto.randomUUID(),
        role: m.role,
        content: m.content,
        time: new Date(m.timestamp).getTime(),
        metadata: m.model ? {
          model: m.model,
          provider: m.provider || '',
          route: m.route || '',
          latency_ms: m.latency_ms || 0,
          cost: m.cost || 0,
        } : undefined,
      }));
      set({ messages: msgs, currentConversationId: conversationId, streamingMsgId: null });
    } catch (e) {
      console.error('Failed to load conversation messages:', e);
    }
  },

  deleteConversation: async (conversationId: string) => {
    try {
      await apiDeleteConversation(conversationId);
      set((state) => ({
        conversations: state.conversations.filter(c => c.id !== conversationId),
        currentConversationId: state.currentConversationId === conversationId ? null : state.currentConversationId,
      }));
      if (get().currentConversationId === null || get().currentConversationId === conversationId) {
        get().startNewChat();
      }
    } catch (e) {
      console.error('Failed to delete conversation:', e);
    }
  },

  clearAllConversations: async () => {
    try {
      await apiClearAll();
      set({ conversations: [], currentConversationId: null });
      get().startNewChat();
    } catch (e) {
      console.error('Failed to clear conversations:', e);
    }
  },

  startNewChat: () => {
    set({
      currentConversationId: null,
      messages: [{ id: 'welcome', role: 'assistant', content: 'Select a conversation or start a new chat.' }],
      streamingMsgId: null,
      workflowState: 'idle',
      workflowStage: 'Ready',
      tokenSpeed: '0.0 tok/s',
      executionTime: '0.0s',
      activeTools: 'None',
      totalSessionCost: 0,
      reasoningTrace: 'No active reasoning trace.',
    });
  }
}));
