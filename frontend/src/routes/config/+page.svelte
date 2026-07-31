<script lang="ts">
  import { onDestroy, onMount, tick } from 'svelte';
  import {
    startSync,
    fetchSyncStatus,
    type SyncLogLine,
    type SyncMode,
    type SyncStatus
  } from '$lib/api';
  import { Settings, RefreshCw, Database, Eraser, AlertTriangle, Terminal } from 'lucide-svelte';

  interface Operation {
    mode: SyncMode;
    label: string;
    icon: typeof RefreshCw;
    summary: string;
    detail: string;
    /** Apaga dados: exige confirmação antes de disparar. */
    destructive: boolean;
  }

  const operations: Operation[] = [
    {
      mode: 'update',
      label: 'Sincronizar',
      icon: RefreshCw,
      summary: 'Atualiza o catálogo a partir do GitLab',
      detail:
        'Relê o project-info.yml e a documentação de cada projeto, atualizando os componentes existentes e importando os novos. Nada é removido.',
      destructive: false
    },
    {
      mode: 'rebuild',
      label: 'Reconstruir base',
      icon: Database,
      summary: 'Apaga o catálogo e importa tudo do zero',
      detail:
        'Zera componentes, tags, links, dependências e documentação antes de reimportar. Use quando o catálogo estiver inconsistente. Os IDs internos mudam, então links antigos para /catalog/:id deixam de funcionar.',
      destructive: true
    },
    {
      mode: 'prune',
      label: 'Remover órfãos',
      icon: Eraser,
      summary: 'Exclui o que não existe mais no GitLab',
      detail:
        'Compara o catálogo com a lista de projetos do GitLab e remove os componentes sem projeto correspondente. Não altera os demais.',
      destructive: false
    }
  ];

  const POLL_MS = 800;

  let status: SyncStatus | null = null;
  let logs: SyncLogLine[] = [];
  let cursor = 0;
  let starting = false;
  let uiError = '';
  let confirming: SyncMode | null = null;
  let timer: ReturnType<typeof setTimeout> | null = null;
  let consoleEl: HTMLDivElement | null = null;
  let stuckToBottom = true;

  $: running = status?.state === 'running' || starting;
  $: busy = running;

  // A barra só vira percentual depois que o backend sabe quantos passos são.
  $: total = status?.total ?? null;
  $: processed = status?.processed ?? 0;
  $: indeterminate = running && (total === null || total === 0);
  $: finished = status?.state === 'success' || status?.state === 'partial';
  // Operação sem passos (prune sem órfãos) termina com total 0: a barra tem que
  // ficar cheia mesmo assim, senão parece que não rodou.
  $: percent =
    total && total > 0
      ? Math.min(100, Math.round((processed / total) * 100))
      : finished
        ? 100
        : 0;

  $: barTone =
    status?.state === 'error'
      ? 'progress-alert'
      : status?.state === 'partial'
        ? 'progress-warn'
        : status?.state === 'success'
          ? 'progress-ok'
          : '';

  $: stateLabel =
    starting && !status
      ? 'Iniciando'
      : {
          idle: 'Ocioso',
          running: 'Em execução',
          success: 'Concluído',
          partial: 'Concluído com falhas',
          error: 'Erro'
        }[status?.state ?? 'idle'];

  $: stateLed =
    status?.state === 'error'
      ? 'led-alert'
      : status?.state === 'partial'
        ? 'led-crest'
        : status?.state === 'success'
          ? 'led-ok'
          : running
            ? 'led-visor'
            : '';

  onMount(() => {
    // Reanexa a uma operação já em andamento (recarregar a página não a cancela).
    poll();
  });

  onDestroy(() => {
    if (timer) clearTimeout(timer);
  });

  async function poll() {
    try {
      const next = await fetchSyncStatus(cursor);

      // Um job novo reinicia a numeração: descarta o log do anterior.
      if (status?.job_id && next.job_id && next.job_id !== status.job_id) {
        logs = [];
      }
      if (next.logs.length) {
        logs = [...logs, ...next.logs];
        await scrollConsole();
      }
      cursor = next.cursor;
      status = next;
      uiError = '';
    } catch (e: any) {
      uiError = e.message || 'Falha ao consultar o progresso';
    }

    if (timer) clearTimeout(timer);
    // Enquanto roda, acompanha de perto; parado, só um heartbeat leve para
    // detectar operação disparada de outra aba.
    timer = setTimeout(poll, status?.state === 'running' ? POLL_MS : 5000);
  }

  async function scrollConsole() {
    if (!stuckToBottom) return;
    await tick();
    if (consoleEl) consoleEl.scrollTop = consoleEl.scrollHeight;
  }

  function onConsoleScroll() {
    if (!consoleEl) return;
    // Se o usuário rolou para ler algo, para de arrastar a view para o fim.
    const distance = consoleEl.scrollHeight - consoleEl.scrollTop - consoleEl.clientHeight;
    stuckToBottom = distance < 24;
  }

  function request(op: Operation) {
    uiError = '';
    if (op.destructive && confirming !== op.mode) {
      confirming = op.mode;
      return;
    }
    run(op.mode);
  }

  async function run(mode: SyncMode) {
    confirming = null;
    starting = true;
    uiError = '';
    try {
      const started = await startSync(mode);
      logs = [];
      cursor = 0;
      status = started;
      await poll();
    } catch (e: any) {
      uiError = e.message || 'Falha ao iniciar a operação';
    } finally {
      starting = false;
    }
  }

  function hhmmss(ts: string) {
    const d = new Date(ts);
    return Number.isNaN(d.getTime()) ? '--:--:--' : d.toLocaleTimeString('pt-BR', { hour12: false });
  }
