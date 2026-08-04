<script lang="ts">
  import { onMount } from 'svelte';
  import { fetchServers, type ServerItem } from '$lib/api';
  import { t } from '$lib/i18n';
  import {
    Server,
    Search,
    ExternalLink,
    Box,
    Globe,
    ShieldAlert,
    AlertTriangle,
    Cpu,
    LayoutGrid,
    Table as TableIcon,
    ChevronRight,
    ArrowRight
  } from 'lucide-svelte';

  let servers: ServerItem[] = [];
  let loading = true;
  let error: string | null = null;
  let searchQuery = '';
  let viewMode: 'cards' | 'table' = 'cards';
  let filterMixedOnly = false;

  onMount(async () => {
    if (typeof window !== 'undefined') {
      const savedMode = localStorage.getItem('daileon_servers_view_mode');
      if (savedMode === 'cards' || savedMode === 'table') {
        viewMode = savedMode;
      }
    }

    try {
      servers = await fetchServers();
    } catch (e: any) {
      console.error(e);
      error = e.message || $t('servers.errorLoading');
    } finally {
      loading = false;
    }
  });

  function setViewMode(mode: 'cards' | 'table') {
    viewMode = mode;
    if (typeof window !== 'undefined') {
      localStorage.setItem('daileon_servers_view_mode', mode);
    }
  }

  function isProdEnv(env: string): boolean {
    const e = (env || '').toLowerCase().trim();
    return e === 'production' || e === 'prod' || e === 'prd';
  }

  function isNonProdEnv(env: string): boolean {
    const e = (env || '').toLowerCase().trim();
    return (
      e === 'test' ||
      e === 'testing' ||
      e === 'homolog' ||
      e === 'homologation' ||
      e === 'staging' ||
      e === 'dev' ||
      e === 'development' ||
      e === 'ci' ||
      e === 'sandbox' ||
      e === 'hml' ||
      e === 'qa' ||
      e.startsWith('qa')
    );
  }

  function isMixedEnvironment(server: ServerItem): boolean {
    const allEnvs = new Set<string>();
    (server.environments || []).forEach((env) => allEnvs.add(env.toLowerCase()));
    (server.components || []).forEach((c) => {
      if (c.environment) allEnvs.add(c.environment.toLowerCase());
    });

    let hasProd = false;
    let hasNonProd = false;

    for (const env of allEnvs) {
      if (isProdEnv(env)) hasProd = true;
      if (isNonProdEnv(env)) hasNonProd = true;
    }

    return hasProd && hasNonProd;
  }

  $: mixedServersCount = servers.filter(isMixedEnvironment).length;

  $: filteredServers = servers.filter((s) => {
    if (filterMixedOnly && !isMixedEnvironment(s)) return false;
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    const matchName = s.server_name.toLowerCase().includes(q);
    const matchIp = (s.server_ip || '').toLowerCase().includes(q);
    const matchEnv = s.environments.some((env) => env.toLowerCase().includes(q));
    const matchComp = s.components.some(
      (c) =>
        c.component_name.toLowerCase().includes(q) ||
        c.owner.toLowerCase().includes(q) ||
        (c.url || '').toLowerCase().includes(q)
    );
    return matchName || matchIp || matchEnv || matchComp;
  });

  function envBadgeClass(env: string): string {
    switch ((env || '').toLowerCase()) {
      case 'production':
      case 'prod':
        return 'chip-crest';
      case 'staging':
      case 'homolog':
      case 'homologation':
        return 'chip-visor';
      case 'test':
      case 'ci':
      case 'dev':
        return 'chip';
      default:
        return 'chip';
    }
  }
</script>

<svelte:head>
  <title>{$t('servers.title')} · Daileon</title>
</svelte:head>

