<script lang="ts">
  export let size: number = 40;
  export let className: string = '';
</script>

<svg
  xmlns="http://www.w3.org/2000/svg"
  viewBox="0 0 512 512"
  width={size}
  height={size}
  class={className}
>
  <defs>
    <radialGradient id="bgGlowComponent" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#4f46e5" stop-opacity="0.5"/>
      <stop offset="100%" stop-color="#0f172a" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="metalLightComp" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#ffffff"/>
      <stop offset="50%" stop-color="#cbd5e1"/>
      <stop offset="100%" stop-color="#64748b"/>
    </linearGradient>
    <linearGradient id="metalDarkComp" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#475569"/>
      <stop offset="100%" stop-color="#1e293b"/>
    </linearGradient>
    <linearGradient id="goldComp" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#fde047"/>
      <stop offset="100%" stop-color="#ca8a04"/>
    </linearGradient>
    <linearGradient id="redComp" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#ef4444"/>
      <stop offset="100%" stop-color="#991b1b"/>
    </linearGradient>
    <linearGradient id="cyanVisorComp" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#22d3ee"/>
      <stop offset="50%" stop-color="#38bdf8"/>
      <stop offset="100%" stop-color="#0284c7"/>
    </linearGradient>
  </defs>

  <circle cx="256" cy="256" r="240" fill="url(#bgGlowComponent)" />

  <g transform="translate(0, 10)">
    <!-- Base Armor -->
    <path d="M120 400 L256 460 L392 400 L440 320 L380 270 L256 320 L132 270 L72 320 Z" fill="url(#metalDarkComp)" stroke="#475569" stroke-width="4" />
    <path d="M150 360 L256 410 L362 360 L390 320 L256 345 L122 320 Z" fill="url(#redComp)" />

    <!-- Gold Chest Emblem -->
    <polygon points="256,310 296,360 216,360" fill="url(#goldComp)" />

    <!-- Mecha Helmet -->
    <path d="M140 160 L180 80 L220 140 L256 60 L292 140 L332 80 L372 160 L360 230 L256 270 L152 230 Z" fill="url(#metalLightComp)" stroke="#64748b" stroke-width="5" />
    <path d="M170 170 L200 240 L256 265 L312 240 L342 170 L300 160 L256 185 L212 160 Z" fill="url(#metalDarkComp)" />

    <!-- Antenna Crest -->
    <path d="M256 45 L276 130 L256 160 L236 130 Z" fill="url(#goldComp)" stroke="#78350f" stroke-width="3" />

    <!-- Red Ear Wings -->
    <path d="M140 160 L170 120 L190 170 Z" fill="url(#redComp)" />
    <path d="M372 160 L342 120 L322 170 Z" fill="url(#redComp)" />

    <!-- Cyan Visor -->
    <path d="M185 175 L256 195 L327 175 L315 205 L256 220 L197 205 Z" fill="url(#cyanVisorComp)" />
    <path d="M195 183 L256 198 L317 183 L308 200 L256 210 L204 200 Z" fill="#ecfeff" opacity="0.9" />
  </g>
</svg>
