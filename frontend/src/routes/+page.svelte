<script lang="ts">
  import { onMount } from 'svelte';
  import { fetchCatalog, type ComponentItem } from '$lib/api';
  import CatalogCard from '$lib/components/CatalogCard.svelte';
  import DaileonLogo from '$lib/components/DaileonLogo.svelte';
  import { Search, Layers, ShieldCheck, ArrowRight, Activity, GitBranch } from 'lucide-svelte';

  let components: ComponentItem[] = [];
  let loading = true;
  let searchQuery = '';

  onMount(async () => {
    try {
      components = await fetchCatalog();
    } catch (e) {
      console.error('Error loading catalog:', e);
    } finally {
      loading = false;
    }
  });

  $: filtered = components.filter(c =>
    c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (c.description && c.description.toLowerCase().includes(searchQuery.toLowerCase())) ||
    c.tags.some(t => t.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  $: stats = [
    { label: 'Total no catálogo', value: components.length, icon: Layers, tone: 't-visor' },
    { label: 'Em produção', value: components.filter(c => c.lifecycle === 'production').length, icon: Activity, tone: 't-ok' },
    { label: 'Microsserviços', value: components.filter(c => c.type === 'service').length, icon: GitBranch, tone: 't-crest' },
    { label: 'Com project-info.yml', value: components.filter(c => c.has_manifest).length, icon: ShieldCheck, tone: 't-txt' }
  ];
</script>

<main class="max-w-7xl mx-auto px-6 py-10 space-y-14">
  <!-- ============ Console principal ============ -->
  <section class="plate plate-deep overflow-hidden" style="--chamfer: 30px;">
    <!-- Malha técnica + varredura do visor -->
    <div class="absolute inset-0 grid-mesh opacity-70 pointer-events-none"></div>
    <div
      class="absolute inset-x-0 top-0 h-24 pointer-events-none animate-sweep"
      style="background: linear-gradient(180deg, transparent, var(--visor-wash), transparent);"
    ></div>

    <!-- Mecha em marca d'água -->
    <div class="absolute -right-16 -bottom-24 opacity-[0.07] pointer-events-none hidden md:block">
      <DaileonLogo size={460} />
    </div>

    <div class="relative p-8 md:p-12 max-w-3xl space-y-7">
      <span class="eyebrow">Unidade de Catálogo &middot; Engenharia</span>

      <h1 class="text-4xl md:text-[3.25rem] font-bold tracking-[-0.035em] leading-[1.05] t-txt">
        Todo o ecossistema de software<br class="hidden md:block" />
        sob um <span class="t-visor">único painel</span>.
      </h1>

      <p class="t-dim text-[15px] leading-relaxed max-w-xl">
        Descubra microsserviços, leia os metadados do
        <code class="font-mono text-[13px] px-1.5 py-0.5 border border-line bg-surface-2 t-crest">project-info.yml</code>
        e navegue pela documentação viva — sem sair do portal.
      </p>

      <!-- Prompt de busca -->
      <div class="search-bar max-w-xl">
        <Search class="w-4 h-4 t-faint shrink-0" />
        <input
          type="text"
          bind:value={searchQuery}
          placeholder="serviço, tag ou tecnologia..."
          aria-label="Pesquisar no catálogo"
        />
        <a href="/catalog" class="btn btn-primary btn-sm">
          Catálogo <ArrowRight class="w-3.5 h-3.5" />
        </a>
      </div>

      <!-- Barra de status do console -->
      <div class="flex flex-wrap items-center gap-x-6 gap-y-2 pt-2">
        <span class="label flex items-center gap-2">
          <span class="led {loading ? 'led-crest' : 'led-ok'}"></span>
          {loading ? 'Lendo catálogo' : 'Sistemas nominais'}
        </span>
        <span class="label">Fonte: GitLab API v4</span>
        <span class="label">{components.length} componentes indexados</span>
      </div>
    </div>
  </section>

  <!-- ============ Instrumentos ============ -->
  <section class="grid grid-cols-2 lg:grid-cols-4 gap-4">
    {#each stats as stat}
      <div class="plate gauge {stat.tone} p-5" style="--chamfer: 12px;">
        <div class="flex items-start justify-between gap-3">
          <span class="readout text-[2rem] leading-none">
            {String(stat.value).padStart(2, '0')}
          </span>
          <svelte:component this={stat.icon} class="w-4 h-4 opacity-70" />
        </div>
        <span class="label block mt-3">{stat.label}</span>
      </div>
    {/each}
  </section>

  <!-- ============ Componentes ============ -->
  <section class="space-y-6">
    <div class="flex items-end justify-between gap-6">
      <div class="min-w-0">
        <div class="rule">
          <h2 class="text-xl font-bold tracking-[-0.02em] t-txt whitespace-nowrap">
            Componentes em destaque
          </h2>
        </div>
        <p class="label mt-2">Catalogados automaticamente a partir do GitLab</p>
      </div>

      <a href="/catalog" class="btn btn-sm shrink-0">
        Ver todos ({components.length}) <ArrowRight class="w-3.5 h-3.5" />
      </a>
    </div>

    {#if loading}
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {#each Array(3) as _}
          <div class="skeleton h-56"></div>
        {/each}
      </div>
    {:else if filtered.length === 0}
      <div class="plate p-16 text-center space-y-3">
        <Layers class="w-9 h-9 mx-auto t-faint" />
        <p class="label">Nenhum componente corresponde à busca</p>
      </div>
    {:else}
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {#each filtered.slice(0, 6) as item}
          <CatalogCard {item} />
        {/each}
      </div>
    {/if}
  </section>
</main>
