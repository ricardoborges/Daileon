<script lang="ts">
  import { page } from '$app/stores';
  import { fetchComponent, fetchComponentDocs, fetchDocContent, type ComponentItem, type DocFileItem, type DocFileDetail } from '$lib/api';
  import TechDocsViewer from '$lib/components/TechDocsViewer.svelte';
  import { ArrowLeft, BookOpen } from 'lucide-svelte';

  let component: ComponentItem | null = null;
  let docs: DocFileItem[] = [];
  let currentDoc: DocFileDetail | null = null;
  let loading = true;

  $: componentId = parseInt($page.params.id);
  $: docPath = $page.params.path || 'index.md';

  $: if (componentId && docPath) {
    loadData();
  }

  async function loadData() {
    loading = true;
    try {
      [component, docs, currentDoc] = await Promise.all([
        fetchComponent(componentId),
        fetchComponentDocs(componentId),
        fetchDocContent(componentId, docPath)
      ]);
    } catch (e) {
      console.error('Error loading doc:', e);
    } finally {
      loading = false;
    }
  }
</script>

<main class="max-w-7xl mx-auto px-6 py-10 space-y-6">
  {#if component}
    <a href={`/catalog/${componentId}`} class="label inline-flex items-center gap-2 hover:t-visor transition-colors">
      <ArrowLeft class="w-3.5 h-3.5" /> {component.name}
    </a>

    <!-- Barra de identificação do documento -->
    <div class="plate plate-deep flex flex-wrap items-center justify-between gap-4 p-5" style="--chamfer: 16px;">
      <div class="flex items-center gap-3 min-w-0">
        <div class="border border-line bg-surface-2 p-2 t-visor shrink-0">
          <BookOpen class="w-4 h-4" />
        </div>
        <div class="min-w-0">
          <h1 class="text-lg font-bold tracking-[-0.02em] t-txt truncate">
            {component.name} <span class="t-faint font-normal">/ TechDocs</span>
          </h1>
          <span class="label block mt-1">Mantido no repositório GitLab</span>
        </div>
      </div>

      <span class="label flex items-center gap-2">
        Origem
        <code class="font-mono text-[11px] px-1.5 py-1 border border-line bg-surface-2 t-crest normal-case tracking-normal">
          {component.docs_dir}
        </code>
      </span>
    </div>
  {/if}

  {#if loading}
    <div class="skeleton h-96"></div>
  {:else if currentDoc && component}
    <TechDocsViewer
      {docs}
      currentDocPath={docPath}
      markdownContent={currentDoc.content_markdown}
      {componentId}
    />
  {/if}
</main>
