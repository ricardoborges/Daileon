<script lang="ts">
  import { onMount } from 'svelte';
  import {
    fetchPortainerConfig,
    savePortainerConfig,
    testPortainerConfig,
    type PortainerServer
  } from '$lib/api';
  import { t } from '$lib/i18n';
  import {
    Activity,
    CheckCircle2,
    AlertTriangle,
    RotateCw,
    Save,
    Server,
    Key,
    User,
    Plus,
    Trash2
  } from 'lucide-svelte';

  type Row = PortainerServer & {
    _key: number;
    _authMode: 'api_key' | 'user_pass';
    _testing: boolean;
    _test: { ok: boolean; text: string } | null;
  };

  let rows: Row[] = [];
  let loading = true;
  let saving = false;
  let statusMessage: { type: 'success' | 'error'; text: string } | null = null;

  let nextKey = 1;

  function toRow(s: PortainerServer): Row {
    return {
      ...s,
      _key: nextKey++,
      _authMode: s.username || s.password ? 'user_pass' : 'api_key',
      _testing: false,
      _test: null
    };
  }

  function blankServer(): Row {
    return toRow({
      name: `Portainer ${rows.length + 1}`,
      url: '',
      api_key: '',
      username: '',
      password: '',
      enabled: true
    });
  }

  function toPayload(r: Row): PortainerServer {
    return {
      id: r.id,
      name: r.name,
      url: r.url,
      api_key: r.api_key || '',
      username: r.username || '',
      password: r.password || '',
      enabled: r.enabled
    };
  }

  async function loadConfig() {
    loading = true;
    try {
      const res = await fetchPortainerConfig();
      rows = (res?.servers ?? []).map(toRow);
    } catch (e) {
      console.error('Failed to load Portainer config:', e);
    } finally {
      loading = false;
    }
  }

  function addServer() {
    rows = [...rows, blankServer()];
  }

  function removeServer(key: number) {
    rows = rows.filter((r) => r._key !== key);
  }

  async function handleSave() {
    saving = true;
    statusMessage = null;
    try {
      const res = await savePortainerConfig({ servers: rows.map(toPayload) });
      rows = (res.servers ?? []).map(toRow);
      statusMessage = {
        type: 'success',
        text: res.message || $t('plugins.portainer.saveSuccess')
      };
    } catch (e: any) {
      statusMessage = { type: 'error', text: e.message || $t('plugins.portainer.saveError') };
    } finally {
      saving = false;
    }
  }

  async function handleTest(row: Row) {
    row._testing = true;
    row._test = null;
    rows = rows;
    try {
      const res = await testPortainerConfig(toPayload(row));
      const extra = res.endpoints_count !== undefined ? ` (${res.endpoints_count} envs)` : '';
      row._test = { ok: res.success, text: `${res.message}${extra}` };
    } catch (e: any) {
      row._test = { ok: false, text: e.message || 'Error testing connection.' };
    } finally {
      row._testing = false;
      rows = rows;
    }
  }

  onMount(() => {
    loadConfig();
  });
</script>

