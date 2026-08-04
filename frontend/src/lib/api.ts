import { getAuthHeader, auth } from '$lib/auth';

export interface DeploymentItem {
  id?: number;
  environment: string;
  url?: string | null;
  server_name?: string | null;
  server_ip?: string | null;
  os?: string | null;
  execution_type?: string | null;
  port?: string | null;
  notes?: string | null;
}

export interface ServerComponentItem {
  deployment_id: number;
  component_id: number;
  component_name: string;
  component_type: string;
  owner: string;
  environment: string;
  url?: string | null;
  os?: string | null;
  execution_type?: string | null;
  port?: string | null;
  notes?: string | null;
}

export interface ServerItem {
  server_name: string;
  server_ip?: string | null;
  environments: string[];
  components_count: number;
  components: ServerComponentItem[];
}

/** Componente como ele aparece dentro de um grupo (domínio ou solução). */
export interface GroupedComponentItem {
  id: number;
  gitlab_project_id: number;
  name: string;
  description?: string | null;
  kind: string;
  type: string;
  lifecycle: string;
  owner: string;
  domain?: string | null;
  solution?: string | null;
  /** @deprecated alias de `solution`, mantido só para compatibilidade. */
  system?: string | null;
  gitlab_url: string;
  has_manifest: boolean;
  docs_count?: number;
  /** Só vem no detalhe do grupo. */
  tags?: string[];
  /** Só vem no detalhe do grupo. */
  deployments_count?: number;
}

/** @deprecated use `GroupedComponentItem`. */
export type DomainComponentItem = GroupedComponentItem;

export interface DomainItem {
  domain: string;
  solutions: string[];
  /** @deprecated alias de `solutions`. */
  systems: string[];
  owners: string[];
  components_count: number;
  components: GroupedComponentItem[];
}

export interface SolutionItem {
  solution: string;
  domains: string[];
  owners: string[];
  components_count: number;
  components: GroupedComponentItem[];
}

export interface RiskItem {
  id?: number;
  severity: 'critical' | 'warning' | 'info';
  category: string;
  title: string;
  description: string;
  file_path?: string | null;
  recommendation: string;
  created_at?: string | null;
}

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
  solution?: string;
  system?: string;
  gitlab_url: string;
  default_branch?: string;
  docs_dir?: string;
  docs_index?: string;
  has_manifest: boolean;
  docs_count?: number;
  tags: string[];
  links: Array<{ title: string; url: string; icon?: string }>;
  dependencies: string[];
  deployments?: DeploymentItem[];
  risks?: RiskItem[];
  critical_risks_count?: number;
  warning_risks_count?: number;
  gitlab_created_at?: string;
  /** Commit mais antigo do repositório; preserva a idade de projetos migrados. */
  first_commit_at?: string;
  last_activity_at?: string;
  updated_at?: string;
}


/** Nó do grafo de dependências: um componente do catálogo ou um alvo não resolvido. */
export interface GraphNode {
  /** `c<id>` para componentes, `u<n>` para alvos que não existem no catálogo. */
  id: string;
  component_id: number | null;
  name: string;
  kind?: string | null;
  type?: string | null;
  lifecycle?: string | null;
  owner?: string | null;
  domain?: string | null;
  solution?: string | null;
  /** `false` quando o nome declarado não casa com nenhum componente. */
  resolved: boolean;
  /** `false` para vizinhos trazidos só como contexto, fora do recorte pedido. */
  in_scope: boolean;
  is_root: boolean;
}

export interface GraphEdge {
  source: string;
  target: string;
  target_name: string;
  resolved: boolean;
  in_cycle: boolean;
}

export interface GraphCycle {
  nodes: string[];
  names: string[];
}

