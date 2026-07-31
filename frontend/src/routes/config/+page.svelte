<script lang="ts">
  import { onDestroy, onMount, tick } from "svelte";
  import {
    startSync,
    fetchSyncStatus,
    fetchLDAPConfig,
    saveLDAPConfig,
    testLDAPConfig,
    type SyncLogLine,
    type SyncMode,
    type SyncStatus,
    type LDAPConfig,
  } from "$lib/api";
  import {
    Settings,
    RefreshCw,
    Database,
    Eraser,
    AlertTriangle,
    Terminal,
    Server,
    ShieldCheck,
    CheckCircle2,
  } from "lucide-svelte";

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
      mode: "update",
      label: "Sincronizar",
      icon: RefreshCw,
      summary: "Atualiza o catálogo a partir do GitLab",
      detail:
        "Relê o project-info.yml e a documentação de cada projeto, atualizando os componentes existentes e importando os novos. Nada é removido.",
      destructive: false,
    },
    {
      mode: "rebuild",
      label: "Reconstruir base",
      icon: Database,
      summary: "Apaga o catálogo e importa tudo do zero",
      detail:
        "Zera componentes, tags, links, dependências e documentação antes de reimportar. Use quando o catálogo estiver inconsistente. Os IDs internos mudam, então links antigos para /catalog/:id deixam de funcionar.",
      destructive: true,
    },
    {
      mode: "prune",
      label: "Remover órfãos",
      icon: Eraser,
      summary: "Exclui o que não existe mais no GitLab",
      detail:
        "Compara o catálogo com a lista de projetos do GitLab e remove os componentes sem projeto correspondente. Não altera os demais.",
      destructive: false,
    },
  ];

  const POLL_MS = 800;

  let activeTab: "sync" | "ldap" = "sync";

  let status: SyncStatus | null = null;
  let logs: SyncLogLine[] = [];
  let cursor = 0;
  let starting = false;
  let uiError = "";
  let confirming: SyncMode | null = null;
  let timer: ReturnType<typeof setTimeout> | null = null;
  let consoleEl: HTMLDivElement | null = null;
  let stuckToBottom = true;

  $: running = status?.state === "running" || starting;
  $: busy = running;

  // A barra só vira percentual depois que o backend sabe quantos passos são.
  $: total = status?.total ?? null;
  $: processed = status?.processed ?? 0;
  $: indeterminate = running && (total === null || total === 0);
  $: finished = status?.state === "success" || status?.state === "partial";
  // Operação sem passos (prune sem órfãos) termina com total 0: a barra tem que
  // ficar cheia mesmo assim, senão parece que não rodou.
  $: percent =
    total && total > 0
      ? Math.min(100, Math.round((processed / total) * 100))
      : finished
        ? 100
        : 0;

  $: barTone =
    status?.state === "error"
      ? "progress-alert"
      : status?.state === "partial"
        ? "progress-warn"
        : status?.state === "success"
          ? "progress-ok"
          : "";

  $: stateLabel =
    starting && !status
      ? "Iniciando"
      : {
          idle: "Ocioso",
          running: "Em execução",
          success: "Concluído",
          partial: "Concluído com falhas",
          error: "Erro",
        }[status?.state ?? "idle"];

  $: stateLed =
    status?.state === "error"
      ? "led-alert"
      : status?.state === "partial"
        ? "led-crest"
        : status?.state === "success"
          ? "led-ok"
          : running
            ? "led-visor"
            : "";

  // LDAP Config State
  let ldapConfig: LDAPConfig = {
    enabled: false,
    server_host: "",
    server_port: 389,
    use_ssl: false,
    bind_dn: "",
    bind_password: "",
    base_dn: "",
    user_attribute: "uid",
  };
  let ldapLoading = false;
  let ldapSaving = false;
  let ldapTesting = false;
  let ldapMessage = "";
  let ldapMessageType: "success" | "error" = "success";

  onMount(() => {
    // Reanexa a uma operação já em andamento (recarregar a página não a cancela).
    poll();
    loadLDAP();
  });

  async function loadLDAP() {
    ldapLoading = true;
    try {
      ldapConfig = await fetchLDAPConfig();
    } catch (e: any) {
      // Ignora erro inicial
    } finally {
      ldapLoading = false;
    }
  }

  async function handleSaveLDAP() {
    ldapSaving = true;
    ldapMessage = "";
    try {
      const res = await saveLDAPConfig(ldapConfig);
      ldapMessage = res.message || "Configurações salvas com sucesso!";
      ldapMessageType = "success";
    } catch (e: any) {
      ldapMessage = e.message || "Falha ao salvar configurações do LDAP.";
      ldapMessageType = "error";
    } finally {
      ldapSaving = false;
    }
  }

  async function handleTestLDAP() {
    ldapTesting = true;
    ldapMessage = "";
    try {
      const res = await testLDAPConfig(ldapConfig);
      ldapMessage = res.message;
      ldapMessageType = res.success ? "success" : "error";
    } catch (e: any) {
      ldapMessage = e.message || "Falha ao testar conexão LDAP.";
      ldapMessageType = "error";
    } finally {
      ldapTesting = false;
    }
  }

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
      uiError = "";
    } catch (e: any) {
      uiError = e.message || "Falha ao consultar o progresso";
    }

    if (timer) clearTimeout(timer);
    // Enquanto roda, acompanha de perto; parado, só um heartbeat leve para
    // detectar operação disparada de outra aba.
    timer = setTimeout(poll, status?.state === "running" ? POLL_MS : 5000);
  }

  async function scrollConsole() {
    if (!stuckToBottom) return;
    await tick();
    if (consoleEl) consoleEl.scrollTop = consoleEl.scrollHeight;
  }

  function onConsoleScroll() {
    if (!consoleEl) return;
    // Se o usuário rolou para ler algo, para de arrastar a view para o fim.
    const distance =
      consoleEl.scrollHeight - consoleEl.scrollTop - consoleEl.clientHeight;
    stuckToBottom = distance < 24;
  }

  function request(op: Operation) {
    uiError = "";
    if (op.destructive && confirming !== op.mode) {
      confirming = op.mode;
      return;
    }
    run(op.mode);
  }

  async function run(mode: SyncMode) {
    confirming = null;
    starting = true;
    uiError = "";
    try {
      const started = await startSync(mode);
      logs = [];
      cursor = 0;
      status = started;
      await poll();
    } catch (e: any) {
      uiError = e.message || "Falha ao iniciar a operação";
    } finally {
      starting = false;
    }
  }

  function hhmmss(ts: string) {
    const d = new Date(ts);
    return Number.isNaN(d.getTime())
      ? "--:--:--"
      : d.toLocaleTimeString("pt-BR", { hour12: false });
  }
