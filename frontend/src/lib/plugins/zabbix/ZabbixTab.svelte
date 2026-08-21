<script lang="ts">
  import { onMount } from 'svelte';
  import { getAuthHeader } from '$lib/auth';
  import { t } from '$lib/i18n';
  import ZabbixStatusBadge from './ZabbixStatusBadge.svelte';
  import ZabbixMetricsWidget from './ZabbixMetricsWidget.svelte';
  import ZabbixProblemsTable from './ZabbixProblemsTable.svelte';
  import ZabbixSlaCard from './ZabbixSlaCard.svelte';
  import { RotateCw, Server, AlertCircle, RefreshCw } from 'lucide-svelte';

  export let component: any;

  let loading = true;
  let data: any = null;
  let error: string | null = null;

  async function loadObservability() {
    if (!component?.id) return;
    loading = true;
    error = null;
    try {
      const res = await fetch(`/api/plugins/zabbix/component/${component.id}`, {
        headers: { ...getAuthHeader() }
      });
      if (res.ok) {
        data = await res.json();
      } else {
        error = $t('plugins.zabbix.saveError');
      }
    } catch (e: any) {
      error = e.message || 'Connection error';
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    loadObservability();
  });
</script>

<div class="space-y-6">
  {#if loading}
    <div class="plate p-12 text-center t-dim flex flex-col items-center justify-center gap-3" style="--chamfer: 16px;">
      <RotateCw size={24} class="animate-spin t-visor" />
      <span class="text-sm font-medium font-mono">{$t('plugins.zabbix.consultingApi')}</span>
    </div>
  {:else if error}
    <div class="chip chip-alert !w-full !whitespace-normal p-4 flex items-center justify-between text-xs">
      <div class="flex items-center gap-2">
        <AlertCircle size={18} />
        <span>{error}</span>
      </div>
      <button
        on:click={loadObservability}
        class="btn btn-sm btn-ghost"
      >
        {$t('plugins.zabbix.retry')}
      </button>
    </div>
  {:else if data}
    <!-- Status Header -->
    <div class="plate p-5 flex flex-col md:flex-row items-start md:items-center justify-between gap-4" style="--chamfer: 16px;">
      <div class="flex items-center gap-3.5">
        <div class="p-3 rounded-xl bg-surface-2 t-txt border border-line">
          <Server size={22} />
        </div>
        <div>
          <div class="flex items-center gap-2">
            <h3 class="text-base font-bold t-txt">{data.host_name || component.name}</h3>
            {#if data.matched}
              <span class="chip font-mono text-[10px]">Host ID: #{data.host_id}</span>
            {/if}
          </div>
          <p class="text-xs t-dim mt-0.5">
            {#if data.matched}
              Host monitored via Zabbix agent ({data.zabbix_available ? 'Available' : 'Unavailable'})
            {:else}
              Search candidates: {data.candidates?.join(', ')}
            {/if}
          </p>
        </div>
      </div>

      <div class="flex items-center gap-3">
        <ZabbixStatusBadge status={data.status} size="lg" />

        <button
          on:click={loadObservability}
          title="Refresh"
          class="btn btn-sm btn-ghost p-2"
        >
          <RefreshCw size={15} />
        </button>
      </div>
    </div>

    {#if !data.matched}
      <div class="plate p-6 border border-crest/30 bg-crest-wash text-xs space-y-2.5" style="--chamfer: 14px;">
        <div class="font-semibold t-crest flex items-center gap-2 text-sm">
          <AlertCircle size={16} />
          {$t('plugins.zabbix.noHostLinked')}
        </div>
        <p class="t-dim leading-relaxed">
          {$t('plugins.zabbix.noHostLinkedHint')}
        </p>
        <pre class="p-3 rounded-lg bg-surface border border-line t-txt text-xs font-mono">spec:
  zabbix:
    host_name: "{component.name}"</pre>
      </div>
    {:else}
      <!-- SLA Card -->
      <ZabbixSlaCard slaPercentage={99.95} sloTarget={99.90} serviceName={component.name} />

      <!-- Golden Metrics Widget -->
      <div class="space-y-3">
        <h4 class="label">Server Performance Metrics</h4>
        <ZabbixMetricsWidget metrics={data.metrics} />
      </div>

      <!-- Active Triggers / Problems -->
      <div class="space-y-3">
        <div class="flex items-center justify-between">
          <h4 class="label">Active Zabbix Alerts &amp; Triggers ({data.problems?.length || 0})</h4>
        </div>
        <ZabbixProblemsTable problems={data.problems || []} />
      </div>
    {/if}
  {/if}
</div>
