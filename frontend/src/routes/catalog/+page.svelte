<script lang="ts">
  import { onMount } from 'svelte';
  import { fetchCatalog, type ComponentItem } from '$lib/api';
  import CatalogCard from '$lib/components/CatalogCard.svelte';
  import CatalogTable from '$lib/components/CatalogTable.svelte';
  import { Layers, Search, X, LayoutGrid, Table } from 'lucide-svelte';
  import { t } from '$lib/i18n';

  let components: ComponentItem[] = [];
  let loading = true;

  let selectedOwner = '';
  let selectedType = '';
  let selectedLifecycle = '';
  let searchQuery = '';
  let selectedSort = 'activity_desc';
  let viewMode: 'cards' | 'table' = 'cards';

  onMount(async () => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('daileon_catalog_view_mode');
      if (saved === 'cards' || saved === 'table') {
        viewMode = saved;
      }
    }
    await loadCatalog();
  });

  function setViewMode(mode: 'cards' | 'table') {
    viewMode = mode;
    if (typeof window !== 'undefined') {
      localStorage.setItem('daileon_catalog_view_mode', mode);
    }
  }

  async function loadCatalog() {
    loading = true;
    try {
      components = await fetchCatalog();
    } catch (e) {
      console.error(e);
    } finally {
      loading = false;
    }
  }

  function clearFilters() {
    selectedOwner = '';
    selectedType = '';
    selectedLifecycle = '';
    searchQuery = '';
    selectedSort = 'activity_desc';
  }

  $: owners = Array.from(new Set(components.map(c => c.owner))).filter(Boolean);
  $: types = Array.from(new Set(components.map(c => c.type))).filter(Boolean);
  $: lifecycles = Array.from(new Set(components.map(c => c.lifecycle))).filter(Boolean);
  $: hasFilters = !!(selectedOwner || selectedType || selectedLifecycle || searchQuery || selectedSort !== 'activity_desc');

  $: filtered = components.filter(c => {
    if (selectedOwner && c.owner !== selectedOwner) return false;
    if (selectedType && c.type !== selectedType) return false;
    if (selectedLifecycle && c.lifecycle !== selectedLifecycle) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        c.name.toLowerCase().includes(q) ||
        (c.description && c.description.toLowerCase().includes(q)) ||
        (c.tags && c.tags.some(tag => tag.toLowerCase().includes(q)))
      );
    }
    return true;
  });

  $: sorted = [...filtered].sort((a, b) => {
    if (selectedSort === 'activity_desc') {
      const tA = a.last_activity_at || a.updated_at || '';
      const tB = b.last_activity_at || b.updated_at || '';
      return tB.localeCompare(tA);
    }
    if (selectedSort === 'activity_asc') {
      const tA = a.last_activity_at || a.updated_at || '';
      const tB = b.last_activity_at || b.updated_at || '';
      return tA.localeCompare(tB);
    }
    if (selectedSort === 'name_asc') {
      return a.name.localeCompare(b.name);
    }
    if (selectedSort === 'name_desc') {
      return b.name.localeCompare(a.name);
    }
    if (selectedSort === 'created_desc') {
      const cA = a.gitlab_created_at || a.updated_at || '';
      const cB = b.gitlab_created_at || b.updated_at || '';
      return cB.localeCompare(cA);
    }
    if (selectedSort === 'created_asc') {
      const cA = a.gitlab_created_at || a.updated_at || '';
      const cB = b.gitlab_created_at || b.updated_at || '';
      return cA.localeCompare(cB);
    }
    if (selectedSort === 'manifest_desc') {
      return (b.has_manifest ? 1 : 0) - (a.has_manifest ? 1 : 0);
    }
    if (selectedSort === 'lifecycle_desc') {
      const order: Record<string, number> = { production: 3, experimental: 2, deprecated: 1 };
      return (order[b.lifecycle.toLowerCase()] || 0) - (order[a.lifecycle.toLowerCase()] || 0);
    }
    return 0;
  });
</script>

