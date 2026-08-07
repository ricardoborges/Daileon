<script lang="ts">
  import { onMount } from 'svelte';
  import { fetchPortainerConfig, savePortainerConfig, testPortainerConfig, type PortainerConfig } from '$lib/api';
  import { Activity, CheckCircle2, AlertTriangle, RotateCw, Save, Server, Key, User } from 'lucide-svelte';

  let config: PortainerConfig = {
    url: 'http://localhost:9000',
    api_key: '',
    username: '',
    password: '',
    enabled: true
  };

  let loading = true;
  let saving = false;
  let testing = false;
  let statusMessage: { type: 'success' | 'error'; text: string } | null = null;
  let authMode: 'api_key' | 'user_pass' = 'api_key';

  async function loadConfig() {
    loading = true;
    try {
      const res = await fetchPortainerConfig();
      if (res) {
        config = { ...config, ...res };
        if (config.username || config.password) {
          authMode = 'user_pass';
        } else {
          authMode = 'api_key';
        }
      }
    } catch (e) {
      console.error('Falha ao carregar configurações do Portainer:', e);
    } finally {
      loading = false;
    }
  }

  async function handleSave() {
    saving = true;
    statusMessage = null;
    try {
      const res = await savePortainerConfig(config);
      statusMessage = { type: 'success', text: res.message || 'Configurações do Portainer salvas com sucesso!' };
    } catch (e: any) {
      statusMessage = { type: 'error', text: e.message || 'Erro ao salvar configurações do Portainer.' };
    } finally {
      saving = false;
    }
  }

  async function handleTest() {
    testing = true;
    statusMessage = null;
    try {
      const res = await testPortainerConfig(config);
      if (res.success) {
        const detailStr = res.endpoints_count !== undefined ? ` (${res.endpoints_count} ambiente(s) encontrado(s))` : '';
        statusMessage = { type: 'success', text: `${res.message}${detailStr}` };
      } else {
        statusMessage = { type: 'error', text: res.message };
      }
    } catch (e: any) {
      statusMessage = { type: 'error', text: e.message || 'Erro ao testar conexão com o Portainer.' };
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
      <Activity class="w-6 h-6 t-visor" />
      <div>
        <h3 class="text-base font-bold t-txt">Observabilidade com Portainer</h3>
        <p class="text-xs t-dim">Configure a integração com a REST API do Portainer para monitorar containers, métricas e logs em tempo real.</p>
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
      <div class="flex items-center gap-3">
        <input
          type="checkbox"
          id="portainer_enabled"
          bind:checked={config.enabled}
          class="rounded bg-surface-3 border-line text-visor focus:ring-visor"
        />
        <label for="portainer_enabled" class="t-txt font-semibold cursor-pointer">
          Habilitar Integração de Observabilidade Portainer
        </label>
      </div>

      <div class="space-y-4 pt-2">
        <div>
          <label for="portainer_url" class="block t-faint font-semibold mb-1">
            <Server class="w-3.5 h-3.5 inline mr-1" /> URL do Portainer
          </label>
          <input
            type="text"
            id="portainer_url"
            bind:value={config.url}
            placeholder="http://portainer.empresa.com:9000 ou https://portainer.empresa.com:9443"
            class="input w-full font-mono"
            required
          />
          <p class="t-dim text-[11px] mt-1">URL base da instância do Portainer com protocolo e porta.</p>
        </div>

        <!-- Seletor de Método de Autenticação -->
        <div class="space-y-2 pt-2">
          <span class="block t-faint font-semibold">Método de Autenticação</span>
          <div class="seg">
            <button
              type="button"
              class="seg-item cursor-pointer {authMode === 'api_key' ? 'is-active' : ''}"
              on:click={() => (authMode = 'api_key')}
            >
              <Key class="w-3.5 h-3.5" /> API Key (Recomendado)
            </button>
            <button
              type="button"
              class="seg-item cursor-pointer {authMode === 'user_pass' ? 'is-active' : ''}"
              on:click={() => (authMode = 'user_pass')}
            >
              <User class="w-3.5 h-3.5" /> Usuário e Senha
            </button>
          </div>
        </div>

        {#if authMode === 'api_key'}
          <div>
            <label for="api_key" class="block t-faint font-semibold mb-1">Portainer API Key (Access Token)</label>
            <input
              type="password"
              id="api_key"
              bind:value={config.api_key}
              placeholder="ptr_..."
              class="input w-full font-mono"
            />
            <p class="t-dim text-[11px] mt-1">Gerada na página de perfil do usuário no Portainer (Settings > Access Tokens / API Keys).</p>
          </div>
        {:else}
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label for="portainer_user" class="block t-faint font-semibold mb-1">Usuário</label>
              <input
                type="text"
                id="portainer_user"
                bind:value={config.username}
                placeholder="admin"
                class="input w-full"
              />
            </div>
            <div>
              <label for="portainer_pass" class="block t-faint font-semibold mb-1">Senha</label>
              <input
                type="password"
                id="portainer_pass"
                bind:value={config.password}
                placeholder="******"
                class="input w-full"
              />
            </div>
          </div>
        {/if}
      </div>

      <div class="flex items-center gap-3 pt-4 border-t border-line justify-end">
        <button
          type="button"
          on:click={handleTest}
          disabled={testing}
          class="btn btn-crest text-xs flex items-center gap-2"
        >
          <RotateCw class="w-3.5 h-3.5 {testing ? 'animate-spin' : ''}" />
          Testar Conexão
        </button>

        <button
          type="submit"
          disabled={saving}
          class="btn btn-visor text-xs flex items-center gap-2"
        >
          <Save class="w-3.5 h-3.5" />
          Salvar Configurações
        </button>
      </div>
    </form>
  {/if}
</div>
