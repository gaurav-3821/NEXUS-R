import { apiFetch } from './client';

export interface WorkflowSummary {
  conversation_id: string;
  title: string;
  created_at: string;
  message_count: number;
}

export interface WorkflowMessage {
  message_id: string;
  conversation_id: string;
  content: string;
  role: 'user' | 'assistant' | 'system';
  model?: string;
  cost?: number;
  latency_ms?: number;
  timestamp: string;
  blocked?: boolean;
}

export async function getWorkflows(limit: number = 50, offset: number = 0): Promise<WorkflowSummary[]> {
  return apiFetch(`/chat/conversations?limit=${limit}&offset=${offset}`);
}

export async function getWorkflowHistory(conversationId: string, limit: number = 200, offset: number = 0): Promise<WorkflowMessage[]> {
  return apiFetch(`/chat/history?conversation_id=${encodeURIComponent(conversationId)}&limit=${limit}&offset=${offset}`);
}
