<script lang="ts">
  import { onDestroy } from 'svelte';
  import { Search, X, FileText, FileType, Image } from 'lucide-svelte';
  import { searchComponentDocs, type DocSearchHit } from '$lib/api';
  import { t } from '$lib/i18n';

  export let componentId: number;
  /** Documento aberto, para destacar a linha correspondente nos resultados. */
  export let currentDocPath: string = '';

  /** Abaixo disso a busca não roda: um caractere casaria com quase tudo. */
  const MIN_TERM = 2;
  const DEBOUNCE_MS = 250;

  let query = '';
  let results: DocSearchHit[] = [];
  let searching = false;
  let error = '';
  let timer: ReturnType<typeof setTimeout> | undefined;
  /** Contador de requisições: só a última respondida pinta a lista. */
  let requestId = 0;

  $: active = query.trim().length >= MIN_TERM;
  $: schedule(query.trim());

  const docHref = (path: string) =>
    `/catalog/${componentId}/docs/${path.split('/').map(encodeURIComponent).join('/')}`;

  function schedule(term: string) {
    clearTimeout(timer);
    if (term.length < MIN_TERM) {
      results = [];
      searching = false;
      error = '';
      return;
    }
    searching = true;
    timer = setTimeout(() => run(term), DEBOUNCE_MS);
  }

  async function run(term: string) {
    const id = ++requestId;
    try {
      const hits = await searchComponentDocs(componentId, term);
      if (id !== requestId) return;
      results = hits;
      error = '';
    } catch (e) {
      if (id !== requestId) return;
      results = [];
      error = e instanceof Error ? e.message : String(e);
    } finally {
      if (id === requestId) searching = false;
    }
  }

  function clear() {
    query = '';
  }

  onDestroy(() => clearTimeout(timer));
</script>

<div class="relative mb-2">
  <Search class="w-3.5 h-3.5 t-faint absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
  <input
    type="search"
    bind:value={query}
    placeholder={$t('techdocs.searchPlaceholder')}
    aria-label={$t('techdocs.searchPlaceholder')}
    class="field pl-8 pr-7 py-1.5 text-[12px]"
    on:keydown={(e) => e.key === 'Escape' && clear()}
  />
  {#if query}
    <button
      type="button"
      class="absolute right-2 top-1/2 -translate-y-1/2 t-faint hover:t-visor transition-colors"
      title={$t('techdocs.clearSearch')}
      aria-label={$t('techdocs.clearSearch')}
      on:click={clear}
    >
      <X class="w-3.5 h-3.5" />
    </button>
  {/if}
</div>

{#if active}
  {#if searching}
    <p class="t-faint text-[11px] px-2 py-1">{$t('techdocs.searching')}</p>
  {:else if error}
    <p class="t-alert text-[11px] px-2 py-1">{error}</p>
  {:else if results.length === 0}
    <p class="t-faint text-[11px] px-2 py-1">{$t('techdocs.noResults')}</p>
  {:else}
    <p class="label px-2 pb-1">{$t('techdocs.resultCount', { count: results.length })}</p>
    <nav class="space-y-0.5">
      {#each results as hit (hit.id)}
        <a
          href={docHref(hit.relative_path)}
          class="result-row"
          class:is-active={currentDocPath === hit.relative_path}
          title={hit.relative_path}
        >
          <span class="flex items-center gap-1.5">
            <span class="shrink-0">
              {#if hit.doc_type === 'pdf'}
                <FileType class="w-3 h-3 t-alert" />
              {:else if hit.doc_type === 'docx'}
                <FileText class="w-3 h-3 text-blue-400 opacity-90" />
              {:else if hit.doc_type === 'image'}
                <Image class="w-3 h-3 t-iris" />
              {:else}
                <FileText class="w-3 h-3 opacity-60" />
              {/if}
            </span>
            <span class="truncate font-medium">{hit.title || hit.relative_path.split('/').pop()}</span>
          </span>
          <span class="block truncate text-[10px] t-faint pl-[1.125rem]">{hit.relative_path}</span>
          {#if hit.snippet}
            <span class="block text-[10px] t-dim pl-[1.125rem] line-clamp-2">{hit.snippet}</span>
          {/if}
        </a>
      {/each}
    </nav>
  {/if}
{:else}
  <slot />
{/if}

<style>
  /* Mesma linguagem visual do `.tree-row` do DocsTree, com espaço para o trecho. */
  .result-row {
    display: block;
    padding: 0.4rem 0.5rem;
    border-left: 2px solid transparent;
    font-size: 0.75rem;
    color: var(--txt-dim);
    transition: all 0.14s ease;
  }
  .result-row:hover {
    color: var(--txt);
    background: var(--surface-2);
    border-left-color: var(--line-strong);
  }
  .result-row.is-active {
    color: var(--visor);
    background: var(--visor-wash);
    border-left-color: var(--visor);
  }
  .line-clamp-2 {
    display: -webkit-box;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
    overflow: hidden;
  }
</style>
