<script lang="ts">
  /**
   * Card de um grupo do catálogo. Domínio e solução são simétricos — mesmo
   * agregado, só muda qual campo agrupa e qual é a dimensão cruzada — então
   * os dois usam este componente em vez de duas telas quase iguais.
   */
  import { ChevronRight, ArrowRight, Cpu, Layers } from 'lucide-svelte';
  import type { ComponentType } from 'svelte';
  import type { GroupedComponentItem } from '$lib/api';
  import { t } from '$lib/i18n';

  export let name: string;
  export let href: string;
  export let icon: ComponentType;
  export let components: GroupedComponentItem[] = [];
  export let componentsCount = 0;
  export let owners: string[] = [];
  /** Valores da dimensão cruzada (soluções de um domínio, domínios de uma solução). */
  export let crossValues: string[] = [];
  export let crossLabel: string;
  /** Campo pelo qual os projetos do card são subagrupados. */
  export let groupBy: 'solution' | 'domain';

  $: fallbackLabel = groupBy === 'solution' ? $t('catalog.noSolution') : $t('catalog.noDomain');

  $: subGroups = (() => {
    const groups = new Map<string, GroupedComponentItem[]>();
    for (const c of components) {
      const key = (c[groupBy] || '').trim() || fallbackLabel;
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key)!.push(c);
    }
    return [...groups.entries()].sort((a, b) => a[0].localeCompare(b[0]));
  })();

  function projectsLabel(n: number) {
    return n === 1 ? $t('catalog.projectSingular') : $t('catalog.projectPlural');
  }
</script>

<a
  {href}
  class="plate plate-interactive p-6 space-y-5 flex flex-col justify-between group transition-transform hover:-translate-y-1"
>
  <div class="space-y-4">
    <div class="flex items-start justify-between gap-3">
      <div class="flex items-center gap-2.5 min-w-0">
        <div class="p-2 rounded-lg bg-[var(--bg-surface)] border border-[var(--line)] shrink-0">
          <svelte:component this={icon} class="w-5 h-5 t-visor" />
        </div>
        <div class="min-w-0">
          <h3 class="font-bold text-lg t-txt group-hover:t-visor transition-colors truncate">
            {name}
          </h3>
          <span class="text-xs t-dim mt-0.5 block">
            {componentsCount} {projectsLabel(componentsCount)}
          </span>
        </div>
      </div>
      <span class="btn btn-sm btn-ghost p-1 group-hover:translate-x-1 transition-transform shrink-0">
        <ChevronRight class="w-5 h-5 text-dim" />
      </span>
    </div>

    {#if crossValues.length > 0}
      <div class="space-y-1.5">
        <span class="text-[11px] uppercase font-mono font-bold tracking-wider t-faint block">
          {crossLabel}
        </span>
        <div class="flex flex-wrap gap-1.5">
          {#each crossValues as value}
            <span class="chip text-xs">{value}</span>
          {/each}
        </div>
      </div>
    {/if}

    <div class="pt-3 border-t border-[var(--line)] space-y-3">
      <span class="text-[11px] uppercase font-mono font-bold tracking-wider t-faint flex items-center gap-1.5">
        <Layers class="w-3.5 h-3.5 t-visor" />
        {groupBy === 'solution' ? $t('catalog.projectsBySolution') : $t('catalog.projectsByDomain')}
      </span>
      <div class="space-y-2.5">
        {#each subGroups as [groupName, comps]}
          <div class="space-y-1.5 p-2.5 rounded-lg bg-[var(--bg-surface)] border border-[var(--line)]">
            <div class="flex items-center justify-between gap-2">
              <span class="text-xs font-bold t-visor flex items-center gap-1 min-w-0">
                <Cpu class="w-3 h-3 shrink-0" />
                <span class="truncate">{groupName}</span>
              </span>
              <span class="text-[10px] font-mono t-faint px-1.5 py-0.5 rounded bg-[var(--bg)] shrink-0">
                {comps.length} {projectsLabel(comps.length)}
              </span>
            </div>
            <div class="space-y-1 pt-0.5">
              {#each comps as comp}
                <div class="flex items-center justify-between gap-2 text-xs py-1 px-2 rounded bg-[var(--bg)]">
                  <span class="font-medium t-txt truncate">{comp.name}</span>
                  <span class="text-[10px] font-mono t-faint uppercase px-1 py-0.5 rounded shrink-0">
                    {comp.type}
                  </span>
                </div>
              {/each}
            </div>
          </div>
        {/each}
      </div>
    </div>
  </div>

  <div class="pt-3 border-t border-[var(--line)] flex items-center justify-between text-xs t-visor font-medium group-hover:underline">
    <span>{$t('domains.viewDetails')}</span>
    <ArrowRight class="w-4 h-4" />
  </div>
</a>
