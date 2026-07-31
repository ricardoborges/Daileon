<script lang="ts">
  import { onMount } from 'svelte';
  import { fetchCatalog, type ComponentItem } from '$lib/api';
  import CatalogCard from '$lib/components/CatalogCard.svelte';
  import { Layers, Search, X } from 'lucide-svelte';

  let components: ComponentItem[] = [];
  let loading = true;

  let selectedOwner = '';
  let selectedType = '';
  let selectedLifecycle = '';
  let searchQuery = '';
  let selectedSort = 'activity_desc';

  onMount(async () => {
    await loadCatalog();
  });

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
      return c.name.toLowerCase().includes(q) || (c.description && c.description.toLowerCase().includes(q));
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
    <span class="eyebrow">Registro de Componentes</span>
    <div class="rule">
      <h1 class="text-3xl font-bold tracking-[-0.03em] t-txt flex items-center gap-3 whitespace-nowrap">
        <Layers class="w-7 h-7 t-visor" /> Catálogo de Software
      </h1>
    </div>
    <p class="t-dim text-sm">
      Microsserviços, bibliotecas e lambdas registrados no ecossistema.
    </p>
  </header>

  <!-- Painel de filtros -->
  <div class="plate plate-deep p-5" style="--chamfer: 14px;">
    <div class="flex flex-wrap items-end gap-4">
      <div class="flex-1 min-w-[220px] space-y-1.5">
        <label for="f-query" class="label block">Consulta</label>
        <div class="relative">
          <Search class="w-3.5 h-3.5 t-faint absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            id="f-query"
            type="text"
            bind:value={searchQuery}
            placeholder="nome ou descrição..."
            class="field font-mono pl-9"
          />
        </div>
      </div>

      <div class="space-y-1.5">
        <label for="f-owner" class="label block">Time</label>
        <select id="f-owner" bind:value={selectedOwner} class="field">
          <option value="">Todos</option>
          {#each owners as owner}<option value={owner}>{owner}</option>{/each}
        </select>
      </div>

      <div class="space-y-1.5">
        <label for="f-type" class="label block">Tipo</label>
        <select id="f-type" bind:value={selectedType} class="field">
          <option value="">Todos</option>
          {#each types as type}<option value={type}>{type}</option>{/each}
        </select>
      </div>

      <div class="space-y-1.5">
        <label for="f-lifecycle" class="label block">Lifecycle</label>
        <select id="f-lifecycle" bind:value={selectedLifecycle} class="field">
          <option value="">Todos</option>
          {#each lifecycles as lc}<option value={lc}>{lc}</option>{/each}
        </select>
      </div>

      <div class="space-y-1.5">
        <label for="f-sort" class="label block">Ordenar por</label>
        <select id="f-sort" bind:value={selectedSort} class="field font-semibold">
          <option value="activity_desc">Última atividade (mais recente)</option>
          <option value="activity_asc">Última atividade (mais antiga)</option>
          <option value="name_asc">Nome (A - Z)</option>
          <option value="name_desc">Nome (Z - A)</option>
          <option value="created_desc">Data de criação (mais novos)</option>
          <option value="created_asc">Data de criação (mais antigos)</option>
          <option value="manifest_desc">Conformidade (project-info.yml)</option>
          <option value="lifecycle_desc">Ciclo de vida (Produção 1º)</option>
        </select>
      </div>

      {#if hasFilters}
        <button on:click={clearFilters} class="btn btn-sm">
          <X class="w-3 h-3" /> Limpar
        </button>
      {/if}
    </div>

    <div class="mt-4 pt-4 border-t border-line flex items-center gap-4">
      <span class="label flex items-center gap-2">
        <span class="led {loading ? 'led-crest' : 'led-ok'}"></span>
        {loading ? 'Carregando' : 'Pronto'}
      </span>
      <span class="label">
        Exibindo <span class="t-visor">{sorted.length}</span> de {components.length}
      </span>
    </div>
  </div>

  <!-- Grade -->
  {#if loading}
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
      {#each Array(6) as _}
        <div class="skeleton h-56"></div>
      {/each}
    </div>
  {:else if sorted.length === 0}
    <div class="plate p-20 text-center space-y-4">
      <Layers class="w-10 h-10 mx-auto t-faint" />
      <h3 class="text-lg font-bold t-txt">Nenhum componente encontrado</h3>
      <p class="t-dim text-sm max-w-sm mx-auto">
        Ajuste os filtros ou acione a sincronização com o GitLab em
        <a href="/config" class="t-visor underline underline-offset-2">Configuração</a>.
      </p>
    </div>
  {:else}
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
      {#each sorted as item}
        <CatalogCard {item} />
      {/each}
    </div>
  {/if}
</main>
