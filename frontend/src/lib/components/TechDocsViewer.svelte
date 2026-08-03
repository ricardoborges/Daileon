<script lang="ts">
  import { onMount } from 'svelte';
  import { marked } from 'marked';
  import mermaid from 'mermaid';
  import { initMermaid } from '$lib/mermaid';
  import { FileText, ChevronRight, Book } from 'lucide-svelte';
  import type { DocFileItem } from '$lib/api';

  export let docs: DocFileItem[] = [];
  export let currentDocPath: string = 'index.md';
  export let markdownContent: string = '';
  export let componentId: number;

  let parsedHtml = '';

  onMount(() => {
    // Mermaid herda a paleta do cockpit em vez do tema padrão; a configuração
    // é a mesma usada pelo grafo de dependências.
    initMermaid();
    renderMarkdown();
  });

  $: if (markdownContent) {
    renderMarkdown();
  }

  async function renderMarkdown() {
    if (!markdownContent) {
      parsedHtml = '<p class="t-faint">Documento em branco.</p>';
      return;
    }
    parsedHtml = await marked.parse(markdownContent);
    setTimeout(renderMermaid, 50);
  }

  async function renderMermaid() {
    try {
      const mermaidNodes = document.querySelectorAll('.doc code.language-mermaid');
      mermaidNodes.forEach((node, idx) => {
        const parent = node.parentElement;
        if (parent && !node.getAttribute('data-mermaid-done')) {
          const code = node.textContent || '';
          const id = `mermaid-diagram-${idx}-${Date.now()}`;
          const container = document.createElement('div');
          container.className = 'mermaid';
          container.id = id;
          container.textContent = code;
          parent.replaceWith(container);
        }
      });
      await mermaid.run();
    } catch (e) {
      console.warn('Mermaid render warning:', e);
    }
  }
</script>

<div class="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
  <!-- Sumário -->
  <aside class="lg:col-span-3 lg:sticky lg:top-24">
    <div class="plate p-4" style="--chamfer: 12px;">
      <div class="flex items-center gap-2 pb-3 mb-2 border-b border-line">
        <Book class="w-3.5 h-3.5 t-visor" />
        <span class="label">Sumário</span>
        <span class="label ml-auto">{docs.length}</span>
      </div>

      <nav class="space-y-0.5 max-h-[70vh] overflow-y-auto -mr-1 pr-1">
        {#each docs as doc}
          <a
            href={`/catalog/${componentId}/docs/${doc.relative_path}`}
            class="toc-link {currentDocPath === doc.relative_path ? 'is-active' : ''}"
          >
            <span class="flex items-center gap-2 truncate">
              <FileText class="w-3 h-3 shrink-0 opacity-60" />
              <span class="truncate">{doc.title}</span>
            </span>
            {#if currentDocPath === doc.relative_path}
              <ChevronRight class="w-3 h-3 shrink-0" />
            {/if}
          </a>
        {/each}
      </nav>
    </div>
  </aside>

  <!-- Documento -->
  <div class="lg:col-span-9 plate" style="--chamfer: 24px;">
    <!-- Cabeçalho de leitura -->
    <div class="flex items-center gap-2 px-8 py-3 border-b border-line bg-surface-2">
      <span class="led led-visor"></span>
      <span class="label truncate">{currentDocPath}</span>
    </div>

    <article class="doc p-8 md:p-10">
      {@html parsedHtml}
    </article>
  </div>
</div>
