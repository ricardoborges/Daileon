<script lang="ts">
  import { Layers, Boxes, FolderGit2 } from 'lucide-svelte';
  import { t } from '$lib/i18n';
  import type { CatalogEntity } from '$lib/catalogView';

  export let value: CatalogEntity = 'projects';
  export let counts: Partial<Record<CatalogEntity, number>> = {};
  /** Chamado com a entidade escolhida; quem monta decide como navegar. */
  export let onSelect: (entity: CatalogEntity) => void;

  $: tabs = [
    { id: 'projects' as const, label: $t('catalog.tabProjects'), hint: $t('catalog.tabProjectsHint'), icon: Layers },
    { id: 'solutions' as const, label: $t('catalog.tabSolutions'), hint: $t('catalog.tabSolutionsHint'), icon: Boxes },
    { id: 'domains' as const, label: $t('catalog.tabDomains'), hint: $t('catalog.tabDomainsHint'), icon: FolderGit2 }
  ];
</script>

<div class="grid grid-cols-1 sm:grid-cols-3 gap-3" role="tablist" aria-label={$t('catalog.tabsLabel')}>
  {#each tabs as tab}
    <button
      type="button"
      role="tab"
      aria-selected={value === tab.id}
      on:click={() => onSelect(tab.id)}
      class="plate p-4 text-left transition-transform hover:-translate-y-0.5 {value === tab.id
        ? 'plate-deep ring-1'
        : 'opacity-80 hover:opacity-100'}"
      style={value === tab.id ? '--chamfer: 12px; --tw-ring-color: var(--visor);' : '--chamfer: 12px;'}
    >
      <div class="flex items-center gap-3">
        <svelte:component
          this={tab.icon}
          class="w-5 h-5 shrink-0 {value === tab.id ? 't-visor' : 't-faint'}"
        />
        <div class="min-w-0 flex-1">
          <div class="flex items-baseline justify-between gap-2">
            <span class="font-bold text-sm {value === tab.id ? 't-txt' : 't-dim'}">{tab.label}</span>
            {#if counts[tab.id] !== undefined}
              <span class="text-xs font-mono t-faint">{counts[tab.id]}</span>
            {/if}
          </div>
          <span class="block text-xs t-faint truncate mt-0.5">{tab.hint}</span>
        </div>
      </div>
    </button>
  {/each}
</div>
