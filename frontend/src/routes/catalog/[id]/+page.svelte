<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import {
    fetchComponent,
    fetchComponentDocs,
    fetchComponentJenkins,
    fetchComponentCommits,
    type ComponentItem,
    type DocFileItem,
    type JenkinsComponentResponse,
    type ComponentCommitsResponse
  } from '$lib/api';
  import CommitHeatmap from '$lib/components/CommitHeatmap.svelte';
  import { t } from '$lib/i18n';
  import {
    BookOpen,
    ExternalLink,
    ShieldAlert,
    GitBranch,
    ArrowLeft,
    Link2,
    Box,
    Layers,
    Activity,
    RotateCw,
    CheckCircle2,
    XCircle,
    Clock,
    AlertTriangle,
    PlayCircle,
    Server,
    LayoutGrid,
    Table
  } from 'lucide-svelte';

  let component: ComponentItem | null = null;
  let docs: DocFileItem[] = [];
  let jenkinsData: JenkinsComponentResponse | null = null;
  let commitsData: ComponentCommitsResponse | null = null;
  let loading = true;
  let loadingJenkins = false;
  let loadingCommits = false;
  let activeTab: 'overview' | 'deployments' | 'docs' | 'jenkins' = 'overview';
  let deploymentViewMode: 'cards' | 'table' = 'cards';

  $: componentId = parseInt($page.params.id);

  $: {
    const tabParam = $page.url.searchParams.get('tab');
    if (tabParam === 'docs' || tabParam === 'techdocs') {
      activeTab = 'docs';
    } else if (tabParam && ['overview', 'deployments', 'jenkins'].includes(tabParam)) {
      activeTab = tabParam as 'overview' | 'deployments' | 'docs' | 'jenkins';
    }
  }

  $: allLinks = [
    ...(component?.deployments || [])
      .filter((d) => d.url)
      .map((d) => ({
        title: `Ambiente: ${d.environment}`,
        url: d.url!,
        env: d.environment
      })),
    ...(component?.links || []).map((l) => ({
      title: l.title,
      url: l.url,
      env: null
    }))
  ];

  onMount(async () => {
    try {
      [component, docs] = await Promise.all([
        fetchComponent(componentId),
        fetchComponentDocs(componentId)
      ]);
      loadJenkinsData();
      loadCommitsData();
    } catch (e) {
      console.error(e);
    } finally {
      loading = false;
    }
  });

  async function loadJenkinsData() {
    loadingJenkins = true;
    try {
      jenkinsData = await fetchComponentJenkins(componentId);
    } catch (e) {
      console.error('Erro ao carregar dados do Jenkins:', e);
    } finally {
      loadingJenkins = false;
    }
  }

  async function loadCommitsData() {
    loadingCommits = true;
    try {
      commitsData = await fetchComponentCommits(componentId);
    } catch (e) {
      console.error('Erro ao carregar atividade de commits:', e);
    } finally {
      loadingCommits = false;
    }
  }

  function lifecycleLed(lifecycle: string) {
    switch ((lifecycle || '').toLowerCase()) {
      case 'production': return 'led-ok';
      case 'experimental': return 'led-crest';
      case 'deprecated': return 'led-alert';
      default: return '';
    }
  }

  function formatDuration(ms?: number): string {
    if (!ms) return '0s';
    const seconds = Math.floor(ms / 1000);
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const remSecs = seconds % 60;
    return `${minutes}m ${remSecs}s`;
  }

  function formatTimeAgo(timestamp?: number): string {
    if (!timestamp) return '—';
    const diffSeconds = Math.floor((Date.now() - timestamp) / 1000);
    if (diffSeconds < 60) return 'agora mesmo';
    const minutes = Math.floor(diffSeconds / 60);
    if (minutes < 60) return `há ${minutes} min`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `há ${hours} h`;
    const days = Math.floor(hours / 24);
    return `há ${days} d`;
  }

  function envBadgeClass(env: string): string {
    switch ((env || '').toLowerCase()) {
      case 'production':
      case 'prod':
        return 'chip-crest';
      case 'staging':
      case 'homolog':
        return 'chip-visor';
      case 'test':
      case 'ci':
        return 'chip';
      default:
        return 'chip';
    }
  }
</script>

