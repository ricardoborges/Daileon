<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { t } from '$lib/i18n';
  import { HelpCircle, FileCode, Sparkles } from 'lucide-svelte';
  import ProjectInfoBuilder from '$lib/components/ProjectInfoBuilder.svelte';
  import ProjectInfoTemplate from '$lib/components/ProjectInfoTemplate.svelte';

  type ToolTab = 'template' | 'builder';
  let activeTab: ToolTab = 'template';

  onMount(() => {
    const tabParam = $page.url.searchParams.get('tab');
    if (tabParam === 'template' || tabParam === 'builder') {
      activeTab = tabParam;
    }
  });

  function selectTab(tab: ToolTab) {
    activeTab = tab;
    const url = new URL(window.location.href);
    url.searchParams.set('tab', tab);
    goto(url.pathname + url.search, { replaceState: true, keepFocus: true, noScroll: true });
  }
</script>

<svelte:head>
  <title>Ajuda & Manifestos · Daileon</title>
  <meta name="description" content="Ajuda para criação, validação e exportação de manifestos project-info.yml no Daileon." />
</svelte:head>

<div class="max-w-7xl mx-auto px-6 py-8 space-y-8">
  <!-- Top Banner / Header -->
  <div class="plate p-8 flex flex-col md:flex-row md:items-center justify-between gap-6 relative overflow-hidden">
    <div class="space-y-2 max-w-3xl z-10">
      <div class="flex items-center gap-2">
        <span class="label">{$t('tools.eyebrow')}</span>
        <span class="text-xs font-mono px-2 py-0.5 rounded bg-[var(--card)] border border-[var(--line)] t-visor font-bold">
          daileon/v1
        </span>
      </div>
      <h1 class="text-3xl font-bold tracking-tight text-[var(--txt)] flex items-center gap-3">
        <HelpCircle class="w-7 h-7 t-visor" />
        <span>{$t('tools.title')}</span>
      </h1>
      <p class="t-muted text-sm leading-relaxed">
        {$t('tools.subtitle')}
      </p>
    </div>

    <!-- Decorative background visor highlight -->
    <div
      class="absolute -right-10 -bottom-10 w-64 h-64 rounded-full opacity-10 blur-3xl pointer-events-none"
      style="background: var(--visor);"
    ></div>
  </div>

  <!-- Tab selector -->
  <div class="flex items-center gap-2 border-b border-[var(--line)] pb-1">
    <button
      on:click={() => selectTab('template')}
      class="px-4 py-2.5 rounded-t-lg font-bold text-xs flex items-center gap-2 transition-colors relative {activeTab === 'template' ? 'text-[var(--txt)] bg-[var(--card)] border-t border-x border-[var(--line)]' : 't-muted hover:text-[var(--txt)]'}"
      aria-current={activeTab === 'template' ? 'page' : undefined}
    >
      <FileCode class="w-4 h-4 {activeTab === 'template' ? 't-visor' : ''}" />
      <span>{$t('tools.tabTemplate')}</span>
    </button>

    <button
      on:click={() => selectTab('builder')}
      class="px-4 py-2.5 rounded-t-lg font-bold text-xs flex items-center gap-2 transition-colors relative {activeTab === 'builder' ? 'text-[var(--txt)] bg-[var(--card)] border-t border-x border-[var(--line)]' : 't-muted hover:text-[var(--txt)]'}"
      aria-current={activeTab === 'builder' ? 'page' : undefined}
    >
      <Sparkles class="w-4 h-4 {activeTab === 'builder' ? 't-visor' : ''}" />
      <span>{$t('tools.tabBuilder')}</span>
    </button>
  </div>

  <!-- Content depending on activeTab -->
  <div>
    {#if activeTab === 'template'}
      <ProjectInfoTemplate />
    {:else if activeTab === 'builder'}
      <ProjectInfoBuilder />
    {/if}
  </div>
</div>
