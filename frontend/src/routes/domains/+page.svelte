<script lang="ts">
  import { onMount } from 'svelte';
  import { fetchDomains, type DomainItem } from '$lib/api';
  import { t } from '$lib/i18n';
  import {
    FolderGit2,
    Search,
    Box,
    Globe,
    ShieldAlert,
    Cpu,
    LayoutGrid,
    Table as TableIcon,
    ChevronRight,
    ArrowRight,
    Users,
    Layers
  } from 'lucide-svelte';

  let domains: DomainItem[] = [];
  let loading = true;
  let error: string | null = null;
  let searchQuery = '';
  let viewMode: 'cards' | 'table' = 'cards';

  onMount(async () => {
    if (typeof window !== 'undefined') {
      const savedMode = localStorage.getItem('daileon_domains_view_mode');
      if (savedMode === 'cards' || savedMode === 'table') {
        viewMode = savedMode;
      }
    }

    try {
      domains = await fetchDomains();
    } catch (e: any) {
      console.error(e);
      error = e.message || $t('domains.errorLoading');
    } finally {
      loading = false;
    }
  });

  function setViewMode(mode: 'cards' | 'table') {
    viewMode = mode;
    if (typeof window !== 'undefined') {
      localStorage.setItem('daileon_domains_view_mode', mode);
    }
  }

  $: filteredDomains = domains.filter((d) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    const matchDomain = d.domain.toLowerCase().includes(q);
    const matchOwners = d.owners.some((owner) => owner.toLowerCase().includes(q));
    const matchSystems = d.systems.some((sys) => sys.toLowerCase().includes(q));
    const matchComp = d.components.some(
      (c) =>
        c.name.toLowerCase().includes(q) ||
        c.owner.toLowerCase().includes(q) ||
        (c.description || '').toLowerCase().includes(q)
    );
    return matchDomain || matchOwners || matchSystems || matchComp;
  });

  $: totalComponentsCount = domains.reduce((acc, d) => acc + d.components_count, 0);
</script>

<svelte:head>
  <title>{$t('domains.title')} · Daileon</title>
</svelte:head>