<main class="max-w-7xl mx-auto px-6 py-10 space-y-8">
  <a href="/catalog" class="label inline-flex items-center gap-2 hover:t-visor transition-colors">
    <ArrowLeft class="w-3.5 h-3.5" /> Voltar ao catálogo
  </a>

  {#if loading}
    <div class="skeleton h-64"></div>
  {:else if !component}
    <div class="plate p-20 text-center space-y-4">
      <ShieldAlert class="w-10 h-10 mx-auto t-alert" />
      <h2 class="text-xl font-bold t-txt">Componente não encontrado</h2>
    </div>
  {:else}
    <!-- ===== Ficha técnica ===== -->
    <section class="plate plate-deep overflow-hidden" style="--chamfer: 24px;">
      <div class="absolute inset-0 grid-mesh opacity-60 pointer-events-none"></div>

      <div class="relative p-8 space-y-7">
        <div class="flex flex-wrap items-start justify-between gap-5">
          <div class="space-y-3 min-w-0">
            <div class="flex flex-wrap items-center gap-2">
              <span class="chip chip-visor">{component.type}</span>
              <span class="chip">
                <span class="led {lifecycleLed(component.lifecycle)}"></span>
                {component.lifecycle}
              </span>
              {#if component.has_manifest}
                <span class="chip chip-crest">project-info.yml</span>
              {/if}
            </div>

            <h1 class="text-3xl md:text-4xl font-bold tracking-[-0.035em] t-txt">
              {component.name}
            </h1>

            <p class="t-dim text-sm max-w-2xl leading-relaxed">
              {component.description || 'Sem descrição cadastrada.'}
            </p>
          </div>

          {#if component.gitlab_url}
            <a href={component.gitlab_url} target="_blank" rel="noopener noreferrer" class="btn btn-crest shrink-0">
              <GitBranch class="w-3.5 h-3.5" /> {$t('catalog.repository')}
              <ExternalLink class="w-3 h-3" />
            </a>
          {/if}
        </div>

        <!-- Leituras -->
        <dl class="grid grid-cols-2 lg:grid-cols-4 gap-y-5 gap-x-4 pt-6 border-t border-line">
          <div class="meta">
            <dt>{$t('catalog.owner_team')}</dt>
            <dd>{component.owner}</dd>
          </div>
          <div class="meta">
            <dt>{$t('catalog.lifecycle')}</dt>
            <dd class="flex items-center gap-2">
              <span class="led {lifecycleLed(component.lifecycle)}"></span>
              {component.lifecycle}
            </dd>
          </div>
          <div class="meta">
            <dt>{$t('catalog.domain_solution')}</dt>
            <dd>{component.domain || '—'} / {component.system || '—'}</dd>
          </div>
          <div class="meta">
            <dt>{$t('catalog.jenkins_pipelines')}</dt>
            <dd class={jenkinsData?.pipelines?.length ? 't-visor' : 't-faint'}>
              {jenkinsData?.pipelines?.length ? $t('catalog.pipelines_configured', { count: jenkinsData.pipelines.length }) : $t('catalog.pipelines_none')}
            </dd>
          </div>
        </dl>

        <!-- Abas -->
        <div class="seg">
          <button on:click={() => activeTab = 'overview'} class="seg-item {activeTab === 'overview' ? 'is-active' : ''}">
            <Layers class="w-3 h-3" /> {$t('catalog.tab_overview')}
          </button>
          <button on:click={() => activeTab = 'deployments'} class="seg-item {activeTab === 'deployments' ? 'is-active' : ''}">
            <Server class="w-3 h-3" /> {$t('catalog.tab_deployments', { count: component.deployments?.length || 0 })}
          </button>
          <button on:click={() => activeTab = 'docs'} class="seg-item {activeTab === 'docs' ? 'is-active' : ''}">
            <BookOpen class="w-3 h-3" /> {$t('catalog.tab_techdocs', { count: docs.length })}
          </button>
          <button on:click={() => activeTab = 'jenkins'} class="seg-item {activeTab === 'jenkins' ? 'is-active' : ''}">
            <Activity class="w-3 h-3" /> {$t('catalog.tab_jenkins', { count: jenkinsData?.pipelines?.length || 0 })}
          </button>
        </div>
      </div>
    </section>

    <!-- ===== Conteúdo ===== -->
    {#if activeTab === 'overview'}
      <div class="space-y-5">
        <!-- Gráfico Heatmap de Commits (Estilo GitHub) -->
        <CommitHeatmap
          dailyCounts={commitsData?.daily_counts || {}}
          totalCommits={commitsData?.total_commits || 0}
          loading={loadingCommits}
        />

        <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
          <!-- Links -->
          <section class="plate p-6 space-y-4" style="--chamfer: 16px;">
          <h3 class="label label-visor flex items-center gap-2">
            <Link2 class="w-3.5 h-3.5" /> Links &amp; recursos
          </h3>

          {#if allLinks.length === 0}
            <p class="t-faint text-[13px]">Nenhum link registrado no project-info.yml.</p>
          {:else}
            <ul class="divide-y" style="border-color: var(--line);">
              {#each allLinks as link}
                <li>
                  <a
                    href={link.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    class="flex items-center justify-between gap-3 py-3 text-sm t-dim hover:t-visor transition-colors group"
                  >
                    <div class="flex items-center gap-2 truncate">
                      {#if link.env}
                        <span class="chip {envBadgeClass(link.env)} uppercase text-[9px] font-bold py-0.5 px-1.5 shrink-0">
                          {link.env}
                        </span>
                      {/if}
                      <span class="truncate">{link.title}</span>
                    </div>
                    <ExternalLink class="w-3.5 h-3.5 shrink-0 opacity-50 group-hover:opacity-100" />
                  </a>
                </li>
              {/each}
            </ul>
          {/if}
        </section>

        <!-- Dependências -->
        <section class="plate p-6 space-y-4" style="--chamfer: 16px;">
          <h3 class="label label-visor flex items-center gap-2">
            <Box class="w-3.5 h-3.5" /> Dependências diretas
          </h3>

          {#if component.dependencies.length === 0}
            <p class="t-faint text-[13px]">Nenhuma dependência registrada.</p>
          {:else}
            <ul class="flex flex-wrap gap-2">
              {#each component.dependencies as dep}
                <li class="tag">{dep}</li>
              {/each}
            </ul>
          {/if}
        </section>
      </div>
    </div>

    {:else if activeTab === 'deployments'}
      <section class="space-y-6">
        <div class="plate p-5 flex flex-wrap items-center justify-between gap-4" style="--chamfer: 16px;">
          <div class="flex items-center gap-3">
            <Server class="w-5 h-5 t-visor" />
            <div>
              <h3 class="text-sm font-semibold t-txt">{$t('catalog.deployments_title')}</h3>
              <p class="text-xs t-dim">{$t('catalog.deployments_sub')}</p>
            </div>
          </div>

          {#if component.deployments && component.deployments.length > 0}
            <div class="flex items-center gap-1 bg-surface-2 p-1 border border-line" style="border-radius: 6px;">
              <button
                type="button"
                on:click={() => deploymentViewMode = 'cards'}
                class={`btn btn-sm text-xs gap-1.5 px-2.5 py-1 ${deploymentViewMode === 'cards' ? 'btn-visor font-bold' : 'opacity-70 hover:opacity-100'}`}
                title={$t('catalog.viewModeCards')}
              >
                <LayoutGrid class="w-3.5 h-3.5" />
                <span>{$t('catalog.viewModeCards')}</span>
              </button>
              <button
                type="button"
                on:click={() => deploymentViewMode = 'table'}
                class={`btn btn-sm text-xs gap-1.5 px-2.5 py-1 ${deploymentViewMode === 'table' ? 'btn-visor font-bold' : 'opacity-70 hover:opacity-100'}`}
                title={$t('catalog.viewModeTable')}
              >
                <Table class="w-3.5 h-3.5" />
                <span>{$t('catalog.viewModeTable')}</span>
              </button>
            </div>
          {/if}
        </div>

        {#if !component.deployments || component.deployments.length === 0}
          <div class="plate p-12 text-center space-y-3">
            <Server class="w-8 h-8 mx-auto t-faint" />
            <h4 class="font-medium t-txt text-base">{$t('catalog.deployments_none')}</h4>
            <p class="t-dim text-xs max-w-md mx-auto">
              Declare a seção <code class="text-xs font-mono bg-line px-1.5 py-0.5 rounded">deployments</code> no seu arquivo <code class="text-xs font-mono bg-line px-1.5 py-0.5 rounded">project-info.yml</code> para registrar os servidores e ambientes deste projeto.
            </p>
          </div>
        {:else if deploymentViewMode === 'cards'}
          <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
            {#each component.deployments as dep}
              <div class="plate p-6 space-y-4" style="--chamfer: 16px;">
                <div class="flex items-center justify-between gap-2 border-b border-[var(--line)] pb-3">
                  <div class="flex items-center gap-2">
                    <span class="chip {envBadgeClass(dep.environment)} uppercase text-[10px] tracking-wider font-bold">
                      {dep.environment}
                    </span>
                    {#if dep.execution_type}
                      <span class="chip font-mono text-[10px] py-0 px-2 font-semibold">
                        {dep.execution_type}
                      </span>
                    {/if}
                  </div>
                  {#if dep.url}
                    <a
                      href={dep.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      class="btn btn-crest text-xs py-1 px-2.5 flex items-center gap-1.5"
                    >
                      Acessar URL <ExternalLink class="w-3 h-3" />
                    </a>
                  {/if}
                </div>

                <div class="space-y-3 text-sm">
                  {#if dep.server_name}
                    <div class="flex items-center justify-between">
                      <span class="t-faint text-xs">Servidor:</span>
                      <a
                        href={`/servers/${encodeURIComponent(dep.server_name)}`}
                        class="font-mono text-xs font-bold t-visor hover:underline"
                        title="Ver detalhamento do servidor"
                      >
                        {dep.server_name}
                      </a>
                    </div>
                  {/if}

                  {#if dep.server_ip}
                    <div class="flex items-center justify-between">
                      <span class="t-faint text-xs">Endereço IP:</span>
                      <a
                        href={`/servers/${encodeURIComponent(dep.server_name || dep.server_ip)}`}
                        class="font-mono text-xs text-emerald-400 font-semibold hover:underline"
                        title="Ver detalhamento do servidor"
                      >
                        {dep.server_ip}
                      </a>
                    </div>
                  {/if}

                  {#if dep.os}
                    <div class="flex items-center justify-between">
                      <span class="t-faint text-xs">Sistema Operacional:</span>
                      <span class="t-txt text-xs font-medium">{dep.os}</span>
                    </div>
                  {/if}

                  {#if dep.execution_type}
                    <div class="flex items-center justify-between">
                      <span class="t-faint text-xs">Execução:</span>
                      <span class="t-txt text-xs font-semibold">{dep.execution_type}</span>
                    </div>
                  {/if}

                  {#if dep.port}
                    <div class="flex items-center justify-between">
                      <span class="t-faint text-xs">Porta:</span>
                      <span class="font-mono text-xs t-visor font-bold">:{dep.port}</span>
                    </div>
                  {/if}

                  {#if dep.url}
                    <div>
                      <span class="t-faint text-xs block">URL:</span>
                      <a href={dep.url} target="_blank" rel="noopener noreferrer" class="text-xs t-dim hover:t-visor truncate block font-mono">
                        {dep.url}
                      </a>
                    </div>
                  {/if}

                  {#if dep.notes}
                    <div class="pt-2 border-t border-[var(--line)] text-xs t-dim">
                      <span class="t-faint block text-[11px] mb-0.5">Observações:</span>
                      {dep.notes}
                    </div>
                  {/if}
                </div>
              </div>
            {/each}
          </div>
        {:else}
          <!-- Visão em Tabela -->
          <div class="plate overflow-x-auto" style="--chamfer: 16px;">
            <table class="w-full text-left text-xs divide-y divide-line">
              <thead class="bg-surface-2 font-semibold t-faint uppercase text-[10px] tracking-wider">
                <tr>
                  <th class="p-3.5">Ambiente</th>
                  <th class="p-3.5">Servidor</th>
                  <th class="p-3.5">Endereço IP</th>
                  <th class="p-3.5">SO / Execução</th>
                  <th class="p-3.5">Porta</th>
                  <th class="p-3.5">URL / Acesso</th>
                  <th class="p-3.5">Observações</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-line">
                {#each component.deployments as dep}
                  <tr class="hover:bg-surface-2/50 transition-colors">
                    <td class="p-3.5">
                      <span class="chip {envBadgeClass(dep.environment)} uppercase text-[10px] tracking-wider font-bold">
                        {dep.environment}
                      </span>
                    </td>
                    <td class="p-3.5 font-mono font-bold t-txt">
                      {#if dep.server_name}
                        <a
                          href={`/servers/${encodeURIComponent(dep.server_name)}`}
                          class="t-visor hover:underline"
                          title="Ver detalhamento do servidor"
                        >
                          {dep.server_name}
                        </a>
                      {:else if dep.server_ip}
                        <a
                          href={`/servers/${encodeURIComponent(dep.server_ip)}`}
                          class="t-visor hover:underline"
                          title="Ver detalhamento do servidor"
                        >
                          {dep.server_ip}
                        </a>
                      {:else}
                        <span class="t-faint">—</span>
                      {/if}
                    </td>
                    <td class="p-3.5 font-mono text-emerald-400 font-semibold">
                      {#if dep.server_ip}
                        <a
                          href={`/servers/${encodeURIComponent(dep.server_name || dep.server_ip)}`}
                          class="hover:underline"
                          title="Ver detalhamento do servidor"
                        >
                          {dep.server_ip}
                        </a>
                      {:else}
                        <span class="t-faint">—</span>
                      {/if}
                    </td>
                    <td class="p-3.5">
                      <div class="space-y-0.5">
                        {#if dep.os}
                          <div class="t-txt font-medium">{dep.os}</div>
                        {/if}
                        {#if dep.execution_type}
                          <span class="chip font-mono text-[9px] py-0 px-1.5 font-semibold">
                            {dep.execution_type}
                          </span>
                        {/if}
                        {#if !dep.os && !dep.execution_type}
                          <span class="t-faint">—</span>
                        {/if}
                      </div>
                    </td>
                    <td class="p-3.5 font-mono t-visor font-bold">
                      {dep.port ? `:${dep.port}` : '—'}
                    </td>
                    <td class="p-3.5 max-w-[220px] truncate">
                      {#if dep.url}
                        <a
                          href={dep.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          class="t-visor hover:underline flex items-center gap-1 font-mono truncate"
                        >
                          {dep.url} <ExternalLink class="w-3 h-3 shrink-0" />
                        </a>
                      {:else}
                        <span class="t-faint">—</span>
                      {/if}
                    </td>
                    <td class="p-3.5 t-dim text-[11px] max-w-[250px] truncate">
                      {dep.notes || '—'}
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        {/if}
      </section>

    {:else if activeTab === 'docs'}
      <section class="plate p-6" style="--chamfer: 16px;">
        {#if docs.length === 0}
          <p class="t-faint text-[13px]">Nenhum documento encontrado neste repositório.</p>
        {:else}
          <ul class="space-y-1">
            {#each docs as doc}
              <li>
                <a href={`/catalog/${component.id}/docs/${doc.relative_path}`} class="toc-link">
                  <span class="truncate">{doc.title}</span>
                  <span class="label truncate">{doc.relative_path}</span>
                </a>
              </li>
            {/each}
          </ul>
        {/if}
      </section>

    {:else if activeTab === 'jenkins'}
      <section class="space-y-6">
        <!-- Header da Seção Jenkins -->
        <div class="flex flex-wrap items-center justify-between gap-4 plate p-5" style="--chamfer: 16px;">
          <div class="flex items-center gap-3">
            <Server class="w-5 h-5 t-visor" />
            <div>
              <h3 class="text-sm font-semibold t-txt">Integração Jenkins CI/CD</h3>
              <p class="text-xs t-dim">
                {#if jenkinsData?.jenkins_token_configured}
                  <span class="t-visor">● JENKINS_API_TOKEN ativo</span> — Monitoramento de builds em tempo real.
                {:else}
                  <span class="t-alert">⚠️ JENKINS_API_TOKEN não configurado</span> — Adicione a variável no ambiente para habilitar a consulta automática.
                {/if}
              </p>
            </div>
          </div>

          <button
            on:click={loadJenkinsData}
            disabled={loadingJenkins}
            class="btn btn-crest text-xs flex items-center gap-2"
          >
            <RotateCw class="w-3.5 h-3.5 {loadingJenkins ? 'animate-spin' : ''}" />
            Atualizar Status
          </button>
        </div>

        {#if loadingJenkins && !jenkinsData}
          <div class="skeleton h-48"></div>
        {:else if !jenkinsData || jenkinsData.pipelines.length === 0}
          <div class="plate p-12 text-center space-y-3">
            <Activity class="w-8 h-8 mx-auto t-faint" />
            <h4 class="font-medium t-txt text-base">Nenhuma pipeline cadastrada</h4>
            <p class="t-dim text-xs max-w-md mx-auto">
              Para visualizar os builds do Jenkins aqui, declare a seção <code class="text-xs font-mono bg-line px-1.5 py-0.5 rounded">jenkins</code> no seu arquivo <code class="text-xs font-mono bg-line px-1.5 py-0.5 rounded">project-info.yml</code>.
            </p>
          </div>
        {:else}
          <!-- Cards de Pipelines -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
            {#each jenkinsData.pipelines as pipe}
              {@const status = pipe.status_info.status}
              {@const build = pipe.status_info.last_build}

              <div class="plate p-6 space-y-5 flex flex-col justify-between" style="--chamfer: 16px;">
                <div class="space-y-4">
                  <!-- Header do Card -->
                  <div class="flex items-start justify-between gap-3">
                    <div class="space-y-1 min-w-0">
                      <div class="flex items-center gap-2">
                        <span class="chip {envBadgeClass(pipe.environment)} uppercase text-[10px] tracking-wider font-semibold">
                          {pipe.environment}
                        </span>
                        <span class="font-mono text-xs opacity-75 t-faint truncate">{pipe.job}</span>
                      </div>
                      <h4 class="text-lg font-bold t-txt truncate">{pipe.name}</h4>
                    </div>

                    <!-- Badge de Status -->
                    <div class="shrink-0">
                      {#if status === 'SUCCESS'}
                        <span class="chip chip-visor flex items-center gap-1.5 px-3 py-1 font-semibold text-xs">
                          <CheckCircle2 class="w-4 h-4 text-emerald-400" /> SUCESSO
                        </span>
                      {:else if status === 'FAILURE'}
                        <span class="chip chip-alert flex items-center gap-1.5 px-3 py-1 font-semibold text-xs">
                          <XCircle class="w-4 h-4 text-rose-400" /> FALHA
                        </span>
                      {:else if status === 'BUILDING'}
                        <span class="chip chip-crest flex items-center gap-1.5 px-3 py-1 font-semibold text-xs animate-pulse">
                          <PlayCircle class="w-4 h-4 animate-spin text-cyan-400" /> EXECUTANDO
                        </span>
                      {:else if status === 'UNSTABLE'}
                        <span class="chip flex items-center gap-1.5 px-3 py-1 font-semibold text-xs text-amber-400 border-amber-500/30">
                          <AlertTriangle class="w-4 h-4" /> INSTÁVEL
                        </span>
                      {:else}
                        <span class="chip flex items-center gap-1.5 px-3 py-1 font-semibold text-xs t-faint">
                          {status}
                        </span>
                      {/if}
                    </div>
                  </div>

                  <!-- Detalhes do Último Build -->
                  {#if build}
                    <div class="plate plate-deep p-4 space-y-3" style="--chamfer: 8px;">
                      <div class="flex items-center justify-between text-xs border-b border-[var(--line)] pb-2">
                        <span class="font-mono font-bold t-visor">{build.display_name}</span>
                        <span class="t-dim flex items-center gap-1">
                          <Clock class="w-3 h-3" /> {formatTimeAgo(build.timestamp)}
                        </span>
                      </div>

                      <div class="grid grid-cols-2 gap-3 text-xs">
                        <div>
                          <span class="t-faint block text-[11px]">Duração:</span>
                          <span class="t-txt font-semibold">{formatDuration(build.duration_ms)}</span>
                        </div>
                        {#if build.branch}
                          <div>
                            <span class="t-faint block text-[11px]">Branch:</span>
                            <span class="t-txt font-mono font-semibold">{build.branch}</span>
                          </div>
                        {/if}
                      </div>

                      {#if build.causes && build.causes.length > 0}
                        <div class="text-[11px] t-faint truncate pt-2 border-t border-[var(--line)]">
                          Gatilho: <span class="t-txt font-medium">{build.causes[0]}</span>
                        </div>
                      {/if}
                    </div>
                  {:else if pipe.status_info.message}
                    <div class="text-xs t-alert bg-rose-500/10 border border-rose-500/20 rounded p-3">
                      {pipe.status_info.message}
                    </div>
                  {/if}
                </div>

                <!-- Footer / Link -->
                <div class="pt-2 flex items-center justify-between border-t border-line">
                  <span class="text-xs t-faint">Jenkins REST API</span>
                  {#if pipe.status_info.job_url || build?.url}
                    <a
                      href={build?.url || pipe.status_info.job_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      class="btn btn-crest text-xs py-1.5 px-3 flex items-center gap-1.5"
                    >
                      Abrir no Jenkins <ExternalLink class="w-3 h-3" />
                    </a>
                  {/if}
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </section>
    {/if}
  {/if}
</main>

