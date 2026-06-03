import { create } from 'zustand';

export interface AppearanceState {
  themeMode: 'light' | 'dark' | 'system';
  accentColor: string;
  compactMode: boolean;
  highContrast: boolean;
  reduceAnimations: boolean;
  sidebarTransparency: boolean;
  showResponseMetadata: boolean;
}

export interface AppearanceActions {
  loadSettings: () => Promise<void>;
  updateSetting: <K extends keyof AppearanceState>(key: K, value: AppearanceState[K]) => Promise<void>;
  updateSettingsBatch: (settings: Partial<AppearanceState>) => Promise<void>;
  resetToDefaults: () => Promise<void>;
  importTheme: () => Promise<void>;
  exportTheme: () => Promise<void>;
}

export type AppearanceStore = AppearanceState & AppearanceActions;

export const ACCENT_PALETTES: Record<string, Record<string, string>> = {
  purple: {
    50: '250 245 255', 100: '243 232 255', 200: '233 213 255', 300: '216 180 254', 400: '192 132 252',
    500: '168 85 247', 600: '147 51 234', 700: '126 34 206', 800: '107 33 168', 900: '88 28 135',
  },
  blue: {
    50: '239 246 255', 100: '219 234 254', 200: '191 219 254', 300: '147 197 253', 400: '96 165 250',
    500: '59 130 246', 600: '37 99 235', 700: '29 78 216', 800: '30 64 175', 900: '30 58 138',
  },
  green: {
    50: '236 253 245', 100: '209 250 229', 200: '167 243 208', 300: '110 231 183', 400: '52 211 153',
    500: '16 185 129', 600: '5 150 105', 700: '4 120 87', 800: '6 95 70', 900: '6 78 59',
  },
  orange: {
    50: '255 247 237', 100: '255 237 213', 200: '254 215 170', 300: '253 186 116', 400: '251 146 60',
    500: '249 115 22', 600: '234 88 12', 700: '194 65 12', 800: '154 52 18', 900: '124 45 18',
  },
  red: {
    50: '254 242 242', 100: '254 226 226', 200: '254 202 202', 300: '252 165 165', 400: '248 113 113',
    500: '239 68 68', 600: '220 38 38', 700: '185 28 28', 800: '153 27 27', 900: '127 29 29',
  },
  pink: {
    50: '253 242 248', 100: '252 231 243', 200: '251 207 232', 300: '249 168 212', 400: '244 114 182',
    500: '236 72 153', 600: '219 39 119', 700: '190 24 93', 800: '157 23 77', 900: '131 24 67',
  }
};

const defaultState: AppearanceState = {
  themeMode: 'system',
  accentColor: 'purple',
  compactMode: false,
  highContrast: false,
  reduceAnimations: false,
  sidebarTransparency: true,
  showResponseMetadata: false,
};

