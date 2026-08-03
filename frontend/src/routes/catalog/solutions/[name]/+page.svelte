<script lang="ts">
  import { page } from '$app/stores';
  import { fetchSolutionDetail, type SolutionItem } from '$lib/api';
  import GroupDetail from '$lib/components/GroupDetail.svelte';
  import { t } from '$lib/i18n';
  import { Boxes } from 'lucide-svelte';

  let solution: SolutionItem | null = null;
  let loading = true;
  let error: string | null = null;

  $: solutionName = $page.params.name;
  $: if (solutionName) load(solutionName);

  async function load(name: string) {
    loading = true;
    error = null;
    try {
      solution = await fetchSolutionDetail(name);
    } catch (e: any) {
      console.error(e);
      solution = null;
      error = e?.message || $t('catalog.errorLoading');
    } finally {
      loading = false;
    }
  }
</script>

<svelte:head>
  <title>{solutionName ? `${solutionName} · ${$t('catalog.tabSolutions')}` : $t('catalog.tabSolutions')} · Daileon</title>
</svelte:head>

<GroupDetail
  kind="solution"
  icon={Boxes}
  eyebrow={$t('solutionDetail.eyebrow')}
  name={solution?.solution || solutionName}
  crossValues={solution?.domains || []}
  crossLabel={$t('catalog.tabDomains')}
  owners={solution?.owners || []}
  componentsCount={solution?.components_count || 0}
  components={solution?.components || []}
  {loading}
  {error}
/>
