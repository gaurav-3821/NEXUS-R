import { create } from 'zustand';
import { getDashboardSummary, getDashboardTasks, getModelBreakdown } from '../api/dashboard';
import type { DashboardSummary, DashboardTask, ModelBreakdown } from '../api/dashboard';

interface DashboardState {
  summary: DashboardSummary | null;
  tasks: DashboardTask[];
  modelBreakdown: ModelBreakdown | null;
  isLoading: boolean;
  error: string | null;
}

interface DashboardActions {
  loadDashboardData: () => Promise<void>;
}

export type DashboardStore = DashboardState & DashboardActions;

export const useDashboardStore = create<DashboardStore>((set) => ({
  summary: null,
  tasks: [],
  modelBreakdown: null,
  isLoading: false,
  error: null,

  loadDashboardData: async () => {
    set({ isLoading: true, error: null });
    try {
      const [summaryData, tasksData, modelBreakdownData] = await Promise.all([
        getDashboardSummary(),
        getDashboardTasks(50),
        getModelBreakdown()
      ]);
      set({ 
        summary: summaryData, 
        tasks: tasksData || [], 
        modelBreakdown: modelBreakdownData, 
        isLoading: false 
      });
    } catch (error: any) {
      set({ error: error.message || 'Failed to load dashboard data', isLoading: false });
    }
  }
}));
