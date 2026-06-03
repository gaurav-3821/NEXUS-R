import { create } from 'zustand';

interface GeneralSettings {
  autoUpdate: boolean;
  telemetryEnabled: boolean;
  defaultDirectory: string;
  language: string;
}

interface GeneralState {
  settings: GeneralSettings;
  isLoading: boolean;
  error: string | null;
}

interface GeneralActions {
  loadSettings: () => Promise<void>;
  updateSetting: <K extends keyof GeneralSettings>(key: K, value: GeneralSettings[K]) => Promise<boolean>;
}

export type GeneralStore = GeneralState & GeneralActions;

const defaultSettings: GeneralSettings = {
  autoUpdate: true,
  telemetryEnabled: true,
  defaultDirectory: '',
  language: 'en'
};

export const useGeneralStore = create<GeneralStore>((set, get) => ({
  settings: defaultSettings,
  isLoading: false,
  error: null,

  loadSettings: async () => {
    set({ isLoading: true, error: null });
    try {
      if ((window as any).nexusDesktop?.general?.getSettings) {
        const stored = await (window as any).nexusDesktop.general.getSettings();
        if (stored && stored.general) {
          set({ settings: { ...defaultSettings, ...stored.general }, isLoading: false });
          return;
        }
      }
      set({ settings: defaultSettings, isLoading: false });
    } catch (error: any) {
      console.error('Failed to load general settings:', error);
      set({ error: error.message || 'Failed to load general settings', isLoading: false });
    }
  },

  updateSetting: async (key, value) => {
    try {
      const currentSettings = get().settings;
      const newSettings = { ...currentSettings, [key]: value };
      
      set({ settings: newSettings });

      if ((window as any).nexusDesktop?.general?.saveSettings) {
        await (window as any).nexusDesktop.general.saveSettings({ general: newSettings });
      }
      return true;
    } catch (error: any) {
      console.error('Failed to save general settings:', error);
      set({ error: error.message || 'Failed to save settings' });
      return false;
    }
  }
}));
