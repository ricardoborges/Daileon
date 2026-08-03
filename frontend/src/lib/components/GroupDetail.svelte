<script lang="ts">
  /**
   * Detalhe de um grupo do catálogo (domínio ou solução): cabeçalho, métricas
   * e a lista dos projetos que pertencem a ele.
   */
  import type { ComponentType } from 'svelte';
  import type { GroupedComponentItem } from '$lib/api';
  import { t } from '$lib/i18n';
  import { domainHref, solutionHref, loadViewMode, saveViewMode, type ViewMode } from '$lib/catalogView';
  import { onMount } from 'svelte';
  import {
    ArrowLeft,
    Box,
    ExternalLink,
    FileText,
    LayoutGrid,
    Search,
    ShieldAlert,
    Table as TableIcon,
    Users
  } from 'lucide-svelte';

  export let kind: 'domain' | 'solution';
  export let icon: ComponentType;
  export let name = '';
  export let eyebrow: string;
  /** Dimensão cruzada: soluções de um domínio, domínios de uma solução. */
  export let crossValues: string[] = [];
  export let crossLabel: string;
  export let owners: string[] = [];
  export let componentsCount = 0;
  export let components: GroupedComponentItem[] = [];
  export let loading = false;
  export let error: string | null = null;

  let searchQuery = '';
  let viewMode: ViewMode = 'table';

  const backHref = kind === 'domain' ? '/catalog?tab=domains' : '/catalog?tab=solutions';

  onMount(() => {
    viewMode = loadViewMode(kind === 'domain' ? 'domains' : 'solutions');
  });

  function setViewMode(mode: ViewMode) {
    viewMode = mode;
    saveViewMode(kind === 'domain' ? 'domains' : 'solutions', mode);
  }

  /** O grupo cruzado de cada projeto: num domínio é a solução, e vice-versa. */
  function crossOf(c: GroupedComponentItem): string {
    return (kind === 'domain' ? c.solution : c.domain) || '';
  }

  function crossHref(value: string): string {
    return kind === 'domain' ? solutionHref(value) : domainHref(value);
  }

  $: filtered = components.filter((c) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return [c.name, c.owner, c.type, c.kind, c.lifecycle, c.domain, c.solution, c.description].some(
      (v) => (v || '').toLowerCase().includes(q)
    );
  });
</script>

