import { create } from 'zustand';

// Define the shape of our appearance settings
export interface AppearanceState {
  theme: 'light' | 'dark' | 'system' | 'custom';
  accentColor: string;
  followSystemTheme: boolean;
  sidebarTranslucent: boolean;
  reduceAnimations: boolean;
  compactMode: boolean;
  highContrast: boolean;
}

interface AppearanceStore extends AppearanceState {
  isLoaded: boolean;
  systemTheme: 'light' | 'dark'; // Read from OS
  
  // Actions
  loadSettings: () => Promise<void>;
  updateSetting: <K extends keyof AppearanceState>(key: K, value: AppearanceState[K]) => Promise<void>;
  updateSettingsBatch: (settings: Partial<AppearanceState>) => Promise<void>;
  importTheme: () => Promise<void>;
  exportTheme: () => Promise<void>;
  resetToDefaults: () => Promise<void>;
}

const defaultState: AppearanceState = {
  theme: 'light',
  accentColor: '#4f46e5', // indigo-600
  followSystemTheme: true,
  sidebarTranslucent: true,
  reduceAnimations: false,
  compactMode: false,
  highContrast: false,
};

export const useAppearanceStore = create<AppearanceStore>((set, get) => {
  // Listen for native OS theme changes if in Desktop
  if (typeof window !== 'undefined' && (window as any).nexusDesktop?.appearance) {
    (window as any).nexusDesktop.appearance.onSystemThemeChanged((newSystemTheme: 'light' | 'dark') => {
      set({ systemTheme: newSystemTheme });
      const state = get();
      if (state.followSystemTheme) {
        // Here we could trigger a DOM update to apply dark/light classes based on system
      }
    });
  }

  const saveToBackend = async (state: AppearanceState) => {
    if (typeof window !== 'undefined' && (window as any).nexusDesktop?.appearance) {
      await (window as any).nexusDesktop.appearance.saveSettings(state);
    }
  };

  return {
    ...defaultState,
    isLoaded: false,
    systemTheme: 'light',

    loadSettings: async () => {
      let loadedSettings = null;
      let sysTheme: 'light' | 'dark' = 'light';

      if (typeof window !== 'undefined' && (window as any).nexusDesktop?.appearance) {
        try {
          loadedSettings = await (window as any).nexusDesktop.appearance.getSettings();
          sysTheme = await (window as any).nexusDesktop.appearance.getSystemTheme();
        } catch (e) {
          console.error("Failed to load settings from IPC", e);
        }
      }

      set((state) => ({
        ...state,
        ...(loadedSettings ? loadedSettings : {}),
        systemTheme: sysTheme,
        isLoaded: true
      }));
    },

    updateSetting: async (key, value) => {
      set({ [key]: value });
      
      // Extract just the storable state to save
      const state = get();
      const storableState: AppearanceState = {
        theme: state.theme,
        accentColor: state.accentColor,
        followSystemTheme: state.followSystemTheme,
        sidebarTranslucent: state.sidebarTranslucent,
        reduceAnimations: state.reduceAnimations,
        compactMode: state.compactMode,
        highContrast: state.highContrast,
      };
      
      await saveToBackend(storableState);
    },

    updateSettingsBatch: async (settings) => {
      set((state) => ({ ...state, ...settings }));
      const state = get();
      const storableState: AppearanceState = {
        theme: state.theme,
        accentColor: state.accentColor,
        followSystemTheme: state.followSystemTheme,
        sidebarTranslucent: state.sidebarTranslucent,
        reduceAnimations: state.reduceAnimations,
        compactMode: state.compactMode,
        highContrast: state.highContrast,
      };
      await saveToBackend(storableState);
    },

    importTheme: async () => {
      if (typeof window !== 'undefined' && (window as any).nexusDesktop?.appearance) {
        const imported = await (window as any).nexusDesktop.appearance.importTheme();
        if (imported) {
          await get().updateSettingsBatch(imported);
        }
      }
    },

    exportTheme: async () => {
      if (typeof window !== 'undefined' && (window as any).nexusDesktop?.appearance) {
        const state = get();
        const exportableTheme: AppearanceState = {
          theme: state.theme,
          accentColor: state.accentColor,
          followSystemTheme: state.followSystemTheme,
          sidebarTranslucent: state.sidebarTranslucent,
          reduceAnimations: state.reduceAnimations,
          compactMode: state.compactMode,
          highContrast: state.highContrast,
        };
        await (window as any).nexusDesktop.appearance.exportTheme(exportableTheme);
      }
    },

    resetToDefaults: async () => {
      set({ ...defaultState });
      await saveToBackend(defaultState);
    }
  };
});
