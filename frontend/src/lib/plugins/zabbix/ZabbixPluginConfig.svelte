<script lang="ts">
  import { onMount } from 'svelte';
  import { getAuthHeader } from '$lib/auth';
  import { t } from '$lib/i18n';
  import { Activity, CheckCircle2, AlertTriangle, RotateCw, Save, Server, Key, Lock, RefreshCw } from 'lucide-svelte';

  let url = '';
  let api_token = '';
  let username = '';
  let password = '';
  let cache_ttl = 30;
  let enabled = true;

  let loading = true;
  let saving = false;
  let testing = false;
  let testResult: { status: string; version?: string; message?: string } | null = null;
  let statusMessage: { type: 'success' | 'error'; text: string } | null = null;

  async function loadConfig() {
    loading = true;
    try {
      const res = await fetch('/api/plugins/zabbix/config', {
        headers: { ...getAuthHeader() }
      });
      if (res.ok) {
        const data = await res.json();
        url = data.url || '';
        api_token = data.api_token || '';
        username = data.username || '';
        password = data.password || '';
        cache_ttl = data.cache_ttl || 30;
        enabled = data.enabled ?? true;
      }
    } catch (e) {
      console.error(e);
    } finally {
      loading = false;
    }
  }

  async function handleSave() {
    saving = true;
    statusMessage = null;
    try {
      const res = await fetch('/api/plugins/zabbix/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
        body: JSON.stringify({
          url,
          api_token,
          username,
          password,
          cache_ttl: Number(cache_ttl),
          enabled
        })
      });
      if (res.ok) {
        statusMessage = { type: 'success', text: $t('plugins.zabbix.saveSuccess') };
      } else {
        const err = await res.json();
        statusMessage = { type: 'error', text: err.detail || $t('plugins.zabbix.saveError') };
      }
    } catch (e: any) {
      statusMessage = { type: 'error', text: e.message || $t('plugins.zabbix.saveError') };
    } finally {
      saving = false;
    }
  }

  async function handleTest() {
    testing = true;
    testResult = null;
    try {
      const res = await fetch('/api/plugins/zabbix/status', {
        headers: { ...getAuthHeader() }
      });
      if (res.ok) {
        testResult = await res.json();
      } else {
        const err = await res.json().catch(() => null);
        testResult = { status: 'error', message: err?.detail || 'HTTP Error' };
      }
    } catch (e: any) {
      testResult = { status: 'error', message: e.message };
    } finally {
      testing = false;
    }
  }

  onMount(() => {
    loadConfig();
  });
</script>

<div class="plate p-6 space-y-6" style="--chamfer: 16px;">
  <!-- Cabeçalho de Configuração -->
  <div class="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-line">
    <div class="flex items-center gap-3">
      <div class="p-2.5 rounded-xl bg-visor-wash t-visor border border-line">
        <Activity size={22} />
      </div>
      <div>
        <h3 class="text-base font-bold t-txt">{$t('plugins.zabbix.title')}</h3>
        <p class="text-xs t-dim">{$t('plugins.zabbix.subtitle')}</p>
      </div>
    </div>

    <label class="relative inline-flex items-center cursor-pointer">
      <input type="checkbox" bind:checked={enabled} class="sr-only peer" />
      <div class="w-11 h-6 bg-surface-3 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[var(--visor)]"></div>
      <span class="ml-3 label font-bold t-txt">{enabled ? $t('plugins.zabbix.enabled') : $t('plugins.zabbix.disabled')}</span>
    </label>
  </div>

  {#if loading}
    <div class="p-8 text-center t-dim flex items-center justify-center gap-2 font-mono text-xs">
      <RotateCw size={18} class="animate-spin t-visor" />
      {$t('plugins.zabbix.loading')}
    </div>
  {:else}
    <div class="space-y-5">
      <div>
        <label for="zabbix-url" class="field-label mb-1.5">{$t('plugins.zabbix.url')}</label>
        <div class="relative">
          <Server size={16} class="absolute left-3 top-3 t-faint" />
          <input
            id="zabbix-url"
            type="text"
            bind:value={url}
            placeholder="https://zabbix.suaempresa.com"
            class="field field-mono pl-9"
          />
        </div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label for="zabbix-token" class="field-label mb-1.5">{$t('plugins.zabbix.apiToken')}</label>
          <div class="relative">
            <Key size={16} class="absolute left-3 top-3 t-faint" />
            <input
              id="zabbix-token"
              type="password"
              bind:value={api_token}
              placeholder="Ex: e78ae697..."
              class="field field-mono pl-9"
            />
          </div>
        </div>

        <div>
          <label for="zabbix-ttl" class="field-label mb-1.5">{$t('plugins.zabbix.cacheTtl')}</label>
          <div class="relative">
            <RefreshCw size={16} class="absolute left-3 top-3 t-faint" />
            <input
              id="zabbix-ttl"
              type="number"
              bind:value={cache_ttl}
              min="5"
              max="300"
              class="field field-mono pl-9"
            />
          </div>
        </div>
      </div>

      <div class="plate p-4 border border-line bg-surface-2/60 space-y-3" style="--chamfer: 10px;">
        <span class="label block t-faint">Legacy Authentication ({$t('plugins.zabbix.username')} &amp; {$t('plugins.zabbix.password')})</span>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <input
              type="text"
              bind:value={username}
              placeholder={$t('plugins.zabbix.username')}
              class="field field-mono"
            />
          </div>
          <div>
            <input
              type="password"
              bind:value={password}
              placeholder={$t('plugins.zabbix.password')}
              class="field field-mono"
            />
          </div>
        </div>
      </div>

      {#if statusMessage}
        <div class="chip {statusMessage.type === 'success' ? 'chip-ok' : 'chip-alert'} !w-full !whitespace-normal text-xs p-3 flex items-center gap-2">
          {#if statusMessage.type === 'success'}
            <CheckCircle2 size={16} />
          {:else}
            <AlertTriangle size={16} />
          {/if}
          <span>{statusMessage.text}</span>
        </div>
      {/if}

      {#if testResult}
        <div class="chip {testResult.status === 'connected' ? 'chip-visor' : 'chip-alert'} !w-full !whitespace-normal text-xs p-3 flex items-center justify-between">
          <div class="flex items-center gap-2">
            {#if testResult.status === 'connected'}
              <CheckCircle2 size={16} />
              <span>Connected to Zabbix (v<strong>{testResult.version}</strong>)</span>
            {:else}
              <AlertTriangle size={16} />
              <span>Connection failed: {testResult.message}</span>
            {/if}
          </div>
        </div>
      {/if}

      <div class="form-actions">
        <button
          type="button"
          on:click={handleTest}
          disabled={testing || !url}
          class="btn btn-sm btn-ghost flex items-center gap-1.5"
        >
          {#if testing}
            <RotateCw size={14} class="animate-spin" />
            <span>{$t('plugins.zabbix.testing')}</span>
          {:else}
            <RefreshCw size={14} />
            <span>{$t('plugins.zabbix.testConnection')}</span>
          {/if}
        </button>

        <button
          type="button"
          on:click={handleSave}
          disabled={saving}
          class="btn btn-primary flex items-center gap-1.5"
        >
          {#if saving}
            <RotateCw size={14} class="animate-spin" />
            <span>{$t('plugins.zabbix.loading')}</span>
          {:else}
            <Save size={14} />
            <span>{$t('plugins.zabbix.save')}</span>
          {/if}
        </button>
      </div>
    </div>
  {/if}
</div>
