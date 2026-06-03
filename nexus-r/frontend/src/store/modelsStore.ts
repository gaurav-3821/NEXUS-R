import { create } from 'zustand';
import { fetchConfig, getLocalModels, configureModels, testModel, getActiveDownloadJobs, startDownload, cancelDownload, getModelsStatus } from '../api/models';
import type { ModelsStatus, LocalModel, CloudProviderOption, DownloadJob, RoutingProfile, ModelsConfig } from '../api/models';

interface ModelsState {
  currentConfig: ModelsStatus['current'] | null;
  cloudOptions: CloudProviderOption[];
  localModels: LocalModel[];
  downloadJobs: DownloadJob[];
  isLoading: boolean;
  error: string | null;
  routingProfile: RoutingProfile | null;
}

interface ModelsActions {
  loadModels: () => Promise<void>;
  updateConfig: (localModel?: string, cloudProvider?: string, apiKey?: string) => Promise<boolean>;
  updateRoutingProfile: (profile: Partial<RoutingProfile>) => Promise<boolean>;
  testConnection: (localModel?: string, cloudProvider?: string, apiKey?: string) => Promise<{ success: boolean; latency_ms?: number; response?: string; error?: string; warning?: string }>;
  loadDownloadJobs: () => Promise<void>;
  refreshLocalModels: () => Promise<void>;
  startModelDownload: (modelName: string) => Promise<boolean>;
  cancelModelDownload: (jobId: string) => Promise<boolean>;
}

export type ModelsStore = ModelsState & ModelsActions;

export const useModelsStore = create<ModelsStore>((set, get) => ({
  currentConfig: null,
  cloudOptions: [],
  localModels: [],
  downloadJobs: [],
  isLoading: false,
  error: null,
  routingProfile: null,

  loadModels: async () => {
    set({ isLoading: true, error: null });
    try {
      const [config, status, local] = await Promise.all([
        fetchConfig(),
        getModelsStatus(),
        getLocalModels()
      ]);
      
      const allLocal = [];
      if (local && typeof local === 'object') {
        for (const key of Object.keys(local)) {
          if (Array.isArray(local[key])) {
            allLocal.push(...local[key]);
          }
        }
      }
      
      set({
        currentConfig: config.current,
        cloudOptions: status.cloud_options,
        localModels: allLocal,
        routingProfile: config.routingProfile,
        isLoading: false
      });
      
    } catch (error: any) {
      set({ error: error.message || 'Failed to load models', isLoading: false });
    }
  },

  updateRoutingProfile: async (profileUpdates: Partial<RoutingProfile>) => {
    const state = get();
    if (!state.routingProfile) return false;
    
    const newProfile = { ...state.routingProfile, ...profileUpdates };
    
    set({ isLoading: true, error: null });
    try {
      const res = await configureModels({
        routingProfile: newProfile
      });
      if (res.status !== 'error') {
        set({ routingProfile: newProfile, isLoading: false });
        return true;
      } else {
        set({ error: res.errors?.join(', ') || 'Failed to update routing profile', isLoading: false });
        return false;
      }
    } catch (error: any) {
      set({ error: error.message || 'Error updating routing profile', isLoading: false });
      return false;
    }
  },

  updateConfig: async (localModel, cloudProvider, apiKey) => {
    set({ isLoading: true, error: null });
    try {
      const res = await configureModels({ local_model: localModel, cloud_provider: cloudProvider, api_key: apiKey });
      if (res.success) {
        set({ currentConfig: res.current, isLoading: false });
        return true;
      } else {
        set({ error: res.errors?.join(', ') || 'Failed to update configuration', isLoading: false });
        return false;
      }
    } catch (error: any) {
      set({ error: error.message || 'Error updating models configuration', isLoading: false });
      return false;
    }
  },

  testConnection: async (localModel, cloudProvider, apiKey) => {
    return testModel({ local_model: localModel, cloud_provider: cloudProvider, api_key: apiKey });
  },

  loadDownloadJobs: async () => {
    try {
      const res = await getActiveDownloadJobs();
      set({ downloadJobs: res.jobs || [] });
    } catch (error: any) {
      console.error("Failed to load download jobs", error);
    }
  },

  refreshLocalModels: async () => {
    try {
      const local = await getLocalModels();
      const allLocal: any[] = [];
      if (local && typeof local === 'object') {
        for (const key of Object.keys(local)) {
          if (Array.isArray(local[key])) {
            allLocal.push(...local[key]);
          }
        }
      }
      set({ localModels: allLocal });
    } catch (error: any) {
      console.error('Failed to refresh local models', error);
    }
  },

  startModelDownload: async (modelName: string) => {
    try {
      const res = await startDownload(modelName);
      if (res.success || res.status === 'already_downloaded') {
        await get().loadDownloadJobs();
        await get().refreshLocalModels();
        return true;
      }
      return false;
    } catch (error: any) {
      set({ error: error.message || 'Failed to start download' });
      return false;
    }
  },

  cancelModelDownload: async (jobId: string) => {
    try {
      const res = await cancelDownload(jobId);
      if (res.success) {
        await get().loadDownloadJobs();
        return true;
      }
      return false;
    } catch (error: any) {
      set({ error: error.message || 'Failed to cancel download' });
      return false;
    }
  }
}));
