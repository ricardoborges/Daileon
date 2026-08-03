<script lang="ts">
  import { page } from '$app/stores';
  import { fetchDomainDetail, type DomainItem } from '$lib/api';
  import GroupDetail from '$lib/components/GroupDetail.svelte';
  import { t } from '$lib/i18n';
  import { FolderGit2 } from 'lucide-svelte';

  let domain: DomainItem | null = null;
  let loading = true;
  let error: string | null = null;

  $: domainName = $page.params.name;
  $: if (domainName) load(domainName);

  async function load(name: string) {
    loading = true;
    error = null;
    try {
      domain = await fetchDomainDetail(name);
    } catch (e: any) {
      console.error(e);
      domain = null;
      error = e?.message || $t('catalog.errorLoading');
    } finally {
      loading = false;
    }
  }
</script>

<svelte:head>
  <title>{domainName ? `${domainName} · ${$t('catalog.tabDomains')}` : $t('catalog.tabDomains')} · Daileon</title>
</svelte:head>

<GroupDetail
  kind="domain"
  icon={FolderGit2}
  eyebrow={$t('domainDetail.eyebrow')}
  name={domain?.domain || domainName}
  crossValues={domain?.solutions || []}
  crossLabel={$t('domains.colSolutions')}
  owners={domain?.owners || []}
  componentsCount={domain?.components_count || 0}
  components={domain?.components || []}
  {loading}
  {error}
/>
