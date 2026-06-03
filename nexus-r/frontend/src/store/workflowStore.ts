import { create } from 'zustand';
import { getWorkflows, getWorkflowHistory } from '../api/workflow';
import type { WorkflowSummary, WorkflowMessage } from '../api/workflow';

interface WorkflowState {
  workflows: WorkflowSummary[];
  selectedWorkflowId: string | null;
  selectedWorkflowHistory: WorkflowMessage[];
  isLoadingWorkflows: boolean;
  isLoadingHistory: boolean;
  error: string | null;
}

interface WorkflowActions {
  loadWorkflows: (limit?: number, offset?: number) => Promise<void>;
  selectWorkflow: (conversationId: string | null) => Promise<void>;
}

export type WorkflowStore = WorkflowState & WorkflowActions;

export const useWorkflowStore = create<WorkflowStore>((set) => ({
  workflows: [],
  selectedWorkflowId: null,
  selectedWorkflowHistory: [],
  isLoadingWorkflows: false,
  isLoadingHistory: false,
  error: null,

  loadWorkflows: async (limit = 50, offset = 0) => {
    set({ isLoadingWorkflows: true, error: null });
    try {
      const data = await getWorkflows(limit, offset);
      set({ workflows: data || [], isLoadingWorkflows: false });
    } catch (error: any) {
      set({ error: error.message || 'Failed to load workflows', isLoadingWorkflows: false });
    }
  },

  selectWorkflow: async (conversationId) => {
    if (!conversationId) {
      set({ selectedWorkflowId: null, selectedWorkflowHistory: [] });
      return;
    }

    set({ selectedWorkflowId: conversationId, isLoadingHistory: true, error: null });
    try {
      const history = await getWorkflowHistory(conversationId);
      set({ selectedWorkflowHistory: history || [], isLoadingHistory: false });
    } catch (error: any) {
      set({ error: error.message || 'Failed to load workflow history', isLoadingHistory: false });
    }
  }
}));
