<script lang="ts">
  import { ShieldCheck, Award, Target } from 'lucide-svelte';
  import { t } from '$lib/i18n';

  export let slaPercentage: number = 99.95;
  export let sloTarget: number = 99.90;
  export let serviceName: string = 'Cataloged Service';
</script>

<div class="plate p-5 flex flex-col md:flex-row items-start md:items-center justify-between gap-4" style="--chamfer: 16px;">
  <div class="flex items-center gap-3.5">
    <div class="p-3 rounded-xl bg-visor-wash t-visor border border-line">
      <ShieldCheck size={22} />
    </div>
    <div>
      <h4 class="text-sm font-bold t-txt">{$t('plugins.zabbix.slaTitle', { service: serviceName })}</h4>
      <p class="text-xs t-dim mt-0.5">{$t('plugins.zabbix.slaSub')}</p>
    </div>
  </div>

  <div class="flex items-center gap-6 self-end md:self-auto">
    <div class="text-right">
      <div class="label flex items-center justify-end gap-1">
        <Target size={12} />
        <span>{$t('plugins.zabbix.sloTarget')}</span>
      </div>
      <div class="text-sm font-bold t-txt font-mono mt-0.5">{sloTarget}%</div>
    </div>

    <div class="h-8 w-px bg-line"></div>

    <div class="text-right">
      <div class="label flex items-center justify-end gap-1 t-ok">
        <Award size={12} />
        <span>{$t('plugins.zabbix.currentUptime')}</span>
      </div>
      <div class="text-2xl font-black t-ok font-mono mt-0.5">
        {slaPercentage}%
      </div>
    </div>
  </div>
</div>
