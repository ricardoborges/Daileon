<script lang="ts">
  /**
   * Mapa de dependências do catálogo inteiro, com recorte por domínio ou
   * solução. Projetos sem nenhuma dependência declarada ficam de fora por
   * padrão — em catálogo grande eles são a maioria e viram ruído no diagrama.
   */
  import { onMount } from 'svelte';
  import {
    fetchDependencyGraph,
    fetchDomains,
    fetchSolutions,
    type DependencyGraph
  } from '$lib/api';
  import DependencyGraphView from '$lib/components/DependencyGraph.svelte';
  import { t } from '$lib/i18n';
  import { GitFork, RotateCw } from 'lucide-svelte';

  let graph: DependencyGraph | null = null;
  let loading = true;
  let error: string | null = null;

  let domains: string[] = [];
  let solutions: string[] = [];
  /** `''` = catálogo inteiro; senão `domain:<nome>` ou `solution:<nome>`. */
  let scope = '';
  let includeIsolated = false;

  onMount(async () => {
    await Promise.all([load(), loadFilters()]);
  });

  async function loadFilters() {
    try {
      const [d, s] = await Promise.all([fetchDomains(), fetchSolutions()]);
      domains = d.map((item) => item.domain).filter(Boolean);
      solutions = s.map((item) => item.solution).filter(Boolean);
    } catch (e) {
      console.error('Erro ao carregar filtros do grafo:', e);
    }
  }

  async function load() {
    loading = true;
    error = null;
    try {
      const [kind, value] = scope ? scope.split(/:(.*)/s) : ['', ''];
      graph = await fetchDependencyGraph({
        domain: kind === 'domain' ? value : undefined,
        solution: kind === 'solution' ? value : undefined,
        includeIsolated
      });
    } catch (e: any) {
      console.error(e);
      graph = null;
      error = e?.message || null;
    } finally {
      loading = false;
    }
  }
</script>

<svelte:head>
  <title>{$t('graph.pageTitle')} · Daileon</title>
</svelte:head>

<main class="max-w-7xl mx-auto px-6 py-10 space-y-8">
  <section class="plate plate-deep p-8 space-y-6 relative overflow-hidden" style="--chamfer: 24px;">
    <div class="absolute inset-0 grid-mesh opacity-60 pointer-events-none"></div>

    <div class="relative flex flex-col md:flex-row md:items-end justify-between gap-6">
      <div class="space-y-2">
        <div class="flex items-center gap-2">
          <GitFork class="w-5 h-5 t-visor" />
          <span class="label">{$t('graph.pageEyebrow')}</span>
        </div>
        <h1 class="text-3xl font-bold tracking-[-0.035em] t-txt">{$t('graph.pageTitle')}</h1>
        <p class="t-dim text-sm max-w-2xl">{$t('graph.pageSub')}</p>
      </div>

      <div class="flex flex-wrap items-end gap-3">
        <label class="space-y-1">
          <span class="label block">{$t('graph.scopeLabel')}</span>
          <select
            bind:value={scope}
            on:change={load}
            class="input px-3 py-1.5 text-xs rounded-lg border focus:outline-none focus:ring-1"
            style="border-color: var(--line); background: var(--bg-surface); color: var(--txt);"
          >
            <option value="">{$t('graph.scopeAll')}</option>
            {#if domains.length}
              <optgroup label={$t('graph.filterDomain')}>
                {#each domains as domain}
                  <option value={`domain:${domain}`}>{domain}</option>
                {/each}
              </optgroup>
            {/if}
            {#if solutions.length}
              <optgroup label={$t('graph.filterSolution')}>
                {#each solutions as solution}
                  <option value={`solution:${solution}`}>{solution}</option>
                {/each}
              </optgroup>
            {/if}
          </select>
        </label>

        <label class="flex items-center gap-2 text-xs t-dim pb-1.5 cursor-pointer">
          <input type="checkbox" bind:checked={includeIsolated} on:change={load} />
          {$t('graph.includeIsolated')}
        </label>

        <button on:click={load} disabled={loading} class="btn btn-crest text-xs flex items-center gap-2">
          <RotateCw class="w-3.5 h-3.5 {loading ? 'animate-spin' : ''}" />
          {$t('graph.reload')}
        </button>
      </div>
    </div>
  </section>

  <DependencyGraphView {graph} {loading} {error} />
</main>
