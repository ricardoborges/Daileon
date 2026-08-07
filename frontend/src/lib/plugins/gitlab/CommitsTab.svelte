<script lang="ts">
  import { onMount } from 'svelte';
  import { fetchComponentCommits, type ComponentCommitsResponse, type ComponentItem } from '$lib/api';
  import CommitHeatmap from '$lib/components/CommitHeatmap.svelte';
  import { GitBranch, RotateCw } from 'lucide-svelte';

  export let component: ComponentItem;

  let commitsData: ComponentCommitsResponse | null = null;
  let loadingCommits = false;

  async function loadCommitsData() {
    if (!component?.id) return;
    loadingCommits = true;
    try {
      commitsData = await fetchComponentCommits(component.id);
    } catch (e) {
      console.error('Error fetching component commits:', e);
    } finally {
      loadingCommits = false;
    }
  }

  onMount(() => {
    loadCommitsData();
  });
</script>

<section class="space-y-6">
  <div class="flex items-center justify-between plate p-5" style="--chamfer: 16px;">
    <div class="flex items-center gap-3">
      <GitBranch class="w-5 h-5 t-visor" />
      <div>
        <h3 class="text-sm font-semibold t-txt">Histórico de Commits e Atividade</h3>
        <p class="text-xs t-dim">Visualização dos últimos 365 dias de commits extraídos do GitLab SCM.</p>
      </div>
    </div>

    <button
      on:click={loadCommitsData}
      disabled={loadingCommits}
      class="btn btn-crest text-xs flex items-center gap-2"
    >
      <RotateCw class="w-3.5 h-3.5 {loadingCommits ? 'animate-spin' : ''}" />
      Atualizar Histórico
    </button>
  </div>

  {#if loadingCommits && !commitsData}
    <div class="skeleton h-64"></div>
  {:else if commitsData}
    <CommitHeatmap {commitsData} />
  {/if}
</section>