export interface DependencyGraph {
  scope: { kind: 'catalog' | 'root' | 'domain' | 'solution'; value: string | null; depth: number | null };
  nodes: GraphNode[];
  edges: GraphEdge[];
  cycles: GraphCycle[];
  /** Nomes declarados em `dependencies` que não existem no catálogo. */
  unresolved: string[];
  /** Projetos do escopo sem nenhuma dependência, omitidos do diagrama. */
  isolated_count: number;
  stats: { components_total: number; edges_total: number; nodes_shown: number; edges_shown: number };
}

export interface GraphQuery {
  root?: number;
  depth?: number;
  domain?: string;
  solution?: string;
  includeIsolated?: boolean;
}

export async function fetchDependencyGraph(query: GraphQuery = {}): Promise<DependencyGraph> {
  const params = new URLSearchParams();
  if (query.root !== undefined) params.append('root', String(query.root));
  if (query.depth !== undefined) params.append('depth', String(query.depth));
  if (query.domain) params.append('domain', query.domain);
  if (query.solution) params.append('solution', query.solution);
  if (query.includeIsolated) params.append('include_isolated', 'true');

  const res = await authFetch(`${API_BASE}/graph?${params.toString()}`);
  if (!res.ok) {
    if (res.status === 404) throw new Error('Escopo não encontrado no catálogo');
    throw new Error('Falha ao carregar o grafo de dependências');
  }
  return res.json();
}

export type DocType = 'markdown' | 'pdf' | 'image' | 'docx';

export interface DocFileItem {
  id: number;
  relative_path: string;
  title: string;
  doc_type: DocType;
  size_bytes?: number | null;
  updated_at?: string;
}

export interface DocSearchHit {
  id: number;
  relative_path: string;
  title: string;
  doc_type: DocType;
  /** O termo aparece no nome/título do arquivo, não só no conteúdo. */
  in_name: boolean;
  /** Trecho do conteúdo em volta do termo; nulo quando o acerto foi só no nome. */
  snippet: string | null;
}

export interface DocFileDetail extends DocFileItem {
  /** Nulo para documentos binários — use `fetchDocRaw` nesses casos. */
  content_markdown: string | null;
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

/** Busca por nome, título ou conteúdo dentro das docs de um único componente. */
export async function searchComponentDocs(id: number, q: string): Promise<DocSearchHit[]> {
  const res = await authFetch(`${API_BASE}/catalog/${id}/docs-search?q=${encodeURIComponent(q)}`);
  if (!res.ok) throw new Error('Falha ao buscar nos documentos');
  const data = await res.json();
  return data.results ?? [];
}

/** Codifica cada segmento, preservando as barras que separam os diretórios. */
function encodeDocPath(docPath: string): string {
  return docPath.split('/').map(encodeURIComponent).join('/');
}

export async function fetchDocContent(id: number, docPath: string): Promise<DocFileDetail> {
  const res = await authFetch(`${API_BASE}/catalog/${id}/docs/${encodeDocPath(docPath)}`);
  if (!res.ok) throw new Error('Conteúdo do documento não encontrado');
  return res.json();
}

/**
 * Baixa os bytes de um documento binário (PDF). O endpoint exige o header de
 * autenticação, que um `<iframe src>` não consegue enviar — daí o blob.
 */
export async function fetchDocRaw(id: number, docPath: string): Promise<Blob> {
  const res = await authFetch(`${API_BASE}/catalog/${id}/docs-raw/${encodeDocPath(docPath)}`);
  if (!res.ok) throw new Error('Arquivo do documento não encontrado');
  return res.blob();
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
  /** 0 quando a operação abrange o catálogo inteiro. */
  scoped_project_count?: number;
  /** Pasta usada no lugar da declarada no manifesto; null = manifesto. */
  docs_dir?: string | null;
  index_images?: boolean;
  cursor: number;
  logs: SyncLogLine[];
}

/** Ajustes que só acompanham uma sincronização de projetos escolhidos. */
export interface SyncOptions {
  /** Pasta a varrer no lugar da declarada em `spec.docs.dir`. */
  docsDir?: string;
  /** Indexar as imagens encontradas na varredura. */
  indexImages?: boolean;
}

export interface SyncableProject {
  id: number;
  name: string;
  path: string;
  web_url?: string | null;
  in_catalog: boolean;
}

/** Projetos do GitLab elegíveis para uma sincronização individual. */
export async function fetchSyncableProjects(): Promise<SyncableProject[]> {
  const res = await authFetch(`${API_BASE}/sync/projects`);
  if (!res.ok) {
    const detail = await res.json().then(b => b?.detail).catch(() => null);
    throw new Error(detail || `Falha ao listar os projetos (HTTP ${res.status})`);
  }
  return res.json();
}

export async function startSync(
  mode: SyncMode,
  projectIds?: number[],
  options: SyncOptions = {}
): Promise<SyncStatus> {
  const res = await authFetch(`${API_BASE}/sync`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      mode,
      project_ids: projectIds?.length ? projectIds : null,
      docs_dir: options.docsDir?.trim() || null,
      index_images: options.indexImages ?? true
    })
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

export interface ComponentCommitsResponse {
  component_id: number;
  component_name: string;
  gitlab_project_id: number;
  total_commits: number;
  since: string;
  until: string;
  daily_counts: Record<string, number>;
}

export async function fetchComponentCommits(id: number, days = 365): Promise<ComponentCommitsResponse> {
  const res = await authFetch(`${API_BASE}/catalog/${id}/commits?days=${days}`);
  if (!res.ok) throw new Error('Falha ao carregar atividade de commits');
  return res.json();
}


export interface OrganizationConfig {
  name: string;
  acronym: string;
}

export async function fetchOrgConfig(): Promise<OrganizationConfig> {
  const res = await fetch(`${API_BASE}/org-config`);
  if (!res.ok) throw new Error('Falha ao carregar configurações da organização');
  return res.json();
}

export async function saveOrgConfig(config: OrganizationConfig): Promise<{ message: string }> {
  const res = await authFetch(`${API_BASE}/org-config`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config)
  });
  if (!res.ok) {
    const detail = await res.json().then(b => b?.detail).catch(() => null);
    throw new Error(detail || 'Falha ao salvar configurações da organização');
  }
  return res.json();
}

