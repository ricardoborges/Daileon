<script lang="ts">
  import { onMount } from 'svelte';
  import { pluginRegistry, type PluginDefinition } from './index';
  import { fetchBackendPlugins, type PluginBackendInfo } from '$lib/api';
  import {
    Blocks,
    Shield,
    FolderGit2,
    PlayCircle,
    Activity,
    CheckCircle2,
    Settings,
    Layers,
    Cpu,
    ExternalLink,
    RefreshCw
  } from 'lucide-svelte';

  export let onSelectConfigPlugin: (pluginId: string) => void = () => {};

  let backendPlugins: PluginBackendInfo[] = [];
  let loading = true;
  let error = '';
  let activeCategory: 'all' | 'auth' | 'scm' | 'cicd' | 'observability' = 'all';

  const categoryLabels = {
    all: 'Todos os Plugins',
    auth: 'Autenticação',
    scm: 'SCM & Crawlers',
    cicd: 'CI / CD',
    observability: 'Observabilidade'
  };

  function setCategory(cat: string) {
    activeCategory = cat as any;
  }

  function getCategoryLabel(cat: string): string {
    return categoryLabels[cat as keyof typeof categoryLabels] || cat;
  }

  async function loadPlugins() {
    loading = true;
    error = '';
    try {
      backendPlugins = await fetchBackendPlugins();
    } catch (e: any) {
      error = e.message || 'Erro ao carregar plugins do backend';
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    loadPlugins();
  });

  $: frontendPlugins = pluginRegistry.getAllPlugins();

  // Combine backend and frontend info by plugin ID
  $: pluginList = mergePluginInfo(frontendPlugins, backendPlugins);

  $: filteredPlugins = activeCategory === 'all'
    ? pluginList
    : pluginList.filter(p => p.category === activeCategory);

  function mergePluginInfo(fe: PluginDefinition[], be: PluginBackendInfo[]) {
    const map = new Map<string, any>();

    // Backend plugins first
    for (const b of be) {
      map.set(b.id, {
        id: b.id,
        name: b.name,
        version: b.version,
        category: b.category,
        type: b.type,
        hasBackend: true,
        hasRouter: b.has_router,
        status: b.status || 'active',
        description: getFallbackDescription(b.id),
        icon: getCategoryIcon(b.category)
      });
    }

    // Merge Frontend plugins
    for (const f of fe) {
      const existing = map.get(f.id);
      if (existing) {
        existing.hasFrontend = true;
        existing.configComponent = f.configComponent;
        existing.tabsCount = f.tabs?.length || 0;
        if (f.name) existing.name = f.name;
        if (f.description) existing.description = f.description;
        if (f.icon) existing.icon = f.icon;
        if (f.category) existing.category = f.category;
      } else {
        map.set(f.id, {
          id: f.id,
          name: f.name,
          version: f.version || '1.0.0',
          category: f.category || 'general',
          type: 'FrontendPlugin',
          hasFrontend: true,
          hasBackend: false,
          configComponent: f.configComponent,
          tabsCount: f.tabs?.length || 0,
          description: f.description || 'Plugin registrado no frontend.',
          icon: f.icon || getCategoryIcon(f.category || 'general')
        });
      }
    }

    return Array.from(map.values());
  }

  function getCategoryIcon(cat: string) {
    switch (cat) {
      case 'auth': return Shield;
      case 'scm': return FolderGit2;
      case 'cicd': return PlayCircle;
      case 'observability': return Activity;
      default: return Blocks;
    }
  }

  function getFallbackDescription(id: string): string {
    switch (id) {
      case 'ldap':
        return 'Autenticação centralizada e consulta de usuários via protocolo LDAP.';
      case 'gitlab':
        return 'Descoberta automatizada de projetos, leitura de project-info.yml e varredura de riscos.';
      case 'jenkins':
        return 'Monitoramento em tempo real do status de jobs e pipelines de integração contínua.';
      default:
        return 'Plugin do ecossistema Daileon.';
    }
  }
</script>

