<script lang="ts">
  import { onMount } from 'svelte';
  import { fetchGitLabConfig, saveGitLabConfig, testGitLabConfig, type GitLabConfig } from '$lib/api';
  import { FolderGit2, CheckCircle2, AlertTriangle, RotateCw, Save, Globe, Key, Users } from 'lucide-svelte';

  let config: GitLabConfig = {
    url: 'https://gitlab.com',
    read_token: '',
    group_id: '',
    enabled: true
  };

  let loading = true;
  let saving = false;
  let testing = false;
  let statusMessage: { type: 'success' | 'error'; text: string } | null = null;

  async function loadConfig() {
    loading = true;
    try {
      const res = await fetchGitLabConfig();
      if (res) {
        config = { ...config, ...res };
      }
    } catch (e) {
      console.error('Falha ao carregar configurações do GitLab:', e);
    } finally {
      loading = false;
    }
  }

  async function handleSave() {
    saving = true;
    statusMessage = null;
    try {
      const res = await saveGitLabConfig(config);
      statusMessage = { type: 'success', text: res.message || 'Configurações do GitLab salvas com sucesso!' };
    } catch (e: any) {
      statusMessage = { type: 'error', text: e.message || 'Erro ao salvar configurações do GitLab.' };
    } finally {
      saving = false;
    }
  }

  async function handleTest() {
    testing = true;
    statusMessage = null;
    try {
      const res = await testGitLabConfig(config);
      if (res.success) {
        statusMessage = { type: 'success', text: res.message };
      } else {
        statusMessage = { type: 'error', text: res.message };
      }
    } catch (e: any) {
      statusMessage = { type: 'error', text: e.message || 'Erro ao testar conexão com o GitLab.' };
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
      <FolderGit2 class="w-6 h-6 t-visor" />
      <div>
        <h3 class="text-base font-bold t-txt">GitLab SCM & Catalog Crawler</h3>
        <p class="text-xs t-dim">Configure as variáveis de ambiente e token para varredura automatcida de repositórios no GitLab.</p>
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
          id="gitlab_enabled"
          bind:checked={config.enabled}
          class="rounded bg-surface-3 border-line text-visor focus:ring-visor"
        />
        <label for="gitlab_enabled" class="t-txt font-semibold cursor-pointer">
          Habilitar Integração SCM GitLab
        </label>
      </div>

      <div class="space-y-4 pt-2">
        <div>
          <label for="gitlab_url" class="block t-faint font-semibold mb-1">
            <Globe class="w-3.5 h-3.5 inline mr-1" /> URL do GitLab (GITLAB_URL)
          </label>
          <input
            type="text"
            id="gitlab_url"
            bind:value={config.url}
            placeholder="https://gitlab.com ou https://gitlab.empresa.com"
            class="input w-full font-mono"
            required
          />
          <p class="t-dim text-[11px] mt-1">URL base da sua instância do GitLab (Cloud ou Self-Hosted).</p>
        </div>

        <div>
          <label for="gitlab_token" class="block t-faint font-semibold mb-1">
            <Key class="w-3.5 h-3.5 inline mr-1" /> Personal Access Token (GITLAB_READ_TOKEN)
          </label>
          <input
            type="password"
            id="gitlab_token"
            bind:value={config.read_token}
            placeholder="glpat-..."
            class="input w-full font-mono"
          />
          <p class="t-dim text-[11px] mt-1">Token com escopos <code class="text-visor">read_api</code> e <code class="text-visor">read_repository</code>.</p>
        </div>

        <div>
          <label for="gitlab_group" class="block t-faint font-semibold mb-1">
            <Users class="w-3.5 h-3.5 inline mr-1" /> ID do Grupo / Organização (GITLAB_GROUP_ID)
          </label>
          <input
            type="text"
            id="gitlab_group"
            bind:value={config.group_id}
            placeholder="Ex: 12345678 ou minha-empresa"
            class="input w-full font-mono"
          />
          <p class="t-dim text-[11px] mt-1">Opcional. Se especificado, limita a descoberta de projetos apenas aos subgrupos desta organização.</p>
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
