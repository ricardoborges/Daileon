<script lang="ts">
  import { AlertTriangle, ShieldAlert, Clock, ExternalLink } from 'lucide-svelte';
  import { t, locale } from '$lib/i18n';

  export let problems: Array<{
    eventid: string;
    name: string;
    severity: number | string;
    severity_name: string;
    severity_color: string;
    clock: number;
  }> = [];

  function formatTime(timestamp: number, loc: string): string {
    if (!timestamp) return 'Recent';
    const date = new Date(timestamp * 1000);
    return date.toLocaleString(loc, {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  function getSeverityChip(severityName: string) {
    switch (severityName.toLowerCase()) {
      case 'disaster':
      case 'high':
        return 'chip-alert';
      case 'average':
      case 'warning':
        return 'chip-crest';
      case 'information':
        return 'chip-visor';
      default:
        return '';
    }
  }
</script>

<div class="space-y-3">
  {#if problems.length === 0}
    <div class="plate p-6 text-center t-ok font-medium flex items-center justify-center gap-2 bg-ok-wash" style="--chamfer: 12px;">
      <span class="inline-block w-2.5 h-2.5 rounded-full bg-[var(--ok)] animate-pulse"></span>
      {$t('plugins.zabbix.noProblems')}
    </div>
  {:else}
    <div class="plate p-0 overflow-x-auto" style="--chamfer: 14px;">
      <table class="w-full text-left text-sm">
        <thead class="bg-surface-2 label border-b border-line">
          <tr>
            <th class="py-3 px-4 text-xs font-mono uppercase tracking-wider t-faint">{$t('plugins.zabbix.severity')}</th>
            <th class="py-3 px-4 text-xs font-mono uppercase tracking-wider t-faint">{$t('plugins.zabbix.problemEvent')}</th>
            <th class="py-3 px-4 text-xs font-mono uppercase tracking-wider t-faint">{$t('plugins.zabbix.startTime')}</th>
            <th class="py-3 px-4 text-xs font-mono uppercase tracking-wider t-faint text-right">{$t('plugins.zabbix.action')}</th>
          </tr>
        </thead>
        <tbody class="divide-y border-line">
          {#each problems as prob}
            <tr class="hover:bg-surface-2/60 transition-colors">
              <td class="py-3.5 px-4 whitespace-nowrap">
                <span class="chip {getSeverityChip(prob.severity_name)} font-bold text-[10px]">
                  {#if Number(prob.severity) >= 4}
                    <ShieldAlert size={13} />
                  {:else}
                    <AlertTriangle size={13} />
                  {/if}
                  {prob.severity_name}
                </span>
              </td>
              <td class="py-3.5 px-4 font-medium t-txt">
                {prob.name}
              </td>
              <td class="py-3.5 px-4 t-dim text-xs whitespace-nowrap">
                <div class="flex items-center gap-1.5 font-mono text-[11px]">
                  <Clock size={12} class="t-faint" />
                  <span>{formatTime(prob.clock, $locale)}</span>
                </div>
              </td>
              <td class="py-3.5 px-4 text-right whitespace-nowrap">
                <span class="inline-flex items-center gap-1 text-xs t-visor font-mono hover:underline font-semibold cursor-pointer">
                  Zabbix Event #{prob.eventid}
                </span>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</div>
