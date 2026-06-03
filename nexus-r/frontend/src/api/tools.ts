import { apiFetch } from './client';

export interface AgentTool {
  id: string;
  name: string;
  description: string;
  category: 'Cognitive' | 'External' | 'Execution' | string;
  status: 'Active' | 'Inactive' | string;
}

interface ToolsResponse {
  tools: AgentTool[];
}

export async function getTools(): Promise<AgentTool[]> {
  const data: ToolsResponse = await apiFetch('/tools');
  return data.tools || [];
}
