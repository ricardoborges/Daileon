<script lang="ts">
  import { onMount } from "svelte";
  import { goto } from "$app/navigation";
  import { auth } from "$lib/auth";
  import DaileonLogo from "$lib/components/DaileonLogo.svelte";
  import {
    Shield,
    KeyRound,
    Lock,
    User,
    AlertTriangle,
    ArrowRight,
    CheckCircle2,
  } from "lucide-svelte";

  let username = "";
  let password = "";
  let error = "";
  let loading = false;

  $: if ($auth.user) {
    goto("/");
  }

  async function handleLogin() {
    error = "";
    if (!username.trim() || !password) {
      error = "Preencha os campos de usuário e senha.";
      return;
    }

    loading = true;
    const success = await auth.login(username.trim(), password);
    loading = false;

    if (success) {
      goto("/");
    } else {
      error = $auth.error || "Credenciais inválidas ou serviço indisponível.";
    }
  }
</script>

<svelte:head>
  <title>Autenticação &middot; Daileon</title>
</svelte:head>

<main
  class="min-h-[calc(100vh-8rem)] flex items-center justify-center px-6 py-12"
>
  <div class="w-full max-w-md space-y-6">
    <!-- Header com Logo -->
    <div class="text-center space-y-3">
      <div class="inline-block plate plate-deep p-3" style="--chamfer: 14px;">
        <DaileonLogo size={56} />
      </div>
      <div>
        <span class="eyebrow block">Daileon</span>
        <h1 class="text-2xl font-bold tracking-[-0.03em] t-txt mt-1">
          DEVELOPER PORTAL
        </h1>
        <p class="t-dim text-xs mt-1">Identifique-se para acessar o catálogo</p>
      </div>
    </div>

    <!-- Form de Login -->
    <form
      on:submit|preventDefault={handleLogin}
      class="plate plate-deep p-6 space-y-5"
      style="--chamfer: 16px;"
    >
      {#if error}
        <div
          class="chip chip-alert !w-full !whitespace-normal !normal-case !tracking-normal !text-xs p-3"
        >
          <AlertTriangle class="w-4 h-4 flex-none" />
          <span>{error}</span>
        </div>
      {/if}

      <div class="space-y-4">
        <!-- Campo Usuário -->
        <div class="space-y-1.5">
          <label
            for="username"
            class="label flex items-center gap-1.5 text-xs font-semibold t-txt"
          >
            <User class="w-3.5 h-3.5 t-visor" /> Nome de Usuário
          </label>
          <div class="relative">
            <input
              id="username"
              type="text"
              bind:value={username}
              placeholder="ex: admin ou usuario.ldap"
              autocomplete="username"
              required
              class="w-full px-3.5 py-2.5 rounded text-sm t-txt outline-none transition-all"
              style="background: var(--surface-2); border: 1px solid var(--line);"
            />
          </div>
        </div>

        <!-- Campo Senha -->
        <div class="space-y-1.5">
          <label
            for="password"
            class="label flex items-center gap-1.5 text-xs font-semibold t-txt"
          >
            <Lock class="w-3.5 h-3.5 t-visor" /> Senha
          </label>
          <div class="relative">
            <input
              id="password"
              type="password"
              bind:value={password}
              placeholder="••••••••"
              autocomplete="current-password"
              required
              class="w-full px-3.5 py-2.5 rounded text-sm t-txt outline-none transition-all"
              style="background: var(--surface-2); border: 1px solid var(--line);"
            />
          </div>
        </div>
      </div>

      <button
        type="submit"
        disabled={loading}
        class="btn btn-primary w-full py-2.5 text-sm flex items-center justify-center gap-2"
      >
        {#if loading}
          <div
            class="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin"
          ></div>
          <span>Autenticando...</span>
        {:else}
          <KeyRound class="w-4 h-4" />
          <span>Entrar no Sistema</span>
          <ArrowRight class="w-4 h-4 ml-auto" />
        {/if}
      </button>

      <div class="pt-2 text-center border-t border-[var(--line)]">
        <p class="text-[0.6875rem] t-faint"></p>
      </div>
    </form>
  </div>
</main>
