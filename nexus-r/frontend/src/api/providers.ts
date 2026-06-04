import { apiFetch, apiPost, apiDelete } from './client';

export interface Provider {
  id: string;
  name: string;
  has_key: boolean;
  status: 'Active' | 'Inactive';
  key_prefix: string;
  base_url?: string;
}

export async function getProviders(): Promise<{ providers: Provider[] }> {
  return apiFetch('/providers');
}

export async function updateProvider(provider: string, apiKey?: string): Promise<{ success: boolean; provider: string }> {
  return apiPost('/providers', { provider, api_key: apiKey });
}

export async function deleteProvider(provider: string): Promise<{ success: boolean; provider: string }> {
  return apiDelete(`/providers/${provider}`);
}