<main class="max-w-7xl mx-auto px-6 py-10 space-y-8">
  <!-- Cabeçalho -->
  <header class="space-y-3">
    <span class="eyebrow">{$t('catalog.eyebrow')}</span>
    <div class="rule">
      <h1 class="text-3xl font-bold tracking-[-0.03em] t-txt flex items-center gap-3 whitespace-nowrap">
        <Layers class="w-7 h-7 t-visor" /> {$t('catalog.title')}
      </h1>
    </div>
    <p class="t-dim text-sm">
      {$t('catalog.subtitle')}
    </p>
  </header>

  <!-- Painel de filtros -->
  <div class="plate plate-deep p-5" style="--chamfer: 14px;">
    <div class="flex flex-wrap items-end gap-4">
      <div class="flex-1 min-w-[220px] space-y-1.5">
        <label for="f-query" class="label block">{$t('catalog.filterQuery')}</label>
        <div class="relative">
          <Search class="w-3.5 h-3.5 t-faint absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            id="f-query"
            type="text"
            bind:value={searchQuery}
            placeholder={$t('catalog.filterQueryPlaceholder')}
            class="field font-mono pl-9"
          />
        </div>
      </div>

      <div class="space-y-1.5">
        <label for="f-owner" class="label block">{$t('catalog.filterTeam')}</label>
        <select id="f-owner" bind:value={selectedOwner} class="field">
          <option value="">{$t('catalog.filterAll')}</option>
          {#each owners as owner}<option value={owner}>{owner}</option>{/each}
        </select>
      </div>

      <div class="space-y-1.5">
        <label for="f-type" class="label block">{$t('catalog.filterType')}</label>
        <select id="f-type" bind:value={selectedType} class="field">
          <option value="">{$t('catalog.filterAll')}</option>
          {#each types as type}<option value={type}>{type}</option>{/each}
        </select>
      </div>

      <div class="space-y-1.5">
        <label for="f-lifecycle" class="label block">{$t('catalog.filterLifecycle')}</label>
        <select id="f-lifecycle" bind:value={selectedLifecycle} class="field">
          <option value="">{$t('catalog.filterAll')}</option>
          {#each lifecycles as lc}<option value={lc}>{lc}</option>{/each}
        </select>
      </div>

      <div class="space-y-1.5">
        <label for="f-sort" class="label block">{$t('catalog.filterSort')}</label>
        <select id="f-sort" bind:value={selectedSort} class="field font-semibold">
          <option value="activity_desc">{$t('catalog.sortActivityDesc')}</option>
          <option value="activity_asc">{$t('catalog.sortActivityAsc')}</option>
          <option value="name_asc">{$t('catalog.sortNameAsc')}</option>
          <option value="name_desc">{$t('catalog.sortNameDesc')}</option>
          <option value="created_desc">{$t('catalog.sortCreatedDesc')}</option>
          <option value="created_asc">{$t('catalog.sortCreatedAsc')}</option>
          <option value="manifest_desc">{$t('catalog.sortManifestDesc')}</option>
          <option value="lifecycle_desc">{$t('catalog.sortLifecycleDesc')}</option>
        </select>
      </div>

      {#if hasFilters}
        <button on:click={clearFilters} class="btn btn-sm">
          <X class="w-3 h-3" /> {$t('catalog.clearFilters')}
        </button>
      {/if}
    </div>

    <div class="mt-4 pt-4 border-t border-line flex flex-wrap items-center justify-between gap-4">
      <div class="flex items-center gap-4">
        <span class="label flex items-center gap-2">
          <span class="led {loading ? 'led-crest' : 'led-ok'}"></span>
          {loading ? $t('catalog.loading') : $t('catalog.ready')}
        </span>
        <span class="label">
          {$t('catalog.showingCount', { shown: sorted.length, total: components.length })}
        </span>
      </div>

      <!-- Alternador de visualização -->
      <div class="flex items-center gap-1 bg-surface-2 p-1 border border-line" style="border-radius: 6px;">
        <button
          type="button"
          on:click={() => setViewMode('cards')}
          class={`btn btn-sm text-xs gap-1.5 px-2.5 py-1 ${viewMode === 'cards' ? 'btn-visor font-bold' : 'opacity-70 hover:opacity-100'}`}
          title={$t('catalog.viewModeCards')}
        >
          <LayoutGrid class="w-3.5 h-3.5" />
          <span>{$t('catalog.viewModeCards')}</span>
        </button>
        <button
          type="button"
          on:click={() => setViewMode('table')}
          class={`btn btn-sm text-xs gap-1.5 px-2.5 py-1 ${viewMode === 'table' ? 'btn-visor font-bold' : 'opacity-70 hover:opacity-100'}`}
          title={$t('catalog.viewModeTable')}
        >
          <Table class="w-3.5 h-3.5" />
          <span>{$t('catalog.viewModeTable')}</span>
        </button>
      </div>
    </div>
  </div>

  <!-- Grade ou Tabela -->
  {#if loading}
    {#if viewMode === 'cards'}
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {#each Array(6) as _}
          <div class="skeleton h-56"></div>
        {/each}
      </div>
    {:else}
      <div class="plate plate-deep p-6 space-y-3" style="--chamfer: 14px;">
        {#each Array(5) as _}
          <div class="skeleton h-10 w-full"></div>
        {/each}
      </div>
    {/if}
  {:else if sorted.length === 0}
    <div class="plate p-20 text-center space-y-4">
      <Layers class="w-10 h-10 mx-auto t-faint" />
      <h3 class="text-lg font-bold t-txt">{$t('catalog.emptyTitle')}</h3>
      <p class="t-dim text-sm max-w-sm mx-auto">
        {$t('catalog.emptySub')}
        <a href="/config" class="t-visor underline underline-offset-2">{$t('nav.config')}</a>.
      </p>
    </div>
  {:else if viewMode === 'cards'}
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
      {#each sorted as item}
        <CatalogCard {item} />
      {/each}
    </div>
  {:else}
    <CatalogTable items={sorted} />
  {/if}
</main>

