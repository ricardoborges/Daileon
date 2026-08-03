<script lang="ts">
  import { LayoutGrid, Table } from 'lucide-svelte';
  import { t } from '$lib/i18n';
  import type { ViewMode } from '$lib/catalogView';

  export let value: ViewMode = 'cards';
  export let onSelect: (mode: ViewMode) => void;
</script>

<div class="flex items-center gap-1 bg-surface-2 p-1 border border-line" style="border-radius: 6px;">
  <button
    type="button"
    on:click={() => onSelect('cards')}
    aria-pressed={value === 'cards'}
    class={`btn btn-sm text-xs gap-1.5 px-2.5 py-1 ${value === 'cards' ? 'btn-visor font-bold' : 'opacity-70 hover:opacity-100'}`}
    title={$t('catalog.viewModeCards')}
  >
    <LayoutGrid class="w-3.5 h-3.5" />
    <span>{$t('catalog.viewModeCards')}</span>
  </button>
  <button
    type="button"
    on:click={() => onSelect('table')}
    aria-pressed={value === 'table'}
    class={`btn btn-sm text-xs gap-1.5 px-2.5 py-1 ${value === 'table' ? 'btn-visor font-bold' : 'opacity-70 hover:opacity-100'}`}
    title={$t('catalog.viewModeTable')}
  >
    <Table class="w-3.5 h-3.5" />
    <span>{$t('catalog.viewModeTable')}</span>
  </button>
</div>
