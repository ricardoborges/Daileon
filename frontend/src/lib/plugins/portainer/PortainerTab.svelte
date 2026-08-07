<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import {
    fetchComponentPortainer,
    fetchPortainerContainerStats,
    fetchPortainerContainerLogs,
    postPortainerContainerAction,
    type ComponentItem,
    type PortainerComponentResponse,
    type PortainerContainer,
    type PortainerContainerStats
  } from '$lib/api';
  import {
    Activity,
    Server,
    RotateCw,
    Play,
    Square,
    Terminal,
    Cpu,
    HardDrive,
    ExternalLink,
    AlertTriangle,
    CheckCircle2,
    X,
    Copy,
    Check
  } from 'lucide-svelte';

  export let component: ComponentItem;

  let loading = true;
  let data: PortainerComponentResponse | null = null;
  let containerStats: Record<string, PortainerContainerStats> = {};
  let actionLoading: Record<string, boolean> = {};
  let actionError: string | null = null;
  let actionSuccess: string | null = null;

  // Modals e Logs
  let selectedContainerForLogs: PortainerContainer | null = null;
  let logsText = '';
  let loadingLogs = false;
  let copiedLogs = false;
  let logTail = 150;

  let statsTimer: ReturnType<typeof setInterval> | null = null;

  async function loadData() {
    loading = true;
    actionError = null;
    try {
      data = await fetchComponentPortainer(component.id);
      if (data && data.containers && data.containers.length > 0) {
        fetchAllStats();
      }
    } catch (e: any) {
      console.error('Erro ao carregar dados do Portainer:', e);
      actionError = e.message || 'Erro ao comunicar com a API do Portainer';
    } finally {
      loading = false;
    }
  }

  async function fetchAllStats() {
    if (!data?.containers) return;
    for (const c of data.containers) {
      if (c.state === 'running') {
        try {
          const stats = await fetchPortainerContainerStats(c.endpoint_id, c.id);
          containerStats[c.id] = stats;
          containerStats = { ...containerStats };
        } catch (e) {
          console.warn(`Não foi possível obter estatísticas do container ${c.name}:`, e);
        }
      }
    }
  }

  async function handleAction(container: PortainerContainer, action: 'start' | 'stop' | 'restart') {
    actionLoading[container.id] = true;
    actionError = null;
    actionSuccess = null;
    try {
      const res = await postPortainerContainerAction(container.endpoint_id, container.id, action);
      actionSuccess = res.message;
      await loadData();
    } catch (e: any) {
      actionError = e.message || `Erro ao executar ação '${action}' no container ${container.name}`;
    } finally {
      actionLoading[container.id] = false;
      actionLoading = { ...actionLoading };
    }
  }

  async function openLogsModal(container: PortainerContainer) {
    selectedContainerForLogs = container;
    loadingLogs = true;
    logsText = '';
    copiedLogs = false;
    try {
      const res = await fetchPortainerContainerLogs(container.endpoint_id, container.id, logTail);
      logsText = res.logs || 'Nenhum log retornado para este container.';
    } catch (e: any) {
      logsText = `Erro ao carregar logs: ${e.message}`;
    } finally {
      loadingLogs = false;
    }
  }

  function closeLogsModal() {
    selectedContainerForLogs = null;
    logsText = '';
  }

  async function copyLogs() {
    if (!logsText) return;
    try {
      await navigator.clipboard.writeText(logsText);
      copiedLogs = true;
      setTimeout(() => (copiedLogs = false), 2000);
    } catch (e) {
      console.error('Erro ao copiar logs:', e);
    }
  }

  function containerStateLed(state: string) {
    switch (state.toLowerCase()) {
      case 'running': return 'led-ok';
      case 'restarting': return 'led-crest';
      case 'exited':
      case 'stopped': return 'led-alert';
      default: return '';
    }
  }

  function containerStateChip(state: string) {
    switch (state.toLowerCase()) {
      case 'running': return 'chip-crest';
      case 'restarting': return 'chip-visor';
      case 'exited':
      case 'stopped': return 'chip-alert';
      default: return 'chip';
    }
  }

  onMount(() => {
    loadData();
    // Atualiza métricas de CPU/RAM a cada 10s
    statsTimer = setInterval(() => {
      if (data?.containers && data.containers.length > 0) {
        fetchAllStats();
      }
    }, 10000);
  });

  onDestroy(() => {
    if (statsTimer) clearInterval(statsTimer);
  });
