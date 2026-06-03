import { apiFetch, apiPost, apiDelete, apiPut } from './client';

export interface Project {
  project_id: string;
  name: string;
  description: string;
  created_at: string;
  conversation_ids: string[];
}

export async function getProjects(): Promise<{ projects: Project[] }> {
  return apiFetch('/projects');
}

export async function createProject(name: string, description: string = ''): Promise<Project> {
  return apiPost('/projects', { name, description });
}

export async function updateProject(projectId: string, name?: string, description?: string): Promise<{ success: boolean }> {
  return apiPut(`/projects/${encodeURIComponent(projectId)}`, { name, description });
}

export async function deleteProject(projectId: string): Promise<{ success: boolean }> {
  return apiDelete(`/projects/${encodeURIComponent(projectId)}`);
}

export async function addConversationToProject(projectId: string, conversationId: string): Promise<{ success: boolean }> {
  return apiPost(`/projects/${encodeURIComponent(projectId)}/conversations`, { conversation_id: conversationId });
}

export async function removeConversationFromProject(projectId: string, conversationId: string): Promise<{ success: boolean }> {
  return apiDelete(`/projects/${encodeURIComponent(projectId)}/conversations/${encodeURIComponent(conversationId)}`);
}
