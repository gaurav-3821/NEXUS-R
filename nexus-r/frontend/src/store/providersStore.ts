import { create } from 'zustand';
import { getProviders, updateProvider, deleteProvider } from '../api/providers';
import type { Provider } from '../api/providers';

interface ProvidersState {
  providers: Provider[];
  isLoading: boolean;
  error: string | null;
}

interface ProvidersActions {
  loadProviders: () => Promise<void>;
  updateKey: (providerId: string, apiKey: string) => Promise<boolean>;
  removeProvider: (providerId: string) => Promise<boolean>;
}

export type ProvidersStore = ProvidersState & ProvidersActions;

export const useProvidersStore = create<ProvidersStore>((set, get) => ({
  providers: [],
  isLoading: false,
  error: null,

  loadProviders: async () => {
    set({ isLoading: true, error: null });
    try {
      const res = await getProviders();
      set({ providers: res.providers || [], isLoading: false });
    } catch (error: any) {
      set({ error: error.message || 'Failed to load providers', isLoading: false });
    }
  },

  updateKey: async (providerId, apiKey) => {
    set({ isLoading: true, error: null });
    try {
      const res = await updateProvider(providerId, apiKey);
      if (res.success) {
        await get().loadProviders();
        return true;
      }
      return false;
    } catch (error: any) {
      set({ error: error.message || 'Failed to update provider key', isLoading: false });
      return false;
    }
  },

  removeProvider: async (providerId) => {
    set({ isLoading: true, error: null });
    try {
      const res = await deleteProvider(providerId);
      if (res.success) {
        await get().loadProviders();
        return true;
      }
      return false;
    } catch (error: any) {
      set({ error: error.message || 'Failed to remove provider', isLoading: false });
      return false;
    }
  }
}));