<div class="plate p-6 space-y-6" style="--chamfer: 16px;">
  <div class="flex items-center justify-between pb-4 border-b border-line">
    <div class="flex items-center gap-3">
      <Activity class="w-6 h-6 t-visor" />
      <div>
        <h3 class="text-base font-bold t-txt">{$t('plugins.portainer.title')}</h3>
        <p class="text-xs t-dim">
          {$t('plugins.portainer.subtitle')}
        </p>
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
      {#if rows.length === 0}
        <div class="plate plate-deep p-8 text-center space-y-3">
          <Server class="w-8 h-8 t-dim mx-auto" />
          <p class="t-dim">{$t('plugins.portainer.noContainers')}</p>
          <button type="button" on:click={addServer} class="btn btn-visor text-xs inline-flex items-center gap-2">
            <Plus class="w-3.5 h-3.5" /> {$t('plugins.portainer.addServer')}
          </button>
        </div>
      {/if}

      {#each rows as row (row._key)}
        <div class="plate plate-deep p-5 space-y-4">
          <div class="flex items-center justify-between gap-3 pb-3 border-b border-line">
            <div class="flex items-center gap-3 flex-1 min-w-0">
              <input
                type="checkbox"
                id="enabled_{row._key}"
                bind:checked={row.enabled}
                class="rounded bg-surface-3 border-line text-visor focus:ring-visor shrink-0"
              />
              <input
                type="text"
                bind:value={row.name}
                placeholder={$t('plugins.portainer.serverName')}
                aria-label={$t('plugins.portainer.serverName')}
                class="input font-semibold flex-1 min-w-0"
                required
              />
              {#if row.id}
                <span class="chip text-[10px] font-mono t-dim shrink-0">
                  {row.id}
                </span>
              {:else}
                <span class="chip chip-crest text-[10px] font-mono shrink-0">new</span>
              {/if}
            </div>
            <button
              type="button"
              on:click={() => removeServer(row._key)}
              class="btn btn-sm btn-ghost text-xs flex items-center gap-1.5 shrink-0"
            >
              <Trash2 class="w-3.5 h-3.5" /> {$t('plugins.portainer.removeServer')}
            </button>
          </div>

          <div>
            <label for="url_{row._key}" class="block t-faint font-semibold mb-1">
              <Server class="w-3.5 h-3.5 inline mr-1" /> {$t('plugins.portainer.serverUrl')}
            </label>
            <input
              type="text"
              id="url_{row._key}"
              bind:value={row.url}
              placeholder="http://portainer.empresa.com:9000"
              class="input w-full font-mono"
              required
            />
          </div>

          <div class="space-y-2">
            <span class="block t-faint font-semibold">{$t('plugins.portainer.authMode')}</span>
            <div class="seg">
              <button
                type="button"
                class="seg-item cursor-pointer {row._authMode === 'api_key' ? 'is-active' : ''}"
                on:click={() => (row._authMode = 'api_key')}
              >
                <Key class="w-3.5 h-3.5" /> {$t('plugins.portainer.apiKey')}
              </button>
              <button
                type="button"
                class="seg-item cursor-pointer {row._authMode === 'user_pass' ? 'is-active' : ''}"
                on:click={() => (row._authMode = 'user_pass')}
              >
                <User class="w-3.5 h-3.5" /> {$t('plugins.portainer.username')} &amp; {$t('plugins.portainer.password')}
              </button>
            </div>
          </div>

          {#if row._authMode === 'api_key'}
            <div>
              <label for="api_key_{row._key}" class="block t-faint font-semibold mb-1">
                {$t('plugins.portainer.apiKey')}
              </label>
              <input
                type="password"
                id="api_key_{row._key}"
                bind:value={row.api_key}
                placeholder="ptr_..."
                class="input w-full font-mono"
              />
            </div>
          {:else}
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label for="user_{row._key}" class="block t-faint font-semibold mb-1">{$t('plugins.portainer.username')}</label>
                <input type="text" id="user_{row._key}" bind:value={row.username} placeholder="admin" class="input w-full" />
              </div>
              <div>
                <label for="pass_{row._key}" class="block t-faint font-semibold mb-1">{$t('plugins.portainer.password')}</label>
                <input type="password" id="pass_{row._key}" bind:value={row.password} placeholder="******" class="input w-full" />
              </div>
            </div>
          {/if}

          {#if row._test}
            <div
              class="p-3 rounded-lg text-[11px] font-medium flex items-center gap-2 border {row._test.ok
                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                : 'bg-red-500/10 text-red-400 border-red-500/30'}"
            >
              {#if row._test.ok}
                <CheckCircle2 class="w-3.5 h-3.5 shrink-0" />
              {:else}
                <AlertTriangle class="w-3.5 h-3.5 shrink-0" />
              {/if}
              <span>{row._test.text}</span>
            </div>
          {/if}

          <div class="flex justify-end">
            <button
              type="button"
              on:click={() => handleTest(row)}
              disabled={row._testing}
              class="btn btn-sm btn-crest text-xs flex items-center gap-2"
            >
              <RotateCw class="w-3.5 h-3.5 {row._testing ? 'animate-spin' : ''}" />
              {$t('plugins.portainer.test')}
            </button>
          </div>
        </div>
      {/each}

      <div class="flex items-center gap-3 pt-4 border-t border-line justify-between">
        {#if rows.length > 0}
          <button type="button" on:click={addServer} class="btn btn-ghost text-xs flex items-center gap-2">
            <Plus class="w-3.5 h-3.5" /> {$t('plugins.portainer.addServer')}
          </button>
        {:else}
          <span></span>
        {/if}

        <button type="submit" disabled={saving} class="btn btn-visor text-xs flex items-center gap-2">
          <Save class="w-3.5 h-3.5" />
          {$t('plugins.portainer.save')}
        </button>
      </div>
    </form>
  {/if}
</div>
