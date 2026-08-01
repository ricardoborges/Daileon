<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { fetchServerDetail, type ServerItem, type ServerComponentItem } from '$lib/api';
  import { t } from '$lib/i18n';
  import {
    Server,
    Search,
    ExternalLink,
    Box,
    Globe,
    ShieldAlert,
    Cpu,
    ArrowLeft,
    Copy,
    Check,
    Layers,
    Terminal,
    Hash,
    LayoutGrid,
    Table as TableIcon
  } from 'lucide-svelte';

  let serverName = '';
  let server: ServerItem | null = null;
  let loading = true;
  let error: string | null = null;
  let searchQuery = '';
  let copiedIp = false;
  let appsViewMode: 'table' | 'cards' = 'table';

  $: serverName = $page.params.name;

  $: if (serverName) {
    loadServerDetail(serverName);
  }

  async function loadServerDetail(name: string) {
    loading = true;
    error = null;
    try {
      server = await fetchServerDetail(name);
    } catch (e: any) {
      console.error(e);
      error = e.message || $t('serverDetail.errorLoading');
    } finally {
      loading = false;
    }
  }

  function copyToClipboard(text: string) {
    if (!text) return;
    navigator.clipboard.writeText(text);
    copiedIp = true;
    setTimeout(() => {
      copiedIp = false;
    }, 2000);
  }

  $: filteredComponents = (server?.components || []).filter((c) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      c.component_name.toLowerCase().includes(q) ||
      c.owner.toLowerCase().includes(q) ||
      c.component_type.toLowerCase().includes(q) ||
      (c.execution_type || '').toLowerCase().includes(q) ||
      (c.environment || '').toLowerCase().includes(q) ||
      (c.port || '').toLowerCase().includes(q) ||
      (c.os || '').toLowerCase().includes(q) ||
      (c.url || '').toLowerCase().includes(q) ||
      (c.notes || '').toLowerCase().includes(q)
    );
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

  $: executionModes = Array.from(
    new Set((server?.components || []).map((c) => c.execution_type).filter(Boolean))
  );

  $: portsList = Array.from(
    new Set((server?.components || []).map((c) => c.port).filter(Boolean))
  );
</script>

<svelte:head>
  <title>{serverName ? `${serverName} · Servidor` : 'Servidor'} · Daileon</title>
</svelte:head>