<main class="max-w-7xl mx-auto px-6 py-10 space-y-8">
  <!-- Header da Seção -->
  <section class="space-y-4">
    <div class="flex items-center gap-3">
      <div class="plate plate-deep p-2" style="--chamfer: 10px;">
        <FolderGit2 class="w-6 h-6 t-visor" />
      </div>
      <div>
        <span class="label">{$t('domains.eyebrow')}</span>
        <h1 class="text-3xl font-bold tracking-[-0.035em] t-txt">{$t('domains.title')}</h1>
      </div>
    </div>
    <p class="t-dim text-sm max-w-2xl leading-relaxed">
      {$t('domains.subtitle')}
    </p>
  </section>

  <!-- Filtros e Controles -->
  <section class="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
    <!-- Campo de Busca -->
    <div class="relative flex-1 max-w-lg">
      <Search class="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 t-faint pointer-events-none" />
      <input
        type="text"
        bind:value={searchQuery}
        placeholder={$t('domains.searchPlaceholder')}
        class="input pl-10 pr-4 py-2 w-full text-sm rounded-lg border focus:outline-none focus:ring-1 transition-all"
        style="border-color: var(--line); background: var(--bg-surface); color: var(--txt);"
      />
      {#if searchQuery}
        <button
          on:click={() => (searchQuery = '')}
          class="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-mono t-faint hover:t-txt transition-colors px-1"
        >
          ESC
        </button>
      {/if}
    </div>

    <div class="flex items-center gap-3 self-end sm:self-auto">
      <!-- Botões de Alternância de Visão -->
      <div class="flex items-center p-1 rounded-lg border" style="border-color: var(--line); background: var(--bg-surface);">
        <button
          on:click={() => setViewMode('cards')}
          class="btn btn-sm px-2.5 py-1 text-xs flex items-center gap-1.5 transition-colors {viewMode === 'cards' ? 'btn-primary' : 'text-dim hover:t-txt'}"
          title={$t('domains.viewCards')}
        >
          <LayoutGrid class="w-3.5 h-3.5" />
          <span>{$t('domains.viewCards')}</span>
        </button>
        <button
          on:click={() => setViewMode('table')}
          class="btn btn-sm px-2.5 py-1 text-xs flex items-center gap-1.5 transition-colors {viewMode === 'table' ? 'btn-primary' : 'text-dim hover:t-txt'}"
          title={$t('domains.viewTable')}
        >
          <TableIcon class="w-3.5 h-3.5" />
          <span>{$t('domains.viewTable')}</span>
        </button>
      </div>

      <!-- Contadores Globais -->
      <div class="hidden md:flex items-center gap-4 px-4 py-1.5 rounded-lg border text-xs" style="border-color: var(--line); background: var(--bg-surface);">
        <div>
          <span class="t-faint text-xs block">{$t('domains.mappedDomains')}</span>
          <span class="text-xl font-bold t-visor">{domains.length}</span>
        </div>
        <div class="h-6 w-px bg-[var(--line)]"></div>
        <div>
          <span class="t-faint text-xs block">{$t('domains.allocatedApps')}</span>
          <span class="text-xl font-bold t-txt">
            {totalComponentsCount}
          </span>
        </div>
      </div>
    </div>
  </section>

  <!-- Lista / Conteúdo Principal -->
  {#if loading}
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {#each Array(6) as _}
        <div class="plate p-6 space-y-4 animate-pulse">
          <div class="h-6 w-2/3 bg-[var(--line)] rounded"></div>
          <div class="h-4 w-1/2 bg-[var(--line)] rounded"></div>
          <div class="h-16 w-full bg-[var(--line)] rounded"></div>
        </div>
      {/each}
    </div>
  {:else if error}
    <div class="plate p-8 text-center space-y-3 border-amber-500/30">
      <ShieldAlert class="w-10 h-10 mx-auto text-amber-500" />
      <h3 class="text-lg font-bold t-txt">{$t('domains.errorLoading')}</h3>
      <p class="t-dim text-sm">{error}</p>
    </div>
  {:else if filteredDomains.length === 0}
    <div class="plate p-12 text-center space-y-4">
      <Box class="w-12 h-12 mx-auto t-faint opacity-40" />
      <h3 class="text-lg font-bold t-txt">{$t('domains.noDomainsTitle')}</h3>
      <p class="t-dim text-sm max-w-md mx-auto">
        {#if searchQuery}
          {$t('domains.noDomainsSubSearch', { query: searchQuery })}
        {:else}
          {$t('domains.noDomainsSubEmpty')}
        {/if}
      </p>
    </div>
  {:else if viewMode === 'cards'}
    <!-- Visão em Cards -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {#each filteredDomains as domain}
        <a
          href={`/domains/${encodeURIComponent(domain.domain)}`}
          class="plate plate-interactive p-6 space-y-5 flex flex-col justify-between group transition-transform hover:-translate-y-1"
        >
          <div class="space-y-4">
            <!-- Cabeçalho do Card -->
            <div class="flex items-start justify-between gap-3">
              <div class="flex items-center gap-2.5">
                <div class="p-2 rounded-lg bg-[var(--bg-surface)] border border-[var(--line)]">
                  <FolderGit2 class="w-5 h-5 t-visor" />
                </div>
                <div>
                  <h3 class="font-bold text-lg t-txt group-hover:t-visor transition-colors">
                    {domain.domain}
                  </h3>
                  <span class="text-xs t-dim flex items-center gap-1.5 mt-0.5">
                    <Box class="w-3.5 h-3.5 t-faint" />
                    {domain.components_count} {domain.components_count === 1 ? 'projeto' : 'projetos'}
                  </span>
                </div>
              </div>
              
              <span class="btn btn-sm btn-ghost p-1 group-hover:translate-x-1 transition-transform">
                <ChevronRight class="w-5 h-5 text-dim" />
              </span>
            </div>

            <!-- Sistemas do Domínio -->
            {#if domain.systems && domain.systems.length > 0}
              <div class="space-y-1.5">
                <span class="text-[11px] uppercase font-mono font-bold tracking-wider t-faint block">
                  {$t('domains.colSystems')}
                </span>
                <div class="flex flex-wrap gap-1.5">
                  {#each domain.systems as sys}
                    <span class="chip text-xs">
                      {sys}
                    </span>
                  {/each}
                </div>
              </div>
            {/if}

            <!-- Responsáveis (Owners) -->
            {#if domain.owners && domain.owners.length > 0}
              <div class="space-y-1.5">
                <span class="text-[11px] uppercase font-mono font-bold tracking-wider t-faint block">
                  {$t('domains.colOwners')}
                </span>
                <div class="flex flex-wrap gap-1.5">
                  {#each domain.owners as owner}
                    <span class="chip chip-visor text-xs flex items-center gap-1">
                      <Users class="w-3 h-3" />
                      {owner}
                    </span>
                  {/each}
                </div>
              </div>
            {/if}

            <!-- Lista Simplificada de Projetos -->
            <div class="pt-2 border-t border-[var(--line)] space-y-2">
              <span class="text-[11px] uppercase font-mono font-bold tracking-wider t-faint block">
                Projetos Mapeados
              </span>
              <div class="space-y-1.5">
                {#each domain.components.slice(0, 3) as comp}
                  <div class="flex items-center justify-between text-xs py-1 px-2.5 rounded bg-[var(--bg-surface)]">
                    <span class="font-medium t-txt truncate max-w-[170px]">{comp.name}</span>
                    <span class="text-[10px] font-mono t-faint uppercase px-1.5 py-0.5 rounded bg-[var(--bg)]">
                      {comp.type}
                    </span>
                  </div>
                {/each}
                {#if domain.components.length > 3}
                  <span class="text-[11px] t-faint block italic pl-1">
                    + {domain.components.length - 3} outro(s) projeto(s)...
                  </span>
                {/if}
              </div>
            </div>
          </div>

          <!-- Rodapé do Card -->
          <div class="pt-3 border-t border-[var(--line)] flex items-center justify-between text-xs t-visor font-medium group-hover:underline">
            <span>{$t('domains.viewDetails')}</span>
            <ArrowRight class="w-4 h-4" />
          </div>
        </a>
      {/each}
    </div>
  {:else}
    <!-- Visão em Tabela -->
    <div class="plate overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-left text-sm border-collapse">
          <thead>
            <tr class="border-b text-xs uppercase font-mono tracking-wider t-faint bg-[var(--bg-surface)]" style="border-color: var(--line);">
              <th class="py-3.5 px-4 font-bold">{$t('domains.colDomain')}</th>
              <th class="py-3.5 px-4 font-bold">{$t('domains.colSystems')}</th>
              <th class="py-3.5 px-4 font-bold">{$t('domains.colOwners')}</th>
              <th class="py-3.5 px-4 font-bold">{$t('domains.colAppsCount')}</th>
              <th class="py-3.5 px-4 font-bold text-right">{$t('domains.colActions')}</th>
            </tr>
          </thead>
          <tbody class="divide-y" style="border-color: var(--line);">
            {#each filteredDomains as domain}
              <tr class="hover:bg-[var(--bg-surface)] transition-colors group">
                <td class="py-3.5 px-4">
                  <a
                    href={`/domains/${encodeURIComponent(domain.domain)}`}
                    class="font-bold t-txt group-hover:t-visor flex items-center gap-2"
                  >
                    <FolderGit2 class="w-4 h-4 t-visor" />
                    <span>{domain.domain}</span>
                  </a>
                </td>
                <td class="py-3.5 px-4">
                  <div class="flex flex-wrap gap-1">
                    {#each domain.systems as sys}
                      <span class="chip text-xs">{sys}</span>
                    {:else}
                      <span class="t-faint text-xs">-</span>
                    {/each}
                  </div>
                </td>
                <td class="py-3.5 px-4">
                  <div class="flex flex-wrap gap-1">
                    {#each domain.owners as owner}
                      <span class="chip chip-visor text-xs flex items-center gap-1">
                        <Users class="w-3 h-3" />
                        {owner}
                      </span>
                    {:else}
                      <span class="t-faint text-xs">-</span>
                    {/each}
                  </div>
                </td>
                <td class="py-3.5 px-4">
                  <span class="badge font-mono font-bold text-xs">
                    {domain.components_count}
                  </span>
                </td>
                <td class="py-3.5 px-4 text-right">
                  <a
                    href={`/domains/${encodeURIComponent(domain.domain)}`}
                    class="btn btn-sm btn-ghost inline-flex items-center gap-1 text-xs"
                  >
                    <span>{$t('domains.viewDetails')}</span>
                    <ArrowRight class="w-3.5 h-3.5" />
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
