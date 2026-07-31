<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import {
    fetchComponent,
    fetchComponentDocs,
    fetchComponentJenkins,
    type ComponentItem,
    type DocFileItem,
    type JenkinsComponentResponse
  } from '$lib/api';
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
    Server
  } from 'lucide-svelte';

  let component: ComponentItem | null = null;
  let docs: DocFileItem[] = [];
  let jenkinsData: JenkinsComponentResponse | null = null;
  let loading = true;
  let loadingJenkins = false;
  let activeTab: 'overview' | 'docs' | 'jenkins' = 'overview';

  $: componentId = parseInt($page.params.id);

  onMount(async () => {
    try {
      [component, docs] = await Promise.all([
        fetchComponent(componentId),
        fetchComponentDocs(componentId)
      ]);
      loadJenkinsData();
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
              <GitBranch class="w-3.5 h-3.5" /> Repositório
              <ExternalLink class="w-3 h-3" />
            </a>
          {/if}
        </div>

        <!-- Leituras -->
        <dl class="grid grid-cols-2 lg:grid-cols-4 gap-y-5 gap-x-4 pt-6 border-t border-line">
          <div class="meta">
            <dt>Owner / Time</dt>
            <dd>{component.owner}</dd>
          </div>
          <div class="meta">
            <dt>Lifecycle</dt>
            <dd class="flex items-center gap-2">
              <span class="led {lifecycleLed(component.lifecycle)}"></span>
              {component.lifecycle}
            </dd>
          </div>
          <div class="meta">
            <dt>Domínio / Sistema</dt>
            <dd>{component.domain || '—'} / {component.system || '—'}</dd>
          </div>
          <div class="meta">
            <dt>Pipelines Jenkins</dt>
            <dd class={jenkinsData?.pipelines?.length ? 't-visor' : 't-faint'}>
              {jenkinsData?.pipelines?.length ? `${jenkinsData.pipelines.length} configurada(s)` : 'Nenhuma'}
            </dd>
          </div>
        </dl>

        <!-- Abas -->
        <div class="seg">
          <button on:click={() => activeTab = 'overview'} class="seg-item {activeTab === 'overview' ? 'is-active' : ''}">
            <Layers class="w-3 h-3" /> Visão geral
          </button>
          <button on:click={() => activeTab = 'docs'} class="seg-item {activeTab === 'docs' ? 'is-active' : ''}">
            <BookOpen class="w-3 h-3" /> TechDocs ({docs.length})
          </button>
          <button on:click={() => activeTab = 'jenkins'} class="seg-item {activeTab === 'jenkins' ? 'is-active' : ''}">
            <Activity class="w-3 h-3" /> Pipelines Jenkins ({jenkinsData?.pipelines?.length || 0})
          </button>
        </div>
      </div>
    </section>

    <!-- ===== Conteúdo ===== -->
    {#if activeTab === 'overview'}
      <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
        <!-- Links -->
        <section class="plate p-6 space-y-4" style="--chamfer: 16px;">
          <h3 class="label label-visor flex items-center gap-2">
            <Link2 class="w-3.5 h-3.5" /> Links &amp; recursos
          </h3>

          {#if component.links.length === 0}
            <p class="t-faint text-[13px]">Nenhum link registrado no project-info.yml.</p>
          {:else}
            <ul class="divide-y" style="border-color: var(--line);">
              {#each component.links as link}
                <li>
                  <a
                    href={link.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    class="flex items-center justify-between gap-3 py-3 text-sm t-dim hover:t-visor transition-colors group"
                  >
                    <span class="truncate">{link.title}</span>
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