<main class="max-w-7xl mx-auto px-6 py-10 space-y-8">
  <!-- Botão de Voltar -->
  <div>
    <a
      href="/servers"
      class="inline-flex items-center gap-2 text-xs font-semibold t-dim hover:t-txt transition-colors group"
    >
      <ArrowLeft class="w-4 h-4 transition-transform group-hover:-translate-x-1" />
      <span>{$t('serverDetail.backToServers')}</span>
    </a>
  </div>

  {#if loading}
    <div class="space-y-6">
      <div class="skeleton h-32"></div>
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div class="skeleton h-24"></div>
        <div class="skeleton h-24"></div>
        <div class="skeleton h-24"></div>
        <div class="skeleton h-24"></div>
      </div>
      <div class="skeleton h-64"></div>
    </div>
  {:else if error || !server}
    <div class="plate p-12 text-center space-y-4" style="--chamfer: 18px;">
      <ShieldAlert class="w-10 h-10 mx-auto t-alert" />
      <h3 class="text-lg font-bold t-txt">{$t('serverDetail.errorLoading')}</h3>
      <p class="t-dim text-xs max-w-md mx-auto">{error || 'Servidor não encontrado.'}</p>
      <a href="/servers" class="btn btn-sm btn-primary inline-flex items-center gap-1 text-xs">
        {$t('serverDetail.backToServers')}
      </a>
    </div>
  {:else}
    <!-- Server Header Box -->
    <div class="plate plate-deep p-6 md:p-8 space-y-6" style="--chamfer: 20px;">
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div class="space-y-3">
          <div class="flex items-center gap-2 text-xs t-visor font-mono">
            <Server class="w-4 h-4" />
            <span>{$t('serverDetail.eyebrow')}</span>
          </div>

          <div class="flex flex-wrap items-center gap-3">
            <h1 class="text-3xl md:text-4xl font-bold font-mono t-txt tracking-tight">
              {server.server_name}
            </h1>

            {#if server.server_ip}
              <div class="flex items-center gap-1.5 bg-emerald-950/50 border border-emerald-500/30 rounded-lg px-3 py-1 text-xs font-mono text-emerald-400">
                <span class="t-faint font-sans">IP:</span>
                <span class="font-bold">{server.server_ip}</span>
                <button
                  on:click={() => copyToClipboard(server?.server_ip || '')}
                  class="ml-1 p-1 hover:text-white transition-colors"
                  title={$t('serverDetail.copyIp')}
                >
                  {#if copiedIp}
                    <Check class="w-3.5 h-3.5 text-emerald-400" />
                  {:else}
                    <Copy class="w-3.5 h-3.5" />
                  {/if}
                </button>
              </div>
            {/if}
          </div>
        </div>

        <!-- Badges de Ambientes -->
        <div class="flex flex-wrap items-center gap-2 md:justify-end">
          {#each server.environments as env}
            <span class="chip {envBadgeClass(env)} uppercase text-xs tracking-wider font-bold px-3 py-1">
              {env}
            </span>
          {/each}
        </div>
      </div>

      <!-- Métricas / Estatísticas do Servidor -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4 border-t border-[var(--line)]">
        <div class="plate p-4 space-y-1 text-center" style="--chamfer: 10px;">
          <Box class="w-4 h-4 mx-auto t-visor" />
          <span class="t-faint text-xs block font-medium">{$t('serverDetail.totalApps')}</span>
          <span class="text-2xl font-bold t-txt">{server.components_count}</span>
        </div>

        <div class="plate p-4 space-y-1 text-center" style="--chamfer: 10px;">
          <Layers class="w-4 h-4 mx-auto t-crest" />
          <span class="t-faint text-xs block font-medium">{$t('serverDetail.hostedEnvs')}</span>
          <span class="text-2xl font-bold t-txt">{server.environments.length}</span>
        </div>

        <div class="plate p-4 space-y-1 text-center" style="--chamfer: 10px;">
          <Terminal class="w-4 h-4 mx-auto text-sky-400" />
          <span class="t-faint text-xs block font-medium">{$t('serverDetail.execModes')}</span>
          <span class="text-2xl font-bold t-txt font-mono">
            {executionModes.length > 0 ? executionModes.join(', ') : '-'}
          </span>
        </div>

        <div class="plate p-4 space-y-1 text-center" style="--chamfer: 10px;">
          <Hash class="w-4 h-4 mx-auto text-purple-400" />
          <span class="t-faint text-xs block font-medium">{$t('serverDetail.portsAllocated')}</span>
          <span class="text-2xl font-bold t-txt font-mono">
            {portsList.length > 0 ? portsList.length : 0}
          </span>
        </div>
      </div>
    </div>

    <!-- Seção de Aplicações Hospedadas -->
    <div class="space-y-6">
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 class="text-xl font-bold t-txt">{$t('serverDetail.hostedApps')}</h2>
          <p class="t-dim text-xs">{$t('serverDetail.hostedAppsSub')}</p>
        </div>

        <!-- Filtro & Alternância de Exibição -->
        <div class="flex items-center gap-3">
          <div class="plate p-2 flex items-center gap-2 w-full md:w-80" style="--chamfer: 10px;">
            <Search class="w-3.5 h-3.5 t-faint shrink-0" />
            <input
              type="text"
              bind:value={searchQuery}
              placeholder={$t('serverDetail.searchPlaceholder')}
              class="bg-transparent border-none outline-none text-xs w-full t-txt placeholder:t-faint font-mono"
            />
            {#if searchQuery}
              <button
                on:click={() => (searchQuery = '')}
                class="btn btn-sm px-1.5 text-[10px] t-faint hover:t-txt"
              >
                Limpar
              </button>
            {/if}
          </div>

          <div class="plate p-1 flex items-center gap-1 shrink-0" style="--chamfer: 8px;">
            <button
              on:click={() => (appsViewMode = 'table')}
              class="btn btn-sm px-2.5 flex items-center gap-1 text-xs {appsViewMode === 'table' ? 'btn-primary' : 't-faint hover:t-txt'}"
              title="Tabela"
            >
              <TableIcon class="w-3.5 h-3.5" />
            </button>
            <button
              on:click={() => (appsViewMode = 'cards')}
              class="btn btn-sm px-2.5 flex items-center gap-1 text-xs {appsViewMode === 'cards' ? 'btn-primary' : 't-faint hover:t-txt'}"
              title="Cards"
            >
              <LayoutGrid class="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {#if filteredComponents.length === 0}
        <div class="plate p-12 text-center space-y-3" style="--chamfer: 14px;">
          <Box class="w-8 h-8 mx-auto t-faint" />
          <h4 class="text-base font-bold t-txt">{$t('serverDetail.noAppsFound')}</h4>
          <p class="t-dim text-xs">
            Nenhuma aplicação cadastrada corresponde aos critérios da busca.
          </p>
        </div>
      {:else if appsViewMode === 'table'}
        <!-- Visão em Tabela de Aplicações -->
        <div class="plate overflow-hidden" style="--chamfer: 14px;">
          <div class="overflow-x-auto">
            <table class="w-full text-left text-xs border-collapse">
              <thead>
                <tr class="border-b border-[var(--line)] bg-[var(--bg-shallow)] text-[11px] uppercase tracking-wider t-faint font-mono">
                  <th class="py-3 px-4 font-bold">{$t('serverDetail.colAppName')}</th>
                  <th class="py-3 px-4 font-bold">{$t('serverDetail.colOwner')}</th>
                  <th class="py-3 px-4 font-bold">{$t('serverDetail.colEnv')}</th>
                  <th class="py-3 px-4 font-bold">{$t('serverDetail.colExecType')}</th>
                  <th class="py-3 px-4 font-bold">{$t('serverDetail.colPort')}</th>
                  <th class="py-3 px-4 font-bold">{$t('serverDetail.colOs')}</th>
                  <th class="py-3 px-4 font-bold">{$t('serverDetail.colUrl')}</th>
                  <th class="py-3 px-4 font-bold text-right">Ação</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-[var(--line)]">
                {#each filteredComponents as comp}
                  <tr class="hover:bg-[var(--bg-hover)] transition-colors">
                    <!-- Nome & Tipo -->
                    <td class="py-3.5 px-4 font-medium">
                      <div class="space-y-0.5">
                        <a
                          href={`/catalog/${comp.component_id}`}
                          class="font-bold text-sm t-txt hover:t-visor transition-colors block truncate max-w-[200px]"
                        >
                          {comp.component_name}
                        </a>
                        <span class="chip text-[9px] py-0 px-1.5">{comp.component_type}</span>
                      </div>
                    </td>

                    <!-- Owner -->
                    <td class="py-3.5 px-4 t-dim">
                      <span class="font-medium t-txt">{comp.owner}</span>
                    </td>

                    <!-- Ambiente -->
                    <td class="py-3.5 px-4">
                      <span class="chip {envBadgeClass(comp.environment)} uppercase text-[9px] font-bold">
                        {comp.environment}
                      </span>
                    </td>

                    <!-- Modo de Execução -->
                    <td class="py-3.5 px-4 font-mono">
                      {#if comp.execution_type}
                        <span class="chip text-[10px] py-0 px-1.5 font-mono">
                          {comp.execution_type}
                        </span>
                      {:else}
                        <span class="t-faint">-</span>
                      {/if}
                    </td>

                    <!-- Porta -->
                    <td class="py-3.5 px-4 font-mono">
                      {#if comp.port}
                        <span class="font-bold text-emerald-400">:{comp.port}</span>
                      {:else}
                        <span class="t-faint">-</span>
                      {/if}
                    </td>

                    <!-- SO -->
                    <td class="py-3.5 px-4 font-mono t-dim">
                      {comp.os || '-'}
                    </td>

                    <!-- URL -->
                    <td class="py-3.5 px-4">
                      {#if comp.url}
                        <a
                          href={comp.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          class="t-visor hover:underline inline-flex items-center gap-1 font-mono text-[11px] truncate max-w-[180px]"
                        >
                          <Globe class="w-3 h-3 shrink-0" />
                          <span class="truncate">{comp.url}</span>
                          <ExternalLink class="w-2.5 h-2.5 shrink-0" />
                        </a>
                      {:else}
                        <span class="t-faint">-</span>
                      {/if}
                    </td>

                    <!-- Ação -->
                    <td class="py-3.5 px-4 text-right">
                      <a
                        href={`/catalog/${comp.component_id}`}
                        class="btn btn-sm btn-ghost px-2 text-xs t-visor hover:t-txt"
                        title="Ver no Catálogo"
                      >
                        {$t('serverDetail.viewCatalogComponent')}
                      </a>
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        </div>
      {:else}
        <!-- Visão em Cards de Aplicações -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          {#each filteredComponents as comp}
            <div class="plate p-5 space-y-3" style="--chamfer: 14px;">
              <div class="flex items-center justify-between gap-2 border-b border-[var(--line)] pb-3">
                <div>
                  <a
                    href={`/catalog/${comp.component_id}`}
                    class="font-bold text-base t-txt hover:t-visor transition-colors"
                  >
                    {comp.component_name}
                  </a>
                  <p class="text-xs t-dim">Time: <strong class="t-txt">{comp.owner}</strong></p>
                </div>
                <div class="flex flex-col items-end gap-1">
                  <span class="chip {envBadgeClass(comp.environment)} uppercase text-[9px] font-bold">
                    {comp.environment}
                  </span>
                  <span class="chip text-[9px] py-0 px-1.5">{comp.component_type}</span>
                </div>
              </div>

              <div class="grid grid-cols-2 gap-2 text-xs t-dim font-mono pt-1">
                {#if comp.execution_type}
                  <div>
                    <span class="t-faint font-sans">Execução:</span>
                    <strong class="t-txt">{comp.execution_type}</strong>
                  </div>
                {/if}
                {#if comp.port}
                  <div>
                    <span class="t-faint font-sans">Porta:</span>
                    <strong class="text-emerald-400">:{comp.port}</strong>
                  </div>
                {/if}
                {#if comp.os}
                  <div class="col-span-2">
                    <span class="t-faint font-sans">Sistema Operacional:</span>
                    <strong class="t-txt">{comp.os}</strong>
                  </div>
                {/if}
              </div>

              {#if comp.url}
                <div class="pt-2 border-t border-[var(--line)]">
                  <a
                    href={comp.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    class="t-visor hover:underline inline-flex items-center gap-1.5 text-xs font-mono truncate max-w-full"
                  >
                    <Globe class="w-3.5 h-3.5 shrink-0" />
                    <span class="truncate">{comp.url}</span>
                    <ExternalLink class="w-3 h-3 shrink-0" />
                  </a>
                </div>
              {/if}

              {#if comp.notes}
                <p class="text-xs t-faint italic border-t border-[var(--line)] pt-2">
                  {comp.notes}
                </p>
              {/if}
            </div>
          {/each}
        </div>
      {/if}
    </div>
  {/if}
</main>
