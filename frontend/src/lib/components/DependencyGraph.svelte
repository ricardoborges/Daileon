<script lang="ts">
  /**
   * Diagrama do grafo de dependências declarado nos `project-info.yml`.
   *
   * O desenho é Mermaid: o catálogo tem poucas dependências declaradas, e um
   * `flowchart` já resolve isso sem trazer uma biblioteca de grafos para o
   * bundle. As cores saem dos tokens do tema, não do tema padrão do Mermaid.
   */
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { theme } from '$lib/theme';
  import { t } from '$lib/i18n';
  import { graphPalette, renderMermaid } from '$lib/mermaid';
  import { buildGraphDefinition } from '$lib/graphDefinition';
  import type { DependencyGraph, GraphNode } from '$lib/api';
  import { AlertTriangle, GitFork, HelpCircle, Repeat } from 'lucide-svelte';

  export let graph: DependencyGraph | null = null;
  export let loading = false;
  export let error: string | null = null;
  /** Listas de "depende de" / "consumido por" abaixo do diagrama. */
  export let showRootLists = false;

  let container: HTMLDivElement;
  let svg = '';
  let renderError: string | null = null;
  let mounted = false;
  let renderCount = 0;

  onMount(() => {
    mounted = true;
  });

  $: if (mounted && graph) void render(graph, $theme);
  $: rootNode = graph?.nodes.find((n) => n.is_root) || null;
  $: dependsOn = rootNode ? neighboursOf(rootNode, 'out') : [];
  $: consumedBy = rootNode ? neighboursOf(rootNode, 'in') : [];

  function neighboursOf(root: GraphNode, direction: 'in' | 'out'): GraphNode[] {
    if (!graph) return [];
    const ids = graph.edges
      .filter((e) => (direction === 'out' ? e.source === root.id : e.target === root.id))
      .map((e) => (direction === 'out' ? e.target : e.source));
    return graph.nodes.filter((n) => ids.includes(n.id));
  }

  async function render(g: DependencyGraph, _theme: string): Promise<void> {
    renderError = null;
    if (g.nodes.length === 0) {
      svg = '';
      return;
    }
    try {
      const definition = buildGraphDefinition(g, graphPalette());
      svg = await renderMermaid(`daileon-graph-${++renderCount}`, definition);
    } catch (e: any) {
      console.error('Falha ao desenhar o grafo:', e);
      svg = '';
      renderError = e?.message || 'Erro ao desenhar o diagrama';
    }
  }

  /**
   * O Mermaid embute os links como âncoras SVG, que o roteador do SvelteKit
   * nem sempre intercepta; capturar o clique aqui garante navegação interna.
   */
  function onGraphClick(event: MouseEvent): void {
    let el = event.target as Element | null;
    while (el && el !== container) {
      const href = el.getAttribute?.('href') || el.getAttribute?.('xlink:href');
      if (href && href.startsWith('/')) {
        event.preventDefault();
        void goto(href);
        return;
      }
      el = el.parentElement;
    }
  }

  function nodeHref(node: GraphNode): string | null {
    return node.component_id !== null ? `/catalog/${node.component_id}` : null;
  }
</script>

