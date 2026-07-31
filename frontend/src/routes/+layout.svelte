<script lang="ts">
  import { onMount } from 'svelte';
  import '../app.css';
  import Navbar from '$lib/components/Navbar.svelte';
  import { initTheme } from '$lib/theme';

  onMount(() => {
    initTheme();
  });
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
        <span class="label">Daileon Developer Portal &middot; Unidade de Catálogo</span>
      </div>

      <div class="flex items-center gap-5">
        <span class="label">GitLab API v4</span>
        <span class="label" style="color: var(--txt-faint);">&copy; 2026</span>
      </div>
    </div>
  </footer>
</div>
