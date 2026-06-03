import { create } from 'zustand';
import { getTools } from '../api/tools';
import type { AgentTool } from '../api/tools';

interface ToolState {
  tools: AgentTool[];
  isLoading: boolean;
  error: string | null;
}

interface ToolActions {
  loadTools: () => Promise<void>;
}

export type ToolStore = ToolState & ToolActions;

export const useToolStore = create<ToolStore>((set) => ({
  tools: [],
  isLoading: false,
  error: null,

  loadTools: async () => {
    set({ isLoading: true, error: null });
    try {
      const tools = await getTools();
      set({ tools, isLoading: false });
    } catch (error: any) {
      set({ error: error.message || 'Failed to load tools', isLoading: false });
    }
  }
}));
