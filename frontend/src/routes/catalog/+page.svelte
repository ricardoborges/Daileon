<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import {
    fetchCatalog,
    fetchDomains,
    fetchSolutions,
    type ComponentItem,
    type DomainItem,
    type SolutionItem
  } from '$lib/api';
  import CatalogCard from '$lib/components/CatalogCard.svelte';
  import CatalogTable from '$lib/components/CatalogTable.svelte';
  import EntityTabs from '$lib/components/EntityTabs.svelte';
  import GroupCard from '$lib/components/GroupCard.svelte';
  import GroupTable from '$lib/components/GroupTable.svelte';
  import ViewToggle from '$lib/components/ViewToggle.svelte';
  import {
    domainHref,
    loadViewMode,
    rememberEntity,
    resolveEntity,
    saveViewMode,
    solutionHref,
    type CatalogEntity,
    type ViewMode
  } from '$lib/catalogView';
  import { Layers, Boxes, FolderGit2, Search, X } from 'lucide-svelte';
  import { t } from '$lib/i18n';

  let entity: CatalogEntity = 'projects';
  let viewMode: ViewMode = 'cards';
  let ready = false;
  let searchInput: HTMLInputElement;

  let components: ComponentItem[] = [];
  let solutions: SolutionItem[] = [];
  let domains: DomainItem[] = [];

  // Uma flag de carga por entidade: trocar de aba não pode reexibir o
  // esqueleto de uma lista que já está em memória.
  let loading: Record<CatalogEntity, boolean> = { projects: false, solutions: false, domains: false };
  let loaded: Record<CatalogEntity, boolean> = { projects: false, solutions: false, domains: false };
  // O erro também é por entidade: uma carga de fundo que falha não pode
  // sobrepor a lista que o usuário está vendo.
  let errors: Partial<Record<CatalogEntity, string>> = {};

  let searchQuery = '';
  let selectedOwner = '';
  let selectedType = '';
  let selectedLifecycle = '';
  let selectedDomain = '';
  let selectedSolution = '';
  let selectedRisk = '';
  let selectedSort = 'activity_desc';

  const ENTITIES: CatalogEntity[] = ['projects', 'solutions', 'domains'];

  onMount(() => {
    entity = resolveEntity($page.url.searchParams.get('tab'));
    viewMode = loadViewMode(entity);
    if ($page.url.searchParams.get('has_risk') === 'true' || $page.url.searchParams.get('risk') === 'true') {
      selectedRisk = 'only';
    }
    ready = true;
    searchInput?.focus();
    // Os contadores das abas saem das próprias listas: carregamos as três já
    // na abertura para os números aparecerem sem precisar visitar cada aba.
    // A aba ativa vai primeiro para não disputar a rede com as de fundo.
    load(entity).then(() => {
      for (const other of ENTITIES) if (other !== entity) load(other);
    });
  });

  // A aba vive na URL: voltar pelo navegador e abrir um link compartilhado
  // precisam cair na mesma lista.
  $: if (ready) {
    const fromUrl = resolveEntity($page.url.searchParams.get('tab'));
    if (fromUrl !== entity) {
      entity = fromUrl;
      viewMode = loadViewMode(entity);
      load(entity);
    }
    if ($page.url.searchParams.get('has_risk') === 'true' || $page.url.searchParams.get('risk') === 'true') {
      selectedRisk = 'only';
    }
  }

  function selectEntity(next: CatalogEntity) {
    if (next === entity) return;
    rememberEntity(next);
    const url = new URL($page.url);
    url.searchParams.set('tab', next);
    goto(`${url.pathname}${url.search}`, { keepFocus: true, noScroll: true });
  }

  function setViewMode(mode: ViewMode) {
    viewMode = mode;
    saveViewMode(entity, mode);
  }

  async function load(target: CatalogEntity) {
    if (loaded[target] || loading[target]) return;
    loading = { ...loading, [target]: true };
    errors = { ...errors, [target]: undefined };
    try {
      if (target === 'projects') components = await fetchCatalog();
      else if (target === 'solutions') solutions = await fetchSolutions();
      else domains = await fetchDomains();
      loaded = { ...loaded, [target]: true };
    } catch (e: any) {
      console.error(e);
      errors = { ...errors, [target]: e?.message || $t('catalog.errorLoading') };
    } finally {
      loading = { ...loading, [target]: false };
    }
  }

  function clearFilters() {
    searchQuery = '';
    selectedOwner = '';
    selectedType = '';
    selectedLifecycle = '';
    selectedDomain = '';
    selectedSolution = '';
    selectedRisk = '';
    selectedSort = 'activity_desc';
  }

  // Trocar de aba não deve carregar filtros que não existem na nova lista.
  $: if (entity) clearFilters();

  $: isLoading = loading[entity];
  $: error = errors[entity];

  // --- Opções dos filtros, derivadas do que está carregado ---
  $: owners =
    entity === 'projects'
      ? Array.from(new Set(components.map((c) => c.owner))).filter(Boolean).sort()
      : entity === 'solutions'
        ? Array.from(new Set(solutions.flatMap((s) => s.owners))).sort()
        : Array.from(new Set(domains.flatMap((d) => d.owners))).sort();

  $: types = Array.from(new Set(components.map((c) => c.type))).filter(Boolean).sort();
  $: lifecycles = Array.from(new Set(components.map((c) => c.lifecycle))).filter(Boolean).sort();
  $: projectDomains = Array.from(new Set(components.map((c) => c.domain))).filter(Boolean).sort();
  $: projectSolutions = Array.from(new Set(components.map((c) => c.solution))).filter(Boolean).sort();
  $: solutionDomains = Array.from(new Set(solutions.flatMap((s) => s.domains))).sort();

  $: hasFilters = !!(
    searchQuery ||
    selectedOwner ||
    selectedType ||
    selectedLifecycle ||
    selectedDomain ||
    selectedSolution ||
    selectedRisk ||
    selectedSort !== 'activity_desc'
  );

  function matchesQuery(haystack: Array<string | null | undefined>, q: string) {
    return haystack.some((v) => (v || '').toLowerCase().includes(q));
  }

  // --- Projetos ---
  $: filteredProjects = components.filter((c) => {
    if (selectedOwner && c.owner !== selectedOwner) return false;
    if (selectedType && c.type !== selectedType) return false;
    if (selectedLifecycle && c.lifecycle !== selectedLifecycle) return false;
    if (selectedDomain && c.domain !== selectedDomain) return false;
    if (selectedSolution && c.solution !== selectedSolution) return false;
    if (selectedRisk === 'only') {
      const hasRisk =
        (c.critical_risks_count || 0) > 0 ||
        (c.warning_risks_count || 0) > 0 ||
        (c.risks && c.risks.length > 0);
      if (!hasRisk) return false;
    }
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      matchesQuery([c.name, c.description, c.domain, c.solution], q) ||
      (c.tags || []).some((tag) => tag.toLowerCase().includes(q))
    );
  });

  $: sortedProjects = [...filteredProjects].sort((a, b) => {
    const activity = (c: ComponentItem) => c.last_activity_at || c.updated_at || '';
    // Mesma precedência da exibição: idade real do código antes da data do repo.
    const created = (c: ComponentItem) => c.first_commit_at || c.gitlab_created_at || c.updated_at || '';
    if (selectedSort === 'activity_desc') return activity(b).localeCompare(activity(a));
    if (selectedSort === 'activity_asc') return activity(a).localeCompare(activity(b));
    if (selectedSort === 'name_asc') return a.name.localeCompare(b.name);
    if (selectedSort === 'name_desc') return b.name.localeCompare(a.name);
    if (selectedSort === 'created_desc') return created(b).localeCompare(created(a));
    if (selectedSort === 'created_asc') return created(a).localeCompare(created(b));
    if (selectedSort === 'manifest_desc') return (b.has_manifest ? 1 : 0) - (a.has_manifest ? 1 : 0);
    if (selectedSort === 'lifecycle_desc') {
      const order: Record<string, number> = { production: 3, experimental: 2, deprecated: 1 };
      return (order[b.lifecycle.toLowerCase()] || 0) - (order[a.lifecycle.toLowerCase()] || 0);
    }
    return 0;
  });

  // --- Soluções ---
  $: filteredSolutions = solutions.filter((s) => {
    if (selectedOwner && !s.owners.includes(selectedOwner)) return false;
    if (selectedDomain && !s.domains.includes(selectedDomain)) return false;
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      matchesQuery([s.solution, ...s.domains, ...s.owners], q) ||
      s.components.some((c) => matchesQuery([c.name, c.description, c.owner], q))
    );
  });

  // --- Domínios ---
  $: filteredDomains = domains.filter((d) => {
    if (selectedOwner && !d.owners.includes(selectedOwner)) return false;
    if (selectedSolution && !d.solutions.includes(selectedSolution)) return false;
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      matchesQuery([d.domain, ...d.solutions, ...d.owners], q) ||
      d.components.some((c) => matchesQuery([c.name, c.description, c.owner, c.solution], q))
    );
  });

  $: domainSolutionOptions = Array.from(new Set(domains.flatMap((d) => d.solutions))).sort();

  $: shown =
    entity === 'projects'
      ? sortedProjects.length
      : entity === 'solutions'
        ? filteredSolutions.length
        : filteredDomains.length;

  $: total =
    entity === 'projects' ? components.length : entity === 'solutions' ? solutions.length : domains.length;

  $: counts = {
    projects: loaded.projects ? components.length : undefined,
    solutions: loaded.solutions ? solutions.length : undefined,
    domains: loaded.domains ? domains.length : undefined
  };

  $: solutionRows = filteredSolutions.map((s) => ({
    name: s.solution,
    href: solutionHref(s.solution),
    crossValues: s.domains,
    owners: s.owners,
    componentsCount: s.components_count
  }));

  $: domainRows = filteredDomains.map((d) => ({
    name: d.domain,
    href: domainHref(d.domain),
    crossValues: d.solutions,
    owners: d.owners,
    componentsCount: d.components_count
  }));

  $: emptyTitle =
    entity === 'projects'
      ? $t('catalog.emptyTitle')
      : entity === 'solutions'
        ? $t('catalog.emptySolutionsTitle')
        : $t('catalog.emptyDomainsTitle');