<div class="space-y-6">
  <!-- Top Stat Cards -->
  <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
    <div class="plate p-4 flex items-center gap-4" style="--chamfer: 12px;">
      <div class="w-10 h-10 rounded-lg bg-visor/10 border border-visor/30 flex items-center justify-center shrink-0">
        <Blocks class="w-5 h-5 t-visor" />
      </div>
      <div>
        <p class="text-[0.6875rem] font-bold uppercase tracking-wider t-faint">Total de Plugins</p>
        <p class="text-xl font-bold t-txt">{pluginList.length}</p>
      </div>
    </div>

    <div class="plate p-4 flex items-center gap-4" style="--chamfer: 12px;">
      <div class="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center shrink-0">
        <Cpu class="w-5 h-5 text-emerald-400" />
      </div>
      <div>
        <p class="text-[0.6875rem] font-bold uppercase tracking-wider t-faint">Backend Services</p>
        <p class="text-xl font-bold t-txt">{backendPlugins.length}</p>
      </div>
    </div>

    <div class="plate p-4 flex items-center gap-4" style="--chamfer: 12px;">
      <div class="w-10 h-10 rounded-lg bg-blue-500/10 border border-blue-500/30 flex items-center justify-center shrink-0">
        <Layers class="w-5 h-5 text-blue-400" />
      </div>
      <div>
        <p class="text-[0.6875rem] font-bold uppercase tracking-wider t-faint">Frontend Extension Tabs</p>
        <p class="text-xl font-bold t-txt">{frontendPlugins.reduce((acc, p) => acc + (p.tabs?.length || 0), 0)}</p>
      </div>
    </div>

    <div class="plate p-4 flex items-center gap-4" style="--chamfer: 12px;">
      <div class="w-10 h-10 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-center justify-center shrink-0">
        <Settings class="w-5 h-5 text-amber-400" />
      </div>
      <div>
        <p class="text-[0.6875rem] font-bold uppercase tracking-wider t-faint">Configuráveis</p>
        <p class="text-xl font-bold t-txt">{frontendPlugins.filter(p => Boolean(p.configComponent)).length}</p>
      </div>
    </div>
  </div>

  <!-- Header Controls & Filters -->
  <div class="flex flex-wrap items-center justify-between gap-4 border-b border-[var(--line)] pb-4">
    <div class="space-y-1">
      <h2 class="text-lg font-bold t-txt flex items-center gap-2">
        <Blocks class="w-5 h-5 t-visor" /> Central de Plugins
      </h2>
      <p class="t-dim text-xs">
        Gerenciamento e diagnóstico da arquitetura extensível do Daileon.
      </p>
    </div>

    <div class="flex items-center gap-3">
      <div class="seg" role="tablist">
        {#each Object.entries(categoryLabels) as [catKey, label]}
          <button
            type="button"
            class="seg-item cursor-pointer {activeCategory === catKey ? 'is-active' : ''}"
            on:click={() => setCategory(catKey)}
          >
            <span>{label}</span>
          </button>
        {/each}
      </div>

      <button
        type="button"
        on:click={loadPlugins}
        disabled={loading}
        class="btn btn-sm btn-ghost p-2 flex items-center gap-1.5"
        title="Atualizar lista de plugins"
      >
        <RefreshCw class="w-3.5 h-3.5 {loading ? 'animate-spin' : ''}" />
      </button>
    </div>
  </div>

  {#if error}
    <div class="p-4 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-xs flex items-center gap-2">
      <span class="font-bold">Erro:</span> {error}
    </div>
  {/if}

  <!-- Plugins Grid -->
  {#if loading && pluginList.length === 0}
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {#each Array(3) as _}
        <div class="skeleton h-48 rounded-xl"></div>
      {/each}
    </div>
  {:else if filteredPlugins.length === 0}
    <div class="plate p-8 text-center space-y-2">
      <p class="t-dim text-sm">Nenhum plugin encontrado para a categoria selecionada.</p>
    </div>
  {:else}
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {#each filteredPlugins as p (p.id)}
        <div class="plate p-6 space-y-4 flex flex-col justify-between hover:border-visor/50 transition-colors" style="--chamfer: 16px;">
          <div class="space-y-3">
            <!-- Header Card -->
            <div class="flex items-start justify-between gap-3">
              <div class="flex items-center gap-3">
                <div class="p-2.5 rounded-lg bg-surface-2 border border-line shrink-0">
                  <svelte:component this={p.icon} class="w-5 h-5 t-visor" />
                </div>
                <div>
                  <h3 class="font-bold text-sm t-txt flex items-center gap-2">
                    {p.name}
                  </h3>
                  <span class="text-[0.6875rem] font-mono t-faint">v{p.version} &middot; {p.id}</span>
                </div>
              </div>

              <span class="chip chip-ok text-[0.625rem] py-0.5 px-2 font-semibold uppercase tracking-wider shrink-0 flex items-center gap-1">
                <CheckCircle2 class="w-3 h-3" /> Builtin
              </span>
            </div>

            <!-- Description -->
            <p class="text-xs t-dim leading-relaxed min-h-[2.5rem]">
              {p.description}
            </p>

            <!-- Metadata Badges -->
            <div class="flex flex-wrap items-center gap-2 text-[0.6875rem] pt-2 border-t border-line/60">
              <span class="px-2 py-0.5 rounded bg-surface-3 t-faint font-semibold uppercase tracking-wider">
                {getCategoryLabel(p.category)}
              </span>
              {#if p.type}
                <span class="px-2 py-0.5 rounded bg-surface-3 t-faint font-mono">
                  {p.type}
                </span>
              {/if}
              {#if p.hasRouter}
                <span class="px-2 py-0.5 rounded bg-visor/10 text-visor font-semibold">
                  API Endpoints
                </span>
              {/if}
              {#if p.tabsCount > 0}
                <span class="px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 font-semibold">
                  {p.tabsCount} {p.tabsCount === 1 ? 'Aba' : 'Abas'} no Catálogo
                </span>
              {/if}
            </div>
          </div>

          <!-- Card Actions -->
          <div class="pt-3 border-t border-line flex items-center justify-between gap-2">
            <span class="text-[0.6875rem] t-faint flex items-center gap-1">
              <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              Ativo no Sistema
            </span>

            {#if p.configComponent}
              <button
                type="button"
                on:click={() => onSelectConfigPlugin(p.id)}
                class="btn btn-sm btn-visor text-xs flex items-center gap-1.5"
              >
                <Settings class="w-3.5 h-3.5" />
                <span>Configurar</span>
              </button>
            {/if}
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>
