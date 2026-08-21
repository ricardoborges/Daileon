<script lang="ts">
  import { onMount } from 'svelte';
  import { fetchJenkinsConfig, saveJenkinsConfig, testJenkinsConfig, type JenkinsConfig } from '$lib/api';
  import { PlayCircle, CheckCircle2, AlertTriangle, RotateCw, Save, Server, User, Key } from 'lucide-svelte';
  import { t } from '$lib/i18n';

  let config: JenkinsConfig = {
    url: 'https://jenkins.example.com',
    user: '',
    api_token: '',
    enabled: true
  };

  let loading = true;
  let saving = false;
  let testing = false;
  let statusMessage: { type: 'success' | 'error'; text: string } | null = null;

  async function loadConfig() {
    loading = true;
    try {
      const res = await fetchJenkinsConfig();
      if (res) {
        config = { ...config, ...res };
      }
    } catch (e) {
      console.error('Failed to load Jenkins config:', e);
    } finally {
      loading = false;
    }
  }

  async function handleSave() {
    saving = true;
    statusMessage = null;
    try {
      const res = await saveJenkinsConfig(config);
      statusMessage = { type: 'success', text: res.message || $t('plugins.jenkins.saveSuccess') };
    } catch (e: any) {
      statusMessage = { type: 'error', text: e.message || $t('plugins.jenkins.saveError') };
    } finally {
      saving = false;
    }
  }

  async function handleTest() {
    testing = true;
    statusMessage = null;
    try {
      const res = await testJenkinsConfig(config);
      if (res.success) {
        statusMessage = { type: 'success', text: res.message };
      } else {
        statusMessage = { type: 'error', text: res.message };
      }
    } catch (e: any) {
      statusMessage = { type: 'error', text: e.message || $t('plugins.jenkins.testError') };
    } finally {
      testing = false;
    }
  }

  onMount(() => {
    loadConfig();
  });
</script>

<div class="plate p-6 space-y-6" style="--chamfer: 16px;">
  <div class="flex items-center justify-between pb-4 border-b border-line">
    <div class="flex items-center gap-3">
      <PlayCircle class="w-6 h-6 t-visor" />
      <div>
        <h3 class="text-base font-bold t-txt">{$t('plugins.jenkins.title')}</h3>
        <p class="text-xs t-dim">{$t('plugins.jenkins.subtitle')}</p>
      </div>
    </div>
    <span class="chip chip-visor text-xs font-mono font-bold">{$t('plugins.builtin')}</span>
  </div>

  {#if loading}
    <div class="skeleton h-48"></div>
  {:else}
    {#if statusMessage}
      <div
        class="p-4 rounded-lg text-xs font-medium flex items-center gap-2 border {statusMessage.type === 'success'
          ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
          : 'bg-red-500/10 text-red-400 border-red-500/30'}"
      >
        {#if statusMessage.type === 'success'}
          <CheckCircle2 class="w-4 h-4 shrink-0" />
        {:else}
          <AlertTriangle class="w-4 h-4 shrink-0" />
        {/if}
        <span>{statusMessage.text}</span>
      </div>
    {/if}

    <form on:submit|preventDefault={handleSave} class="space-y-5 text-xs">
      <div class="flex items-center gap-3">
        <input
          type="checkbox"
          id="jenkins_enabled"
          bind:checked={config.enabled}
          class="rounded bg-surface-3 border-line text-visor focus:ring-visor"
        />
        <label for="jenkins_enabled" class="t-txt font-semibold cursor-pointer">
          {$t('plugins.jenkins.enable')}
        </label>
      </div>

      <div class="space-y-4 pt-2">
        <div>
          <label for="jenkins_url" class="block t-faint font-semibold mb-1">
            <Server class="w-3.5 h-3.5 inline mr-1" /> {$t('plugins.jenkins.url')}
          </label>
          <input
            type="text"
            id="jenkins_url"
            bind:value={config.url}
            placeholder="https://jenkins.empresa.com"
            class="input w-full font-mono"
            required
          />
          <p class="t-dim text-[11px] mt-1">{$t('plugins.jenkins.urlHint')}</p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label for="jenkins_user" class="block t-faint font-semibold mb-1">
              <User class="w-3.5 h-3.5 inline mr-1" /> {$t('plugins.jenkins.user')}
            </label>
            <input
              type="text"
              id="jenkins_user"
              bind:value={config.user}
              placeholder="daileon-bot"
              class="input w-full font-mono"
            />
          </div>

          <div>
            <label for="jenkins_api_token" class="block t-faint font-semibold mb-1">
              <Key class="w-3.5 h-3.5 inline mr-1" /> {$t('plugins.jenkins.token')}
            </label>
            <input
              type="password"
              id="jenkins_api_token"
              bind:value={config.api_token}
              placeholder="11xxxxxxxxxxxxxxxxxxxxxxxxxxxx"
              class="input w-full font-mono"
            />
          </div>
        </div>
      </div>

      <div class="flex items-center gap-3 pt-4 border-t border-line justify-end">
        <button
          type="button"
          on:click={handleTest}
          disabled={testing}
          class="btn btn-crest text-xs flex items-center gap-2"
        >
          <RotateCw class="w-3.5 h-3.5 {testing ? 'animate-spin' : ''}" />
          {$t('plugins.jenkins.test')}
        </button>

        <button
          type="submit"
          disabled={saving}
          class="btn btn-visor text-xs flex items-center gap-2"
        >
          <Save class="w-3.5 h-3.5" />
          {$t('plugins.jenkins.save')}
        </button>
      </div>
    </form>
  {/if}
</div>
