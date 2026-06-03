import { create } from 'zustand';

export interface PerformanceState {
  cpuUsageLimit: string;
  ramUsageLimit: string;
  diskCacheLimit: string;
  hardwareAcceleration: boolean;
  gpuMode: boolean;
  activeProfile: string;
  automaticResourceManagement: boolean;
}

interface PerformanceStore extends PerformanceState {
  isLoaded: boolean;
  loadSettings: () => Promise<void>;
  updateSetting: <K extends keyof PerformanceState>(key: K, value: PerformanceState[K]) => Promise<void>;
}

const defaultState: PerformanceState = {
  cpuUsageLimit: '80',
  ramUsageLimit: '12',
  diskCacheLimit: '20',
  hardwareAcceleration: true,
  gpuMode: false,
  activeProfile: 'balanced',
  automaticResourceManagement: true,
};

export const usePerformanceStore = create<PerformanceStore>((set, get) => {
  const saveToBackend = async (state: PerformanceState) => {
    if (typeof window !== 'undefined' && (window as any).nexusDesktop?.performance) {
      await (window as any).nexusDesktop.performance.saveSettings(state);
    }
  };

  return {
    ...defaultState,
    isLoaded: false,

    loadSettings: async () => {
      let loadedSettings = null;
      if (typeof window !== 'undefined' && (window as any).nexusDesktop?.performance) {
        try {
          loadedSettings = await (window as any).nexusDesktop.performance.getSettings();
        } catch (e) {
          console.error("Failed to load settings from IPC", e);
        }
      }
      set((state) => ({
        ...state,
        ...(loadedSettings ? loadedSettings : {}),
        isLoaded: true
      }));
    },

    updateSetting: async (key, value) => {
      set({ [key]: value });
      const state = get();
      const storableState: PerformanceState = {
        cpuUsageLimit: state.cpuUsageLimit,
        ramUsageLimit: state.ramUsageLimit,
        diskCacheLimit: state.diskCacheLimit,
        hardwareAcceleration: state.hardwareAcceleration,
        gpuMode: state.gpuMode,
        activeProfile: state.activeProfile,
        automaticResourceManagement: state.automaticResourceManagement,
      };
      await saveToBackend(storableState);
    },
  };
});
