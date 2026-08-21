<script lang="ts">
  import { Cpu, HardDrive, Activity, Server } from 'lucide-svelte';
  import { t } from '$lib/i18n';

  export let metrics: {
    cpu_utilization?: number | null;
    memory_utilization?: number | null;
    disk_utilization?: number | null;
    uptime?: string | number | null;
    items?: Array<{ name: string; key: string; value: any; units: string }>;
  } | null = null;

  function formatUptime(uptimeSeconds: any): string {
    if (!uptimeSeconds) return 'N/A';
    const totalSecs = parseInt(uptimeSeconds, 10);
    if (isNaN(totalSecs)) return String(uptimeSeconds);

    const days = Math.floor(totalSecs / (3600 * 24));
    const hours = Math.floor((totalSecs % (3600 * 24)) / 3600);
    const mins = Math.floor((totalSecs % 3600) / 60);

    if (days > 0) return `${days}d ${hours}h ${mins}m`;
    return `${hours}h ${mins}m`;
  }
</script>

<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
  <!-- CPU Metric -->
  <div class="plate p-5 flex flex-col justify-between" style="--chamfer: 14px;">
    <div class="flex items-center justify-between">
      <span class="label">{$t('plugins.zabbix.cpuUsage')}</span>
      <div class="p-2 rounded-lg bg-visor-wash t-visor border border-line">
        <Cpu size={18} />
      </div>
    </div>
    <div class="mt-4">
      {#if metrics?.cpu_utilization !== undefined && metrics?.cpu_utilization !== null}
        <div class="text-2xl font-bold font-mono t-txt">{metrics.cpu_utilization}%</div>
        <div class="w-full bg-surface-3 h-2 rounded-full mt-2.5 overflow-hidden border border-line">
          <div
            class="h-full rounded-full transition-all duration-500 {metrics.cpu_utilization > 85 ? 'bg-[var(--alert)]' : metrics.cpu_utilization > 60 ? 'bg-[var(--crest)]' : 'bg-[var(--visor)]'}"
            style="width: {Math.min(metrics.cpu_utilization, 100)}%"
          ></div>
        </div>
      {:else}
        <div class="text-xs t-faint font-mono">{$t('plugins.zabbix.noData')}</div>
      {/if}
    </div>
  </div>

  <!-- Memory Metric -->
  <div class="plate p-5 flex flex-col justify-between" style="--chamfer: 14px;">
    <div class="flex items-center justify-between">
      <span class="label">{$t('plugins.zabbix.memUsage')}</span>
      <div class="p-2 rounded-lg bg-iris-wash t-iris border border-line">
        <Activity size={18} />
      </div>
    </div>
    <div class="mt-4">
      {#if metrics?.memory_utilization !== undefined && metrics?.memory_utilization !== null}
        <div class="text-2xl font-bold font-mono t-txt">{metrics.memory_utilization}%</div>
        <div class="w-full bg-surface-3 h-2 rounded-full mt-2.5 overflow-hidden border border-line">
          <div
            class="h-full rounded-full transition-all duration-500 {metrics.memory_utilization > 85 ? 'bg-[var(--alert)]' : metrics.memory_utilization > 60 ? 'bg-[var(--crest)]' : 'bg-[var(--iris)]'}"
            style="width: {Math.min(metrics.memory_utilization, 100)}%"
          ></div>
        </div>
      {:else}
        <div class="text-xs t-faint font-mono">{$t('plugins.zabbix.noData')}</div>
      {/if}
    </div>
  </div>

  <!-- Uptime Metric -->
  <div class="plate p-5 flex flex-col justify-between" style="--chamfer: 14px;">
    <div class="flex items-center justify-between">
      <span class="label">{$t('plugins.zabbix.uptime')}</span>
      <div class="p-2 rounded-lg bg-ok-wash t-ok border border-line">
        <Server size={18} />
      </div>
    </div>
    <div class="mt-4">
      {#if metrics?.uptime}
        <div class="text-2xl font-bold font-mono t-txt">{formatUptime(metrics.uptime)}</div>
        <div class="text-xs t-ok mt-1.5 flex items-center gap-1.5 font-mono">
          <span class="w-2 h-2 rounded-full bg-[var(--ok)] animate-pulse"></span>
          {$t('plugins.zabbix.operatingNormal')}
        </div>
      {:else}
        <div class="text-xs t-faint font-mono">{$t('plugins.zabbix.noData')}</div>
      {/if}
    </div>
  </div>
</div>
