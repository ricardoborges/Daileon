<script lang="ts">
  import { onMount } from 'svelte';
  import { fetchLDAPConfig, saveLDAPConfig, testLDAPConfig } from '$lib/api';
  import { Shield, CheckCircle2, AlertTriangle, RotateCw, Save } from 'lucide-svelte';

  let config = {
    enabled: false,
    server_host: '',
    server_port: 389,
    use_ssl: false,
    bind_dn: '',
    bind_password: '',
    base_dn: '',
    user_attribute: 'uid'
  };

  let loading = true;
  let saving = false;
  let testing = false;
  let statusMessage: { type: 'success' | 'error'; text: string } | null = null;

  async function loadConfig() {
    loading = true;
    try {
      const res = await fetchLDAPConfig();
      if (res) {
        config = { ...config, ...res };
      }
    } catch (e) {
      console.error('Failed to load LDAP config:', e);
    } finally {
      loading = false;
    }
  }

  async function handleSave() {
    saving = true;
    statusMessage = null;
    try {
      await saveLDAPConfig(config);
      statusMessage = { type: 'success', text: 'Configurações de LDAP salvas com sucesso!' };
    } catch (e: any) {
      statusMessage = { type: 'error', text: e.message || 'Erro ao salvar configurações do LDAP.' };
    } finally {
      saving = false;
    }
  }

  async function handleTest() {
    testing = true;
    statusMessage = null;
    try {
      const res = await testLDAPConfig(config);
      if (res.success) {
        statusMessage = { type: 'success', text: res.message };
      } else {
        statusMessage = { type: 'error', text: res.message };
      }
    } catch (e: any) {
      statusMessage = { type: 'error', text: e.message || 'Erro ao testar conexão LDAP.' };
    } finally {
      testing = false;
    }
  }

  onMount(() => {
    loadConfig();
  });
</script>

<div class="plate p-6 space-y-6" style="--chamfer: 16px;">
  <div class="flex items-center gap-3 pb-4 border-b border-line">
    <Shield class="w-6 h-6 t-visor" />
    <div>
      <h3 class="text-base font-bold t-txt">Autenticação LDAP / Active Directory</h3>
      <p class="text-xs t-dim">Configure a integração com o diretório LDAP da sua organização.</p>
    </div>
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

    <form on:submit|preventDefault={handleSave} class="space-y-4 text-xs">
      <div class="flex items-center gap-3">
        <input
          type="checkbox"
          id="ldap_enabled"
          bind:checked={config.enabled}
          class="rounded bg-surface-3 border-line text-visor focus:ring-visor"
        />
        <label for="ldap_enabled" class="t-txt font-semibold cursor-pointer">
          Habilitar Autenticação LDAP
        </label>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
        <div>
          <label for="server_host" class="block t-faint font-semibold mb-1">Servidor (Host)</label>
          <input
            type="text"
            id="server_host"
            bind:value={config.server_host}
            placeholder="ldap.empresa.com"
            class="input w-full"
          />
        </div>

        <div>
          <label for="server_port" class="block t-faint font-semibold mb-1">Porta</label>
          <input
            type="number"
            id="server_port"
            bind:value={config.server_port}
            placeholder="389"
            class="input w-full"
          />
        </div>

        <div>
          <label for="bind_dn" class="block t-faint font-semibold mb-1">Bind DN</label>
          <input
            type="text"
            id="bind_dn"
            bind:value={config.bind_dn}
            placeholder="cn=admin,dc=empresa,dc=com"
            class="input w-full"
          />
        </div>

        <div>
          <label for="bind_password" class="block t-faint font-semibold mb-1">Bind Password</label>
          <input
            type="password"
            id="bind_password"
            bind:value={config.bind_password}
            placeholder="******"
            class="input w-full"
          />
        </div>

        <div>
          <label for="base_dn" class="block t-faint font-semibold mb-1">Base DN</label>
          <input
            type="text"
            id="base_dn"
            bind:value={config.base_dn}
            placeholder="ou=users,dc=empresa,dc=com"
            class="input w-full"
          />
        </div>

        <div>
          <label for="user_attribute" class="block t-faint font-semibold mb-1">Atributo do Usuário</label>
          <input
            type="text"
            id="user_attribute"
            bind:value={config.user_attribute}
            placeholder="uid ou sAMAccountName"
            class="input w-full"
          />
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
