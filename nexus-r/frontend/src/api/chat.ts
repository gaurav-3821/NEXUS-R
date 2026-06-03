import { apiFetch, apiPost, apiDelete, getToken, clearTokenCache, API_BASE } from './client';

export interface ChatRequestParams {
  message: string;
  model?: string;
  conversation_id?: string;
  images?: string[];
}

export interface Conversation {
  id: string;
  title: string;
  updated_at: string;
}

export async function sendChat(params: ChatRequestParams): Promise<any> {
  return apiPost('/chat', params);
}

export async function streamChat(
  params: ChatRequestParams,
  onEvent: (event: any) => void
): Promise<void> {
  let url = `${API_BASE || '/api/v1'}/chat/stream?token=${encodeURIComponent(await getToken())}`;
  
  let reqConfig = {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  };
  
  let response = await fetch(url, reqConfig);
  if (response.status === 403 && import.meta.env.DEV) {
    clearTokenCache();
    url = `${API_BASE || '/api/v1'}/chat/stream?token=${encodeURIComponent(await getToken())}`;
    response = await fetch(url, reqConfig);
  }

  if (!response.ok) {
    throw new Error(`Stream error: ${response.status}`);
  }

  const reader = response.body?.getReader();
  const decoder = new TextDecoder('utf-8');

  if (reader) {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      const lines = chunk.split('\n');
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            onEvent(data);
          } catch (e) {
            // Ignore parse errors on partial chunks
          }
        }
      }
    }
  }
}

export async function interruptChat(messageId: string): Promise<{ success: boolean }> {
  return apiPost('/chat/interrupt', { message_id: messageId });
}

export async function resumeHITL(messageId: string, code?: string, solved: boolean = false): Promise<{ success: boolean }> {
  return apiPost('/chat/hitl-resume', { message_id: messageId, code, solved });
}

export async function deleteConversation(conversationId: string): Promise<{ success: boolean }> {
  return apiDelete(`/chat/conversations/${encodeURIComponent(conversationId)}`);
}

export async function clearAllConversations(): Promise<{ success: boolean }> {
  return apiPost('/chat/clear-all');
}

export async function getConversations(limit: number = 50, offset: number = 0): Promise<{ conversations: Conversation[] }> {
  return apiFetch('/chat/conversations', { limit, offset });
}

export async function getHistory(conversationId?: string, limit: number = 50, offset: number = 0): Promise<{ messages: any[] }> {
  return apiFetch('/chat/history', { conversation_id: conversationId, limit, offset } as any);
}
