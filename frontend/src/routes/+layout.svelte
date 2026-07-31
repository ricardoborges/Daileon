<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import '../app.css';
  import Navbar from '$lib/components/Navbar.svelte';
  import { initTheme } from '$lib/theme';
  import { auth } from '$lib/auth';
  import { initLocale, t } from '$lib/i18n';

  onMount(() => {
    initTheme();
    initLocale();
    auth.init();
  });

  $: currentPath = $page.url.pathname;
  $: if (!$auth.loading) {
    if (!$auth.user && currentPath !== '/login') {
      goto('/login');
    }
  }
</script>

<div class="relative z-10 min-h-screen flex flex-col">
  <Navbar />

  <div class="flex-1">
    <slot />
  </div>

  <footer class="mt-16 border-t" style="border-color: var(--line);">
    <!-- Régua de instrumento separando o rodapé do conteúdo -->
    <div
      class="h-1.5 w-full"
      style="background-image: linear-gradient(90deg, var(--line-strong) 1px, transparent 1px); background-size: 7px 100%;"
    ></div>

    <div class="max-w-7xl mx-auto px-6 py-8 flex flex-col md:flex-row items-center justify-between gap-4">
      <div class="flex items-center gap-3">
        <span class="led led-visor"></span>
        <span class="label">{$t('footer.portalUnit')}</span>
      </div>

      <div class="flex items-center gap-5">
        <span class="label">GitLab API v4</span>
        <span class="label" style="color: var(--txt-faint);">&copy; 2026</span>
      </div>
    </div>
  </footer>
</div>
