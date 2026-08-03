<script lang="ts">
  import { FileText, FileType, Image, ChevronRight, ChevronDown, Folder, FolderOpen } from 'lucide-svelte';
  import type { DocTreeNode } from '$lib/docsTree';

  export let nodes: DocTreeNode[] = [];
  export let currentDocPath: string = '';
  export let componentId: number;
  export let expanded: Set<string>;
  export let depth: number = 0;
  export let onToggle: (path: string) => void;

  /** Nomes de pasta com espaço ou acento são comuns aqui; a URL precisa deles escapados. */
  const docHref = (path: string) =>
    `/catalog/${componentId}/docs/${path.split('/').map(encodeURIComponent).join('/')}`;
</script>

{#each nodes as node (node.path)}
  {#if node.kind === 'folder'}
    <button
      type="button"
      class="tree-row tree-folder w-full text-left"
      style="padding-left: {0.5 + depth * 0.75}rem"
      aria-expanded={expanded.has(node.path)}
      on:click={() => onToggle(node.path)}
    >
      <span class="shrink-0 opacity-70">
        {#if expanded.has(node.path)}
          <ChevronDown class="w-3 h-3" />
        {:else}
          <ChevronRight class="w-3 h-3" />
        {/if}
      </span>
      <span class="shrink-0 t-crest">
        {#if expanded.has(node.path)}
          <FolderOpen class="w-3.5 h-3.5" />
        {:else}
          <Folder class="w-3.5 h-3.5" />
        {/if}
      </span>
      <span class="truncate font-medium" title={node.name}>{node.name}</span>
    </button>

    {#if expanded.has(node.path)}
      <svelte:self
        nodes={node.children}
        {currentDocPath}
        {componentId}
        {expanded}
        {onToggle}
        depth={depth + 1}
      />
    {/if}
  {:else}
    <a
      href={docHref(node.path)}
      class="tree-row tree-file"
      class:is-active={currentDocPath === node.path}
      style="padding-left: {1.25 + depth * 0.75}rem"
      title={node.path}
    >
      <span class="shrink-0">
        {#if node.doc.doc_type === 'pdf'}
          <FileType class="w-3 h-3 t-alert" />
        {:else if node.doc.doc_type === 'image'}
          <Image class="w-3 h-3 t-iris" />
        {:else}
          <FileText class="w-3 h-3 opacity-60" />
        {/if}
      </span>
      <span class="truncate">{node.name}</span>
    </a>
  {/if}
{/each}

<style>
  /* Alinhado com `.toc-link` do app.css, com recuo por profundidade. */
  .tree-row {
    position: relative;
    display: flex;
    align-items: center;
    gap: 0.4rem;
    padding-top: 0.35rem;
    padding-bottom: 0.35rem;
    padding-right: 0.5rem;
    border-left: 2px solid transparent;
    font-size: 0.75rem;
    color: var(--txt-dim);
    transition: all 0.14s ease;
  }
  .tree-row:hover {
    color: var(--txt);
    background: var(--surface-2);
    border-left-color: var(--line-strong);
  }
  .tree-file.is-active {
    color: var(--visor);
    background: var(--visor-wash);
    border-left-color: var(--visor);
  }
  .tree-folder {
    color: var(--txt);
  }
</style>
