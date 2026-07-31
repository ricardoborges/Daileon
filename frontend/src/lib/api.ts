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

export async function fetchCatalog(filters?: { owner?: string; type?: string; lifecycle?: string; tag?: string }): Promise<ComponentItem[]> {
  const params = new URLSearchParams();
  if (filters?.owner) params.append('owner', filters.owner);
  if (filters?.type) params.append('type', filters.type);
  if (filters?.lifecycle) params.append('lifecycle', filters.lifecycle);
  if (filters?.tag) params.append('tag', filters.tag);

  const res = await fetch(`${API_BASE}/catalog?${params.toString()}`);
  if (!res.ok) throw new Error('Falha ao carregar catálogo');
  return res.json();
}

export async function fetchComponent(id: number): Promise<ComponentItem> {
  const res = await fetch(`${API_BASE}/catalog/${id}`);
  if (!res.ok) throw new Error('Componente não encontrado');
  return res.json();
}

export async function fetchComponentDocs(id: number): Promise<DocFileItem[]> {
  const res = await fetch(`${API_BASE}/catalog/${id}/docs`);
  if (!res.ok) throw new Error('Docs não encontradas');
  return res.json();
}

export async function fetchDocContent(id: number, docPath: string): Promise<DocFileDetail> {
  const res = await fetch(`${API_BASE}/catalog/${id}/docs/${encodeURIComponent(docPath)}`);
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
  /** `null` enquanto o total de passos ainda é desconhecido. */
  total?: number | null;
  processed?: number;
  started_at?: string;
  finished_at?: string | null;
  synced_count?: number;
  removed_count?: number;
  failed_count?: number;
  failures?: Array<{ project_id: number | null; name: string; error: string }>;
  error?: string | null;
  /** Passar como `since` no próximo poll para receber só as linhas novas. */
  cursor: number;
  logs: SyncLogLine[];
}

/** Dispara a operação; ela roda em segundo plano no backend. */
export async function startSync(mode: SyncMode): Promise<SyncStatus> {
  const res = await fetch(`${API_BASE}/sync`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ mode })
  });
  if (!res.ok) {
    // Sem o detalhe do backend, qualquer falha de infraestrutura aparecia
    // como se fosse um erro do GitLab.
    const detail = await res.json().then(b => b?.detail).catch(() => null);
    throw new Error(detail || `Falha ao iniciar a operação (HTTP ${res.status})`);
  }
  return res.json();
}

export async function fetchSyncStatus(since = 0): Promise<SyncStatus> {
  const res = await fetch(`${API_BASE}/sync/status?since=${since}`);
  if (!res.ok) throw new Error(`Falha ao consultar o progresso (HTTP ${res.status})`);
  return res.json();
}

export async function globalSearch(query: string): Promise<SearchResults> {
  const res = await fetch(`${API_BASE}/search?q=${encodeURIComponent(query)}`);
  if (!res.ok) throw new Error('Erro na busca');
  return res.json();
}