export async function fetchServers(): Promise<ServerItem[]> {
  const res = await authFetch(`${API_BASE}/servers`);
  if (!res.ok) throw new Error('Falha ao carregar lista de servidores');
  return res.json();
}

export async function fetchServerDetail(serverName: string): Promise<ServerItem> {
  const res = await authFetch(`${API_BASE}/servers/${encodeURIComponent(serverName)}`);
  if (!res.ok) {
    if (res.status === 404) throw new Error('Servidor não encontrado');
    throw new Error('Falha ao carregar detalhes do servidor');
  }
  return res.json();
}

export async function fetchDomains(): Promise<DomainItem[]> {
  const res = await authFetch(`${API_BASE}/domains`);
  if (!res.ok) throw new Error('Falha ao carregar lista de domínios');
  return res.json();
}

export async function fetchDomainDetail(domainName: string): Promise<DomainItem> {
  const res = await authFetch(`${API_BASE}/domains/${encodeURIComponent(domainName)}`);
  if (!res.ok) {
    if (res.status === 404) throw new Error('Domínio não encontrado');
    throw new Error('Falha ao carregar detalhes do domínio');
  }
  return res.json();
}

export async function fetchSolutions(): Promise<SolutionItem[]> {
  const res = await authFetch(`${API_BASE}/solutions`);
  if (!res.ok) throw new Error('Falha ao carregar lista de soluções');
  return res.json();
}

export async function fetchSolutionDetail(solutionName: string): Promise<SolutionItem> {
  const res = await authFetch(`${API_BASE}/solutions/${encodeURIComponent(solutionName)}`);
  if (!res.ok) {
    if (res.status === 404) throw new Error('Solução não encontrada');
    throw new Error('Falha ao carregar detalhes da solução');
  }
  return res.json();
}



