<script lang="ts">
  import { ShieldAlert, CheckCircle2, AlertTriangle, HelpCircle } from 'lucide-svelte';

  export let status: 'OK' | 'WARNING' | 'CRITICAL' | 'NOTICE' | 'UNKNOWN' = 'UNKNOWN';
  export let size: 'sm' | 'md' | 'lg' = 'md';

  $: chipClass = {
    OK: 'chip-ok',
    WARNING: 'chip-crest',
    NOTICE: 'chip-visor',
    CRITICAL: 'chip-alert',
    UNKNOWN: ''
  }[status] || '';

  $: iconSize = size === 'sm' ? 12 : size === 'lg' ? 16 : 14;
</script>

<div class="chip {chipClass} font-mono font-bold tracking-wider uppercase transition-all shadow-sm">
  {#if status === 'OK'}
    <CheckCircle2 size={iconSize} />
    <span>OK / SAUDÁVEL</span>
  {:else if status === 'WARNING' || status === 'NOTICE'}
    <AlertTriangle size={iconSize} />
    <span>ATENÇÃO</span>
  {:else if status === 'CRITICAL'}
    <ShieldAlert size={iconSize} class="animate-pulse" />
    <span>CRÍTICO / INCIDENTE</span>
  {:else}
    <HelpCircle size={iconSize} />
    <span>DESCONHECIDO</span>
  {/if}
</div>
