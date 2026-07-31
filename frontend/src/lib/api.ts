import { getAuthHeader, auth } from '$lib/auth';

export interface ComponentItem {
  id: number;
  gitlab_project_id: number;
  name: string;
  description?: string;
  kind: string;
  type: string;
  lifecycle: string;
  owner: string;
  domain?: string;
  system?: string;
  gitlab_url: string;
  default_branch?: string;
  docs_dir?: string;
  docs_index?: string;
  has_manifest: boolean;
  tags: string[];
  links: Array<{ title: string; url: string; icon?: string }>;
  dependencies: string[];
  gitlab_created_at?: string;
  last_activity_at?: string;
  updated_at?: string;
}

export interface DocFileItem {
  id: number;
  relative_path: string;
  title: string;
  updated_at?: string;
}

export interface DocFileDetail extends DocFileItem {
  content_markdown: string;
}

export interface SearchResults {
  query: string;
  components: Array<{
    id: number;
    name: string;
    description: string;
    type: string;
    owner: string;
  }>;
  docs: Array<{
    id: number;
    component_id: number;
    relative_path: string;
    title: string;
  }>;
}

const API_BASE = '/api';

async function authFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const headers = {
    ...getAuthHeader(),
    ...(options.headers || {})
  };
  const res = await fetch(url, { ...options, headers });
  if (res.status === 401) {
    auth.logout();
    if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
      window.location.href = '/login';
    }
  }
  return res;
}

export async function fetchCatalog(filters?: { owner?: string; type?: string; lifecycle?: string; tag?: string }): Promise<ComponentItem[]> {
  const params = new URLSearchParams();
  if (filters?.owner) params.append('owner', filters.owner);
  if (filters?.type) params.append('type', filters.type);
  if (filters?.lifecycle) params.append('lifecycle', filters.lifecycle);
  if (filters?.tag) params.append('tag', filters.tag);

  const res = await authFetch(`${API_BASE}/catalog?${params.toString()}`);
  if (!res.ok) throw new Error('Falha ao carregar catálogo');
  return res.json();
}

export async function fetchComponent(id: number): Promise<ComponentItem> {
  const res = await authFetch(`${API_BASE}/catalog/${id}`);
  if (!res.ok) throw new Error('Componente não encontrado');
  return res.json();
}

export async function fetchComponentDocs(id: number): Promise<DocFileItem[]> {
  const res = await authFetch(`${API_BASE}/catalog/${id}/docs`);
  if (!res.ok) throw new Error('Docs não encontradas');
  return res.json();
}

export async function fetchDocContent(id: number, docPath: string): Promise<DocFileDetail> {
  const res = await authFetch(`${API_BASE}/catalog/${id}/docs/${encodeURIComponent(docPath)}`);
  if (!res.ok) throw new Error('Conteúdo do documento não encontrado');
  return res.json();
}

export type SyncMode = 'update' | 'rebuild' | 'prune';

export type SyncState = 'idle' | 'running' | 'success' | 'partial' | 'error';

export interface SyncLogLine {
  seq: number;
  ts: string;
  level: 'info' | 'ok' | 'warn' | 'error';
  message: string;
}

export interface SyncStatus {
  state: SyncState;
  job_id?: string;
  mode?: SyncMode;
  total?: number | null;
  processed?: number;
  started_at?: string;
  finished_at?: string | null;
  synced_count?: number;
  removed_count?: number;
  failed_count?: number;
  failures?: Array<{ project_id: number | null; name: string; error: string }>;
  error?: string | null;
  cursor: number;
  logs: SyncLogLine[];
}

export async function startSync(mode: SyncMode): Promise<SyncStatus> {
  const res = await authFetch(`${API_BASE}/sync`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ mode })
  });
  if (!res.ok) {
    const detail = await res.json().then(b => b?.detail).catch(() => null);
    throw new Error(detail || `Falha ao iniciar a operação (HTTP ${res.status})`);
  }
  return res.json();
}

export async function fetchSyncStatus(since = 0): Promise<SyncStatus> {
  const res = await authFetch(`${API_BASE}/sync/status?since=${since}`);
  if (!res.ok) throw new Error(`Falha ao consultar o progresso (HTTP ${res.status})`);
  return res.json();
}

export async function globalSearch(query: string): Promise<SearchResults> {
  const res = await authFetch(`${API_BASE}/search?q=${encodeURIComponent(query)}`);
  if (!res.ok) throw new Error('Erro na busca');
  return res.json();
}

export interface LDAPConfig {
  enabled: boolean;
  server_host: string;
  server_port: number;
  use_ssl: boolean;
  bind_dn: string;
  bind_password?: string;
  base_dn: string;
  user_attribute: string;
}

export async function fetchLDAPConfig(): Promise<LDAPConfig> {
  const res = await authFetch(`${API_BASE}/auth/ldap-config`);
  if (!res.ok) throw new Error('Falha ao carregar configurações de LDAP');
  return res.json();
}

export async function saveLDAPConfig(config: LDAPConfig): Promise<{ message: string }> {
  const res = await authFetch(`${API_BASE}/auth/ldap-config`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config)
  });
  if (!res.ok) {
    const detail = await res.json().then(b => b?.detail).catch(() => null);
    throw new Error(detail || 'Falha ao salvar configuração LDAP');
  }
  return res.json();
}

export async function testLDAPConfig(config: LDAPConfig): Promise<{ success: boolean; message: string }> {
  const res = await authFetch(`${API_BASE}/auth/ldap-config/test`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config)
  });
  if (!res.ok) {
    const detail = await res.json().then(b => b?.detail).catch(() => null);
    throw new Error(detail || 'Falha ao testar conexão LDAP');
  }
  return res.json();
}

export interface JenkinsLastBuild {
  number?: number;
  url?: string;
  building?: boolean;
  result?: string;
  duration_ms?: number;
  timestamp?: number;
  display_name?: string;
  causes?: string[];
  branch?: string;
  commit?: string;
}

export interface JenkinsStatusInfo {
  job: string;
  configured: boolean;
  status: 'SUCCESS' | 'FAILURE' | 'UNSTABLE' | 'ABORTED' | 'BUILDING' | 'NOT_FOUND' | 'UNAUTHORIZED' | 'UNREACHABLE' | 'NOT_CONFIGURED' | 'UNKNOWN';
  message?: string | null;
  job_url?: string;
  last_build?: JenkinsLastBuild | null;
}

export interface JenkinsPipelineItem {
  id: number;
  name: string;
  environment: string;
  job: string;
  server_url?: string | null;
  status_info: JenkinsStatusInfo;
}

export interface JenkinsComponentResponse {
  component_id: number;
  component_name: string;
  jenkins_token_configured: boolean;
  pipelines: JenkinsPipelineItem[];
}

export async function fetchComponentJenkins(id: number): Promise<JenkinsComponentResponse> {
  const res = await authFetch(`${API_BASE}/catalog/${id}/jenkins`);
  if (!res.ok) throw new Error('Falha ao carregar status do Jenkins');
  return res.json();
}

