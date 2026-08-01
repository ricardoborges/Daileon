<script lang="ts">
  import { t } from '$lib/i18n';
  import { GitCommit, Activity, Calendar } from 'lucide-svelte';

  export let dailyCounts: Record<string, number> = {};
  export let totalCommits: number = 0;
  export let loading: boolean = false;

  interface DayCell {
    dateStr: string;
    displayDate: string;
    count: number;
    level: number; // 0..4
    monthLabel?: string;
  }

  // Gera o grid de 52 semanas x 7 dias
  function generateGrid(counts: Record<string, number>): { weeks: DayCell[][]; monthHeaders: { name: string; colIndex: number }[] } {
    const weeks: DayCell[][] = [];
    const monthHeaders: { name: string; colIndex: number }[] = [];

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    // Ajusta para o próximo sábado para fechar a grade na semana atual
    const endDate = new Date(today);
    const dayOfWeek = endDate.getDay(); // 0 = Domingo, 6 = Sábado
    const daysToSaturday = (6 - dayOfWeek);
    endDate.setDate(endDate.getDate() + daysToSaturday);

    // 52 semanas retroativas (364 dias)
    const startDate = new Date(endDate);
    startDate.setDate(startDate.getDate() - (52 * 7 - 1));

    let currentMonth = -1;
    const monthFormatter = new Intl.DateTimeFormat('pt-BR', { month: 'short' });

    let currentDate = new Date(startDate);
    let currentWeek: DayCell[] = [];

    for (let i = 0; i < 52 * 7; i++) {
      const year = currentDate.getFullYear();
      const month = String(currentDate.getMonth() + 1).padStart(2, '0');
      const day = String(currentDate.getDate()).padStart(2, '0');
      const dateStr = `${year}-${month}-${day}`;

      const count = counts[dateStr] || 0;
      let level = 0;
      if (count >= 10) level = 4;
      else if (count >= 6) level = 3;
      else if (count >= 3) level = 2;
      else if (count >= 1) level = 1;

      const displayDate = currentDate.toLocaleDateString('pt-BR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
      });

      // Checa início de novo mês para o cabeçalho
      const monthIdx = currentDate.getMonth();
      if (monthIdx !== currentMonth) {
        currentMonth = monthIdx;
        const monthName = monthFormatter.format(currentDate).replace('.', '');
        monthHeaders.push({
          name: monthName.charAt(0).toUpperCase() + monthName.slice(1),
          colIndex: weeks.length
        });
      }

      const cell: DayCell = {
        dateStr,
        displayDate,
        count,
        level
      };

      currentWeek.push(cell);

      if (currentWeek.length === 7) {
        weeks.push(currentWeek);
        currentWeek = [];
      }

      currentDate.setDate(currentDate.getDate() + 1);
    }

    if (currentWeek.length > 0) {
      weeks.push(currentWeek);
    }

    return { weeks, monthHeaders };
  }

  $: gridData = generateGrid(dailyCounts);

  function getLevelClass(level: number): string {
    switch (level) {
      case 1:
        return 'heat heat-1';
      case 2:
        return 'heat heat-2';
      case 3:
        return 'heat heat-3';
      case 4:
        return 'heat heat-4';
      default:
        return 'heat heat-0';
    }
  }
</script>

