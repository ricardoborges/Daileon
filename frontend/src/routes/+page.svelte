<script lang="ts">
  import { onMount } from "svelte";
  import {
    fetchCatalog,
    fetchServers,
    fetchOrgConfig,
    isMixedEnvironment,
    type ComponentItem,
    type ServerItem,
    type OrganizationConfig,
  } from "$lib/api";
  import DaileonLogo from "$lib/components/DaileonLogo.svelte";
  import {
    Layers,
    ShieldCheck,
    ArrowRight,
    Activity,
    AlertTriangle,
    Server,
    Network,
    FolderKanban,
  } from "lucide-svelte";
  import { t } from "$lib/i18n";

  let components: ComponentItem[] = [];
  let servers: ServerItem[] = [];
  let orgConfig: OrganizationConfig | null = null;
  let loading = true;

  onMount(async () => {
    try {
      const [catRes, srvRes, orgRes] = await Promise.allSettled([
        fetchCatalog(),
        fetchServers(),
        fetchOrgConfig(),
      ]);
      if (catRes.status === "fulfilled") components = catRes.value;
      if (srvRes.status === "fulfilled") servers = srvRes.value;
      if (orgRes.status === "fulfilled") orgConfig = orgRes.value;
    } catch (e) {
      console.error("Error loading home data:", e);
    } finally {
      loading = false;
    }
  });

  $: projectsWithRisksCount = components.filter(
    (c) =>
      (c.critical_risks_count || 0) > 0 ||
      (c.warning_risks_count || 0) > 0 ||
      (c.risks && c.risks.length > 0)
  ).length;

  $: serversWithAlertsCount = servers.filter(isMixedEnvironment).length;

  $: stats = [
    {
      label: $t("home.statTotal"),
      value: components.length,
      icon: Layers,
      tone: "t-visor",
      href: "/catalog",
    },
    {
      label: $t("home.statProjectsWithRisks"),
      value: projectsWithRisksCount,
      icon: AlertTriangle,
      tone: projectsWithRisksCount > 0 ? "t-alert" : "t-ok",
      href: "/catalog",
    },
    {
      label: $t("home.statServers"),
      value: servers.length,
      icon: Server,
      tone: "t-visor",
      href: "/servers",
    },
    {
      label: $t("home.statServersWithAlerts"),
      value: serversWithAlertsCount,
      icon: AlertTriangle,
      tone: serversWithAlertsCount > 0 ? "t-alert" : "t-ok",
      href: "/servers",
    },
    {
      label: $t("home.statProduction"),
      value: components.filter((c) => c.lifecycle === "production").length,
      icon: Activity,
      tone: "t-ok",
      href: "/catalog",
    },
    {
      label: $t("home.statManifest"),
      value: components.filter((c) => c.has_manifest).length,
      icon: ShieldCheck,
      tone: "t-txt",
      href: "/catalog",
    },
  ];

  $: quickAccessCards = [
    {
      title: $t("nav.catalog"),
      desc: $t("home.navCatalogDesc"),
      icon: Layers,
      href: "/catalog",
      badge: `${components.length} ${$t("catalog.projectPlural")}`,
    },
    {
      title: $t("nav.servers"),
      desc: $t("home.navServersDesc"),
      icon: Server,
      href: "/servers",
      badge: `${servers.length} servidores`,
    },
    {
      title: $t("graph.navLabel"),
      desc: $t("home.navGraphDesc"),
      icon: Network,
      href: "/graph",
      badge: "Grafo",
    },
    {
      title: $t("catalog.tabDomains"),
      desc: $t("home.navDomainsDesc"),
      icon: FolderKanban,
      href: "/domains",
      badge: "Arquitetura",
    },
  ];
</script>

<svelte:head>
  <title>Daileon · Developer Portal</title>
</svelte:head>

