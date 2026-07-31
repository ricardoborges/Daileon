<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { fetchComponent, fetchComponentDocs, type ComponentItem, type DocFileItem } from '$lib/api';
  import { BookOpen, ExternalLink, ShieldAlert, GitBranch, ArrowLeft, Link2, Box, Layers } from 'lucide-svelte';

  let component: ComponentItem | null = null;
  let docs: DocFileItem[] = [];
  let loading = true;
  let activeTab: 'overview' | 'docs' = 'overview';

  $: componentId = parseInt($page.params.id);

  onMount(async () => {
    try {
      [component, docs] = await Promise.all([
        fetchComponent(componentId),
        fetchComponentDocs(componentId)
      ]);
    } catch (e) {
      console.error(e);
    } finally {
      loading = false;
    }
  });

  function lifecycleLed(lifecycle: string) {
    switch ((lifecycle || '').toLowerCase()) {
      case 'production': return 'led-ok';
      case 'experimental': return 'led-crest';
      case 'deprecated': return 'led-alert';
      default: return '';
    }
  }
</script>

<main class="max-w-7xl mx-auto px-6 py-10 space-y-8">
  <a href="/catalog" class="label inline-flex items-center gap-2 hover:t-visor transition-colors">
    <ArrowLeft class="w-3.5 h-3.5" /> Voltar ao catálogo
  </a>

  {#if loading}
    <div class="skeleton h-64"></div>
  {:else if !component}
    <div class="plate p-20 text-center space-y-4">
      <ShieldAlert class="w-10 h-10 mx-auto t-alert" />
      <h2 class="text-xl font-bold t-txt">Componente não encontrado</h2>
    </div>
  {:else}
    <!-- ===== Ficha técnica ===== -->
    <section class="plate plate-deep overflow-hidden" style="--chamfer: 24px;">
      <div class="absolute inset-0 grid-mesh opacity-60 pointer-events-none"></div>

      <div class="relative p-8 space-y-7">
        <div class="flex flex-wrap items-start justify-between gap-5">
          <div class="space-y-3 min-w-0">
            <div class="flex flex-wrap items-center gap-2">
              <span class="chip chip-visor">{component.type}</span>
              <span class="chip">
                <span class="led {lifecycleLed(component.lifecycle)}"></span>
                {component.lifecycle}
              </span>
              {#if component.has_manifest}
                <span class="chip chip-crest">project-info.yml</span>
              {/if}
            </div>

            <h1 class="text-3xl md:text-4xl font-bold tracking-[-0.035em] t-txt">
              {component.name}
            </h1>

            <p class="t-dim text-sm max-w-2xl leading-relaxed">
              {component.description || 'Sem descrição cadastrada.'}
            </p>
          </div>

          {#if component.gitlab_url}
            <a href={component.gitlab_url} target="_blank" rel="noopener noreferrer" class="btn btn-crest shrink-0">
              <GitBranch class="w-3.5 h-3.5" /> Repositório
              <ExternalLink class="w-3 h-3" />
            </a>
          {/if}
        </div>

        <!-- Leituras -->
        <dl class="grid grid-cols-2 lg:grid-cols-4 gap-y-5 gap-x-4 pt-6 border-t border-line">
          <div class="meta">
            <dt>Owner / Time</dt>
            <dd>{component.owner}</dd>
          </div>
          <div class="meta">
            <dt>Lifecycle</dt>
            <dd class="flex items-center gap-2">
              <span class="led {lifecycleLed(component.lifecycle)}"></span>
              {component.lifecycle}
            </dd>
          </div>
          <div class="meta">
            <dt>Domínio / Sistema</dt>
            <dd>{component.domain || '—'} / {component.system || '—'}</dd>
          </div>
          <div class="meta">
            <dt>Manifesto</dt>
            <dd class={component.has_manifest ? 't-visor' : 't-faint'}>
              {component.has_manifest ? 'project-info.yml ativo' : 'Fallback sintético'}
            </dd>
          </div>
        </dl>

        <!-- Abas -->
        <div class="seg">
          <button on:click={() => activeTab = 'overview'} class="seg-item {activeTab === 'overview' ? 'is-active' : ''}">
            <Layers class="w-3 h-3" /> Visão geral
          </button>
          <button on:click={() => activeTab = 'docs'} class="seg-item {activeTab === 'docs' ? 'is-active' : ''}">
            <BookOpen class="w-3 h-3" /> TechDocs ({docs.length})
          </button>
        </div>
      </div>
    </section>

    <!-- ===== Conteúdo ===== -->
    {#if activeTab === 'overview'}
      <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
        <!-- Links -->
        <section class="plate p-6 space-y-4" style="--chamfer: 16px;">
          <h3 class="label label-visor flex items-center gap-2">
            <Link2 class="w-3.5 h-3.5" /> Links &amp; recursos
          </h3>

          {#if component.links.length === 0}
            <p class="t-faint text-[13px]">Nenhum link registrado no project-info.yml.</p>
          {:else}
            <ul class="divide-y" style="border-color: var(--line);">
              {#each component.links as link}
                <li>
                  <a
                    href={link.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    class="flex items-center justify-between gap-3 py-3 text-sm t-dim hover:t-visor transition-colors group"
                  >
                    <span class="truncate">{link.title}</span>
                    <ExternalLink class="w-3.5 h-3.5 shrink-0 opacity-50 group-hover:opacity-100" />
                  </a>
                </li>
              {/each}
            </ul>
          {/if}
        </section>

        <!-- Dependências -->
        <section class="plate p-6 space-y-4" style="--chamfer: 16px;">
          <h3 class="label label-visor flex items-center gap-2">
            <Box class="w-3.5 h-3.5" /> Dependências diretas
          </h3>

          {#if component.dependencies.length === 0}
            <p class="t-faint text-[13px]">Nenhuma dependência registrada.</p>
          {:else}
            <ul class="flex flex-wrap gap-2">
              {#each component.dependencies as dep}
                <li class="tag">{dep}</li>
              {/each}
            </ul>
          {/if}
        </section>
      </div>
    {:else}
      <section class="plate p-6" style="--chamfer: 16px;">
        {#if docs.length === 0}
          <p class="t-faint text-[13px]">Nenhum documento encontrado neste repositório.</p>
        {:else}
          <ul class="space-y-1">
            {#each docs as doc}
              <li>
                <a href={`/catalog/${component.id}/docs/${doc.relative_path}`} class="toc-link">
                  <span class="truncate">{doc.title}</span>
                  <span class="label truncate">{doc.relative_path}</span>
                </a>
              </li>
            {/each}
          </ul>
        {/if}
      </section>
    {/if}
  {/if}
</main>
