import { create } from 'zustand';
import { getMemories, deleteMemory, clearAllMemories, rebuildMemoryIndex, optimizeMemory, getMemoryDetailStats, togglePersistentMemory, toggleSmartMemory } from '../api/memory';
import type { Memory, MemoryStats, MemoryDetailStats } from '../api/memory';

interface MemoryState {
  memories: Memory[];
  stats: MemoryStats | null;
  detailStats: MemoryDetailStats | null;
  isLoading: boolean;
  error: string | null;
  persistentEnabled: boolean;
  smartEnabled: boolean;
}

interface MemoryActions {
  loadMemories: () => Promise<void>;
  loadDetailStats: () => Promise<void>;
  removeMemory: (memoryId: string) => Promise<boolean>;
  clearAll: () => Promise<boolean>;
  rebuild: () => Promise<boolean>;
  optimize: () => Promise<boolean>;
  setPersistent: (enabled: boolean) => Promise<void>;
  setSmart: (enabled: boolean) => Promise<void>;
}

export type MemoryStore = MemoryState & MemoryActions;

export const useMemoryStore = create<MemoryStore>((set, get) => ({
  memories: [],
  stats: null,
  detailStats: null,
  isLoading: false,
  error: null,
  persistentEnabled: true,
  smartEnabled: true,

  loadMemories: async () => {
    set({ isLoading: true, error: null });
    try {
      const res = await getMemories();
      set({ memories: res.memories || [], stats: res.stats || null, isLoading: false });
    } catch (error: any) {
      set({ error: error.message || 'Failed to load memories', isLoading: false });
    }
  },

  loadDetailStats: async () => {
    try {
      const detailStats = await getMemoryDetailStats();
      set({ detailStats });
    } catch (error: any) {
      console.error('Failed to load detail stats:', error);
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
        await get().loadDetailStats();
        return true;
      }
      return false;
    } catch (error: any) {
      set({ error: error.message || 'Failed to clear memories', isLoading: false });
      return false;
    }
  },

  rebuild: async () => {
    set({ isLoading: true, error: null });
    try {
      const res = await rebuildMemoryIndex();
      if (res.success) {
        await get().loadMemories();
        return true;
      }
      return false;
    } catch (error: any) {
      set({ error: error.message || 'Failed to rebuild index', isLoading: false });
      return false;
    }
  },

  optimize: async () => {
    set({ isLoading: true, error: null });
    try {
      const res = await optimizeMemory();
      if (res.success) {
        await get().loadMemories();
        await get().loadDetailStats();
        return true;
      }
      return false;
    } catch (error: any) {
      set({ error: error.message || 'Failed to optimize', isLoading: false });
      return false;
    }
  },

  setPersistent: async (enabled) => {
    try {
      const res = await togglePersistentMemory(enabled);
      if (res.success) set({ persistentEnabled: res.enabled });
    } catch (error: any) {
      console.error('Failed to toggle persistent memory:', error);
    }
  },

  setSmart: async (enabled) => {
    try {
      const res = await toggleSmartMemory(enabled);
      if (res.success) set({ smartEnabled: res.enabled });
    } catch (error: any) {
      console.error('Failed to toggle smart memory:', error);
    }
  }
}));