</script>

<svelte:head>
  <title>{$t('catalog.title')} · Daileon</title>
</svelte:head>

<main class="max-w-7xl mx-auto px-6 py-10 space-y-8">
  <header class="space-y-3">
    <span class="eyebrow">{$t('catalog.eyebrow')}</span>
    <div class="rule">
      <h1 class="text-3xl font-bold tracking-[-0.03em] t-txt flex items-center gap-3 whitespace-nowrap">
        <Layers class="w-7 h-7 t-visor" /> {$t('catalog.title')}
      </h1>
    </div>
    <p class="t-dim text-sm">{$t('catalog.subtitle')}</p>
  </header>

  <!-- Passo 1: o que listar -->
  <section class="space-y-3">
    <span class="label block">{$t('catalog.step1')}</span>
    <EntityTabs value={entity} {counts} onSelect={selectEntity} />
  </section>

  <!-- Passo 2: filtrar e escolher a visualização -->
  <div class="plate plate-deep p-5" style="--chamfer: 14px;">
    <div class="flex flex-wrap items-end gap-4">
      <div class="flex-1 min-w-[220px] space-y-1.5">
        <label for="f-query" class="label block">{$t('catalog.filterQuery')}</label>
        <div class="relative">
          <Search class="w-3.5 h-3.5 t-faint absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            id="f-query"
            type="text"
            bind:this={searchInput}
            bind:value={searchQuery}
            placeholder={$t('catalog.filterQueryPlaceholder')}
            class="field font-mono pl-9"
          />
        </div>
      </div>

      <div class="space-y-1.5">
        <label for="f-owner" class="label block">{$t('catalog.filterTeam')}</label>
        <select id="f-owner" bind:value={selectedOwner} class="field">
          <option value="">{$t('catalog.filterAll')}</option>
          {#each owners as owner}<option value={owner}>{owner}</option>{/each}
        </select>
      </div>

      {#if entity === 'projects'}
        <div class="space-y-1.5">
          <label for="f-type" class="label block">{$t('catalog.filterType')}</label>
          <select id="f-type" bind:value={selectedType} class="field">
            <option value="">{$t('catalog.filterAll')}</option>
            {#each types as type}<option value={type}>{type}</option>{/each}
          </select>
        </div>

        <div class="space-y-1.5">
          <label for="f-lifecycle" class="label block">{$t('catalog.filterLifecycle')}</label>
          <select id="f-lifecycle" bind:value={selectedLifecycle} class="field">
            <option value="">{$t('catalog.filterAll')}</option>
            {#each lifecycles as lc}<option value={lc}>{lc}</option>{/each}
          </select>
        </div>

        <div class="space-y-1.5">
          <label for="f-domain" class="label block">{$t('catalog.filterDomain')}</label>
          <select id="f-domain" bind:value={selectedDomain} class="field">
            <option value="">{$t('catalog.filterAll')}</option>
            {#each projectDomains as d}<option value={d}>{d}</option>{/each}
          </select>
        </div>

        <div class="space-y-1.5">
          <label for="f-solution" class="label block">{$t('catalog.filterSolution')}</label>
          <select id="f-solution" bind:value={selectedSolution} class="field">
            <option value="">{$t('catalog.filterAll')}</option>
            {#each projectSolutions as s}<option value={s}>{s}</option>{/each}
          </select>
        </div>

        <div class="space-y-1.5">
          <label for="f-risk" class="label block">{$t('catalog.filterRisks')}</label>
          <select id="f-risk" bind:value={selectedRisk} class="field font-semibold {selectedRisk === 'only' ? 'text-amber-500 border-amber-500/50' : ''}">
            <option value="">{$t('catalog.filterRisksAll')}</option>
            <option value="only">{$t('catalog.filterRisksOnly')}</option>
          </select>
        </div>

        <div class="space-y-1.5">
          <label for="f-sort" class="label block">{$t('catalog.filterSort')}</label>
          <select id="f-sort" bind:value={selectedSort} class="field font-semibold">
            <option value="activity_desc">{$t('catalog.sortActivityDesc')}</option>
            <option value="activity_asc">{$t('catalog.sortActivityAsc')}</option>
            <option value="name_asc">{$t('catalog.sortNameAsc')}</option>
            <option value="name_desc">{$t('catalog.sortNameDesc')}</option>
            <option value="created_desc">{$t('catalog.sortCreatedDesc')}</option>
            <option value="created_asc">{$t('catalog.sortCreatedAsc')}</option>
            <option value="manifest_desc">{$t('catalog.sortManifestDesc')}</option>
            <option value="lifecycle_desc">{$t('catalog.sortLifecycleDesc')}</option>
          </select>
        </div>
      {:else if entity === 'solutions'}
        <div class="space-y-1.5">
          <label for="f-sol-domain" class="label block">{$t('catalog.filterDomain')}</label>
          <select id="f-sol-domain" bind:value={selectedDomain} class="field">
            <option value="">{$t('catalog.filterAll')}</option>
            {#each solutionDomains as d}<option value={d}>{d}</option>{/each}
          </select>
        </div>
      {:else}
        <div class="space-y-1.5">
          <label for="f-dom-solution" class="label block">{$t('catalog.filterSolution')}</label>
          <select id="f-dom-solution" bind:value={selectedSolution} class="field">
            <option value="">{$t('catalog.filterAll')}</option>
            {#each domainSolutionOptions as s}<option value={s}>{s}</option>{/each}
          </select>
        </div>
      {/if}

      {#if hasFilters}
        <button on:click={clearFilters} class="btn btn-sm">
          <X class="w-3 h-3" /> {$t('catalog.clearFilters')}
        </button>
      {/if}
    </div>

    <div class="mt-4 pt-4 border-t border-line flex flex-wrap items-center justify-between gap-4">
      <div class="flex items-center gap-4">
        <span class="label flex items-center gap-2">
          <span class="led {isLoading ? 'led-crest' : 'led-ok'}"></span>
          {isLoading ? $t('catalog.loading') : $t('catalog.ready')}
        </span>
        <span class="label">{$t('catalog.showingCount', { shown, total })}</span>
      </div>
      <ViewToggle value={viewMode} onSelect={setViewMode} />
    </div>
  </div>

  <!-- Passo 3: a lista -->
  {#if isLoading}
    {#if viewMode === 'cards'}
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {#each Array(6) as _}<div class="skeleton h-56"></div>{/each}
      </div>
    {:else}
      <div class="plate plate-deep p-6 space-y-3" style="--chamfer: 14px;">
        {#each Array(5) as _}<div class="skeleton h-10 w-full"></div>{/each}
      </div>
    {/if}
  {:else if error}
    <div class="plate p-12 text-center space-y-3">
      <h3 class="text-lg font-bold t-txt">{$t('catalog.errorLoading')}</h3>
      <p class="t-dim text-sm">{error}</p>
    </div>
  {:else if shown === 0}
    <div class="plate p-20 text-center space-y-4">
      <Layers class="w-10 h-10 mx-auto t-faint" />
      <h3 class="text-lg font-bold t-txt">{emptyTitle}</h3>
      <p class="t-dim text-sm max-w-sm mx-auto">
        {$t('catalog.emptySub')}
        <a href="/config" class="t-visor underline underline-offset-2">{$t('nav.config')}</a>.
      </p>
    </div>
  {:else if entity === 'projects'}
    {#if viewMode === 'cards'}
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {#each sortedProjects as item (item.id)}
          <CatalogCard {item} />
        {/each}
      </div>
    {:else}
      <CatalogTable items={sortedProjects} />
    {/if}
  {:else if entity === 'solutions'}
    {#if viewMode === 'cards'}
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {#each filteredSolutions as solution (solution.solution)}
          <GroupCard
            name={solution.solution}
            href={solutionHref(solution.solution)}
            icon={Boxes}
            components={solution.components}
            componentsCount={solution.components_count}
            owners={solution.owners}
            crossValues={solution.domains}
            crossLabel={$t('catalog.tabDomains')}
            groupBy="domain"
          />
        {/each}
      </div>
    {:else}
      <GroupTable
        rows={solutionRows}
        icon={Boxes}
        nameLabel={$t('catalog.colSolution')}
        crossLabel={$t('catalog.tabDomains')}
      />
    {/if}
  {:else if viewMode === 'cards'}
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {#each filteredDomains as domain (domain.domain)}
        <GroupCard
          name={domain.domain}
          href={domainHref(domain.domain)}
          icon={FolderGit2}
          components={domain.components}
          componentsCount={domain.components_count}
          owners={domain.owners}
          crossValues={domain.solutions}
          crossLabel={$t('domains.colSolutions')}
          groupBy="solution"
        />
      {/each}
    </div>
  {:else}
    <GroupTable
      rows={domainRows}
      icon={FolderGit2}
      nameLabel={$t('domains.colDomain')}
      crossLabel={$t('domains.colSolutions')}
    />
  {/if}
</main>