</script>

<div class="space-y-6">
  <!-- Topbar com status geral do plugin -->
  <div class="plate p-5 flex flex-wrap items-center justify-between gap-4" style="--chamfer: 16px;">
    <div class="flex items-center gap-3">
      <Activity class="w-5 h-5 t-visor" />
      <div>
        <h3 class="text-sm font-semibold t-txt">Observabilidade de Containers (Portainer)</h3>
        <p class="text-xs t-dim">Métricas de CPU, memória, estado de execução e logs em tempo real dos containers deste componente.</p>
      </div>
    </div>

    <div class="flex items-center gap-3">
      <button
        type="button"
        on:click={loadData}
        disabled={loading}
        class="btn btn-sm btn-ghost flex items-center gap-1.5 text-xs"
        title="Atualizar containers"
      >
        <RotateCw class="w-3.5 h-3.5 {loading ? 'animate-spin' : ''}" />
        <span>Atualizar</span>
      </button>

      {#if data?.portainer_url}
        <a
          href={data.portainer_url}
          target="_blank"
          rel="noopener noreferrer"
          class="btn btn-sm btn-crest flex items-center gap-1.5 text-xs"
        >
          <ExternalLink class="w-3.5 h-3.5" /> Abrir Portainer
        </a>
      {/if}
    </div>
  </div>

  {#if actionSuccess}
    <div class="chip chip-ok !w-full !whitespace-normal text-xs p-3 flex items-center gap-2">
      <CheckCircle2 class="w-4 h-4 flex-none" />
      <span>{actionSuccess}</span>
    </div>
  {/if}

  {#if actionError}
    <div class="chip chip-alert !w-full !whitespace-normal text-xs p-3 flex items-center gap-2">
      <AlertTriangle class="w-4 h-4 flex-none" />
      <span>{actionError}</span>
    </div>
  {/if}

  {#if loading && !data}
    <div class="skeleton h-48"></div>
  {:else if !data?.configured}
    <div class="plate p-10 text-center space-y-4" style="--chamfer: 16px;">
      <Server class="w-10 h-10 mx-auto t-faint" />
      <h4 class="font-bold t-txt text-base">Integração Portainer não configurada</h4>
      <p class="t-dim text-xs max-w-md mx-auto leading-relaxed">
        {data?.message || 'Acesse a área de Configurações > Plugins para definir a URL e API Key do Portainer da sua infraestrutura.'}
      </p>
      <a href="/config" class="btn btn-visor text-xs inline-flex items-center gap-2">
        <Server class="w-3.5 h-3.5" /> Configurar Portainer
      </a>
    </div>
  {:else if !data.containers || data.containers.length === 0}
    <div class="plate p-10 text-center space-y-3" style="--chamfer: 16px;">
      <Activity class="w-8 h-8 mx-auto t-faint" />
      <h4 class="font-medium t-txt text-base">Nenhum container Docker associado</h4>
      <p class="t-dim text-xs max-w-md mx-auto leading-relaxed">
        Não foram encontrados containers no Portainer com o nome <code class="font-mono bg-surface-3 px-1.5 py-0.5 rounded text-visor">{component.name}</code> ou rotulados no Docker Compose.
      </p>
      <p class="t-faint text-[11px]">
        Dica: Você também pode declarar a seção <code class="font-mono bg-surface-3 px-1.5 py-0.5 rounded">portainer</code> no arquivo <code class="font-mono bg-surface-3 px-1.5 py-0.5 rounded">project-info.yml</code>.
      </p>
    </div>
  {:else}
    <!-- Grid de Containers -->
    <div class="grid grid-cols-1 gap-5">
      {#each data.containers as container (container.id)}
        {@const stats = containerStats[container.id]}
        {@const isBusy = actionLoading[container.id]}

        <div class="plate p-6 space-y-5" style="--chamfer: 16px;">
          <!-- Cabeçalho do Container -->
          <div class="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-line">
            <div class="space-y-1">
              <div class="flex flex-wrap items-center gap-2">
                <span class="chip {containerStateChip(container.state)} font-bold text-[10px] uppercase">
                  <span class="led {containerStateLed(container.state)}"></span>
                  {container.state}
                </span>
                {#if container.stack_name}
                  <span class="chip chip-sm font-mono">Stack: {container.stack_name}</span>
                {/if}
                <span class="chip chip-sm text-faint font-mono">Endpoint: {container.endpoint_name}</span>
              </div>
              <h4 class="text-base font-bold t-txt font-mono flex items-center gap-2">
                🐳 {container.name}
                <span class="text-xs font-normal t-faint">({container.short_id})</span>
              </h4>
            </div>

            <!-- Botões de Ação do Container -->
            <div class="flex items-center gap-2">
              <button
                type="button"
                on:click={() => openLogsModal(container)}
                class="btn btn-sm btn-ghost text-xs flex items-center gap-1.5"
                title="Visualizar logs do container"
              >
                <Terminal class="w-3.5 h-3.5 t-visor" /> Logs
              </button>

              {#if container.state === 'running'}
                <button
                  type="button"
                  on:click={() => handleAction(container, 'restart')}
                  disabled={isBusy}
                  class="btn btn-sm btn-ghost text-xs flex items-center gap-1.5"
                  title="Reiniciar container"
                >
                  <RotateCw class="w-3.5 h-3.5 t-crest {isBusy ? 'animate-spin' : ''}" /> Reiniciar
                </button>
                <button
                  type="button"
                  on:click={() => handleAction(container, 'stop')}
                  disabled={isBusy}
                  class="btn btn-sm btn-crest text-xs flex items-center gap-1.5"
                  title="Parar container"
                >
                  <Square class="w-3.5 h-3.5" /> Parar
                </button>
              {:else}
                <button
                  type="button"
                  on:click={() => handleAction(container, 'start')}
                  disabled={isBusy}
                  class="btn btn-sm btn-visor text-xs flex items-center gap-1.5"
                  title="Iniciar container"
                >
                  <Play class="w-3.5 h-3.5" /> Iniciar
                </button>
              {/if}
            </div>
          </div>

          <!-- Métricas de CPU / Memória / Rede em Tempo Real -->
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <!-- CPU -->
            <div class="bg-surface-2 p-4 rounded-lg border border-line space-y-2">
              <div class="flex items-center justify-between text-xs">
                <span class="t-faint font-semibold flex items-center gap-1.5">
                  <Cpu class="w-3.5 h-3.5 t-visor" /> Uso de CPU
                </span>
                <span class="font-mono font-bold t-txt">
                  {stats ? `${stats.cpu_percent}%` : container.state === 'running' ? 'Carregando...' : '—'}
                </span>
              </div>
              <div class="w-full bg-surface-3 h-2 rounded-full overflow-hidden">
                <div
                  class="bg-visor h-full transition-all duration-500"
                  style="width: {Math.min(100, stats?.cpu_percent || 0)}%"
                ></div>
              </div>
              <p class="text-[10px] t-faint text-right">
                {stats ? `${stats.online_cpus} núcleo(s) CPU` : ''}
              </p>
            </div>

            <!-- Memória RAM -->
            <div class="bg-surface-2 p-4 rounded-lg border border-line space-y-2">
              <div class="flex items-center justify-between text-xs">
                <span class="t-faint font-semibold flex items-center gap-1.5">
                  <HardDrive class="w-3.5 h-3.5 t-crest" /> Memória RAM
                </span>
                <span class="font-mono font-bold t-txt">
                  {stats ? `${stats.memory_usage_mb} MB (${stats.memory_percent}%)` : container.state === 'running' ? 'Carregando...' : '—'}
                </span>
              </div>
              <div class="w-full bg-surface-3 h-2 rounded-full overflow-hidden">
                <div
                  class="bg-emerald-400 h-full transition-all duration-500"
                  style="width: {Math.min(100, stats?.memory_percent || 0)}%"
                ></div>
              </div>
              <p class="text-[10px] t-faint text-right">
                {stats ? `Limite: ${stats.memory_limit_mb} MB` : ''}
              </p>
            </div>

            <!-- Info & Portas -->
            <div class="bg-surface-2 p-4 rounded-lg border border-line space-y-1.5 text-xs">
              <div class="flex items-center justify-between">
                <span class="t-faint">Imagem:</span>
                <span class="font-mono text-[11px] t-txt truncate max-w-[180px]" title={container.image}>
                  {container.image}
                </span>
              </div>
              <div class="flex items-center justify-between">
                <span class="t-faint">Status:</span>
                <span class="t-dim text-[11px] truncate max-w-[180px]" title={container.status}>
                  {container.status}
                </span>
              </div>
              {#if container.ports && container.ports.length > 0}
                <div class="flex items-center justify-between pt-1 border-t border-line">
                  <span class="t-faint">Portas:</span>
                  <span class="font-mono text-visor font-bold text-[11px]">
                    {container.ports.join(', ')}
                  </span>
                </div>
              {/if}
            </div>
          </div>
        </div>
      {/each}
    </div>
  {/if}

  <!-- Modal de Logs do Container -->
  {#if selectedContainerForLogs}
    <div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div class="plate plate-deep w-full max-w-4xl max-h-[85vh] flex flex-col overflow-hidden" style="--chamfer: 16px;">
        <!-- Header do Modal -->
        <div class="p-4 border-b border-line flex items-center justify-between bg-surface-2">
          <div class="flex items-center gap-2">
            <Terminal class="w-5 h-5 t-visor" />
            <div>
              <h4 class="font-bold t-txt text-sm font-mono">
                Logs: {selectedContainerForLogs.name}
              </h4>
              <p class="text-[11px] t-faint">Últimas {logTail} linhas de log do container</p>
            </div>
          </div>

          <div class="flex items-center gap-2">
            <button
              type="button"
              on:click={() => selectedContainerForLogs && openLogsModal(selectedContainerForLogs)}
              disabled={loadingLogs}
              class="btn btn-sm btn-ghost text-xs flex items-center gap-1"
              title="Recarregar logs"
            >
              <RotateCw class="w-3.5 h-3.5 {loadingLogs ? 'animate-spin' : ''}" />
            </button>
            <button
              type="button"
              on:click={copyLogs}
              disabled={loadingLogs || !logsText}
              class="btn btn-sm btn-ghost text-xs flex items-center gap-1"
            >
              {#if copiedLogs}
                <Check class="w-3.5 h-3.5 text-emerald-400" /> Copiado
              {:else}
                <Copy class="w-3.5 h-3.5" /> Copiar
              {/if}
            </button>
            <button
              type="button"
              on:click={closeLogsModal}
              class="btn btn-sm btn-ghost text-xs p-1"
            >
              <X class="w-4 h-4" />
            </button>
          </div>
        </div>

        <!-- Terminal Body -->
        <div class="p-4 flex-1 overflow-y-auto bg-neutral-950 font-mono text-xs text-emerald-400 leading-relaxed whitespace-pre-wrap">
          {#if loadingLogs}
            <div class="py-10 text-center t-faint flex items-center justify-center gap-2">
              <RotateCw class="w-4 h-4 animate-spin" /> Carregando logs do container...
            </div>
          {:else}
            {logsText}
          {/if}
        </div>
      </div>
    </div>
  {/if}
</div>
