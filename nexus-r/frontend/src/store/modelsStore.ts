import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { fetchConfig, getLocalModels, configureModels, testModel, getActiveDownloadJobs, startDownload, cancelDownload, getModelsStatus, searchHuggingFace, pauseDownload, resumeDownload, deleteLocalModel as deleteModelApi, listOpenRouterModels } from '../api/models';
import type { ModelsStatus, LocalModel, CloudProviderOption, DownloadJob, RoutingProfile, ModelsConfig } from '../api/models';

interface ModelsState {
  currentConfig: ModelsStatus['current'] | null;
  cloudOptions: CloudProviderOption[];
  localModels: LocalModel[];
  downloadJobs: DownloadJob[];
  huggingfaceResults: any[];
  openrouterModels: any[];
  isSearching: boolean;
  isLoading: boolean;
  error: string | null;
  routingProfile: RoutingProfile | null;
  providerModels: Record<string, any[]>;
  pinnedCloudModels: string[];
}

interface ModelsActions {
  loadModels: () => Promise<void>;
  updateConfig: (localModel?: string, cloudProvider?: string, apiKey?: string) => Promise<boolean>;
  updateRoutingProfile: (profile: Partial<RoutingProfile>) => Promise<boolean>;
  testConnection: (localModel?: string, cloudProvider?: string, apiKey?: string) => Promise<{ success: boolean; latency_ms?: number; response?: string; error?: string; warning?: string }>;
  loadDownloadJobs: () => Promise<void>;
  refreshLocalModels: () => Promise<void>;
  searchHFModels: (query: string, filter?: string) => Promise<void>;
  listOpenRouter: () => Promise<void>;
  startModelDownload: (modelName: string, url?: string) => Promise<boolean>;
  pauseModelDownload: (jobId: string) => Promise<boolean>;
  resumeModelDownload: (jobId: string) => Promise<boolean>;
  cancelModelDownload: (jobId: string) => Promise<boolean>;
  deleteLocalModel: (modelName: string) => Promise<boolean>;
  fetchProviderModels: (providerId: string) => Promise<void>;
  togglePinnedModel: (modelId: string) => void;
}

export type ModelsStore = ModelsState & ModelsActions;

export const useModelsStore = create<ModelsStore>()(
  persist(
    (set, get) => ({
      currentConfig: null,
      cloudOptions: [],
      localModels: [],
      downloadJobs: [],
      huggingfaceResults: [],
      openrouterModels: [],
      isSearching: false,
      isLoading: false,
      error: null,
      routingProfile: null,
      providerModels: {},
      pinnedCloudModels: [],

      loadModels: async () => {
        set({ isLoading: true, error: null });
        const results = await Promise.allSettled([
          fetchConfig(),
          getModelsStatus(),
          getLocalModels()
        ]);

        let localModels: any[] = [];
        let cloudOptions: any[] = [];
        let configData: any = null;
        const errors: string[] = [];

        if (results[0].status === 'fulfilled') {
          configData = results[0].value;
        } else {
          errors.push('config: ' + (results[0].reason?.message || 'failed'));
        }

        if (results[1].status === 'fulfilled') {
          cloudOptions = results[1].value.cloud_options || [];
          if (!configData) {
            configData = { current: results[1].value.current, routingProfile: null };
          }
        } else {
          errors.push('status: ' + (results[1].reason?.message || 'failed'));
        }

        if (results[2].status === 'fulfilled') {
          localModels = results[2].value?.all ?? [];
        }

        set({
          currentConfig: configData?.current || null,
          cloudOptions,
          localModels,
          routingProfile: configData?.routingProfile || null,
          isLoading: false,
          error: errors.length > 0 ? errors.join('; ') : null,
        });
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
          set({ localModels: local?.all ?? [] });
        } catch (error: any) {
          console.error('Failed to refresh local models', error);
        }
      },

      searchHFModels: async (query: string, filter: string = '') => {
        set({ isSearching: true, error: null });
        try {
          const res = await searchHuggingFace(query, filter);
          set({ huggingfaceResults: res.results || [], isSearching: false });
        } catch (error: any) {
          set({ error: error.message || 'Failed to search models', isSearching: false });
        }
      },

      listOpenRouter: async () => {
        set({ isSearching: true, error: null });
        try {
          const res = await listOpenRouterModels();
          set({ openrouterModels: res.results || [], isSearching: false });
        } catch (error: any) {
          set({ error: error.message || 'Failed to list OpenRouter models', isSearching: false });
        }
      },

      fetchProviderModels: async (providerId: string) => {
        if (!providerId || providerId === 'none') return;
        try {
          const { apiFetch } = await import('../api/client');
          const res = await apiFetch(`/providers/${providerId}/models`);
          const currentModels = get().providerModels;
          set({ providerModels: { ...currentModels, [providerId]: res.models || [] } });
        } catch (error) {
          console.error(`Failed to fetch models for provider ${providerId}`, error);
        }
      },

      startModelDownload: async (modelName: string, url?: string) => {
        try {
          const res = await startDownload(modelName, url);
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

      pauseModelDownload: async (jobId: string) => {
        try {
          const res = await pauseDownload(jobId);
          if (res.success) {
            await get().loadDownloadJobs();
            return true;
          }
          return false;
        } catch (error: any) {
          set({ error: error.message || 'Failed to pause download' });
          return false;
        }
      },

      resumeModelDownload: async (jobId: string) => {
        try {
          const res = await resumeDownload(jobId);
          if (res.success) {
            await get().loadDownloadJobs();
            return true;
          }
          return false;
        } catch (error: any) {
          set({ error: error.message || 'Failed to resume download' });
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
      },

      deleteLocalModel: async (modelName: string) => {
        try {
          const res = await deleteModelApi(modelName);
          if (res.success) {
            await get().refreshLocalModels();
            return true;
          }
          return false;
        } catch (error: any) {
          set({ error: error.message || 'Failed to delete model' });
          return false;
        }
      },

      togglePinnedModel: (modelId: string) => {
        const { pinnedCloudModels } = get();
        if (pinnedCloudModels.includes(modelId)) {
          set({ pinnedCloudModels: pinnedCloudModels.filter(id => id !== modelId) });
        } else {
          set({ pinnedCloudModels: [...pinnedCloudModels, modelId] });
        }
      }
    }),
    {
      name: 'nexusr-models-storage',
      partialize: (state) => ({
        pinnedCloudModels: state.pinnedCloudModels,
      }),
    }
  )
);