</script>

<svelte:head><title>Configuração &middot; Daileon</title></svelte:head>

<main class="max-w-7xl mx-auto px-6 py-10 space-y-8">
  <header class="space-y-3">
    <span class="eyebrow">Painel de Controle</span>
    <div class="rule">
      <h1
        class="text-3xl font-bold tracking-[-0.03em] t-txt flex items-center gap-3 whitespace-nowrap"
      >
        <Settings class="w-7 h-7 t-visor" /> Configuração
      </h1>
    </div>
    <p class="t-dim text-sm">
      Gerenciamento de sincronização do catálogo e autenticação LDAP.
    </p>
  </header>

  <!-- Navegação de Abas -->
  <div class="border-b border-[var(--line)] pb-4">
    <div class="seg" role="tablist">
      <button
        type="button"
        role="tab"
        aria-selected={activeTab === "sync"}
        class="seg-item cursor-pointer {activeTab === 'sync' ? 'is-active' : ''}"
        on:click={() => (activeTab = "sync")}
      >
        <RefreshCw class="w-4 h-4" />
        <span>Sincronização</span>
      </button>
      <button
        type="button"
        role="tab"
        aria-selected={activeTab === "ldap"}
        class="seg-item cursor-pointer {activeTab === 'ldap' ? 'is-active' : ''}"
        on:click={() => (activeTab = "ldap")}
      >
        <Server class="w-4 h-4" />
        <span>LDAP</span>
      </button>
    </div>
  </div>

  {#if activeTab === "sync"}
    <!-- ABA 1: Sincronização -->
    <div class="space-y-8">
      <!-- Operações -->
      <section class="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {#each operations as op}
          <div
            class="plate plate-deep p-5 flex flex-col gap-4"
            style="--chamfer: 14px;"
          >
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
                <p
                  class="chip chip-alert !whitespace-normal !normal-case !text-[0.6875rem] !tracking-normal w-full"
                >
                  <AlertTriangle class="w-3.5 h-3.5 flex-none" />
                  Esta ação apaga dados e não pode ser desfeita.
                </p>
                <div class="flex gap-2">
                  <button
                    class="btn btn-sm flex-1"
                    on:click={() => (confirming = null)}
                  >
                    Cancelar
                  </button>
                  <button
                    class="btn btn-sm btn-crest flex-1"
                    disabled={busy}
                    on:click={() => run(op.mode)}
                  >
                    Confirmar
                  </button>
                </div>
              </div>
            {:else}
              <button
                class="btn btn-sm w-full {op.destructive
                  ? 'btn-crest'
                  : 'btn-primary'}"
                disabled={busy}
                on:click={() => request(op)}
              >
                <svelte:component
                  this={op.icon}
                  class="w-3.5 h-3.5 {running && status?.mode === op.mode
                    ? 'animate-spin'
                    : ''}"
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
            {#if status?.mode && status.state !== "idle"}
              <span class="t-faint">&middot; {status.mode}</span>
            {/if}
          </span>

          <div class="flex items-center gap-4">
            {#if (status?.synced_count ?? 0) > 0}
              <span class="label"
                >Sincronizados <span class="t-visor">{status?.synced_count}</span
                ></span
              >
            {/if}
            {#if (status?.removed_count ?? 0) > 0}
              <span class="label"
                >Removidos <span class="t-crest">{status?.removed_count}</span
                ></span
              >
            {/if}
            {#if (status?.failed_count ?? 0) > 0}
              <span class="label"
                >Falhas <span class="t-alert">{status?.failed_count}</span></span
              >
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
            <div
              class="progress-fill"
              style="width: {status?.state === 'idle' ? 0 : percent}%"
            ></div>
          {/if}
        </div>

        {#if uiError}
          <p
            class="chip chip-alert !normal-case !tracking-normal !text-[0.6875rem]"
          >
            <AlertTriangle class="w-3.5 h-3.5" />
            {uiError}
          </p>
        {/if}
        {#if status?.error}
          <p
            class="chip chip-alert !whitespace-normal !normal-case !tracking-normal !text-[0.6875rem]"
          >
            <AlertTriangle class="w-3.5 h-3.5 flex-none" />
            {status.error}
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
              <p class="px-3 py-3 t-faint">
                Nenhuma operação executada nesta sessão.
              </p>
            {:else}
              {#each logs as line (line.seq)}
                <div class="console-line">
                  <span class="console-ts">{hhmmss(line.ts)}</span>
                  <span
                    class:console-ok={line.level === "ok"}
                    class:console-warn={line.level === "warn"}
                    class:console-error={line.level === "error"}
                    >{line.message}</span
                  >
                </div>
              {/each}
            {/if}
          </div>
        </div>
      </section>
    </div>
  {:else if activeTab === "ldap"}
    <!-- ABA 2: LDAP -->
    <section class="plate p-6 space-y-6" style="--chamfer: 16px;">
      <div
        class="flex flex-wrap items-center justify-between gap-4 border-b border-[var(--line)] pb-4"
      >
        <div class="space-y-1">
          <h2 class="text-lg font-bold t-txt flex items-center gap-2">
            <Server class="w-5 h-5 t-visor" /> Configuração do LDAP
          </h2>
          <p class="t-dim text-xs">
            Configure a integração com o diretório LDAP/Active Directory para
            autenticação dos demais usuários do portal.
          </p>
        </div>

        <label
          class="flex items-center gap-3 cursor-pointer select-none plate plate-deep px-4 py-2"
          style="--chamfer: 8px;"
        >
          <input
            type="checkbox"
            bind:checked={ldapConfig.enabled}
            class="w-4 h-4 rounded text-[var(--visor)] focus:ring-0 cursor-pointer"
          />
          <span class="text-xs font-bold uppercase tracking-wider t-txt">
            {ldapConfig.enabled ? "LDAP Ativado" : "LDAP Desativado"}
          </span>
          <span class="led {ldapConfig.enabled ? 'led-ok' : 'led-alert'}"></span>
        </label>
      </div>

      {#if ldapMessage}
        <div
          class="chip {ldapMessageType === 'success'
            ? 'chip-ok'
            : 'chip-alert'} !w-full !whitespace-normal !normal-case !tracking-normal text-xs p-3"
        >
          {#if ldapMessageType === "success"}
            <CheckCircle2 class="w-4 h-4 flex-none" />
          {:else}
            <AlertTriangle class="w-4 h-4 flex-none" />
          {/if}
          <span>{ldapMessage}</span>
        </div>
      {/if}

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        <!-- Servidor Host -->
        <div class="space-y-1.5">
          <label for="ldap_host" class="label text-xs font-semibold t-txt"
            >Servidor LDAP (Host)</label
          >
          <input
            id="ldap_host"
            type="text"
            bind:value={ldapConfig.server_host}
            placeholder="ldap.empresa.com"
            class="w-full px-3 py-2 rounded text-sm t-txt outline-none"
            style="background: var(--surface-2); border: 1px solid var(--line);"
          />
        </div>

        <!-- Porta -->
        <div class="space-y-1.5">
          <label for="ldap_port" class="label text-xs font-semibold t-txt"
            >Porta (ex: 389 ou 636)</label
          >
          <input
            id="ldap_port"
            type="number"
            bind:value={ldapConfig.server_port}
            placeholder="389"
            class="w-full px-3 py-2 rounded text-sm t-txt outline-none"
            style="background: var(--surface-2); border: 1px solid var(--line);"
          />
        </div>

        <!-- Checkbox SSL -->
        <div class="space-y-1.5 flex flex-col justify-end">
          <label
            class="flex items-center gap-2 text-xs font-semibold t-txt cursor-pointer py-2.5"
          >
            <input
              type="checkbox"
              bind:checked={ldapConfig.use_ssl}
              class="w-4 h-4 rounded text-[var(--visor)]"
            />
            <span>Usar Conexão Segura (SSL / LDAPS)</span>
          </label>
        </div>

        <!-- Bind DN -->
        <div class="space-y-1.5 lg:col-span-2">
          <label for="bind_dn" class="label text-xs font-semibold t-txt"
            >Bind DN (Conta de Serviço)</label
          >
          <input
            id="bind_dn"
            type="text"
            bind:value={ldapConfig.bind_dn}
            placeholder="cn=admin,dc=empresa,dc=com"
            class="w-full px-3 py-2 rounded text-sm t-txt outline-none"
            style="background: var(--surface-2); border: 1px solid var(--line);"
          />
        </div>

        <!-- Bind Password -->
        <div class="space-y-1.5">
          <label for="bind_password" class="label text-xs font-semibold t-txt"
            >Senha do Bind DN</label
          >
          <input
            id="bind_password"
            type="password"
            bind:value={ldapConfig.bind_password}
            placeholder="••••••••"
            class="w-full px-3 py-2 rounded text-sm t-txt outline-none"
            style="background: var(--surface-2); border: 1px solid var(--line);"
          />
        </div>

        <!-- Base DN -->
        <div class="space-y-1.5 lg:col-span-2">
          <label for="base_dn" class="label text-xs font-semibold t-txt"
            >Base DN (Busca de Usuários)</label
          >
          <input
            id="base_dn"
            type="text"
            bind:value={ldapConfig.base_dn}
            placeholder="ou=users,dc=empresa,dc=com"
            class="w-full px-3 py-2 rounded text-sm t-txt outline-none"
            style="background: var(--surface-2); border: 1px solid var(--line);"
          />
        </div>

        <!-- Atributo do Usuário -->
        <div class="space-y-1.5">
          <label for="user_attr" class="label text-xs font-semibold t-txt"
            >Atributo do Usuário (ex: sAMAccountName ou uid)</label
          >
          <input
            id="user_attr"
            type="text"
            bind:value={ldapConfig.user_attribute}
            placeholder="uid ou sAMAccountName"
            class="w-full px-3 py-2 rounded text-sm t-txt outline-none"
            style="background: var(--surface-2); border: 1px solid var(--line);"
          />
        </div>
      </div>

      <!-- Botões de Ação -->
      <div
        class="flex flex-wrap items-center justify-end gap-3 pt-4 border-t border-[var(--line)]"
      >
        <button
          type="button"
          on:click={handleTestLDAP}
          disabled={ldapTesting || !ldapConfig.server_host}
          class="btn btn-sm px-4 flex items-center gap-2"
        >
          {#if ldapTesting}
            <div
              class="w-3.5 h-3.5 border-2 border-current border-t-transparent rounded-full animate-spin"
            ></div>
            <span>Testando...</span>
          {:else}
            <Server class="w-3.5 h-3.5 t-visor" />
            <span>Testar Conexão</span>
          {/if}
        </button>

        <button
          type="button"
          on:click={handleSaveLDAP}
          disabled={ldapSaving}
          class="btn btn-sm btn-primary px-5 flex items-center gap-2"
        >
          {#if ldapSaving}
            <div
              class="w-3.5 h-3.5 border-2 border-current border-t-transparent rounded-full animate-spin"
            ></div>
            <span>Salvando...</span>
          {:else}
            <ShieldCheck class="w-3.5 h-3.5" />
            <span>Salvar Configuração LDAP</span>
          {/if}
        </button>
      </div>
    </section>
  {/if}
</main>
