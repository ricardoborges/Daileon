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
  }

  $: owners = Array.from(new Set(components.map(c => c.owner))).filter(Boolean);
  $: types = Array.from(new Set(components.map(c => c.type))).filter(Boolean);
  $: lifecycles = Array.from(new Set(components.map(c => c.lifecycle))).filter(Boolean);
  $: hasFilters = !!(selectedOwner || selectedType || selectedLifecycle || searchQuery);

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
        Exibindo <span class="t-visor">{filtered.length}</span> de {components.length}
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
  {:else if filtered.length === 0}
    <div class="plate p-20 text-center space-y-4">
      <Layers class="w-10 h-10 mx-auto t-faint" />
      <h3 class="text-lg font-bold t-txt">Nenhum componente encontrado</h3>
      <p class="t-dim text-sm max-w-sm mx-auto">
        Ajuste os filtros ou acione a sincronização com o GitLab no topo da tela.
      </p>
    </div>
  {:else}
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
      {#each filtered as item}
        <CatalogCard {item} />
      {/each}
    </div>
  {/if}
</main>