<section class="plate p-6 space-y-5" style="--chamfer: 16px;">
  <!-- Sub-header com estatísticas -->
  <div class="flex flex-wrap items-center justify-between gap-4 border-b border-line pb-4">
    <div class="flex items-center gap-3">
      <Activity class="w-5 h-5 t-visor" />
      <div>
        <h3 class="text-sm font-bold t-txt flex items-center gap-2">
          {$t('catalog.commits_title')}
        </h3>
        <p class="text-xs t-dim font-medium">{$t('catalog.commits_subtitle')}</p>
      </div>
    </div>

    <div class="flex items-center gap-2">
      <span class="chip chip-visor text-xs font-bold px-3 py-1 flex items-center gap-1.5">
        <GitCommit class="w-3.5 h-3.5" />
        {$t('catalog.commits_total', { count: totalCommits })}
      </span>
    </div>
  </div>

  {#if loading}
    <div class="skeleton h-32 w-full rounded-lg"></div>
  {:else}
    <div class="overflow-x-auto pt-2 pb-2">
      <div class="min-w-[720px] space-y-2">
        <!-- Rótulos dos Meses -->
        <div class="flex text-[10px] font-mono t-faint pl-8 relative h-4">
          {#each gridData.monthHeaders as header}
            <span
              class="absolute font-semibold uppercase tracking-wider"
              style="left: {header.colIndex * 13 + 32}px;"
            >
              {header.name}
            </span>
          {/each}
        </div>

        <!-- Grade Principal + Rótulos dos Dias da Semana -->
        <div class="flex items-start gap-2">
          <!-- Dias da semana (Seg, Qua, Sex) -->
          <div class="grid grid-rows-7 gap-[3px] text-[9px] font-mono t-faint h-[98px] pr-1 pt-[1px]">
            <span class="h-[11px] leading-[11px]"></span>
            <span class="h-[11px] leading-[11px]">Seg</span>
            <span class="h-[11px] leading-[11px]"></span>
            <span class="h-[11px] leading-[11px]">Qua</span>
            <span class="h-[11px] leading-[11px]"></span>
            <span class="h-[11px] leading-[11px]">Sex</span>
            <span class="h-[11px] leading-[11px]"></span>
          </div>

          <!-- Matriz de 52 Semanas -->
          <div class="flex gap-[3px] flex-1">
            {#each gridData.weeks as week}
              <div class="grid grid-rows-7 gap-[3px]">
                {#each week as day}
                  <div
                    class="w-[11px] h-[11px] rounded-[2px] relative group cursor-pointer {getLevelClass(day.level)}"
                  >
                    <!-- Tooltip customizado -->
                    <div
                      class="pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:flex flex-col items-center z-30 min-w-[130px]"
                    >
                      <div class="bg-surface-3 border border-line t-txt text-[11px] rounded py-1 px-2.5 shadow-xl text-center whitespace-nowrap">
                        <div class="font-bold t-ok">
                          {day.count === 0 ? 'Nenhum commit' : `${day.count} commit${day.count > 1 ? 's' : ''}`}
                        </div>
                        <div class="text-[10px] opacity-75 font-mono">{day.displayDate}</div>
                      </div>
                      <div class="w-1.5 h-1.5 bg-surface-3 border-r border-b border-line rotate-45 -mt-1"></div>
                    </div>
                  </div>
                {/each}
              </div>
            {/each}
          </div>
        </div>

        <!-- Legenda -->
        <div class="flex items-center justify-between pt-3 text-[11px] t-faint border-t border-line-soft">
          <span class="flex items-center gap-1.5">
            <Calendar class="w-3.5 h-3.5 opacity-60" />
            <span>Últimos 12 meses</span>
          </span>

          <div class="flex items-center gap-2">
            <span>{$t('catalog.commits_less')}</span>
            <div class="flex items-center gap-[3px]">
              <div class="w-[11px] h-[11px] rounded-[2px] heat heat-0" title="0 commits"></div>
              <div class="w-[11px] h-[11px] rounded-[2px] heat heat-1" title="1-2 commits"></div>
              <div class="w-[11px] h-[11px] rounded-[2px] heat heat-2" title="3-5 commits"></div>
              <div class="w-[11px] h-[11px] rounded-[2px] heat heat-3" title="6-9 commits"></div>
              <div class="w-[11px] h-[11px] rounded-[2px] heat heat-4" title="10+ commits"></div>
            </div>
            <span>{$t('catalog.commits_more')}</span>
          </div>
        </div>
      </div>
    </div>
  {/if}
</section>