<main class="max-w-7xl mx-auto px-6 py-10 space-y-8">
  <!-- Header da Seção -->
  <section class="space-y-4">
    <div class="flex items-center gap-3">
      <div class="plate plate-deep p-2" style="--chamfer: 10px;">
        <Server class="w-6 h-6 t-visor" />
      </div>
      <div>
        <span class="label">{$t('servers.eyebrow')}</span>
        <h1 class="text-3xl font-bold tracking-[-0.035em] t-txt">{$t('servers.title')}</h1>
      </div>
    </div>
    <p class="t-dim text-sm max-w-2xl leading-relaxed">
      {$t('servers.subtitle')}
    </p>
  </section>

  <!-- Barra de Busca, Métricas & Seletor de Exibição -->
  <div class="grid grid-cols-1 md:grid-cols-12 gap-5 items-center">
    <!-- Input de Busca -->
    <div class="md:col-span-5 plate p-3.5 flex items-center gap-3" style="--chamfer: 12px;">
      <Search class="w-4 h-4 t-faint shrink-0" />
      <input
        type="text"
        bind:value={searchQuery}
        placeholder={$t('servers.searchPlaceholder')}
        class="bg-transparent border-none outline-none text-sm w-full t-txt placeholder:t-faint font-mono"
      />
      {#if filterMixedOnly}
        <button
          on:click={() => (filterMixedOnly = false)}
          class="btn btn-sm px-2 text-[10px] font-bold bg-amber-500/20 border border-amber-500/40 text-amber-500 hover:bg-amber-500/30 flex items-center gap-1 shrink-0"
        >
          <AlertTriangle class="w-3 h-3" />
          Risco Misto (x)
        </button>
      {/if}
      {#if searchQuery}
        <button
          on:click={() => (searchQuery = '')}
          class="btn btn-sm px-2 text-xs t-faint hover:t-txt shrink-0"
        >
          Limpar
        </button>
      {/if}
    </div>

    <!-- Seletor de Modo de Exibição (Cards vs Tabela) -->
    <div class="md:col-span-3 flex items-center justify-center md:justify-end gap-2">
      <div class="plate p-1.5 flex items-center gap-1" style="--chamfer: 8px;">
        <button
          on:click={() => setViewMode('cards')}
          class="btn btn-sm px-3 flex items-center gap-1.5 text-xs font-semibold transition-all {viewMode === 'cards' ? 'btn-primary' : 't-faint hover:t-txt'}"
          title={$t('servers.viewCards')}
        >
          <LayoutGrid class="w-3.5 h-3.5" />
          <span>{$t('servers.viewCards')}</span>
        </button>
        <button
          on:click={() => setViewMode('table')}
          class="btn btn-sm px-3 flex items-center gap-1.5 text-xs font-semibold transition-all {viewMode === 'table' ? 'btn-primary' : 't-faint hover:t-txt'}"
          title={$t('servers.viewTable')}
        >
          <TableIcon class="w-3.5 h-3.5" />
          <span>{$t('servers.viewTable')}</span>
        </button>
      </div>
    </div>

    <!-- Métricas Globais -->
    <div class="md:col-span-4 plate p-3.5 flex items-center justify-around text-center gap-2" style="--chamfer: 12px;">
      <div>
        <span class="t-faint text-xs block">{$t('servers.mappedServers')}</span>
        <span class="text-xl font-bold t-visor">{servers.length}</span>
      </div>
      <div class="w-px h-8 bg-[var(--line)]"></div>
      <div>
        <span class="t-faint text-xs block">{$t('servers.allocatedApps')}</span>
        <span class="text-xl font-bold t-crest">
          {servers.reduce((acc, s) => acc + s.components_count, 0)}
        </span>
      </div>
      {#if mixedServersCount > 0}
        <div class="w-px h-8 bg-[var(--line)]"></div>
        <button
          on:click={() => (filterMixedOnly = !filterMixedOnly)}
          class="text-center group focus:outline-none transition-transform active:scale-95"
          title={$t('servers.filterMixedOnly')}
        >
          <span class="t-faint text-[10px] uppercase font-bold flex items-center justify-center gap-1 text-amber-500">
            <AlertTriangle class="w-3 h-3 text-amber-500 shrink-0" />
            {$t('servers.cohostingRisk')}
          </span>
          <span class="text-xl font-bold text-amber-500 flex items-center justify-center gap-1">
            {mixedServersCount}
            {#if filterMixedOnly}
              <span class="text-[9px] bg-amber-500/20 border border-amber-500/40 text-amber-500 px-1 py-0.2 rounded font-sans uppercase">Filtrado</span>
            {/if}
          </span>
        </button>
      {/if}
    </div>
  </div>

  <!-- Conteúdo: Servidores -->
  {#if loading}
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div class="skeleton h-56"></div>
      <div class="skeleton h-56"></div>
    </div>
  {:else if error}
    <div class="plate p-12 text-center space-y-4">
      <ShieldAlert class="w-10 h-10 mx-auto t-alert" />
      <h3 class="text-lg font-bold t-txt">{$t('servers.errorLoading')}</h3>
      <p class="t-dim text-xs max-w-md mx-auto">{error}</p>
    </div>
  {:else if filteredServers.length === 0}
    <div class="plate p-16 text-center space-y-4" style="--chamfer: 20px;">
      <Server class="w-10 h-10 mx-auto t-faint" />
      <h3 class="text-lg font-bold t-txt">{$t('servers.noServersTitle')}</h3>
      <p class="t-dim text-xs max-w-md mx-auto leading-relaxed">
        {#if searchQuery}
          {$t('servers.noServersSubSearch', { query: searchQuery })}
        {:else if filterMixedOnly}
          Nenhum servidor com risco de co-hospedagem (Prod + Teste) foi encontrado.
        {:else}
          {$t('servers.noServersSubEmpty')}
        {/if}
      </p>
    </div>
  {:else if viewMode === 'cards'}
    <!-- Visão em Cards -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      {#each filteredServers as server}
        <div
          class="plate plate-deep p-6 space-y-5 flex flex-col justify-between transition-all group relative overflow-hidden {isMixedEnvironment(server) ? 'border-amber-500/40 shadow-[0_0_15px_rgba(245,158,11,0.06)]' : 'hover:border-[var(--line-bright)]'}"
          style="--chamfer: 18px;"
        >
          <div class="space-y-4">
            <!-- Header do Card do Servidor -->
            <div class="flex items-start justify-between gap-3 border-b border-[var(--line)] pb-4">
              <div class="space-y-1.5 min-w-0">
                <div class="flex items-center gap-2">
                  <a
                    href={`/servers/${encodeURIComponent(server.server_name)}`}
                    class="flex items-center gap-2 group-hover:t-visor transition-colors"
                  >
                    <Cpu class="w-4 h-4 t-visor shrink-0" />
                    <h3 class="text-xl font-bold font-mono t-txt truncate group-hover:underline">{server.server_name}</h3>
                  </a>
                </div>

                {#if server.server_ip}
                  <div class="flex items-center gap-2 text-xs">
                    <span class="t-faint">IP:</span>
                    <span class="chip chip-net text-[11px] px-2 py-0.5">
                      {server.server_ip}
                    </span>
                  </div>
                {/if}
              </div>

              <!-- Badges de Ambientes no Servidor & Alerta Misto -->
              <div class="flex flex-col items-end gap-1.5 max-w-[200px]">
                {#if isMixedEnvironment(server)}
                  <span
                    class="chip bg-amber-500/15 border border-amber-500/40 text-amber-500 text-[10px] font-bold uppercase tracking-wider flex items-center gap-1 px-2 py-0.5 rounded-full"
                    title={$t('servers.mixedUsageWarning')}
                  >
                    <AlertTriangle class="w-3 h-3 shrink-0" />
                    <span>{$t('servers.mixedUsageBadge')}</span>
                  </span>
                {/if}
                <div class="flex flex-wrap items-center gap-1.5 justify-end">
                  {#each server.environments as env}
                    <span class="chip {envBadgeClass(env)} uppercase text-[9px] tracking-wider font-bold">
                      {env}
                    </span>
                  {/each}
                </div>
              </div>
            </div>

            <!-- Banner Alerta Interno para Co-hospedagem -->
            {#if isMixedEnvironment(server)}
              <div class="plate p-3 bg-amber-500/10 border border-amber-500/30 text-amber-600 dark:text-amber-400 flex items-start gap-2.5 text-xs" style="--chamfer: 8px;">
                <AlertTriangle class="w-4 h-4 shrink-0 text-amber-500 mt-0.5" />
                <div class="space-y-0.5">
                  <strong class="font-bold block">{$t('servers.mixedUsageBadge')}</strong>
                  <p class="text-[11px] leading-snug opacity-90">
                    {$t('servers.mixedUsageWarning')}
                  </p>
                </div>
              </div>
            {/if}

            <!-- Lista de Aplicações Instaladas -->
            <div class="space-y-3">
              <div class="flex items-center justify-between text-xs t-faint font-medium">
                <span class="flex items-center gap-1.5">
                  <Box class="w-3.5 h-3.5 t-visor" /> Aplicações hospedadas ({server.components_count}):
                </span>
              </div>

              <div class="space-y-2.5 max-h-64 overflow-y-auto pr-1">
                {#each server.components as comp}
                  <div class="plate p-3 space-y-1.5 text-xs hover:border-[var(--line-bright)] transition-colors" style="--chamfer: 8px;">
                    <div class="flex items-center justify-between gap-2">
                      <a
                        href={`/catalog/${comp.component_id}`}
                        class="font-bold t-txt hover:t-visor transition-colors text-sm truncate"
                      >
                        {comp.component_name}
                      </a>
                      <div class="flex items-center gap-1.5 shrink-0">
                        {#if comp.execution_type}
                          <span class="chip font-mono text-[9px] py-0 px-1.5 font-semibold">
                            {comp.execution_type}
                          </span>
                        {/if}
                        <span class="chip text-[10px] py-0 px-1.5">{comp.component_type}</span>
                        <span class="chip {envBadgeClass(comp.environment)} uppercase text-[9px] py-0 px-1.5 font-bold">
                          {comp.environment}
                        </span>
                      </div>
                    </div>

                    <div class="flex items-center justify-between text-[11px] t-dim pt-1 border-t border-[var(--line)]">
                      <div>
                        <span class="t-faint">Owner:</span> <strong class="t-txt">{comp.owner}</strong>
                      </div>
                      {#if comp.port}
                        <div>
                          <span class="t-faint">Porta:</span> <span class="font-mono t-visor font-bold">:{comp.port}</span>
                        </div>
                      {/if}
                    </div>
                  </div>
                {/each}
              </div>
            </div>
          </div>

          <!-- Botão Ver Detalhes -->
          <div class="pt-2 border-t border-[var(--line)] flex justify-end">
            <a
              href={`/servers/${encodeURIComponent(server.server_name)}`}
              class="btn btn-sm btn-primary px-4 flex items-center gap-1.5 text-xs"
            >
              <span>{$t('servers.viewDetails')}</span>
              <ArrowRight class="w-3.5 h-3.5" />
            </a>
          </div>
        </div>
      {/each}
    </div>
  {:else}
    <!-- Visão em Tabela -->
    <div class="plate overflow-hidden" style="--chamfer: 14px;">
      <div class="overflow-x-auto">
        <table class="w-full text-left text-xs border-collapse">
          <thead>
            <tr class="border-b border-[var(--line)] bg-[var(--bg-shallow)] text-[11px] uppercase tracking-wider t-faint font-mono">
              <th class="py-3.5 px-4 font-bold">{$t('servers.colServer')}</th>
              <th class="py-3.5 px-4 font-bold">{$t('servers.colEnvs')}</th>
              <th class="py-3.5 px-4 font-bold">{$t('servers.colAppsCount')}</th>
              <th class="py-3.5 px-4 font-bold text-right">{$t('servers.colActions')}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-[var(--line)]">
            {#each filteredServers as server}
              <tr class="hover:bg-[var(--bg-hover)] transition-colors group {isMixedEnvironment(server) ? 'bg-amber-500/5' : ''}">
                <!-- Servidor / IP -->
                <td class="py-4 px-4">
                  <a
                    href={`/servers/${encodeURIComponent(server.server_name)}`}
                    class="space-y-1 block group-hover:t-visor transition-colors"
                  >
                    <div class="flex items-center gap-2 font-mono font-bold text-sm t-txt group-hover:underline">
                      <Cpu class="w-4 h-4 t-visor shrink-0" />
                      {server.server_name}
                      {#if isMixedEnvironment(server)}
                        <span
                          class="chip bg-amber-500/15 border border-amber-500/40 text-amber-500 text-[9px] font-bold uppercase tracking-wider inline-flex items-center gap-1 px-1.5 py-0.5 rounded"
                          title={$t('servers.mixedUsageWarning')}
                        >
                          <AlertTriangle class="w-3 h-3 shrink-0" />
                          {$t('servers.mixedUsageShortBadge')}
                        </span>
                      {/if}
                    </div>
                    {#if server.server_ip}
                      <span class="chip chip-net text-[11px] px-2 py-0.5">
                        {server.server_ip}
                      </span>
                    {/if}
                  </a>
                </td>

                <!-- Ambientes -->
                <td class="py-4 px-4">
                  <div class="flex flex-wrap items-center gap-1.5">
                    {#each server.environments as env}
                      <span class="chip {envBadgeClass(env)} uppercase text-[9px] tracking-wider font-bold">
                        {env}
                      </span>
                    {/each}
                  </div>
                </td>

                <!-- Aplicações Hospedadas -->
                <td class="py-4 px-4">
                  <div class="space-y-1.5">
                    <span class="chip font-mono font-bold text-[11px] t-visor">
                      {server.components_count} {server.components_count === 1 ? 'aplicação' : 'aplicações'}
                    </span>
                    <div class="flex flex-wrap gap-1 max-w-md">
                      {#each server.components.slice(0, 4) as comp}
                        <a
                          href={`/catalog/${comp.component_id}`}
                          class="text-[10px] bg-line-soft hover:bg-surface-3 px-1.5 py-0.5 rounded font-medium t-txt hover:t-visor transition-colors truncate max-w-[120px]"
                          title={`${comp.component_name} (${comp.environment})`}
                        >
                          {comp.component_name}
                        </a>
                      {/each}
                      {#if server.components.length > 4}
                        <span class="text-[10px] t-faint px-1">+{server.components.length - 4} mais</span>
                      {/if}
                    </div>
                  </div>
                </td>

                <!-- Ações -->
                <td class="py-4 px-4 text-right">
                  <a
                    href={`/servers/${encodeURIComponent(server.server_name)}`}
                    class="btn btn-sm btn-primary px-3 inline-flex items-center gap-1 text-xs"
                  >
                    <span>{$t('servers.viewDetails')}</span>
                    <ChevronRight class="w-3.5 h-3.5" />
                  </a>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>
  {/if}
</main>
