import { apiFetch, apiPost, apiDelete, getToken, clearTokenCache, API_BASE } from './client';

export interface Memory {
  id: string;
  fact_text: string;
  type: string;
  importance_score: number;
  confidence: number;
  created_at: string;
  updated_at?: string;
  source_conversation_id?: string;
  source_message_id?: string;
  expires_at?: string | null;
  last_referenced_at?: string | null;
}

export interface MemoryStats {
  total_memories: number;
  total_size_bytes: number;
  oldest_memory_date?: string;
  newest_memory_date?: string;
}

export interface MemoryCategories {
  semantic?: number;
  golden?: number;
  persistent?: number;
  smart?: number;
}

export interface MemoryDetailStats {
  total_memories: number;
  total_size_bytes: number;
  categories: MemoryCategories;
}

export async function getMemories(): Promise<{ memories: Memory[], stats: MemoryStats }> {
  return apiFetch('/memory');
}

export async function deleteMemory(memoryId: string): Promise<{ success: boolean }> {
  return apiDelete(`/memory/${memoryId}`);
}

export async function clearAllMemories(): Promise<{ success: boolean, count: number }> {
  return apiPost('/memory/clear');
}

export async function rebuildMemoryIndex(): Promise<{ success: boolean, rebuilt: number }> {
  return apiPost('/memory/rebuild');
}

export async function optimizeMemory(): Promise<{ success: boolean, pruned: number, remaining: number }> {
  return apiPost('/memory/optimize');
}

export async function getMemoryDetailStats(): Promise<MemoryDetailStats> {
  return apiFetch('/memory/stats');
}

async function apiPostWithParams(path: string, queryParams: Record<string, string | number | boolean>): Promise<any> {
  const params = new URLSearchParams();
  params.set('token', await getToken());
  for (const [k, v] of Object.entries(queryParams)) {
    params.set(k, String(v));
  }
  let url = `${API_BASE}${path}?${params}`;
  let resp = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' } });
  if (resp.status === 403 && import.meta.env.DEV) {
    clearTokenCache();
    params.set('token', await getToken());
    url = `${API_BASE}${path}?${params}`;
    resp = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' } });
  }
  if (!resp.ok) {
    if (resp.status === 403) window.dispatchEvent(new Event('auth_error'));
    let detail = '';
    try { const errBody = await resp.json(); detail = errBody.detail || errBody.error || ''; }
    catch { detail = await resp.text(); }
    throw new Error(`${resp.status}: ${detail || resp.statusText}`);
  }
  return resp.json();
}

export async function togglePersistentMemory(enabled: boolean): Promise<{ success: boolean, enabled: boolean }> {
  return apiPostWithParams('/memory/persistent/toggle', { enabled });
}

export async function toggleSmartMemory(enabled: boolean): Promise<{ success: boolean, enabled: boolean }> {
  return apiPostWithParams('/memory/smart/toggle', { enabled });
}

export async function saveMemory(payload: {
  fact_text: string;
  type?: string;
  importance_score?: number;
  confidence?: number;
  conversation_id?: string;
}): Promise<{ success: boolean; fact: Memory }> {
  return apiPost('/memory/save', payload);
}
