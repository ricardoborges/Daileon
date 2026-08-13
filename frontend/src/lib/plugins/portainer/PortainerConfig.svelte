<script lang="ts">
  import { onMount } from 'svelte';
  import {
    fetchPortainerConfig,
    savePortainerConfig,
    testPortainerConfig,
    type PortainerServer
  } from '$lib/api';
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

  /** Estado local por servidor: modo de autenticação e resultado do teste,
   *  que são da tela e não vão para o banco. */
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

  // Chave só para o `{#each}`: servidor novo ainda não tem id do backend.
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

  /** Só os campos que o backend conhece — o resto é estado de tela. */
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
      console.error('Falha ao carregar configurações do Portainer:', e);
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
      // O backend devolve a lista já normalizada: é dela que vêm os ids dos
      // servidores recém-criados, sem os quais um novo salvamento duplicaria
      // o registro em vez de atualizá-lo.
      rows = (res.servers ?? []).map(toRow);
      statusMessage = {
        type: 'success',
        text: res.message || 'Configurações do Portainer salvas com sucesso!'
      };
    } catch (e: any) {
      statusMessage = { type: 'error', text: e.message || 'Erro ao salvar configurações do Portainer.' };
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
      const extra = res.endpoints_count !== undefined ? ` (${res.endpoints_count} ambiente(s))` : '';
      row._test = { ok: res.success, text: `${res.message}${extra}` };
    } catch (e: any) {
      row._test = { ok: false, text: e.message || 'Erro ao testar conexão.' };
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
        <h3 class="text-base font-bold t-txt">Observabilidade com Portainer</h3>
        <p class="text-xs t-dim">
          Cadastre um ou mais servidores Portainer. Os containers de todos eles são consultados
          em conjunto e identificados pelo servidor de origem.
        </p>
      </div>
    </div>
    <span class="chip chip-visor text-xs font-mono font-bold">Builtin Plugin</span>
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
          <p class="t-dim">Nenhum servidor Portainer cadastrado.</p>
          <button type="button" on:click={addServer} class="btn btn-visor text-xs inline-flex items-center gap-2">
            <Plus class="w-3.5 h-3.5" /> Adicionar servidor
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
                placeholder="Nome do servidor (ex: Produção)"
                aria-label="Nome do servidor"
                class="input font-semibold flex-1 min-w-0"
                required
              />
              {#if row.id}
                <span class="chip text-[10px] font-mono t-dim shrink-0" title="Identificador interno">
                  {row.id}
                </span>
              {:else}
                <span class="chip chip-crest text-[10px] font-mono shrink-0">novo</span>
              {/if}
            </div>
            <button
              type="button"
              on:click={() => removeServer(row._key)}
              class="btn btn-sm btn-ghost text-xs flex items-center gap-1.5 shrink-0"
              title="Remover servidor"
            >
              <Trash2 class="w-3.5 h-3.5" /> Remover
            </button>
          </div>

          <div>
            <label for="url_{row._key}" class="block t-faint font-semibold mb-1">
              <Server class="w-3.5 h-3.5 inline mr-1" /> URL do Portainer
            </label>
            <input
              type="text"
              id="url_{row._key}"
              bind:value={row.url}
              placeholder="http://portainer.empresa.com:9000 ou https://portainer.empresa.com:9443"
              class="input w-full font-mono"
              required
            />
          </div>

          <div class="space-y-2">
            <span class="block t-faint font-semibold">Método de Autenticação</span>
            <div class="seg">
              <button
                type="button"
                class="seg-item cursor-pointer {row._authMode === 'api_key' ? 'is-active' : ''}"
                on:click={() => (row._authMode = 'api_key')}
              >
                <Key class="w-3.5 h-3.5" /> API Key (Recomendado)
              </button>
              <button
                type="button"
                class="seg-item cursor-pointer {row._authMode === 'user_pass' ? 'is-active' : ''}"
                on:click={() => (row._authMode = 'user_pass')}
              >
                <User class="w-3.5 h-3.5" /> Usuário e Senha
              </button>
            </div>
          </div>

          {#if row._authMode === 'api_key'}
            <div>
              <label for="api_key_{row._key}" class="block t-faint font-semibold mb-1">
                Portainer API Key (Access Token)
              </label>
              <input
                type="password"
                id="api_key_{row._key}"
                bind:value={row.api_key}
                placeholder="ptr_..."
                class="input w-full font-mono"
              />
              <p class="t-dim text-[11px] mt-1">
                Gerada no perfil do usuário no Portainer (Settings &gt; Access Tokens).
                Deixe o valor mascarado para manter a chave já gravada.
              </p>
            </div>
          {:else}
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label for="user_{row._key}" class="block t-faint font-semibold mb-1">Usuário</label>
                <input type="text" id="user_{row._key}" bind:value={row.username} placeholder="admin" class="input w-full" />
              </div>
              <div>
                <label for="pass_{row._key}" class="block t-faint font-semibold mb-1">Senha</label>
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
              Testar Conexão
            </button>
          </div>
        </div>
      {/each}

      <div class="flex items-center gap-3 pt-4 border-t border-line justify-between">
        {#if rows.length > 0}
          <button type="button" on:click={addServer} class="btn btn-ghost text-xs flex items-center gap-2">
            <Plus class="w-3.5 h-3.5" /> Adicionar servidor
          </button>
        {:else}
          <span></span>
        {/if}

        <button type="submit" disabled={saving} class="btn btn-visor text-xs flex items-center gap-2">
          <Save class="w-3.5 h-3.5" />
          Salvar Configurações
        </button>
      </div>
    </form>
  {/if}
</div>
