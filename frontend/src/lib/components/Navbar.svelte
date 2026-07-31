<script lang="ts">
  import { page } from '$app/stores';
  import DaileonLogo from './DaileonLogo.svelte';
  import { Search, Layers, Home, Sun, Moon, Settings } from 'lucide-svelte';
  import { theme, toggleTheme } from '$lib/theme';

  const links = [
    { href: '/', label: 'Home', icon: Home },
    { href: '/catalog', label: 'Catálogo', icon: Layers },
    { href: '/search', label: 'Busca', icon: Search }
  ];

  $: current = $page.url.pathname;
  $: onConfig = current.startsWith('/config');
</script>

<header
  class="sticky top-0 z-50 border-b backdrop-blur-xl"
  style="border-color: var(--line); background: color-mix(in srgb, var(--bg) 82%, transparent);"
>
  <div class="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between gap-6">
    <!-- Marca: bezel chanfrado ao redor do mecha -->
    <a href="/" class="flex items-center gap-3 group shrink-0">
      <div
        class="plate plate-deep p-1 transition-transform group-hover:-translate-y-0.5"
        style="--chamfer: 7px;"
      >
        <DaileonLogo size={34} />
      </div>
      <div class="leading-none">
        <span class="block text-[15px] font-bold tracking-[-0.02em]" style="color: var(--txt);">
          DAILEON
        </span>
        <span class="label mt-1 block">Developer Portal</span>
      </div>
    </a>

    <!-- Navegação -->
    <nav class="hidden md:flex items-center gap-1">
      {#each links as link}
        <a
          href={link.href}
          class="nav-link"
          aria-current={current === link.href || (link.href !== '/' && current.startsWith(link.href)) ? 'page' : undefined}
        >
          <svelte:component this={link.icon} class="w-3.5 h-3.5" />
          {link.label}
        </a>
      {/each}
    </nav>

    <!-- Comandos -->
    <div class="flex items-center gap-3">
      <button
        on:click={toggleTheme}
        title="Alternar tema"
        aria-label="Alternar tema claro / escuro"
        class="btn btn-sm px-2"
      >
        {#if $theme === 'dark'}
          <Sun class="w-3.5 h-3.5" />
        {:else}
          <Moon class="w-3.5 h-3.5" />
        {/if}
      </button>

      <a
        href="/config"
        title="Configuração"
        aria-label="Configuração"
        aria-current={onConfig ? 'page' : undefined}
        class="btn btn-sm px-2 {onConfig ? 'btn-primary' : ''}"
      >
        <Settings class="w-3.5 h-3.5" />
      </a>
    </div>
  </div>
</header>