</script>

<svelte:head><title>Configuração &middot; Daileon</title></svelte:head>

<main class="max-w-7xl mx-auto px-6 py-10 space-y-8">
  <header class="space-y-3">
    <span class="eyebrow">Painel de Controle</span>
    <div class="rule">
      <h1 class="text-3xl font-bold tracking-[-0.03em] t-txt flex items-center gap-3 whitespace-nowrap">
        <Settings class="w-7 h-7 t-visor" /> Configuração
      </h1>
    </div>
    <p class="t-dim text-sm">
      Operações de manutenção do catálogo contra a API do GitLab.
    </p>
  </header>

  <!-- Operações -->
  <section class="grid grid-cols-1 lg:grid-cols-3 gap-5">
    {#each operations as op}
      <div class="plate plate-deep p-5 flex flex-col gap-4" style="--chamfer: 14px;">
        <div class="space-y-2">
          <h2 class="text-sm font-bold t-txt flex items-center gap-2">
            <svelte:component
              this={op.icon}
              class="w-4 h-4 {op.destructive ? 't-crest' : 't-visor'}"
            />
            {op.label}
          </h2>
          <p class="label" style="letter-spacing: 0.1em;">{op.summary}</p>
        </div>

        <p class="t-dim text-xs leading-relaxed flex-1">{op.detail}</p>

        {#if confirming === op.mode}
          <div class="space-y-3">
            <p class="chip chip-alert !whitespace-normal !normal-case !text-[0.6875rem] !tracking-normal w-full">
              <AlertTriangle class="w-3.5 h-3.5 flex-none" />
              Esta ação apaga dados e não pode ser desfeita.
            </p>
            <div class="flex gap-2">
              <button class="btn btn-sm flex-1" on:click={() => (confirming = null)}>
                Cancelar
              </button>
              <button class="btn btn-sm btn-crest flex-1" disabled={busy} on:click={() => run(op.mode)}>
                Confirmar
              </button>
            </div>
          </div>
        {:else}
          <button
            class="btn btn-sm w-full {op.destructive ? 'btn-crest' : 'btn-primary'}"
            disabled={busy}
            on:click={() => request(op)}
          >
            <svelte:component
              this={op.icon}
              class="w-3.5 h-3.5 {running && status?.mode === op.mode ? 'animate-spin' : ''}"
            />
            {op.label}
          </button>
        {/if}
      </div>
    {/each}
  </section>

  <!-- Instrumentação: progresso + saída -->
  <section class="plate p-5 space-y-4" style="--chamfer: 16px;">
    <div class="flex flex-wrap items-center justify-between gap-4">
      <span class="label flex items-center gap-2">
        {#if stateLed}<span class="led {stateLed}"></span>{/if}
        {stateLabel}
        {#if status?.mode && status.state !== 'idle'}
          <span class="t-faint">&middot; {status.mode}</span>
        {/if}
      </span>

      <div class="flex items-center gap-4">
        {#if (status?.synced_count ?? 0) > 0}
          <span class="label">Sincronizados <span class="t-visor">{status?.synced_count}</span></span>
        {/if}
        {#if (status?.removed_count ?? 0) > 0}
          <span class="label">Removidos <span class="t-crest">{status?.removed_count}</span></span>
        {/if}
        {#if (status?.failed_count ?? 0) > 0}
          <span class="label">Falhas <span class="t-alert">{status?.failed_count}</span></span>
        {/if}
        <span class="readout text-sm">
          {#if indeterminate}
            --
          {:else if total && total > 0}
            {processed}/{total}
          {:else}
            {percent}%
          {/if}
        </span>
      </div>
    </div>

    <div
      class="progress {barTone} {indeterminate ? 'progress-indeterminate' : ''}"
      role="progressbar"
      aria-valuemin="0"
      aria-valuemax="100"
      aria-valuenow={indeterminate ? undefined : percent}
      aria-label="Progresso da operação"
    >
      {#if !indeterminate}
        <div class="progress-fill" style="width: {status?.state === 'idle' ? 0 : percent}%"></div>
      {/if}
    </div>

    {#if uiError}
      <p class="chip chip-alert !normal-case !tracking-normal !text-[0.6875rem]">
        <AlertTriangle class="w-3.5 h-3.5" /> {uiError}
      </p>
    {/if}
    {#if status?.error}
      <p class="chip chip-alert !whitespace-normal !normal-case !tracking-normal !text-[0.6875rem]">
        <AlertTriangle class="w-3.5 h-3.5 flex-none" /> {status.error}
      </p>
    {/if}

    <div class="space-y-2">
      <span class="label flex items-center gap-2">
        <Terminal class="w-3 h-3" /> Saída
      </span>
      <div
        class="console h-72"
        bind:this={consoleEl}
        on:scroll={onConsoleScroll}
        role="log"
        aria-live="polite"
      >
        {#if logs.length === 0}
          <p class="px-3 py-3 t-faint">Nenhuma operação executada nesta sessão.</p>
        {:else}
          {#each logs as line (line.seq)}
            <div class="console-line">
              <span class="console-ts">{hhmmss(line.ts)}</span>
              <span
                class:console-ok={line.level === 'ok'}
                class:console-warn={line.level === 'warn'}
                class:console-error={line.level === 'error'}
              >{line.message}</span>
            </div>
          {/each}
        {/if}
      </div>
    </div>
  </section>
</main>
