<script lang="ts">
  import { page } from '$app/stores';
  import DaileonLogo from './DaileonLogo.svelte';
  import { Search, Layers, Home, Sun, Moon, Settings, LogIn, LogOut, Globe } from 'lucide-svelte';
  import { theme, toggleTheme } from '$lib/theme';
  import { auth } from '$lib/auth';
  import { t, locale, setLocale } from '$lib/i18n';

  $: links = [
    { href: '/', label: $t('nav.home'), icon: Home },
    { href: '/catalog', label: $t('nav.catalog'), icon: Layers },
    { href: '/search', label: $t('nav.search'), icon: Search }
  ];

  $: current = $page.url.pathname;
  $: onConfig = current.startsWith('/config');
  $: onLogin = current.startsWith('/login');

  function toggleLanguage() {
    setLocale($locale === 'pt-BR' ? 'en-US' : 'pt-BR');
  }
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
        <span class="label mt-1 block">{$t('nav.portalTitle')}</span>
      </div>
    </a>

    <!-- Navegação -->
    {#if $auth.user}
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
    {/if}

    <!-- Comandos -->
    <div class="flex items-center gap-3">
      <!-- Seletor de Idioma -->
      <button
        on:click={toggleLanguage}
        title={$locale === 'pt-BR' ? 'Mudar para English (US)' : 'Mudar para Português (BR)'}
        aria-label="Alternar idioma"
        class="btn btn-sm px-2.5 flex items-center gap-1.5 font-mono text-xs"
      >
        <Globe class="w-3.5 h-3.5 t-visor" />
        <span>{$locale === 'pt-BR' ? 'PT' : 'EN'}</span>
      </button>

      <button
        on:click={toggleTheme}
        title={$t('nav.toggleTheme')}
        aria-label={$t('nav.toggleTheme')}
        class="btn btn-sm px-2"
      >
        {#if $theme === 'dark'}
          <Sun class="w-3.5 h-3.5" />
        {:else}
          <Moon class="w-3.5 h-3.5" />
        {/if}
      </button>

      {#if $auth.user}
        <a
          href="/config"
          title={$t('nav.config')}
          aria-label={$t('nav.config')}
          aria-current={onConfig ? 'page' : undefined}
          class="btn btn-sm px-2 {onConfig ? 'btn-primary' : ''}"
        >
          <Settings class="w-3.5 h-3.5" />
        </a>
      {/if}

      {#if $auth.user}
        <div class="flex items-center gap-2 pl-2 border-l border-[var(--line)]">
          <div class="flex flex-col text-right leading-tight hidden sm:flex">
            <span class="text-xs font-bold t-txt truncate max-w-[120px]">{$auth.user.name}</span>
            <span class="text-[0.625rem] font-mono uppercase tracking-wider t-visor">
              {$auth.user.auth_type === 'break_glass' ? 'Break-Glass' : 'LDAP'}
            </span>
          </div>
          <button
            on:click={() => auth.logout()}
            title={$t('nav.logout')}
            class="btn btn-sm px-2.5 btn-crest flex items-center gap-1.5 text-xs"
          >
            <LogOut class="w-3.5 h-3.5" />
            <span class="hidden sm:inline">{$t('nav.logout')}</span>
          </button>
        </div>
      {:else if !onLogin}
        <a
          href="/login"
          class="btn btn-sm btn-primary px-3 flex items-center gap-1.5 text-xs"
        >
          <LogIn class="w-3.5 h-3.5" />
          <span>{$t('nav.login')}</span>
        </a>
      {/if}
    </div>
  </div>
</header>