<main class="max-w-7xl mx-auto px-6 py-10 space-y-8">
  <div>
    <a
      href={backHref}
      class="btn btn-sm btn-ghost inline-flex items-center gap-1.5 text-xs font-mono t-dim hover:t-txt transition-colors"
    >
      <ArrowLeft class="w-3.5 h-3.5" />
      <span>{$t('catalog.backToCatalog')}</span>
    </a>
  </div>

  {#if loading}
    <div class="space-y-6 animate-pulse">
      <div class="plate p-8 space-y-4">
        <div class="h-4 w-32 bg-[var(--line)] rounded"></div>
        <div class="h-8 w-64 bg-[var(--line)] rounded"></div>
        <div class="h-16 w-full bg-[var(--line)] rounded"></div>
      </div>
    </div>
  {:else if error}
    <div class="plate p-10 text-center space-y-4 border-amber-500/30">
      <ShieldAlert class="w-12 h-12 mx-auto text-amber-500" />
      <h3 class="text-lg font-bold t-txt">{$t('catalog.errorLoading')}</h3>
      <p class="t-dim text-sm max-w-md mx-auto">{error}</p>
      <a href={backHref} class="btn btn-sm btn-primary inline-flex items-center gap-1 text-xs">
        {$t('catalog.backToCatalog')}
      </a>
    </div>
  {:else}
    <section class="plate plate-deep p-8 space-y-6 relative overflow-hidden">
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-6 relative z-10">
        <div class="space-y-2">
          <div class="flex items-center gap-2">
            <svelte:component this={icon} class="w-5 h-5 t-visor" />
            <span class="label">{eyebrow}</span>
          </div>
          <h1 class="text-3xl font-bold tracking-[-0.035em] t-txt">{name}</h1>
        </div>

        <div class="flex flex-wrap items-center gap-3">
          {#if crossValues.length > 0}
            <div class="px-3 py-1.5 rounded-lg border text-xs bg-[var(--bg-surface)] border-[var(--line)]">
              <span class="t-faint block text-[10px] uppercase font-mono">{crossLabel}</span>
              <div class="flex flex-wrap gap-1 mt-1">
                {#each crossValues as value}
                  <a href={crossHref(value)} class="chip text-xs hover:t-visor transition-colors">{value}</a>
                {/each}
              </div>
            </div>
          {/if}

          {#if owners.length > 0}
            <div class="px-3 py-1.5 rounded-lg border text-xs bg-[var(--bg-surface)] border-[var(--line)]">
              <span class="t-faint block text-[10px] uppercase font-mono">{$t('domains.colOwners')}</span>
              <div class="flex flex-wrap gap-1 mt-1">
                {#each owners as owner}
                  <span class="chip chip-visor text-xs flex items-center gap-1">
                    <Users class="w-3 h-3" />
                    {owner}
                  </span>
                {/each}
              </div>
            </div>
          {/if}
        </div>
      </div>

      <div class="grid grid-cols-2 sm:grid-cols-3 gap-4 pt-6 border-t border-[var(--line)]">
        <div class="p-4 rounded-lg bg-[var(--bg-surface)] border border-[var(--line)]">
          <span class="t-faint text-xs block font-medium">{$t('domainDetail.totalApps')}</span>
          <span class="text-2xl font-bold t-txt">{componentsCount}</span>
        </div>
        <div class="p-4 rounded-lg bg-[var(--bg-surface)] border border-[var(--line)]">
          <span class="t-faint text-xs block font-medium">{crossLabel}</span>
          <span class="text-2xl font-bold t-visor">{crossValues.length}</span>
        </div>
        <div class="p-4 rounded-lg bg-[var(--bg-surface)] border border-[var(--line)] col-span-2 sm:col-span-1">
          <span class="t-faint text-xs block font-medium">{$t('domainDetail.ownersCount')}</span>
          <span class="text-2xl font-bold t-txt">{owners.length}</span>
        </div>
      </div>
    </section>

    <section class="space-y-6">
      <div class="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
        <div>
          <h2 class="text-xl font-bold t-txt">{$t('domainDetail.hostedApps')}</h2>
          <p class="t-dim text-xs">{$t('domainDetail.hostedAppsSub')}</p>
        </div>

        <div class="flex items-center gap-3">
          <div class="relative w-full sm:w-72">
            <Search class="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 t-faint pointer-events-none" />
            <input
              type="text"
              bind:value={searchQuery}
              placeholder={$t('domainDetail.searchPlaceholder')}
              class="input pl-9 pr-3 py-1.5 w-full text-xs rounded-lg border focus:outline-none focus:ring-1"
              style="border-color: var(--line); background: var(--bg-surface); color: var(--txt);"
            />
          </div>

          <div
            class="flex items-center p-1 rounded-lg border shrink-0"
            style="border-color: var(--line); background: var(--bg-surface);"
          >
            <button
              on:click={() => setViewMode('table')}
              aria-pressed={viewMode === 'table'}
              class="btn btn-sm px-2 py-1 text-xs flex items-center gap-1 transition-colors {viewMode === 'table'
                ? 'btn-primary'
                : 'text-dim hover:t-txt'}"
              title={$t('catalog.viewModeTable')}
            >
              <TableIcon class="w-3.5 h-3.5" />
            </button>
            <button
              on:click={() => setViewMode('cards')}
              aria-pressed={viewMode === 'cards'}
              class="btn btn-sm px-2 py-1 text-xs flex items-center gap-1 transition-colors {viewMode === 'cards'
                ? 'btn-primary'
                : 'text-dim hover:t-txt'}"
              title={$t('catalog.viewModeCards')}
            >
              <LayoutGrid class="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {#if filtered.length === 0}
        <div class="plate p-8 text-center space-y-2">
          <Box class="w-8 h-8 mx-auto t-faint opacity-40" />
          <h4 class="text-base font-bold t-txt">{$t('domainDetail.noAppsFound')}</h4>
        </div>
      {:else if viewMode === 'table'}
        <div class="plate overflow-hidden">
          <div class="overflow-x-auto">
            <table class="w-full text-left text-xs border-collapse">
              <thead>
                <tr
                  class="border-b uppercase font-mono tracking-wider t-faint bg-[var(--bg-surface)]"
                  style="border-color: var(--line);"
                >
                  <th class="py-3 px-4 font-bold">{$t('domainDetail.colAppName')}</th>
                  <th class="py-3 px-4 font-bold">{$t('domainDetail.colOwner')}</th>
                  <th class="py-3 px-4 font-bold">{crossLabel}</th>
                  <th class="py-3 px-4 font-bold">{$t('domainDetail.colType')}</th>
                  <th class="py-3 px-4 font-bold">{$t('domainDetail.colLifecycle')}</th>
                  <th class="py-3 px-4 font-bold">{$t('domainDetail.colDocs')}</th>
                  <th class="py-3 px-4 font-bold text-right">{$t('domainDetail.colActions')}</th>
                </tr>
              </thead>
              <tbody class="divide-y" style="border-color: var(--line);">
                {#each filtered as c (c.id)}
                  <tr class="hover:bg-[var(--bg-surface)] transition-colors group">
                    <td class="py-3 px-4">
                      <div class="space-y-0.5">
                        <a
                          href={`/catalog/${c.id}`}
                          class="font-bold text-sm t-txt group-hover:t-visor hover:underline flex items-center gap-1.5"
                        >
                          <Box class="w-3.5 h-3.5 t-visor" />
                          <span>{c.name}</span>
                        </a>
                        {#if c.description}
                          <p class="t-dim text-[11px] line-clamp-1 max-w-md">{c.description}</p>
                        {/if}
                      </div>
                    </td>
                    <td class="py-3 px-4">
                      <span class="chip chip-visor text-xs">{c.owner}</span>
                    </td>
                    <td class="py-3 px-4">
                      {#if crossOf(c)}
                        <a href={crossHref(crossOf(c))} class="chip text-xs font-mono hover:t-visor transition-colors">
                          {crossOf(c)}
                        </a>
                      {:else}
                        <span class="t-faint text-xs">-</span>
                      {/if}
                    </td>
                    <td class="py-3 px-4">
                      <span class="font-mono text-xs uppercase t-txt">{c.type}</span>
                    </td>
                    <td class="py-3 px-4">
                      <span class="chip text-xs capitalize">{c.lifecycle}</span>
                    </td>
                    <td class="py-3 px-4">
                      <span class="t-faint text-xs flex items-center gap-1">
                        <FileText class="w-3.5 h-3.5" />
                        {c.docs_count || 0}
                      </span>
                    </td>
                    <td class="py-3 px-4 text-right">
                      <div class="flex items-center justify-end gap-2">
                        <a href={`/catalog/${c.id}`} class="btn btn-sm btn-primary text-xs py-1 px-2.5">
                          {$t('nav.catalog')}
                        </a>
                        {#if c.gitlab_url}
                          <a
                            href={c.gitlab_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            class="btn btn-sm btn-ghost p-1"
                            title="GitLab"
                          >
                            <ExternalLink class="w-3.5 h-3.5" />
                          </a>
                        {/if}
                      </div>
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        </div>
      {:else}
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {#each filtered as c (c.id)}
            <div class="plate plate-interactive p-5 space-y-4 flex flex-col justify-between">
              <div class="space-y-3">
                <div class="flex items-start justify-between gap-2">
                  <a
                    href={`/catalog/${c.id}`}
                    class="font-bold text-base t-txt hover:t-visor hover:underline flex items-center gap-2 min-w-0"
                  >
                    <Box class="w-4 h-4 t-visor shrink-0" />
                    <span class="truncate">{c.name}</span>
                  </a>
                  <span class="chip text-[10px] uppercase font-mono shrink-0">{c.type}</span>
                </div>

                {#if c.description}
                  <p class="t-dim text-xs line-clamp-2">{c.description}</p>
                {/if}

                <div class="flex flex-wrap gap-2 text-xs pt-1">
                  <span class="chip chip-visor text-xs flex items-center gap-1">
                    <Users class="w-3 h-3" />
                    {c.owner}
                  </span>
                  {#if crossOf(c)}
                    <a href={crossHref(crossOf(c))} class="chip text-xs hover:t-visor transition-colors">
                      {crossOf(c)}
                    </a>
                  {/if}
                </div>
              </div>

              <div class="pt-3 border-t border-[var(--line)] flex items-center justify-between">
                <a href={`/catalog/${c.id}`} class="text-xs font-medium t-visor hover:underline">
                  {$t('domains.viewDetails')} →
                </a>
                {#if c.gitlab_url}
                  <a
                    href={c.gitlab_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    class="btn btn-sm btn-ghost p-1"
                    title="GitLab"
                  >
                    <ExternalLink class="w-3.5 h-3.5" />
                  </a>
                {/if}
              </div>
            </div>
          {/each}
        </div>
      {/if}
    </section>
  {/if}
</main>
