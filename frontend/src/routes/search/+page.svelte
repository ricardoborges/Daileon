<script lang="ts">
  import { globalSearch, type SearchResults } from '$lib/api';
  import { Search, Layers, FileText, ArrowRight, CornerDownLeft } from 'lucide-svelte';
  import { t } from '$lib/i18n';

  let query = '';
  let results: SearchResults | null = null;
  let searching = false;
  let lastQuery = '';

  async function handleSearch() {
    if (!query.trim()) return;
    searching = true;
    try {
      results = await globalSearch(query);
      lastQuery = query;
    } catch (e) {
      console.error(e);
    } finally {
      searching = false;
    }
  }
</script>

<main class="max-w-5xl mx-auto px-6 py-10 space-y-8">
  <header class="space-y-3">
    <span class="eyebrow">{$t('search.eyebrow')}</span>
    <div class="rule">
      <h1 class="text-3xl font-bold tracking-[-0.03em] t-txt flex items-center gap-3 whitespace-nowrap">
        <Search class="w-7 h-7 t-visor" /> {$t('search.title')}
      </h1>
    </div>
    <p class="t-dim text-sm">
      {$t('search.subtitle')}
    </p>
  </header>

  <form on:submit|preventDefault={handleSearch} class="search-bar">
    <span class="label t-visor shrink-0 hidden sm:block">&gt;</span>
    <Search class="w-4 h-4 t-faint shrink-0 sm:hidden" />
    <input
      type="text"
      bind:value={query}
      placeholder={$t('search.placeholder')}
      aria-label={$t('search.placeholder')}
    />
    <button type="submit" disabled={searching || !query.trim()} class="btn btn-primary btn-sm">
      {#if searching}
        {$t('search.btnSearching')}
      {:else}
        {$t('search.btnExecute')} <CornerDownLeft class="w-3 h-3" />
      {/if}
    </button>
  </form>

  {#if results}
    <div class="space-y-10">
      <p class="label">
        {$t('search.resultsFor')} <span class="t-visor">"{lastQuery}"</span> &middot;
        {$t('search.occurrences', { count: results.components.length + results.docs.length })}
      </p>

      <!-- Componentes -->
      <section class="space-y-4">
        <div class="rule">
          <h2 class="text-base font-bold t-txt flex items-center gap-2 whitespace-nowrap">
            <Layers class="w-4 h-4 t-visor" /> {$t('search.secComponents')}
            <span class="label">({results.components.length})</span>
          </h2>
        </div>

        {#if results.components.length === 0}
          <p class="label">{$t('search.noComponentsMatched')}</p>
        {:else}
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            {#each results.components as comp}
              <a href={`/catalog/${comp.id}`} class="plate plate-link block p-4" style="--chamfer: 12px;">
                <h3 class="font-bold t-txt">{comp.name}</h3>
                <p class="t-dim text-[13px] mt-1 line-clamp-2">{comp.description}</p>
                <div class="flex items-center justify-between mt-3 pt-3 border-t border-line">
                  <span class="label">{comp.type} &middot; {comp.owner}</span>
                  <ArrowRight class="w-3.5 h-3.5 t-visor" />
                </div>
              </a>
            {/each}
          </div>
        {/if}
      </section>

      <!-- Documentos -->
      <section class="space-y-4">
        <div class="rule">
          <h2 class="text-base font-bold t-txt flex items-center gap-2 whitespace-nowrap">
            <FileText class="w-4 h-4 t-crest" /> {$t('search.secDocs')}
            <span class="label">({results.docs.length})</span>
          </h2>
        </div>

        {#if results.docs.length === 0}
          <p class="label">{$t('search.noDocsMatched')}</p>
        {:else}
          <div class="space-y-2">
            {#each results.docs as doc}
              <a
                href={`/catalog/${doc.component_id}/docs/${doc.relative_path}`}
                class="plate plate-link flex items-center justify-between gap-4 p-4"
                style="--chamfer: 10px;"
              >
                <div class="flex items-center gap-3 min-w-0">
                  <FileText class="w-4 h-4 t-crest shrink-0" />
                  <div class="min-w-0">
                    <span class="font-semibold t-txt text-sm block truncate">{doc.title}</span>
                    <span class="label block mt-1 truncate">{doc.relative_path}</span>
                  </div>
                </div>
                <ArrowRight class="w-4 h-4 t-faint shrink-0" />
              </a>
            {/each}
          </div>
        {/if}
      </section>
    </div>
  {/if}
</main>
