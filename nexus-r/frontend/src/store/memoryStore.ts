import { create } from 'zustand';
import { getMemories, deleteMemory, clearAllMemories } from '../api/memory';
import type { Memory, MemoryStats } from '../api/memory';

interface MemoryState {
  memories: Memory[];
  stats: MemoryStats | null;
  isLoading: boolean;
  error: string | null;
}

interface MemoryActions {
  loadMemories: () => Promise<void>;
  removeMemory: (memoryId: string) => Promise<boolean>;
  clearAll: () => Promise<boolean>;
}

export type MemoryStore = MemoryState & MemoryActions;

export const useMemoryStore = create<MemoryStore>((set, get) => ({
  memories: [],
  stats: null,
  isLoading: false,
  error: null,

  loadMemories: async () => {
    set({ isLoading: true, error: null });
    try {
      const res = await getMemories();
      set({ memories: res.memories || [], stats: res.stats || null, isLoading: false });
    } catch (error: any) {
      set({ error: error.message || 'Failed to load memories', isLoading: false });
    }
  },

  removeMemory: async (memoryId) => {
    set({ isLoading: true, error: null });
    try {
      const res = await deleteMemory(memoryId);
      if (res.success) {
        await get().loadMemories();
        return true;
      }
      return false;
    } catch (error: any) {
      set({ error: error.message || 'Failed to delete memory', isLoading: false });
      return false;
    }
  },

  clearAll: async () => {
    set({ isLoading: true, error: null });
    try {
      const res = await clearAllMemories();
      if (res.success) {
        await get().loadMemories();
        return true;
      }
      return false;
    } catch (error: any) {
      set({ error: error.message || 'Failed to clear memories', isLoading: false });
      return false;
    }
  }
}));
