import { apiFetch, apiPost } from './client';

export interface LocalModelDetails {
  parameter_size?: string;
  quantization_level?: string;
}

export interface LocalModel {
  name: string;
  size?: string;
  source?: string;
  details?: LocalModelDetails;
}

export interface CloudProviderOption {
  value: string;
  label: string;
  model: string;
  secret_name: string;
  env_var: string;
  cost_per_1k: string;
  key_prefix: string;
}

export interface ModelsStatus {
  current: {
    local_model: string;
    cloud_provider: string;
    api_key_configured: boolean;
  };
  cloud_options: CloudProviderOption[];
}

export interface DownloadJob {
  job_id: string;
  model_name: string;
  status: string;
  progress: number;
  progress_percent: number;
  downloaded_bytes: number;
  total_bytes: number;
  speed_mbps: number;
  message: string;
  error?: string;
  elapsed_seconds?: number;
  completed_at?: string;
}

export interface RoutingProfile {
  router: string;
  reasoning: string;
  coding: string;
  general: string;
  embedding: string;
}

export interface ModelsConfig {
  current: {
    local_model: string;
    cloud_provider: string;
    api_key_configured: boolean;
  };
  routingProfile: RoutingProfile;
}

export async function getModelsStatus(): Promise<ModelsStatus> {
  return apiFetch('/models/status');
}

export async function fetchRoutingProfile(): Promise<RoutingProfile> {
  return apiFetch('/models/routing-profile');
}

export async function fetchConfig(): Promise<ModelsConfig> {
  return apiFetch('/models/config');
}

export async function getLocalModels(): Promise<Record<string, LocalModel[]>> {
  return apiFetch('/models/list-local');
}

export async function getActiveDownloadJobs(): Promise<{ jobs: DownloadJob[] }> {
  return apiFetch('/models/download-jobs');
}

export async function getDownloadStatus(jobId: string): Promise<DownloadJob> {
  return apiFetch(`/models/download-status/${jobId}`);
}

export async function checkOllamaStatus(modelName: string): Promise<{ installed: boolean; model: string; size?: string; error?: string }> {
  return apiFetch(`/models/ollama-status/${encodeURIComponent(modelName)}`);
}

export async function startDownload(modelName: string): Promise<{ success: boolean; job_id?: string; model?: string; error?: string }> {
  return apiPost('/models/download', { model_name: modelName });
}

export async function cancelDownload(jobId: string): Promise<{ success: boolean; error?: string }> {
  return apiPost(`/models/download-cancel/${jobId}`);
}

export async function testModel(params: { local_model?: string; cloud_provider?: string; api_key?: string }): Promise<{ success: boolean; latency_ms?: number; response?: string; error?: string; warning?: string }> {
  return apiPost('/models/test', params);
}

export async function configureModels(params: { local_model?: string; cloud_provider?: string; api_key?: string; routingProfile?: RoutingProfile }): Promise<{ status: string; changed: boolean; current: ModelsStatus["current"]; errors: string[]; warnings: string[] }> {
  return apiPost('/models/config', params);
}
