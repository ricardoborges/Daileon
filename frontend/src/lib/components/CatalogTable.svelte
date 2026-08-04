<script lang="ts">
  import type { ComponentItem } from "$lib/api";
  import { BookOpen, ExternalLink, Cpu, ShieldAlert } from "lucide-svelte";
  import { t, locale } from "$lib/i18n";

  export let items: ComponentItem[] = [];


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
</script>

<div class="plate plate-deep p-0 overflow-x-auto" style="--chamfer: 14px;">
  <table class="w-full text-left border-collapse min-w-[800px]">
    <thead>
      <tr
        class="border-b border-line bg-surface-2 text-[11px] font-mono uppercase tracking-wider t-faint"
      >
        <th class="py-3 px-4">{$t("catalog.colName")}</th>
        <th class="py-3 px-4">{$t("catalog.colType")}</th>
        <th class="py-3 px-4">{$t("catalog.colLifecycle")}</th>
        <th class="py-3 px-4">{$t("catalog.colOwner")}</th>
        <th class="py-3 px-4">{$t("catalog.colLastCommit")}</th>
        <th class="py-3 px-4">{$t("catalog.colFirstCommit")}</th>
        <th class="py-3 px-4 text-right">{$t("catalog.colActions")}</th>
      </tr>
    </thead>
    <tbody class="divide-y divide-line/40 text-sm">
      {#each items as item}
        {@const status = getLifecycle(item.lifecycle)}
        {@const lastCommitDate = formatDate(
          item.last_activity_at || item.updated_at,
          $locale,
        )}
        <!-- O primeiro commit preserva a idade de projetos migrados de outra
             instância do GitLab; `gitlab_created_at` é só o fallback. -->
        {@const createdDate = formatDate(item.first_commit_at || item.gitlab_created_at, $locale)}
        <tr class="hover:bg-surface-2 transition-colors">
          <!-- Nome e Descrição -->
          <td class="py-3.5 px-4 max-w-xs">
            <div class="flex items-center gap-2">
              <a
                href={`/catalog/${item.id}`}
                class="font-bold t-txt hover:t-visor transition-colors truncate"
              >
                {item.name}
              </a>
            </div>
            {#if item.description}
              <p class="text-xs t-dim truncate mt-0.5" title={item.description}>
                {item.description}
              </p>
            {/if}
          </td>

          <!-- Tipo -->
          <td class="py-3.5 px-4 whitespace-nowrap">
            {#if item.has_manifest}
              <span class="chip chip-visor">
                <Cpu class="w-3 h-3" />
                {item.type}
              </span>
            {:else}
              <span class="text-xs t-faint font-mono">—</span>
            {/if}
          </td>

          <!-- Lifecycle -->
          <td class="py-3.5 px-4 whitespace-nowrap">
            {#if item.has_manifest}
              <span class="chip {status.chip}">
                <span class="led {status.led}"></span>
                {status.text}
              </span>
            {:else}
              <span class="text-xs t-faint font-mono">—</span>
            {/if}
          </td>

          <!-- Owner / Time -->
          <td class="py-3.5 px-4 whitespace-nowrap">
            <span class="label text-xs t-dim font-mono">{item.owner}</span>
          </td>

          <!-- Data de Última Atividade -->
          <td class="py-3.5 px-4 whitespace-nowrap text-xs font-mono t-dim">
            {lastCommitDate || "—"}
          </td>

          <!-- Data de Criação -->
          <td class="py-3.5 px-4 whitespace-nowrap text-xs font-mono t-dim">
            {createdDate || "—"}
          </td>

          <!-- Ações -->
          <td class="py-3.5 px-4 whitespace-nowrap text-right">
            <div class="flex items-center justify-end gap-2">
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
          </td>
        </tr>
      {/each}
    </tbody>
  </table>
</div>
