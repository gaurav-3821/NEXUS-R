import { apiFetch, apiPost, apiDelete } from './client';

export interface Memory {
  id: string;
  content: string;
  type: string;
  created_at: string;
  metadata?: Record<string, any>;
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

export async function togglePersistentMemory(enabled: boolean): Promise<{ success: boolean, enabled: boolean }> {
  return apiPost(`/memory/persistent/toggle?enabled=${enabled}`);
}

export async function toggleSmartMemory(enabled: boolean): Promise<{ success: boolean, enabled: boolean }> {
  return apiPost(`/memory/smart/toggle?enabled=${enabled}`);
}