<main class="max-w-7xl mx-auto px-6 py-10 space-y-12">
  <!-- ============ Console principal ============ -->
  <section class="plate plate-deep overflow-hidden relative" style="--chamfer: 30px;">
    <!-- Malha técnica + varredura do visor -->
    <div
      class="absolute inset-0 grid-mesh opacity-70 pointer-events-none"
    ></div>
    <div
      class="absolute inset-x-0 top-0 h-24 pointer-events-none animate-sweep"
      style="background: linear-gradient(180deg, transparent, var(--visor-wash), transparent);"
    ></div>

    <!-- Mecha em marca d'água -->
    <div
      class="absolute -right-16 -bottom-24 opacity-[0.07] pointer-events-none hidden md:block"
    >
      <DaileonLogo size={460} />
    </div>

    <div class="relative p-8 md:p-12 max-w-3xl space-y-6">
      <div class="flex flex-wrap items-center gap-2">
        {#if orgConfig?.acronym || orgConfig?.name}
          <span class="eyebrow">{orgConfig.name} · {orgConfig.acronym}</span>
        {:else}
          <span class="eyebrow">{$t("home.unitEyebrow")}</span>
        {/if}
      </div>

      <h1
        class="text-2xl md:text-3xl font-bold tracking-[-0.03em] leading-tight t-txt"
      >
        {$t("home.heroTitle")}
      </h1>

      <p class="t-dim text-[15px] leading-relaxed max-w-none">
        {$t("home.heroDesc")}
      </p>

      <div class="flex flex-wrap items-center gap-3 pt-2">
        <a href="/catalog" class="btn btn-primary btn-md flex items-center gap-2">
          <span>{$t("home.btnCatalog")}</span>
          <ArrowRight class="w-4 h-4" />
        </a>
        <a href="/servers" class="btn btn-md flex items-center gap-2">
          <Server class="w-4 h-4 t-visor" />
          <span>{$t("nav.servers")}</span>
        </a>
      </div>

      <!-- Barra de status do console -->
      <div class="flex flex-wrap items-center gap-x-6 gap-y-2 pt-4 border-t border-[var(--line)]">
        <span class="label flex items-center gap-2">
          <span class="led {loading ? 'led-crest' : 'led-ok'}"></span>
          {loading ? $t("home.readingCatalog") : $t("home.systemsNominal")}
        </span>
        <span class="label">{$t("home.sourceGitlab")}</span>
        <span class="label"
          >{$t("home.indexedComponents", { count: components.length })}</span
        >
      </div>
    </div>
  </section>

  <!-- ============ Gauges / Indicadores ============ -->
  <section class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
    {#each stats as stat}
      <a
        href={stat.href}
        class="plate gauge {stat.tone} p-5 hover:border-[var(--line-bright)] transition-all group block"
        style="--chamfer: 12px;"
      >
        <div class="flex items-start justify-between gap-3">
          <span class="readout text-[2rem] leading-none group-hover:scale-105 transition-transform">
            {String(stat.value).padStart(2, "0")}
          </span>
          <svelte:component this={stat.icon} class="w-4 h-4 opacity-70 group-hover:opacity-100 transition-opacity" />
        </div>
        <span class="label block mt-3 text-xs leading-tight">{stat.label}</span>
      </a>
    {/each}
  </section>

  <!-- ============ Hub de Acesso Rápido ============ -->
  <section class="space-y-6">
    <div class="min-w-0">
      <div class="rule">
        <h2 class="text-xl font-bold tracking-[-0.02em] t-txt whitespace-nowrap">
          {$t("home.quickAccessTitle")}
        </h2>
      </div>
      <p class="label mt-2">{$t("home.quickAccessSubtitle")}</p>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
      {#each quickAccessCards as card}
        <a
          href={card.href}
          class="plate plate-deep p-6 space-y-4 hover:border-[var(--line-bright)] transition-all group flex flex-col justify-between"
          style="--chamfer: 16px;"
        >
          <div class="space-y-3">
            <div class="flex items-center justify-between">
              <div class="plate p-2.5" style="--chamfer: 8px;">
                <svelte:component this={card.icon} class="w-5 h-5 t-visor group-hover:scale-110 transition-transform" />
              </div>
              <span class="chip text-[10px] font-mono font-semibold">{card.badge}</span>
            </div>

            <h3 class="text-lg font-bold t-txt group-hover:t-visor transition-colors">
              {card.title}
            </h3>

            <p class="t-dim text-xs leading-relaxed">
              {card.desc}
            </p>
          </div>

          <div class="flex items-center gap-1 text-xs font-bold t-visor pt-2 group-hover:translate-x-1 transition-transform">
            <span>Acessar</span>
            <ArrowRight class="w-3.5 h-3.5" />
          </div>
        </a>
      {/each}
    </div>
  </section>
</main>
