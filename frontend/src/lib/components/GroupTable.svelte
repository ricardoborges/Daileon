<script lang="ts">
  /** Visão em tabela dos grupos do catálogo. Contraparte de `GroupCard`. */
  import { ArrowRight, Users } from 'lucide-svelte';
  import type { ComponentType } from 'svelte';
  import { t } from '$lib/i18n';
  import type { GroupRow } from '$lib/catalogView';

  export let rows: GroupRow[] = [];
  export let icon: ComponentType;
  export let nameLabel: string;
  export let crossLabel: string;
</script>

<div class="plate overflow-hidden">
  <div class="overflow-x-auto">
    <table class="w-full text-left text-sm border-collapse">
      <thead>
        <tr
          class="border-b text-xs uppercase font-mono tracking-wider t-faint bg-[var(--bg-surface)]"
          style="border-color: var(--line);"
        >
          <th class="py-3.5 px-4 font-bold">{nameLabel}</th>
          <th class="py-3.5 px-4 font-bold">{crossLabel}</th>
          <th class="py-3.5 px-4 font-bold">{$t('domains.colOwners')}</th>
          <th class="py-3.5 px-4 font-bold">{$t('domains.colAppsCount')}</th>
          <th class="py-3.5 px-4 font-bold text-right">{$t('domains.colActions')}</th>
        </tr>
      </thead>
      <tbody class="divide-y" style="border-color: var(--line);">
        {#each rows as row}
          <tr class="hover:bg-[var(--bg-surface)] transition-colors group">
            <td class="py-3.5 px-4">
              <a href={row.href} class="font-bold t-txt group-hover:t-visor flex items-center gap-2">
                <svelte:component this={icon} class="w-4 h-4 t-visor shrink-0" />
                <span>{row.name}</span>
              </a>
            </td>
            <td class="py-3.5 px-4">
              <div class="flex flex-wrap gap-1">
                {#each row.crossValues as value}
                  <span class="chip text-xs">{value}</span>
                {:else}
                  <span class="t-faint text-xs">-</span>
                {/each}
              </div>
            </td>
            <td class="py-3.5 px-4">
              <div class="flex flex-wrap gap-1">
                {#each row.owners as owner}
                  <span class="chip chip-visor text-xs flex items-center gap-1">
                    <Users class="w-3 h-3" />
                    {owner}
                  </span>
                {:else}
                  <span class="t-faint text-xs">-</span>
                {/each}
              </div>
            </td>
            <td class="py-3.5 px-4">
              <span class="badge font-mono font-bold text-xs">{row.componentsCount}</span>
            </td>
            <td class="py-3.5 px-4 text-right">
              <a href={row.href} class="btn btn-sm btn-ghost inline-flex items-center gap-1 text-xs">
                <span>{$t('domains.viewDetails')}</span>
                <ArrowRight class="w-3.5 h-3.5" />
              </a>
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
</div>
