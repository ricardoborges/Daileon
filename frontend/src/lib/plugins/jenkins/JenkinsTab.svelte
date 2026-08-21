<script lang="ts">
  import { onMount } from 'svelte';
  import { fetchComponentJenkins, type JenkinsComponentResponse, type ComponentItem } from '$lib/api';
  import { t } from '$lib/i18n';
  import {
    Server,
    Activity,
    RotateCw,
    CheckCircle2,
    XCircle,
    PlayCircle,
    AlertTriangle,
    Clock,
    ExternalLink
  } from 'lucide-svelte';

  export let component: ComponentItem;

  let jenkinsData: JenkinsComponentResponse | null = null;
  let loadingJenkins = false;

  async function loadJenkinsData() {
    if (!component?.id) return;
    loadingJenkins = true;
    try {
      jenkinsData = await fetchComponentJenkins(component.id);
    } catch (e) {
      console.error('Error fetching Jenkins status:', e);
    } finally {
      loadingJenkins = false;
    }
  }

  onMount(() => {
    loadJenkinsData();
  });

  function envBadgeClass(env?: string): string {
    const e = env?.toLowerCase() || '';
    if (e.includes('prod')) return 'chip-alert';
    if (e.includes('stag') || e.includes('hml')) return 'chip-crest';
    return 'chip-ok';
  }

  function formatDuration(ms?: number): string {
    if (!ms) return '0s';
    const totalSec = Math.floor(ms / 1000);
    const min = Math.floor(totalSec / 60);
    const sec = totalSec % 60;
    if (min > 0) return `${min}m ${sec}s`;
    return `${sec}s`;
  }

  function formatTimeAgo(timestamp?: number): string {
    if (!timestamp) return '';
    const diffSec = Math.floor((Date.now() - timestamp) / 1000);
    if (diffSec < 60) return 'just now';
    if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
    if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
    return `${Math.floor(diffSec / 86400)}d ago`;
  }
</script>

<section class="space-y-6">
  <div class="flex flex-wrap items-center justify-between gap-4 plate p-5" style="--chamfer: 16px;">
    <div class="flex items-center gap-3">
      <Server class="w-5 h-5 t-visor" />
      <div>
        <h3 class="text-sm font-semibold t-txt">{$t('plugins.jenkins.title')}</h3>
        <p class="text-xs t-dim">
          {#if jenkinsData?.jenkins_token_configured}
            <span class="t-visor">{$t('plugins.jenkins.tokenActive')}</span>
          {:else}
            <span class="t-alert">{$t('plugins.jenkins.tokenMissing')}</span>
          {/if}
        </p>
      </div>
    </div>

    <button
      on:click={loadJenkinsData}
      disabled={loadingJenkins}
      class="btn btn-crest text-xs flex items-center gap-2"
    >
      <RotateCw class="w-3.5 h-3.5 {loadingJenkins ? 'animate-spin' : ''}" />
      {$t('plugins.jenkins.refresh')}
    </button>
  </div>

  {#if loadingJenkins && !jenkinsData}
    <div class="skeleton h-48"></div>
  {:else if !jenkinsData || jenkinsData.pipelines.length === 0}
    <div class="plate p-12 text-center space-y-3">
      <Activity class="w-8 h-8 mx-auto t-faint" />
      <h4 class="font-medium t-txt text-base">{$t('plugins.jenkins.noPipelines')}</h4>
      <p class="t-dim text-xs max-w-md mx-auto">
        {$t('plugins.jenkins.noPipelinesHint')}
      </p>
    </div>
  {:else}
    <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
      {#each jenkinsData.pipelines as pipe}
        {@const status = pipe.status_info.status}
        {@const build = pipe.status_info.last_build}

        <div class="plate p-6 space-y-5 flex flex-col justify-between" style="--chamfer: 16px;">
          <div class="space-y-4">
            <div class="flex items-start justify-between gap-3">
              <div class="space-y-1 min-w-0">
                <div class="flex items-center gap-2">
                  <span class="chip {envBadgeClass(pipe.environment)} uppercase text-[10px] tracking-wider font-semibold">
                    {pipe.environment}
                  </span>
                  <span class="font-mono text-xs opacity-75 t-faint truncate">{pipe.job}</span>
                </div>
                <h4 class="text-lg font-bold t-txt truncate">{pipe.name}</h4>
              </div>

              <div class="shrink-0">
                {#if status === 'SUCCESS'}
                  <span class="chip chip-ok flex items-center gap-1.5 px-3 py-1 font-semibold text-xs">
                    <CheckCircle2 class="w-4 h-4" /> {$t('plugins.jenkins.statusSuccess')}
                  </span>
                {:else if status === 'FAILURE'}
                  <span class="chip chip-alert flex items-center gap-1.5 px-3 py-1 font-semibold text-xs">
                    <XCircle class="w-4 h-4" /> {$t('plugins.jenkins.statusFailure')}
                  </span>
                {:else if status === 'BUILDING'}
                  <span class="chip chip-visor flex items-center gap-1.5 px-3 py-1 font-semibold text-xs animate-pulse">
                    <PlayCircle class="w-4 h-4 animate-spin" /> {$t('plugins.jenkins.statusBuilding')}
                  </span>
                {:else if status === 'UNSTABLE'}
                  <span class="chip chip-crest flex items-center gap-1.5 px-3 py-1 font-semibold text-xs">
                    <AlertTriangle class="w-4 h-4" /> {$t('plugins.jenkins.statusUnstable')}
                  </span>
                {:else}
                  <span class="chip flex items-center gap-1.5 px-3 py-1 font-semibold text-xs t-faint">
                    {status}
                  </span>
                {/if}
              </div>
            </div>

            {#if build}
              <div class="plate plate-deep p-4 space-y-3" style="--chamfer: 8px;">
                <div class="flex items-center justify-between text-xs border-b border-[var(--line)] pb-2">
                  <span class="font-mono font-bold t-visor">{build.display_name}</span>
                  <span class="t-dim flex items-center gap-1">
                    <Clock class="w-3 h-3" /> {formatTimeAgo(build.timestamp)}
                  </span>
                </div>

                <div class="grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <span class="t-faint block text-[11px]">Duration:</span>
                    <span class="t-txt font-semibold">{formatDuration(build.duration_ms)}</span>
                  </div>
                  {#if build.branch}
                    <div>
                      <span class="t-faint block text-[11px]">Branch:</span>
                      <span class="t-txt font-mono font-semibold">{build.branch}</span>
                    </div>
                  {/if}
                </div>

                {#if build.causes && build.causes.length > 0}
                  <div class="text-[11px] t-faint truncate pt-2 border-t border-[var(--line)]">
                    Trigger: <span class="t-txt font-medium">{build.causes[0]}</span>
                  </div>
                {/if}
              </div>
            {:else if pipe.status_info.message}
              <div class="text-xs t-alert bg-alert-wash border border-line rounded p-3">
                {pipe.status_info.message}
              </div>
            {/if}
          </div>

          <div class="pt-2 flex items-center justify-between border-t border-line">
            <span class="text-xs t-faint">Jenkins REST API</span>
            {#if pipe.status_info.job_url || build?.url}
              <a
                href={build?.url || pipe.status_info.job_url}
                target="_blank"
                rel="noopener noreferrer"
                class="btn btn-crest text-xs py-1.5 px-3 flex items-center gap-1.5"
              >
                {$t('catalog.jenkins_open')} <ExternalLink class="w-3 h-3" />
              </a>
            {/if}
          </div>
        </div>
      {/each}
    </div>
  {/if}
</section>