const applyThemeToDOM = (themeMode: 'light' | 'dark' | 'system') => {
  if (typeof document !== 'undefined') {
    const isDark = themeMode === 'dark' || (themeMode === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches);
    if (isDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }
};

const applyAccentColorToDOM = (accentColor: string) => {
  if (typeof document !== 'undefined') {
    const palette = ACCENT_PALETTES[accentColor] || ACCENT_PALETTES['purple'];
    Object.entries(palette).forEach(([shade, rgbValue]) => {
      document.documentElement.style.setProperty(`--accent-${shade}`, rgbValue);
    });
  }
};

const applyReduceAnimationsToDOM = (reduceAnimations: boolean) => {
  if (typeof document !== 'undefined') {
    if (reduceAnimations) {
      document.documentElement.classList.add('reduce-animations');
    } else {
      document.documentElement.classList.remove('reduce-animations');
    }
  }
};

const applyHighContrastToDOM = (highContrast: boolean) => {
  if (typeof document !== 'undefined') {
    if (highContrast) {
      document.documentElement.classList.add('high-contrast');
    } else {
      document.documentElement.classList.remove('high-contrast');
    }
  }
};

export const useAppearanceStore = create<AppearanceStore>((set, get) => ({
  ...defaultState,
  
  loadSettings: async () => {
    try {
      if ((window as any).nexusDesktop?.appearance?.getSettings) {
        const stored = await (window as any).nexusDesktop.appearance.getSettings();
        if (stored && stored.appearance) {
          const loaded = { ...defaultState, ...stored.appearance };
          set(loaded);
          applyThemeToDOM(loaded.themeMode);
          applyAccentColorToDOM(loaded.accentColor);
          applyReduceAnimationsToDOM(loaded.reduceAnimations);
          applyHighContrastToDOM(loaded.highContrast);
          return;
        }
      }
    } catch (error) {
      console.error('Failed to load appearance settings from IPC:', error);
    }
    // Fallback to localStorage (web-only mode)
    try {
      const ls = localStorage.getItem('nexus-appearance');
      if (ls) {
        const parsed = JSON.parse(ls);
        const loaded = { ...defaultState, ...parsed };
        set(loaded);
        applyThemeToDOM(loaded.themeMode);
        applyAccentColorToDOM(loaded.accentColor);
        applyReduceAnimationsToDOM(loaded.reduceAnimations);
        applyHighContrastToDOM(loaded.highContrast);
        return;
      }
    } catch (_) {}
    // Fallback to default
    set(defaultState);
    applyThemeToDOM(defaultState.themeMode);
    applyAccentColorToDOM(defaultState.accentColor);
    applyReduceAnimationsToDOM(defaultState.reduceAnimations);
    applyHighContrastToDOM(defaultState.highContrast);
  },

  updateSetting: async (key, value) => {
    set({ [key]: value });
    if (key === 'themeMode') applyThemeToDOM(value as 'light' | 'dark' | 'system');
    if (key === 'accentColor') applyAccentColorToDOM(value as string);
    if (key === 'reduceAnimations') applyReduceAnimationsToDOM(value as boolean);
    if (key === 'highContrast') applyHighContrastToDOM(value as boolean);

    // Persist to localStorage (web-only) and IPC (Electron)
    const { loadSettings, updateSetting, updateSettingsBatch, resetToDefaults, importTheme, exportTheme, ...appearanceState } = get();
    try { localStorage.setItem('nexus-appearance', JSON.stringify(appearanceState)); } catch (_) {}
    if ((window as any).nexusDesktop?.appearance?.saveSettings) {
      await (window as any).nexusDesktop.appearance.saveSettings({ appearance: appearanceState });
    }
  },

  updateSettingsBatch: async (settings) => {
    set((state) => ({ ...state, ...settings }));
    if (settings.themeMode) applyThemeToDOM(settings.themeMode);
    if (settings.accentColor) applyAccentColorToDOM(settings.accentColor);
    if (settings.reduceAnimations !== undefined) applyReduceAnimationsToDOM(settings.reduceAnimations);
    if (settings.highContrast !== undefined) applyHighContrastToDOM(settings.highContrast);

    // Persist to localStorage (web-only) and IPC (Electron)
    const { loadSettings, updateSetting, updateSettingsBatch, resetToDefaults, importTheme, exportTheme, ...appearanceState } = get();
    try { localStorage.setItem('nexus-appearance', JSON.stringify(appearanceState)); } catch (_) {}
    if ((window as any).nexusDesktop?.appearance?.saveSettings) {
      await (window as any).nexusDesktop.appearance.saveSettings({ appearance: appearanceState });
    }
  },

  resetToDefaults: async () => {
    set(defaultState);
    applyThemeToDOM(defaultState.themeMode);
    applyAccentColorToDOM(defaultState.accentColor);
    applyReduceAnimationsToDOM(defaultState.reduceAnimations);
    applyHighContrastToDOM(defaultState.highContrast);

    try { localStorage.removeItem('nexus-appearance'); } catch (_) {}
    if ((window as any).nexusDesktop?.appearance?.saveSettings) {
      await (window as any).nexusDesktop.appearance.saveSettings({ appearance: defaultState });
    }
  },

  importTheme: async () => {
    if ((window as any).nexusDesktop?.appearance?.importTheme) {
      try {
        const theme = await (window as any).nexusDesktop.appearance.importTheme();
        if (theme) {
          get().updateSettingsBatch(theme);
        }
      } catch (e) {
        console.error('Failed to import theme via IPC', e);
      }
    } else {
      // Fallback to DOM if not running in electron
      if (typeof document !== 'undefined') {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = 'application/json';
        input.onchange = (e) => {
          const file = (e.target as HTMLInputElement).files?.[0];
          if (!file) return;

          const reader = new FileReader();
          reader.onload = (event) => {
            try {
              const data = JSON.parse(event.target?.result as string);
              get().updateSettingsBatch({
                themeMode: data.themeMode,
                accentColor: data.accentColor,
                compactMode: data.compactMode,
                highContrast: data.highContrast,
                reduceAnimations: data.reduceAnimations,
                sidebarTransparency: data.sidebarTransparency,
                showResponseMetadata: data.showResponseMetadata ?? false
              });
              alert('Theme imported successfully!');
            } catch (err) {
              alert('Failed to parse theme file.');
            }
          };
          reader.readAsText(file);
        };
        input.click();
      }
    }
  },

  exportTheme: async () => {
    const { loadSettings, updateSetting, updateSettingsBatch, resetToDefaults, importTheme, exportTheme, ...appearanceState } = get();
    if ((window as any).nexusDesktop?.appearance?.exportTheme) {
      try {
        await (window as any).nexusDesktop.appearance.exportTheme({ appearance: appearanceState });
      } catch (e) {
        console.error('Failed to export theme via IPC', e);
      }
    } else {
      // Fallback to DOM download
      if (typeof document !== 'undefined') {
        const blob = new Blob([JSON.stringify(appearanceState, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'theme.json';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }
    }
  },
}));

if (typeof window !== 'undefined') {
  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
  mediaQuery.addEventListener('change', (e) => {
    const { themeMode } = useAppearanceStore.getState();
    if (themeMode === 'system') {
      if (e.matches) {
        document.documentElement.classList.add('dark');
      } else {
        document.documentElement.classList.remove('dark');
      }
    }
  });
}
