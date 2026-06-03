import { apiFetch } from './client';

export interface DashboardSummary {
  total_cost: number;
  total_tasks: number;
  avg_latency_ms: number;
  session_id?: string;
  total_tokens?: number;
}

export interface DashboardTask {
  task_id: string;
  total_cost: number;
  avg_latency_ms: number;
  start_time: string;
  end_time?: string;
  model: string;
  tier: string;
  tokens?: number;
}

export interface ModelBreakdown {
  [modelName: string]: {
    cost: number;
    tasks: number;
    tokens?: number;
  }
}

export async function getDashboardSummary(): Promise<DashboardSummary> {
  return apiFetch('/cost/summary');
}

export async function getDashboardTasks(limit: number = 20): Promise<DashboardTask[]> {
  return apiFetch(`/cost/tasks?limit=${limit}`);
}

export async function getModelBreakdown(): Promise<ModelBreakdown> {
  return apiFetch('/cost/models');
}
