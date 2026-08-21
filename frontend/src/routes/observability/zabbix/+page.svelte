<script lang="ts">
  import { onMount } from 'svelte';
  import { getAuthHeader } from '$lib/auth';
  import ZabbixProblemsTable from '$lib/plugins/zabbix/ZabbixProblemsTable.svelte';
  import ZabbixStatusBadge from '$lib/plugins/zabbix/ZabbixStatusBadge.svelte';
  import { Activity, ShieldAlert, AlertTriangle, RefreshCw, Server, Filter } from 'lucide-svelte';

  let loading = true;
  let statusData: any = null;
  let problems: any[] = [];
  let minSeverity = 0;
  let filterText = '';

  async function loadData() {
    loading = true;
    try {
      const authHeaders = getAuthHeader();
      const [statusRes, probRes] = await Promise.all([
        fetch('/api/plugins/zabbix/status', { headers: { ...authHeaders } }),
        fetch(`/api/plugins/zabbix/problems?min_severity=${minSeverity}`, { headers: { ...authHeaders } })
      ]);

      if (statusRes.ok) statusData = await statusRes.json();
      if (probRes.ok) problems = await probRes.json();
    } catch (e) {
      console.error(e);
    } finally {
      loading = false;
    }
  }

  $: filteredProblems = problems.filter((p) =>
    filterText ? p.name.toLowerCase().includes(filterText.toLowerCase()) : true
  );

  $: disasterCount = problems.filter((p) => Number(p.severity) === 5).length;
  $: highCount = problems.filter((p) => Number(p.severity) === 4).length;
  $: averageCount = problems.filter((p) => Number(p.severity) === 3).length;
  $: warningCount = problems.filter((p) => Number(p.severity) === 2).length;

  onMount(() => {
    loadData();
  });
</script>

<svelte:head>
  <title>Zabbix Observability Hub | Daileon Developer Portal</title>
</svelte:head>

<main class="max-w-7xl mx-auto px-4 py-8 space-y-8">
  <!-- Header -->
  <div class="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border-b border-line pb-6">
    <div class="flex items-center gap-4">
      <div class="p-3.5 rounded-2xl bg-visor-wash t-visor border border-line">
        <Activity size={32} />
      </div>
      <div>
        <h1 class="text-2xl font-black t-txt tracking-tight">Zabbix Observability Hub</h1>
        <p class="text-xs t-dim mt-1">Visão centralizada de saúde da infraestrutura, servidores e incidentes em tempo real</p>
      </div>
    </div>

    <div class="flex items-center gap-3">
      {#if statusData?.status === 'connected'}
        <div class="chip chip-ok font-bold">
          <span class="w-2 h-2 rounded-full bg-[var(--ok)] animate-pulse"></span>
          Conectado v{statusData.version}
        </div>
      {:else}
        <div class="chip">
          Status: {statusData?.status || 'Carregando...'}
        </div>
      {/if}

      <button
        on:click={loadData}
        disabled={loading}
        class="btn btn-sm btn-ghost flex items-center gap-1.5"
      >
        <RefreshCw size={14} class={loading ? 'animate-spin' : ''} />
        <span>Atualizar</span>
      </button>
    </div>
  </div>

  <!-- KPI Severity Cards -->
  <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
    <div class="plate p-5 flex items-center justify-between border-alert/30 bg-alert-wash" style="--chamfer: 14px;">
      <div>
        <span class="label t-alert font-bold">Desastres (Disaster)</span>
        <div class="text-3xl font-black font-mono t-alert mt-1">{disasterCount}</div>
      </div>
      <div class="p-3 rounded-xl bg-alert-wash t-alert border border-alert/20">
        <ShieldAlert size={26} />
      </div>
    </div>

    <div class="plate p-5 flex items-center justify-between border-alert/20 bg-alert-wash" style="--chamfer: 14px;">
      <div>
        <span class="label t-alert font-bold">Alta Severidade (High)</span>
        <div class="text-3xl font-black font-mono t-alert mt-1">{highCount}</div>
      </div>
      <div class="p-3 rounded-xl bg-alert-wash t-alert border border-alert/20">
        <AlertTriangle size={26} />
      </div>
    </div>

    <div class="plate p-5 flex items-center justify-between border-crest/30 bg-crest-wash" style="--chamfer: 14px;">
      <div>
        <span class="label t-crest font-bold">Média Severidade (Average)</span>
        <div class="text-3xl font-black font-mono t-crest mt-1">{averageCount}</div>
      </div>
      <div class="p-3 rounded-xl bg-crest-wash t-crest border border-crest/20">
        <AlertTriangle size={26} />
      </div>
    </div>

    <div class="plate p-5 flex items-center justify-between border-crest/20 bg-crest-wash" style="--chamfer: 14px;">
      <div>
        <span class="label t-crest font-bold">Avisos (Warning)</span>
        <div class="text-3xl font-black font-mono t-crest mt-1">{warningCount}</div>
      </div>
      <div class="p-3 rounded-xl bg-crest-wash t-crest border border-crest/20">
        <AlertTriangle size={26} />
      </div>
    </div>
  </div>

  <!-- Problems Table Section -->
  <div class="space-y-4">
    <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
      <h3 class="text-base font-bold t-txt flex items-center gap-2">
        <Server size={18} class="t-visor" />
        Problemas Ativos Monitorados ({filteredProblems.length})
      </h3>

      <div class="flex items-center gap-3 w-full sm:w-auto">
        <div class="search-bar w-full sm:w-64">
          <Filter size={14} class="t-faint" />
          <input
            type="text"
            bind:value={filterText}
            placeholder="Filtrar por nome..."
          />
        </div>

        <select
          bind:value={minSeverity}
          on:change={loadData}
          class="field field-mono text-xs !w-auto"
        >
          <option value={0}>Todas as Severidades</option>
          <option value={2}>Warning ou superior</option>
          <option value={4}>High & Disaster</option>
        </select>
      </div>
    </div>

    {#if loading}
      <div class="plate p-12 text-center t-dim flex flex-col items-center justify-center gap-2 font-mono text-xs" style="--chamfer: 16px;">
        <RefreshCw size={24} class="animate-spin t-visor" />
        <span>Carregando incidentes do Zabbix...</span>
      </div>
    {:else}
      <ZabbixProblemsTable problems={filteredProblems} />
    {/if}
  </div>
</main>