<section class="plate p-6 space-y-5" style="--chamfer: 16px;">
  <div class="flex flex-wrap items-center justify-between gap-3">
    <h3 class="label label-visor flex items-center gap-2">
      <GitFork class="w-3.5 h-3.5" />
      {$t('graph.title')}
    </h3>
    <slot name="controls" />
  </div>

  {#if loading}
    <div class="skeleton h-56"></div>
  {:else if error || renderError}
    <div class="flex items-start gap-2 text-[13px] t-alert">
      <AlertTriangle class="w-4 h-4 shrink-0 mt-0.5" />
      <span>{error || renderError}</span>
    </div>
  {:else if !graph || graph.nodes.length === 0}
    <div class="text-center space-y-3 py-10">
      <GitFork class="w-8 h-8 mx-auto t-faint" />
      <p class="t-dim text-[13px] max-w-md mx-auto">{$t('graph.empty')}</p>
      <p class="t-faint text-xs max-w-md mx-auto">
        {$t('graph.emptyHint')}
        <code class="font-mono bg-surface-3 border border-line px-1.5 py-0.5 rounded t-crest">dependencies</code>
      </p>
    </div>
  {:else}
    <!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
    <div
      bind:this={container}
      on:click={onGraphClick}
      class="daileon-graph overflow-x-auto py-2"
    >
      {@html svg}
    </div>

    <!-- Legenda -->
    <div class="flex flex-wrap items-center gap-x-5 gap-y-2 text-[11px] t-faint border-t border-line pt-4">
      <span class="flex items-center gap-1.5">
        <span class="inline-block w-3 h-2.5 border-2" style="border-color: var(--visor);"></span>
        {$t('graph.legendRoot')}
      </span>
      <span class="flex items-center gap-1.5">
        <span class="inline-block w-3 h-2.5 border border-dashed" style="border-color: var(--crest);"></span>
        {$t('graph.legendUnresolved')}
      </span>
      <span class="flex items-center gap-1.5">
        <span class="inline-block w-3 h-2.5 border-2" style="border-color: var(--ok);"></span>
        {$t('graph.legendExternal')}
      </span>
      <span class="flex items-center gap-1.5">
        <span class="inline-block w-3 h-2.5 border-2" style="border-color: var(--visor);"></span>
        {$t('graph.legendResource')}
      </span>
      <span class="flex items-center gap-1.5">
        <span class="inline-block w-3 h-2.5 border-2 rounded-sm" style="border-color: var(--visor);"></span>
        {$t('graph.legendDatabase')}
      </span>
      <span class="flex items-center gap-1.5">
        <span class="inline-block w-3 h-2.5 border" style="border-color: var(--alert);"></span>
        {$t('graph.legendDeprecated')}
      </span>
      <span class="flex items-center gap-1.5">
        <span class="inline-block w-3 h-2.5 border border-dashed" style="border-color: var(--line-strong);"></span>
        {$t('graph.legendOutOfScope')}
      </span>
      <span class="ml-auto font-mono">
        {$t('graph.counts', { nodes: graph.stats.nodes_shown, edges: graph.stats.edges_shown })}
        {#if graph.isolated_count > 0}
          · {$t('graph.isolated', { count: graph.isolated_count })}
        {/if}
      </span>
    </div>

    {#if showRootLists && rootNode}
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
        {#each [{ label: $t('graph.dependsOn'), items: dependsOn }, { label: $t('graph.consumedBy'), items: consumedBy }] as group}
          <div class="space-y-2">
            <span class="label">{group.label}</span>
            {#if group.items.length === 0}
              <p class="t-faint text-[13px]">{$t('graph.none')}</p>
            {:else}
              <ul class="flex flex-wrap gap-2">
                {#each group.items as node}
                  <li>
                    {#if nodeHref(node)}
                      <a href={nodeHref(node)} class="tag hover:t-visor transition-colors">{node.name}</a>
                    {:else if node.is_resource}
                      <span class="tag t-visor border-cyan-500/30" title={$t('graph.legendResource')}>{node.name} (recurso)</span>
                    {:else if node.is_external}
                      <span class="tag t-ok border-emerald-500/30" title={$t('graph.legendExternal')}>{node.name} (externo)</span>
                    {:else}
                      <span class="tag t-crest" title={$t('graph.legendUnresolved')}>{node.name} ?</span>
                    {/if}
                  </li>
                {/each}
              </ul>
            {/if}
          </div>
        {/each}
      </div>
    {/if}

    {#if graph.cycles.length > 0}
      <div class="space-y-2 border-t border-line pt-4">
        <span class="label flex items-center gap-1.5 t-alert">
          <Repeat class="w-3.5 h-3.5" />
          {$t('graph.cyclesTitle', { count: graph.cycles.length })}
        </span>
        <ul class="space-y-1">
          {#each graph.cycles as cycle}
            <li class="text-[13px] font-mono t-alert">
              {cycle.names.join(' → ')} → {cycle.names[0]}
            </li>
          {/each}
        </ul>
        <p class="t-faint text-xs">{$t('graph.cyclesHint')}</p>
      </div>
    {/if}

    {#if graph.unresolved.length > 0}
      <div class="space-y-2 border-t border-line pt-4">
        <span class="label flex items-center gap-1.5 t-crest">
          <HelpCircle class="w-3.5 h-3.5" />
          {$t('graph.unresolvedTitle', { count: graph.unresolved.length })}
        </span>
        <ul class="flex flex-wrap gap-2">
          {#each graph.unresolved as name}
            <li class="tag t-crest">{name}</li>
          {/each}
        </ul>
        <p class="t-faint text-xs">{$t('graph.unresolvedHint')}</p>
      </div>
    {/if}
  {/if}
</section>

<style>
  /* O SVG do Mermaid vem com largura fixa; aqui ele acompanha a plate. */
  .daileon-graph :global(svg) {
    max-width: 100%;
    height: auto;
  }

  .daileon-graph :global(a) {
    cursor: pointer;
  }

  .daileon-graph :global(.node:hover rect),
  .daileon-graph :global(.node:hover polygon) {
    filter: brightness(1.15);
  }
</style>
