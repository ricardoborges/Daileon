<script lang="ts">
  import type { ComponentItem } from '$lib/api';
  import { BookOpen, ExternalLink, Cpu } from 'lucide-svelte';

  export let item: ComponentItem;

  function getLifecycle(lifecycle: string) {
    switch (lifecycle.toLowerCase()) {
      case 'production':
        return { text: 'Produção', chip: 'chip-ok', led: 'led-ok' };
      case 'experimental':
        return { text: 'Experimental', chip: 'chip-crest', led: 'led-crest' };
      case 'deprecated':
        return { text: 'Depreciado', chip: 'chip-alert', led: 'led-alert' };
      default:
        return { text: lifecycle, chip: '', led: '' };
    }
  }

  $: status = getLifecycle(item.lifecycle);
</script>

<article class="plate plate-link flex flex-col p-5" style="--chamfer: 14px;">
  <!-- Identificação -->
  <div class="flex items-center justify-between gap-3 mb-4">
    <span class="chip chip-visor">
      <Cpu class="w-3 h-3" />
      {item.type}
    </span>
    <span class="chip {status.chip}">
      <span class="led {status.led}"></span>
      {status.text}
    </span>
  </div>

  <a href={`/catalog/${item.id}`} class="group/name block">
    <h3 class="text-lg font-bold tracking-[-0.02em] t-txt group-hover/name:t-visor transition-colors flex items-center gap-2">
      <span class="truncate">{item.name}</span>
      {#if item.has_manifest}
        <span class="led led-visor" title="Possui daileon.yml"></span>
      {/if}
    </h3>
  </a>

  <p class="text-[13px] leading-relaxed t-dim mt-2 line-clamp-2">
    {item.description || 'Sem descrição cadastrada.'}
  </p>

  {#if item.tags.length > 0}
    <div class="flex flex-wrap gap-1.5 mt-4">
      {#each item.tags.slice(0, 5) as tag}
        <span class="tag">{tag}</span>
      {/each}
    </div>
  {/if}

  <!-- Rodapé técnico -->
  <div class="mt-auto pt-5 border-t border-line flex items-center justify-between gap-3">
    <span class="label truncate" title={item.owner}>
      <span class="t-faint">Owner /</span>
      <span class="t-dim">{item.owner}</span>
    </span>

    <div class="flex items-center gap-2 shrink-0">
      <a href={`/catalog/${item.id}/docs/index.md`} class="btn btn-sm">
        <BookOpen class="w-3 h-3" /> Docs
      </a>

      {#if item.gitlab_url}
        <a
          href={item.gitlab_url}
          target="_blank"
          rel="noopener noreferrer"
          class="btn btn-sm px-2"
          title="Abrir no GitLab"
          aria-label="Abrir no GitLab"
        >
          <ExternalLink class="w-3 h-3" />
        </a>
      {/if}
    </div>
  </div>
</article>
