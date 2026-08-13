<script lang="ts">
  import { onDestroy, onMount, tick } from "svelte";
  import {
    startSync,
    fetchSyncStatus,
    fetchSyncableProjects,
    fetchOrgConfig,
    saveOrgConfig,
    type SyncLogLine,
    type SyncMode,
    type SyncStatus,
    type SyncableProject,
    type OrganizationConfig,
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
    Building2,
    Search,
    FolderGit2,
    FolderOpen,
    Image as ImageIcon,
    RotateCw,
    Blocks,
    ArrowLeft,
  } from "lucide-svelte";
  import { t } from "$lib/i18n";
  import { pluginRegistry } from "$lib/plugins";
  import PluginCenter from "$lib/plugins/PluginCenter.svelte";

  interface Operation {
    mode: SyncMode;
    label: string;
    icon: typeof RefreshCw;
    summary: string;
    detail: string;
    /** Apaga dados: exige confirmação antes de disparar. */
    destructive: boolean;
  }

  $: operations = [
    {
      mode: "update",
      label: $t("config.opUpdateLabel"),
      icon: RefreshCw,
      summary: $t("config.opUpdateSummary"),
      detail: $t("config.opUpdateDetail"),
      destructive: false,
    },
    {
      mode: "rebuild",
      label: $t("config.opRebuildLabel"),
      icon: Database,
      summary: $t("config.opRebuildSummary"),
      detail: $t("config.opRebuildDetail"),
      destructive: true,
    },
    {
      mode: "prune",
      label: $t("config.opPruneLabel"),
      icon: Eraser,
      summary: $t("config.opPruneSummary"),
      detail: $t("config.opPruneDetail"),
      destructive: false,
    },
  ] as Operation[];

  const POLL_MS = 800;

  let activeTab: string = "sync";

  $: configurablePlugins = pluginRegistry.getConfigurablePlugins();

  let status: SyncStatus | null = null;
  let logs: SyncLogLine[] = [];
  let cursor = 0;
  let starting = false;
  let uiError = "";
  let confirming: SyncMode | null = null;
  let timer: ReturnType<typeof setTimeout> | null = null;
  let consoleEl: HTMLDivElement | null = null;
  let stuckToBottom = true;

  // -- Escopo da sincronização ------------------------------------------
  let scope: "all" | "selected" = "all";
  let projects: SyncableProject[] = [];
  let projectsLoaded = false;
  let projectsLoading = false;
  let projectsError = "";
  let projectQuery = "";
  let selectedIds = new Set<number>();
  /** Vazio = usar o `spec.docs.dir` de cada manifesto. */
  let docsDir = "";
  let indexImages = true;

  $: scoped = scope === "selected";
  $: selectedProjectIds = [...selectedIds];
  $: visibleProjects = filterProjects(projects, projectQuery);

  function filterProjects(list: SyncableProject[], query: string) {
    const q = query.trim().toLowerCase();
    if (!q) return list;
    return list.filter(
      (p) =>
        p.name.toLowerCase().includes(q) || p.path.toLowerCase().includes(q),
    );
  }

  async function loadProjects(force = false) {
    if (projectsLoading || (projectsLoaded && !force)) return;
    projectsLoading = true;
    projectsError = "";
    try {
      projects = await fetchSyncableProjects();
      projectsLoaded = true;
    } catch (e: any) {
      projectsError = e.message || "Falha ao listar os projetos";
    } finally {
      projectsLoading = false;
    }
  }

  function setScope(next: "all" | "selected") {
    scope = next;
    confirming = null;
    uiError = "";
    if (next === "selected") loadProjects();
  }

  function toggleProject(id: number) {
    const next = new Set(selectedIds);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    selectedIds = next;
  }

  $: running = status?.state === "running" || starting;
  $: busy = running;
  /** Reconstruir e remover órfãos raciocinam sobre o catálogo inteiro. */
  $: blockedByScope = (mode: SyncMode) => scoped && mode !== "update";

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
      ? $t("config.statusStarting")
      : {
          idle: $t("config.statusIdle"),
          running: $t("config.statusRunning"),
          success: $t("config.statusSuccess"),
          partial: $t("config.statusPartial"),
          error: $t("config.statusError"),
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

  // Organization Config State
  let orgConfig: OrganizationConfig = {
    name: "",
    acronym: "",
  };
  let orgLoading = false;
  let orgSaving = false;
  let orgMessage = "";
  let orgMessageType: "success" | "error" = "success";

  onMount(() => {
    // Reanexa a uma operação já em andamento (recarregar a página não a cancela).
    poll();
    loadOrg();
  });

  async function loadOrg() {
    orgLoading = true;
    try {
      orgConfig = await fetchOrgConfig();
    } catch (e: any) {
      // Ignora erro inicial
    } finally {
      orgLoading = false;
    }
  }

  async function handleSaveOrg() {
    orgSaving = true;
    orgMessage = "";
    try {
      const res = await saveOrgConfig(orgConfig);
      orgMessage = res.message || "Configurações da organização salvas com sucesso!";
      orgMessageType = "success";
    } catch (e: any) {
      orgMessage = e.message || "Falha ao salvar configurações da organização.";
      orgMessageType = "error";
    } finally {
      orgSaving = false;
    }
  }

  onDestroy(() => {
    if (timer) clearTimeout(timer);
  });

  async function poll() {
    try {
      const next = await fetchSyncStatus(cursor);

      if (status && status.mode !== next.mode) {
        logs = [];
        cursor = 0;
      }
      status = next;

      if (next.logs && next.logs.length > 0) {
        logs = [...logs, ...next.logs];
        cursor = logs[logs.length - 1].seq + 1;
        scrollConsole();
      }

      if (next.state === "running") {
        timer = setTimeout(poll, POLL_MS);
      }
    } catch (e: any) {
      uiError = e.message || "Falha ao consultar status da operação";
    }
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
    if (scoped && selectedIds.size === 0) {
      uiError = $t("config.scopeNeedsSelection");
      return;
    }
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
      // Pasta e imagens descrevem um repositório: só acompanham o recorte.
      const withScope = scoped && mode === "update";
      const started = await startSync(
        mode,
        withScope ? selectedProjectIds : undefined,
        withScope ? { docsDir, indexImages } : {},
      );
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

<svelte:head><title>{$t("config.title")} &middot; Daileon</title></svelte:head>

<main class="max-w-7xl mx-auto px-6 py-10 space-y-8">
  <header class="space-y-3">
    <span class="eyebrow">{$t("config.eyebrow")}</span>
    <div class="rule">
      <h1
        class="text-3xl font-bold tracking-[-0.03em] t-txt flex items-center gap-3 whitespace-nowrap"
      >
        <Settings class="w-7 h-7 t-visor" /> {$t("config.title")}
      </h1>
    </div>
    <p class="t-dim text-sm">
      Gerenciamento de sincronização do catálogo e autenticação LDAP.
    </p>
  </header>

  <!-- Navegação de Abas -->
  <div class="border-b border-[var(--line)] pb-4">
    <div class="seg flex-wrap gap-1" role="tablist">
      <button
        type="button"
        role="tab"
        aria-selected={activeTab === "sync"}
        class="seg-item cursor-pointer {activeTab === 'sync' ? 'is-active' : ''}"
        on:click={() => (activeTab = "sync")}
      >
        <RefreshCw class="w-4 h-4" />
        <span>{$t("config.tabSync")}</span>
      </button>
      <button
        type="button"
        role="tab"
        aria-selected={activeTab === "org"}
        class="seg-item cursor-pointer {activeTab === 'org' ? 'is-active' : ''}"
        on:click={() => (activeTab = "org")}
      >
        <Building2 class="w-4 h-4" />
        <span>{$t("config.tabOrg")}</span>
      </button>

      <button
        type="button"
        role="tab"
        aria-selected={activeTab === "plugins" || configurablePlugins.some(p => p.id === activeTab)}
        class="seg-item cursor-pointer {activeTab === 'plugins' || configurablePlugins.some(p => p.id === activeTab) ? 'is-active' : ''}"
        on:click={() => (activeTab = "plugins")}
      >
        <Blocks class="w-4 h-4 t-visor" />
        <span>Plugins</span>
      </button>
    </div>
  </div>

  {#if activeTab === "sync"}
    <!-- ABA 1: Sincronização -->
    <div class="space-y-8">
      <!-- Escopo -->
      <section class="plate plate-deep p-5 space-y-4" style="--chamfer: 14px;">
        <div class="flex flex-wrap items-center justify-between gap-4">
          <h2 class="text-sm font-bold t-txt flex items-center gap-2">
            <FolderGit2 class="w-4 h-4 t-visor" />
            {$t("config.scopeTitle")}
          </h2>

          <div class="seg" role="radiogroup">
            <button
              type="button"
              role="radio"
              aria-checked={!scoped}
              class="seg-item cursor-pointer {!scoped ? 'is-active' : ''}"
              disabled={busy}
              on:click={() => setScope("all")}
            >
              <Database class="w-3.5 h-3.5" />
              <span>{$t("config.scopeAll")}</span>
            </button>
            <button
              type="button"
              role="radio"
              aria-checked={scoped}
              class="seg-item cursor-pointer {scoped ? 'is-active' : ''}"
              disabled={busy}
              on:click={() => setScope("selected")}
            >
              <FolderGit2 class="w-3.5 h-3.5" />
              <span>{$t("config.scopeSelected")}</span>
            </button>
          </div>
        </div>

        <p class="t-dim text-xs leading-relaxed">
          {scoped ? $t("config.scopeSelectedHint") : $t("config.scopeAllHint")}
        </p>

        {#if scoped}
          <div class="space-y-3 pt-1">
            <div class="flex flex-wrap items-center gap-3">
              <div class="relative flex-1 min-w-[16rem]">
                <Search
                  class="w-3.5 h-3.5 t-faint absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none"
                />
                <input
                  class="field pl-9"
                  type="search"
                  bind:value={projectQuery}
                  placeholder={$t("config.scopeSearchPlaceholder")}
                  disabled={projectsLoading}
                />
              </div>
              <span class="label">
                {$t("config.scopeSelectedCount", { count: selectedIds.size })}
              </span>
              {#if selectedIds.size > 0}
                <button
                  class="btn btn-sm btn-ghost"
                  disabled={busy}
                  on:click={() => (selectedIds = new Set())}
                >
                  {$t("config.scopeClear")}
                </button>
              {/if}
              <button
                class="btn btn-sm btn-ghost"
                disabled={projectsLoading || busy}
                title={$t("config.scopeReload")}
                on:click={() => loadProjects(true)}
              >
                <RotateCw
                  class="w-3.5 h-3.5 {projectsLoading ? 'animate-spin' : ''}"
                />
              </button>
            </div>

            {#if projectsLoading && projects.length === 0}
              <p class="t-faint text-xs">{$t("config.scopeLoading")}</p>
            {:else if projectsError}
              <p class="chip chip-alert !normal-case !tracking-normal">
                <AlertTriangle class="w-3.5 h-3.5 flex-none" />
                {projectsError}
              </p>
            {:else if projects.length === 0}
              <p class="t-faint text-xs">{$t("config.scopeEmpty")}</p>
            {:else if visibleProjects.length === 0}
              <p class="t-faint text-xs">{$t("config.scopeNoMatch")}</p>
            {:else}
              <div
                class="max-h-72 overflow-y-auto border border-line divide-y divide-[var(--line-soft)]"
              >
                {#each visibleProjects as project (project.id)}
                  <label
                    class="flex items-center gap-3 px-3 py-2 cursor-pointer hover:bg-surface-2 transition-colors"
                  >
                    <input
                      type="checkbox"
                      class="shrink-0"
                      checked={selectedIds.has(project.id)}
                      disabled={busy}
                      on:change={() => toggleProject(project.id)}
                    />
                    <span class="min-w-0 flex-1">
                      <span class="block text-xs t-txt truncate"
                        >{project.name}</span
                      >
                      <span class="block text-[11px] t-faint font-mono truncate"
                        >{project.path}</span
                      >
                    </span>
                    <span
                      class="label shrink-0 {project.in_catalog
                        ? 't-visor'
                        : 't-crest'}"
                    >
                      {project.in_catalog
                        ? $t("config.scopeInCatalog")
                        : $t("config.scopeNew")}
                    </span>
                  </label>
                {/each}
              </div>
            {/if}

            <div
              class="grid gap-5 sm:grid-cols-2 pt-4 border-t border-[var(--line-soft)]"
            >
              <div class="space-y-1.5">
                <label class="label block" for="sync-docs-dir">
                  {$t("config.scopeDocsDirLabel")}
                </label>
                <div class="relative">
                  <FolderOpen
                    class="w-3.5 h-3.5 t-faint absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none"
                  />
                  <input
                    id="sync-docs-dir"
                    class="field pl-9 font-mono"
                    type="text"
                    bind:value={docsDir}
                    placeholder={$t("config.scopeDocsDirPlaceholder")}
                    disabled={busy}
                  />
                </div>
                <p class="t-faint text-[11px] leading-relaxed">
                  {$t("config.scopeDocsDirHint")}
                </p>
              </div>

              <div class="space-y-1.5">
                <span class="label block">{$t("config.scopeImagesLabel")}</span>
                <label class="flex items-center gap-2 cursor-pointer py-1.5">
                  <input
                    type="checkbox"
                    class="shrink-0"
                    bind:checked={indexImages}
                    disabled={busy}
                  />
                  <ImageIcon class="w-3.5 h-3.5 t-visor" />
                  <span class="text-xs t-txt"
                    >{$t("config.scopeIndexImages")}</span
                  >
                </label>
                <p class="t-faint text-[11px] leading-relaxed">
                  {$t("config.scopeIndexImagesHint")}
                </p>
              </div>
            </div>
          </div>
        {/if}
      </section>

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
                  {$t("config.opDestructiveAlert")}
                </p>
                <div class="flex gap-2">
                  <button
                    class="btn btn-sm flex-1"
                    on:click={() => (confirming = null)}
                  >
                    {$t("config.opCancel")}
                  </button>
                  <button
                    class="btn btn-sm btn-crest flex-1"
                    disabled={busy}
                    on:click={() => run(op.mode)}
                  >
                    {$t("config.opConfirmAction")}
                  </button>
                </div>
              </div>
            {:else}
              <button
                class="btn btn-sm w-full {op.destructive
                  ? 'btn-crest'
                  : 'btn-primary'}"
                disabled={busy || blockedByScope(op.mode)}
                title={blockedByScope(op.mode)
                  ? $t("config.scopeOnlyUpdate")
                  : undefined}
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
              {#if blockedByScope(op.mode)}
                <p class="label t-faint !normal-case !tracking-normal">
                  {$t("config.scopeOnlyUpdate")}
                </p>
              {/if}
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
            {#if (status?.scoped_project_count ?? 0) > 0}
              <span class="t-faint">
                &middot; {$t("config.scopeSelectedCount", {
                  count: status?.scoped_project_count,
                })}
              </span>
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
            <Terminal class="w-3 h-3" /> {$t("config.consoleTitle")}
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
  {:else if activeTab === "plugins"}
    <!-- ABA: Central de Plugins -->
    <PluginCenter onSelectConfigPlugin={(pluginId) => (activeTab = pluginId)} />
  {:else if activeTab === "org"}
    <!-- ABA 3: Organização -->
    <section class="plate p-6 space-y-6" style="--chamfer: 16px;">
      <div
        class="form-head"
      >
        <div class="space-y-1">
          <h2 class="text-lg font-bold t-txt flex items-center gap-2">
            <Building2 class="w-5 h-5 t-visor" /> {$t("config.orgTitle")}
          </h2>
          <p class="t-dim text-xs">
            {$t("config.orgSubtitle")}
          </p>
        </div>
      </div>

      {#if orgMessage}
        <div
          class="chip {orgMessageType === 'success'
            ? 'chip-ok'
            : 'chip-alert'} !w-full !whitespace-normal !normal-case !tracking-normal text-xs p-3"
        >
          {#if orgMessageType === "success"}
            <CheckCircle2 class="w-4 h-4 flex-none" />
          {:else}
            <AlertTriangle class="w-4 h-4 flex-none" />
          {/if}
          <span>{orgMessage}</span>
        </div>
      {/if}

      <div class="form-grid form-grid-2">
        <!-- Nome da Organização -->
        <div class="form-row">
          <label for="org_name" class="field-label"
            >{$t("config.orgName")}</label
          >
          <input
            id="org_name"
            type="text"
            bind:value={orgConfig.name}
            placeholder={$t("config.orgNamePlaceholder")}
            class="field"
          />
        </div>

        <!-- Sigla da Organização -->
        <div class="form-row">
          <label for="org_acronym" class="field-label"
            >{$t("config.orgAcronym")}</label
          >
          <input
            id="org_acronym"
            type="text"
            bind:value={orgConfig.acronym}
            placeholder={$t("config.orgAcronymPlaceholder")}
            class="field field-mono"
          />
        </div>
      </div>

      <!-- Botões de Ação -->
      <div
        class="form-actions"
      >
        <button
          type="button"
          on:click={handleSaveOrg}
          disabled={orgSaving}
          class="btn btn-sm btn-primary px-5 flex items-center gap-2"
        >
          {#if orgSaving}
            <div
              class="w-3.5 h-3.5 border-2 border-current border-t-transparent rounded-full animate-spin"
            ></div>
            <span>{$t("config.orgSaving")}</span>
          {:else}
            <ShieldCheck class="w-3.5 h-3.5" />
            <span>{$t("config.orgSave")}</span>
          {/if}
        </button>
      </div>
    </section>
  {:else}
    <!-- Configuração de Plugin Específico -->
    {#each configurablePlugins as plugin (plugin.id)}
      {#if activeTab === plugin.id && plugin.configComponent}
        <div class="space-y-4">
          <div class="flex items-center justify-between pb-3 border-b border-[var(--line)]">
            <button
              type="button"
              on:click={() => (activeTab = "plugins")}
              class="btn btn-sm btn-ghost flex items-center gap-2 text-xs font-semibold t-dim hover:t-txt"
            >
              <ArrowLeft class="w-4 h-4" />
              <span>Voltar para Central de Plugins</span>
            </button>
            <span class="chip chip-visor text-xs font-mono font-bold">
              Configurando: {plugin.name}
            </span>
          </div>
          <svelte:component this={plugin.configComponent} />
        </div>
      {/if}
    {/each}
  {/if}
</main>

