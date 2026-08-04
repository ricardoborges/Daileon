<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { browser } from '$app/environment';
  import { marked } from 'marked';
  import mermaid from 'mermaid';
  import { initMermaid } from '$lib/mermaid';
  import { Book, Download, ExternalLink, ChevronsDownUp, ChevronsUpDown, FileWarning } from 'lucide-svelte';
  import { fetchDocRaw, type DocFileItem, type DocType } from '$lib/api';
  import { buildDocsTree, ancestorFolders, allFolderPaths, formatDocSize, resolveDocPath } from '$lib/docsTree';
  import DocsTree from '$lib/components/DocsTree.svelte';
  import DocsSearch from '$lib/components/DocsSearch.svelte';
  import { t } from '$lib/i18n';

  export let docs: DocFileItem[] = [];
  export let currentDocPath: string = 'index.md';
  export let markdownContent: string | null = '';
  export let docType: DocType = 'markdown';
  export let componentId: number;

  let parsedHtml = '';
  let expanded = new Set<string>();
  let autoExpandedFor = '';
  /** Object URL do documento binário aberto (PDF ou imagem). */
  let assetUrl = '';
  let assetError = '';
  let assetLoading = false;
  let loadedAssetPath = '';
  /** Object URLs das imagens embutidas no Markdown, revogadas a cada render. */
  let inlineImageUrls: string[] = [];

  $: isBinary = docType === 'pdf' || docType === 'image';

  $: tree = buildDocsTree(docs);
  $: folderPaths = allFolderPaths(tree);
  $: currentDoc = docs.find((d) => d.relative_path === currentDocPath);

  // Abrir um documento revela as pastas em que ele está. O guard por
  // `autoExpandedFor` é o que permite fechar essa mesma pasta em seguida:
  // sem ele, o bloco reagiria à própria mudança e a reabriria na hora.
  $: if (currentDocPath && currentDocPath !== autoExpandedFor) {
    autoExpandedFor = currentDocPath;
    const next = new Set(expanded);
    for (const folder of ancestorFolders(currentDocPath)) next.add(folder);
    expanded = next;
  }

  onMount(() => {
    // Mermaid herda a paleta do cockpit em vez do tema padrão; a configuração
    // é a mesma usada pelo grafo de dependências.
    initMermaid();
  });

  onDestroy(() => {
    revokeAsset();
    revokeInlineImages();
  });

  $: if (!isBinary) {
    revokeAsset();
    renderMarkdown(markdownContent);
  }

  // `browser`: object URL e download só existem do lado do cliente.
  $: if (browser && isBinary && currentDocPath && currentDocPath !== loadedAssetPath) {
    loadAsset(currentDocPath);
  }

  function toggleFolder(path: string) {
    const next = new Set(expanded);
    if (next.has(path)) next.delete(path);
    else next.add(path);
    expanded = next;
  }

  $: everythingExpanded = folderPaths.length > 0 && folderPaths.every((p) => expanded.has(p));

  function toggleAll() {
    expanded = everythingExpanded ? new Set(ancestorFolders(currentDocPath)) : new Set(folderPaths);
  }

  function revokeAsset() {
    if (assetUrl) {
      URL.revokeObjectURL(assetUrl);
      assetUrl = '';
    }
    loadedAssetPath = '';
  }

  async function loadAsset(path: string) {
    revokeAsset();
    loadedAssetPath = path;
    assetLoading = true;
    assetError = '';
    try {
      const blob = await fetchDocRaw(componentId, path);
      // O endpoint é autenticado por header, então o iframe/img não pode apontar
      // direto para a API: servimos os bytes já baixados por object URL.
      assetUrl = URL.createObjectURL(blob);
    } catch (e) {
      assetError = e instanceof Error ? e.message : String(e);
    } finally {
      assetLoading = false;
    }
  }

  function downloadAsset() {
    if (!assetUrl) return;
    const link = document.createElement('a');
    link.href = assetUrl;
    link.download = currentDocPath.split('/').pop() || 'documento';
    link.click();
  }

  function revokeInlineImages() {
    for (const url of inlineImageUrls) URL.revokeObjectURL(url);
    inlineImageUrls = [];
  }

  async function renderMarkdown(content: string | null = markdownContent) {
    revokeInlineImages();
    if (!content) {
      parsedHtml = `<p class="t-faint">${$t('techdocs.emptyDocument')}</p>`;
      return;
    }
    parsedHtml = await marked.parse(content);
    setTimeout(() => {
      renderMermaid();
      hydrateInlineImages();
    }, 50);
  }

  /**
   * `![diagrama](imagens/fluxo.png)` aponta para um caminho do repositório, que
   * o navegador resolveria contra a URL da página e não acharia. Trocamos pelo
   * blob da imagem já indexada — o endpoint exige o header de autenticação.
   */
  async function hydrateInlineImages() {
    if (!browser) return;
    const root = document.querySelector('.doc');
    if (!root) return;

    for (const img of Array.from(root.querySelectorAll('img'))) {
      const raw = img.getAttribute('src') || '';
      // Absolutas, data: e blob: já resolvem sozinhas.
      if (!raw || /^([a-z]+:|\/\/|\/)/i.test(raw)) continue;

      let target: string;
      try {
        target = resolveDocPath(currentDocPath, decodeURI(raw.split(/[?#]/)[0]));
      } catch {
        continue;
      }

      const asset = docs.find((d) => d.relative_path === target && d.doc_type === 'image');
      if (!asset) continue;

      try {
        const blob = await fetchDocRaw(componentId, asset.relative_path);
        const url = URL.createObjectURL(blob);
        inlineImageUrls = [...inlineImageUrls, url];
        img.setAttribute('src', url);
      } catch (e) {
        console.warn('Inline image load warning:', asset.relative_path, e);
      }
    }
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
        <span class="label">{$t('techdocs.summary')}</span>
        <span class="label ml-auto">{docs.length}</span>
        {#if folderPaths.length > 0}
          <button
            type="button"
            class="t-faint hover:t-visor transition-colors"
            title={everythingExpanded ? $t('techdocs.collapseAll') : $t('techdocs.expandAll')}
            on:click={toggleAll}
          >
            {#if everythingExpanded}
              <ChevronsDownUp class="w-3.5 h-3.5" />
            {:else}
              <ChevronsUpDown class="w-3.5 h-3.5" />
            {/if}
          </button>
        {/if}
      </div>

      <div class="max-h-[70vh] overflow-y-auto -mr-1 pr-1">
        <DocsSearch {componentId} {currentDocPath}>
          <nav class="space-y-0.5">
            <DocsTree
              nodes={tree}
              {currentDocPath}
              {componentId}
              {expanded}
              onToggle={toggleFolder}
            />
          </nav>
        </DocsSearch>
      </div>
    </div>
  </aside>

  <!-- Documento -->
  <div class="lg:col-span-9 plate" style="--chamfer: 24px;">
    <!-- Cabeçalho de leitura -->
    <div class="flex items-center gap-2 px-8 py-3 border-b border-line bg-surface-2">
      <span class="led led-visor"></span>
      <span class="label truncate">{currentDocPath}</span>

      {#if isBinary}
        <span class="label ml-auto shrink-0 flex items-center gap-3">
          {#if currentDoc?.size_bytes}
            <span class="t-faint">{formatDocSize(currentDoc.size_bytes)}</span>
          {/if}
          {#if assetUrl}
            <button type="button" class="hover:t-visor transition-colors" title={$t('techdocs.download')} on:click={downloadAsset}>
              <Download class="w-3.5 h-3.5" />
            </button>
            <a href={assetUrl} target="_blank" rel="noopener noreferrer" class="hover:t-visor transition-colors" title={$t('techdocs.openInNewTab')}>
              <ExternalLink class="w-3.5 h-3.5" />
            </a>
          {/if}
        </span>
      {/if}
    </div>

    {#if isBinary}
      {#if assetLoading}
        <div class="skeleton h-[75vh] m-4"></div>
      {:else if assetError}
        <div class="p-8 flex flex-col items-center gap-3 text-center">
          <FileWarning class="w-8 h-8 t-alert" />
          <p class="t-dim text-sm">{$t('techdocs.assetError')}</p>
          <code class="font-mono text-[11px] t-faint">{assetError}</code>
        </div>
      {:else if assetUrl && docType === 'image'}
        <div class="p-6 flex justify-center bg-surface-2">
          <img src={assetUrl} alt={currentDoc?.title || currentDocPath} class="max-w-full h-auto" />
        </div>
      {:else if assetUrl}
        <iframe src={assetUrl} title={currentDocPath} class="w-full h-[80vh] border-0 bg-surface-2"></iframe>
      {/if}
    {:else}
      <article class="doc p-8 md:p-10">
        {@html parsedHtml}
      </article>
    {/if}
  </div>
</div>
