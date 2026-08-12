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
  import {
    AlertTriangle,
    Download,
    Eye,
    EyeOff,
    FileText,
    GitFork,
    HelpCircle,
    Image as ImageIcon,
    Repeat
  } from 'lucide-svelte';

  export let graph: DependencyGraph | null = null;
  export let loading = false;
  export let error: string | null = null;
  /** Listas de "depende de" / "consumido por" abaixo do diagrama. */
  export let showRootLists = false;
  /** Opção para incluir ou remover recursos/bancos do grafo. */
  export let showResources = true;

  let container: HTMLDivElement;
  let svg = '';
  let renderError: string | null = null;
  let mounted = false;
  let renderCount = 0;
  let exportMenuOpen = false;

  onMount(() => {
    mounted = true;
  });

  $: displayGraph = filterGraph(graph, showResources);
  $: if (mounted && displayGraph) void render(displayGraph, $theme);
  $: rootNode = displayGraph?.nodes.find((n) => n.is_root) || null;
  $: dependsOn = rootNode ? neighboursOf(rootNode, 'out') : [];
  $: consumedBy = rootNode ? neighboursOf(rootNode, 'in') : [];

  function filterGraph(g: DependencyGraph | null, includeRes: boolean): DependencyGraph | null {
    if (!g) return null;
    if (includeRes) return g;

    const isResourceNode = (n: GraphNode) =>
      Boolean(
        n.is_resource ||
        (n.type || '').toLowerCase() === 'database' ||
        (n.type || '').toLowerCase() === 'db' ||
        (n.type || '').toLowerCase() === 'resource'
      );

    const nodes = g.nodes.filter((n) => !isResourceNode(n));
    const validNodeIds = new Set(nodes.map((n) => n.id));
    const edges = g.edges.filter((e) => validNodeIds.has(e.source) && validNodeIds.has(e.target));

    return {
      ...g,
      nodes,
      edges,
      stats: {
        ...g.stats,
        nodes_shown: nodes.length,
        edges_shown: edges.length
      }
    };
  }

  function neighboursOf(root: GraphNode, direction: 'in' | 'out'): GraphNode[] {
    if (!displayGraph) return [];
    const ids = displayGraph.edges
      .filter((e) => (direction === 'out' ? e.source === root.id : e.target === root.id))
      .map((e) => (direction === 'out' ? e.target : e.source));
    return displayGraph.nodes.filter((n) => ids.includes(n.id));
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

  function getPreparedSvgElement(): { clone: SVGElement; width: number; height: number } | null {
    if (!container) return null;
    const svgEl = container.querySelector('svg');
    if (!svgEl) return null;

    const clone = svgEl.cloneNode(true) as SVGElement;
    clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
    clone.setAttribute('xmlns:xlink', 'http://www.w3.org/1999/xlink');
    clone.removeAttribute('style');

    let width = 800;
    let height = 600;

    const viewBox = svgEl.getAttribute('viewBox');
    if (viewBox) {
      const parts = viewBox.split(/[\s,]+/).map(Number);
      if (parts.length === 4 && parts[2] > 0 && parts[3] > 0) {
        width = parts[2];
        height = parts[3];
      }
    } else {
      const rect = svgEl.getBoundingClientRect();
      width = rect.width || 800;
      height = rect.height || 600;
    }

    const padding = 24;
    const exportWidth = Math.ceil(width + padding * 2);
    const exportHeight = Math.ceil(height + padding * 2);

    clone.setAttribute('width', exportWidth.toString());
    clone.setAttribute('height', exportHeight.toString());
    clone.setAttribute('viewBox', `-${padding} -${padding} ${exportWidth} ${exportHeight}`);

    const p = graphPalette();
    const styleEl = document.createElementNS('http://www.w3.org/2000/svg', 'style');
    styleEl.textContent = `
      svg {
        background-color: ${p.surface};
        font-family: 'JetBrains Mono', ui-monospace, monospace;
      }
      .node text, .node label, .node tspan {
        font-family: 'JetBrains Mono', ui-monospace, monospace !important;
        font-size: 13px !important;
        white-space: pre !important;
        fill: ${p.txt} !important;
      }
      .edgePath path {
        stroke-width: 1.5px;
      }
    `;
    clone.insertBefore(styleEl, clone.firstChild);

    const bgRect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    bgRect.setAttribute('x', `-${padding}`);
    bgRect.setAttribute('y', `-${padding}`);
    bgRect.setAttribute('width', '100%');
    bgRect.setAttribute('height', '100%');
    bgRect.setAttribute('fill', p.surface);
    clone.insertBefore(bgRect, styleEl.nextSibling);

    return { clone, width: exportWidth, height: exportHeight };
  }

  function exportSvg(): void {
    const prepared = getPreparedSvgElement();
    if (!prepared) return;

    const svgData = new XMLSerializer().serializeToString(prepared.clone);
    const blob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = `dependency-graph-${Date.now()}.svg`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    exportMenuOpen = false;
  }

  function exportPng(): void {
    const prepared = getPreparedSvgElement();
    if (!prepared) return;

    const { clone, width, height } = prepared;
    const svgData = new XMLSerializer().serializeToString(clone);
    const svgBlob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(svgBlob);

    const img = new window.Image();
    img.onload = () => {
      try {
        const scale = 2;
        const canvas = document.createElement('canvas');
        canvas.width = Math.max(1, Math.round(width * scale));
        canvas.height = Math.max(1, Math.round(height * scale));

        const ctx = canvas.getContext('2d');
        if (!ctx) {
          console.error('Canvas 2D context not supported');
          URL.revokeObjectURL(url);
          return;
        }

        ctx.scale(scale, scale);
        ctx.drawImage(img, 0, 0, width, height);
        URL.revokeObjectURL(url);

        canvas.toBlob((blob) => {
          if (!blob) {
            console.error('Falha ao gerar blob PNG');
            return;
          }
          const pngUrl = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = pngUrl;
          a.download = `dependency-graph-${Date.now()}.png`;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          URL.revokeObjectURL(pngUrl);
        }, 'image/png');
      } catch (err) {
        console.error('Erro ao renderizar canvas:', err);
        URL.revokeObjectURL(url);
      }
    };

    img.onerror = (err) => {
      console.error('Erro ao carregar imagem SVG para PNG:', err);
      URL.revokeObjectURL(url);
    };

    img.src = url;
    exportMenuOpen = false;
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

    <div class="flex flex-wrap items-center gap-2">
      <slot name="controls" />

      <!-- Botão para incluir/remover recursos do gráfico -->
      <button
        type="button"
        on:click={() => (showResources = !showResources)}
        class="px-2.5 py-1 text-xs rounded border transition-colors flex items-center gap-1.5 font-medium"
        style="background: var(--bg-surface-2); border-color: var(--line); color: var(--txt);"
        title={$t(showResources ? 'graph.hideResources' : 'graph.showResources')}
      >
        {#if showResources}
          <Eye class="w-3.5 h-3.5 t-visor" />
          <span>{$t('graph.hideResources')}</span>
        {:else}
          <EyeOff class="w-3.5 h-3.5 t-dim" />
          <span>{$t('graph.showResources')}</span>
        {/if}
      </button>

      <!-- Opção para exportar imagem -->
      <div class="relative inline-block text-left">
        <button
          type="button"
          on:click={() => (exportMenuOpen = !exportMenuOpen)}
          class="px-2.5 py-1 text-xs rounded border transition-colors flex items-center gap-1.5 font-medium"
          style="background: var(--bg-surface-2); border-color: var(--line); color: var(--txt);"
        >
          <Download class="w-3.5 h-3.5 t-visor" />
          <span>{$t('graph.exportImage')}</span>
        </button>

        {#if exportMenuOpen}
          <!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
          <div class="fixed inset-0 z-10" on:click={() => (exportMenuOpen = false)}></div>

          <div
            class="absolute right-0 mt-1 w-36 rounded-md shadow-lg border z-20 py-1"
            style="background: var(--bg-surface-3); border-color: var(--line);"
          >
            <button
              type="button"
              on:click={exportPng}
              class="w-full text-left px-3 py-1.5 text-xs hover:bg-surface-2 flex items-center gap-2 t-txt transition-colors"
            >
              <ImageIcon class="w-3.5 h-3.5 t-visor" />
              <span>{$t('graph.exportPng')}</span>
            </button>
            <button
              type="button"
              on:click={exportSvg}
              class="w-full text-left px-3 py-1.5 text-xs hover:bg-surface-2 flex items-center gap-2 t-txt transition-colors"
            >
              <FileText class="w-3.5 h-3.5 t-ok" />
              <span>{$t('graph.exportSvg')}</span>
            </button>
          </div>
        {/if}
      </div>
    </div>
  </div>

  {#if loading}
    <div class="skeleton h-56"></div>
  {:else if error || renderError}
    <div class="flex items-start gap-2 text-[13px] t-alert">
      <AlertTriangle class="w-4 h-4 shrink-0 mt-0.5" />
      <span>{error || renderError}</span>
    </div>
  {:else if !displayGraph || displayGraph.nodes.length === 0}
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

    <!-- Legenda na ordem de destaque solicitada -->
    <div class="flex flex-wrap items-center gap-x-5 gap-y-2 text-[11px] t-faint border-t border-line pt-4">
      <span class="flex items-center gap-1.5" title="Destaque principal">
        <span class="inline-block w-3 h-2.5 border-2" style="border-color: var(--visor);"></span>
        {$t('graph.legendWebsite')}
      </span>
      <span class="flex items-center gap-1.5" title="Destaque intermediário">
        <span class="inline-block w-3 h-2.5 border-[1.5px]" style="border-color: var(--crest);"></span>
        {$t('graph.legendService')}
      </span>
      <span class="flex items-center gap-1.5" title="Destaque suave">
        <span class="inline-block w-3 h-2.5 border" style="border-color: var(--line-strong);"></span>
        {$t('graph.legendResource')}
      </span>
      <span class="flex items-center gap-1.5" title="Destaque suave">
        <span class="inline-block w-3 h-2.5 border rounded-sm" style="border-color: var(--line-strong);"></span>
        {$t('graph.legendDatabase')}
      </span>
      <span class="flex items-center gap-1.5">
        <span class="inline-block w-3 h-2.5 border-2" style="border-color: var(--visor);"></span>
        {$t('graph.legendRoot')}
      </span>
      <span class="flex items-center gap-1.5" title="Caixa maior com destaque de borda">
        <span class="inline-block w-3.5 h-3 border-2" style="border-color: var(--visor); box-shadow: 0 0 4px var(--visor);"></span>
        {$t('graph.legendHub')}
      </span>
      <span class="flex items-center gap-1.5">
        <span class="inline-block w-3 h-2.5 border-2" style="border-color: var(--ok);"></span>
        {$t('graph.legendExternal')}
      </span>
      <span class="flex items-center gap-1.5">
        <span class="inline-block w-3 h-2.5 border border-dashed" style="border-color: var(--crest);"></span>
        {$t('graph.legendUnresolved')}
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
        {$t('graph.counts', { nodes: displayGraph.stats.nodes_shown, edges: displayGraph.stats.edges_shown })}
        {#if displayGraph.isolated_count > 0}
          · {$t('graph.isolated', { count: displayGraph.isolated_count })}
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
                      <span class="tag t-dim border-line" title={$t('graph.legendResource')}>{node.name} (recurso)</span>
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

    {#if displayGraph.cycles.length > 0}
      <div class="space-y-2 border-t border-line pt-4">
        <span class="label flex items-center gap-1.5 t-alert">
          <Repeat class="w-3.5 h-3.5" />
          {$t('graph.cyclesTitle', { count: displayGraph.cycles.length })}
        </span>
        <ul class="space-y-1">
          {#each displayGraph.cycles as cycle}
            <li class="text-[13px] font-mono t-alert">
              {cycle.names.join(' → ')} → {cycle.names[0]}
            </li>
          {/each}
        </ul>
        <p class="t-faint text-xs">{$t('graph.cyclesHint')}</p>
      </div>
    {/if}

    {#if displayGraph.unresolved.length > 0}
      <div class="space-y-2 border-t border-line pt-4">
        <span class="label flex items-center gap-1.5 t-crest">
          <HelpCircle class="w-3.5 h-3.5" />
          {$t('graph.unresolvedTitle', { count: displayGraph.unresolved.length })}
        </span>
        <ul class="flex flex-wrap gap-2">
          {#each displayGraph.unresolved as name}
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
    overflow: visible;
  }

  .daileon-graph :global(a) {
    cursor: pointer;
  }

  .daileon-graph :global(.node text),
  .daileon-graph :global(.node label),
  .daileon-graph :global(.node span),
  .daileon-graph :global(.node tspan) {
    overflow: visible !important;
    white-space: pre !important;
  }

  .daileon-graph :global(.node foreignObject) {
    overflow: visible !important;
  }

  .daileon-graph :global(.node:hover rect),
  .daileon-graph :global(.node:hover polygon),
  .daileon-graph :global(.node:hover path) {
    filter: brightness(1.15);
  }

  .daileon-graph :global(.hub rect),
  .daileon-graph :global(.hub polygon),
  .daileon-graph :global(.hub path) {
    stroke-width: 3px !important;
    filter: drop-shadow(0 0 6px rgba(46, 211, 236, 0.35));
  }

  .daileon-graph :global(.hub text) {
    font-weight: 700 !important;
    font-size: 14.5px !important;
  }
</style>
