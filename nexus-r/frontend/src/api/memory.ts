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

export async function getMemories(): Promise<{ memories: Memory[], stats: MemoryStats }> {
  return apiFetch('/memory');
}

export async function deleteMemory(memoryId: string): Promise<{ success: boolean }> {
  return apiDelete(`/memory/${memoryId}`);
}

export async function clearAllMemories(): Promise<{ success: boolean, count: number }> {
  return apiPost('/memory/clear');
}
