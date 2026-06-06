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

export async function getBrowserStatus() { return apiFetch('/tools/browser/status'); }
export async function startBrowser(config?: any) { return (await import('./client')).apiPost('/tools/browser/start', config); }
export async function stopBrowser() { return (await import('./client')).apiPost('/tools/browser/stop'); }
export async function getBrowserPageText() { return apiFetch('/tools/browser/page-text'); }
export async function takeBrowserScreenshot() { return apiFetch('/tools/browser/screenshot'); }
export async function switchBrowserHeaded(config: { headed: boolean }) { return (await import('./client')).apiPost('/tools/browser/headed', config); }
export async function saveBrowserSession(path?: string) { return (await import('./client')).apiPost('/tools/browser/save-session', { path }); }
export async function loadBrowserSession(path?: string) { return (await import('./client')).apiPost('/tools/browser/load-session', { path }); }
export async function getBrowserNetworkData(maxEntries?: number) { return apiFetch('/tools/browser/network-data', { max_entries: maxEntries || 20 }); }
