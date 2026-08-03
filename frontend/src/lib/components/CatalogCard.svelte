<script lang="ts">
  import type { ComponentItem } from "$lib/api";
  import { BookOpen, ExternalLink, Cpu, Calendar } from "lucide-svelte";
  import { t, locale } from "$lib/i18n";

  export let item: ComponentItem;

  function getLifecycle(lifecycle: string) {
    switch (lifecycle.toLowerCase()) {
      case "production":
        return {
          text: $t("card.lifecycleProduction"),
          chip: "chip-ok",
          led: "led-ok",
        };
      case "experimental":
        return {
          text: $t("card.lifecycleExperimental"),
          chip: "chip-crest",
          led: "led-crest",
        };
      case "deprecated":
        return {
          text: $t("card.lifecycleDeprecated"),
          chip: "chip-alert",
          led: "led-alert",
        };
      default:
        return { text: lifecycle, chip: "", led: "" };
    }
  }

  function formatDate(isoStr?: string, loc: string = "pt-BR") {
    if (!isoStr) return null;
    const d = new Date(isoStr);
    return Number.isNaN(d.getTime())
      ? null
      : d.toLocaleDateString(loc, {
          day: "2-digit",
          month: "2-digit",
          year: "numeric",
        });
  }

  $: status = getLifecycle(item.lifecycle);
  $: lastCommitDate = formatDate(
    item.last_activity_at || item.updated_at,
    $locale,
  );
  // Projetos migrados de outra instância do GitLab têm `gitlab_created_at`
  // igual à data da migração. O primeiro commit é a idade real do código;
  // a data de criação do repositório só entra quando ele não está disponível.
  $: createdDate = formatDate(item.first_commit_at || item.gitlab_created_at, $locale);
  $: createdLabel = item.first_commit_at ? $t("card.firstCommit") : $t("card.created");
</script>

<article class="plate plate-link flex flex-col p-5" style="--chamfer: 14px;">
  <!-- Identificação -->
  <div class="flex items-center justify-between gap-3 mb-4">
    {#if item.has_manifest}
      <span class="chip chip-visor">
        <Cpu class="w-3 h-3" />
        {item.type}
      </span>
      <span class="chip {status.chip}">
        <span class="led {status.led}"></span>
        {status.text}
      </span>
    {:else}
      <span class="chip chip-alert opacity-80">
        <span class="led led-alert"></span>
        {$t("card.noManifest")}
      </span>
    {/if}
  </div>

  <a href={`/catalog/${item.id}`} class="group/name block">
    <h3
      class="text-lg font-bold tracking-[-0.02em] t-txt group-hover/name:t-visor transition-colors flex items-center gap-2"
    >
      <span class="truncate">{item.name}</span>
    </h3>
  </a>

  <p class="text-[13px] leading-relaxed t-dim mt-2 line-clamp-2">
    {item.description || $t("card.noDescription")}
  </p>

  {#if item.tags.length > 0}
    <div class="flex flex-wrap gap-1.5 mt-4 mb-2">
      {#each item.tags.slice(0, 5) as tag}
        <span class="tag">{tag}</span>
      {/each}
    </div>
  {/if}

  <!-- Rodapé técnico -->
  <div class="mt-auto pt-4 border-t border-line flex flex-col gap-2.5">
    <div class="flex items-center justify-between gap-3">
      <span class="label truncate" title={item.owner}>
        <span class="t-faint">{$t("card.ownerPrefix")}</span>
        <span class="t-dim">{item.owner}</span>
      </span>

      <div class="flex items-center gap-2 shrink-0">
        {#if item.has_manifest || (item.docs_count && item.docs_count > 0)}
          <a href={`/catalog/${item.id}?tab=docs`} class="btn btn-sm">
            <BookOpen class="w-3 h-3" />
            {$t("card.docs", { count: item.docs_count ?? 0 })}
          </a>
        {/if}

        {#if item.gitlab_url}
          <a
            href={item.gitlab_url}
            target="_blank"
            rel="noopener noreferrer"
            class="btn btn-sm px-2"
            title={$t("card.openGitlab")}
            aria-label={$t("card.openGitlab")}
          >
            <ExternalLink class="w-3 h-3" />
          </a>
        {/if}
      </div>
    </div>

    <!-- Datas com labels -->
    <div
      class="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 pt-2 border-t border-line-soft text-[0.6875rem] font-mono"
    >
      <div class="flex items-center gap-1.5">
        <span class="t-faint">{$t("card.lastCommit")}</span>
        <span class="t-dim">{lastCommitDate || "—"}</span>
      </div>
      <div class="flex items-center gap-1.5">
        <span class="t-faint">{createdLabel}</span>
        <span class="t-dim">{createdDate || "—"}</span>
      </div>
    </div>
  </div>
</article>
