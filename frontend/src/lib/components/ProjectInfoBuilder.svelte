<script lang="ts">
  import { t } from '$lib/i18n';
  import {
    Copy,
    Check,
    Download,
    Plus,
    Trash2,
    Sparkles,
    RefreshCw,
    FileCode,
    CheckCircle2,
    HelpCircle,
    Columns,
    Rows,
    PanelBottom,
    ChevronUp,
    ChevronDown,
    Eye
  } from 'lucide-svelte';

  export interface DeploymentItem {
    environment: string;
    server_name: string;
    server_ip: string;
    os: string;
    execution_type: string;
    port: string;
    url: string;
    notes: string;
  }

  export interface JenkinsItem {
    name: string;
    environment: string;
    job: string;
    server_url: string;
  }

  export interface LinkItem {
    title: string;
    url: string;
    icon: string;
  }

  export interface DependencyItem {
    component: string;
  }

  // Layout mode state: 'cols' (Side by Side) | 'rows' (Top / Bottom Horizontal) | 'drawer' (Sticky Floating Drawer)
  type LayoutMode = 'cols' | 'rows' | 'drawer';
  let layoutMode: LayoutMode = 'cols';
  let drawerOpen = true;

  // Initial state
  let kind = 'Component';
  let name = 'daileon-portal';
  let description = 'Developer Portal interno inspirado no Spotify Backstage com backend Python FastAPI e frontend SvelteKit.';
  let owner = 'team-platform-engineering';
  let domain = 'internal-tooling';
  let tags = 'python, fastapi, sveltekit, dev-portal, gitlab';
  
  let type = 'website';
  let lifecycle = 'production';
  let system = 'platform-engineering';
  
  let docsDir = '/docs';
  let docsIndex = 'index.md';

  let deployments: DeploymentItem[] = [
    {
      environment: 'production',
      server_name: 'srv-prod-portal01',
      server_ip: '192.168.10.100',
      os: 'Linux Ubuntu 22.04 LTS',
      execution_type: 'Docker',
      port: '5173',
      url: 'http://localhost:5173',
      notes: 'Ambiente principal de produção do Daileon'
    },
    {
      environment: 'test',
      server_name: 'srv-test-portal01',
      server_ip: '192.168.20.100',
      os: 'Windows Server 2022',
      execution_type: 'VM',
      port: '8000',
      url: 'http://localhost:8000',
      notes: 'Servidor de testes e homologação local'
    }
  ];

  let jenkinsPipelines: JenkinsItem[] = [
    {
      name: 'Pipeline de Produção',
      environment: 'production',
      job: 'deployments/daileon-prod',
      server_url: ''
    },
    {
      name: 'Testes Automáticos & CI',
      environment: 'test',
      job: 'ci/daileon-ci',
      server_url: ''
    }
  ];

  let links: LinkItem[] = [
    {
      title: 'FastAPI OpenAPI Specs',
      url: 'http://localhost:8000/docs',
      icon: 'api'
    }
  ];

  let dependencies: DependencyItem[] = [
    { component: 'gitlab-api' }
  ];

  let copied = false;

  const kindOptions = ['Component', 'API', 'Library', 'Resource', 'System'];
  const typeOptions = ['service', 'website', 'library', 'cronjob', 'mobile', 'cli'];
  const lifecycleOptions = ['production', 'experimental', 'deprecated'];
  const executionTypeOptions = ['Docker', 'VM', 'Bare-Metal', 'Serverless', 'Static'];
  const environmentOptions = ['production', 'staging', 'test', 'development'];
  const iconOptions = ['api', 'docs', 'dashboard', 'monitoring', 'gitlab', 'jenkins', 'jira', 'confluence', 'link'];

  function formatYamlString(str: string): string {
    if (!str) return '""';
    if (str.includes('\n') || str.includes(':') || str.includes('#') || str.includes('"')) {
      return JSON.stringify(str);
    }
    return str;
  }

  $: yamlOutput = generateYaml({
    kind,
    name,
    description,
    owner,
    domain,
    tags,
    type,
    lifecycle,
    system,
    docsDir,
    docsIndex,
    deployments,
    jenkinsPipelines,
    links,
    dependencies
  });

  function generateYaml(data: any): string {
    const lines: string[] = [];
    lines.push('apiVersion: daileon/v1');
    lines.push(`kind: ${data.kind || 'Component'}`);
    lines.push('metadata:');
    lines.push(`  name: ${data.name || 'unnamed-component'}`);
    if (data.description) {
      lines.push(`  description: ${formatYamlString(data.description)}`);
    }
    
    const tagList = (data.tags || '')
      .split(',')
      .map((t: string) => t.trim())
      .filter((t: string) => t.length > 0);
    
    if (tagList.length > 0) {
      lines.push('  tags:');
      tagList.forEach((t: string) => lines.push(`    - ${t}`));
    }

    lines.push(`  owner: ${data.owner || 'unassigned'}`);
    if (data.domain) {
      lines.push(`  domain: ${data.domain}`);
    }

    lines.push('');
    lines.push('spec:');
    lines.push(`  type: ${data.type || 'service'}`);
    lines.push(`  lifecycle: ${data.lifecycle || 'production'}`);
    if (data.system) {
      lines.push(`  system: ${data.system}`);
    }

    lines.push('  ');
    lines.push('  docs:');
    lines.push(`    dir: ${data.docsDir || '/docs'}`);
    lines.push(`    index: ${data.docsIndex || 'index.md'}`);

    if (data.links && data.links.length > 0) {
      lines.push('  ');
      lines.push('  links:');
      data.links.forEach((l: LinkItem) => {
        if (l.title || l.url) {
          lines.push(`    - url: ${l.url || ''}`);
          lines.push(`      title: ${formatYamlString(l.title || '')}`);
          if (l.icon) {
            lines.push(`      icon: ${l.icon}`);
          }
        }
      });
    }

    if (data.dependencies && data.dependencies.length > 0) {
      lines.push('  ');
      lines.push('  dependencies:');
      data.dependencies.forEach((d: DependencyItem) => {
        if (d.component) {
          lines.push(`    - component: ${d.component}`);
        }
      });
    }

    if (data.jenkinsPipelines && data.jenkinsPipelines.length > 0) {
      lines.push('  ');
      lines.push('  jenkins:');
      lines.push('    pipelines:');
      data.jenkinsPipelines.forEach((j: JenkinsItem) => {
        if (j.name || j.job) {
          lines.push(`      - name: ${formatYamlString(j.name || '')}`);
          lines.push(`        environment: ${j.environment || 'production'}`);
          lines.push(`        job: ${formatYamlString(j.job || '')}`);
          if (j.server_url) {
            lines.push(`        server_url: ${j.server_url}`);
          }
        }
      });
    }

    if (data.deployments && data.deployments.length > 0) {
      lines.push('  ');
      lines.push('  deployments:');
      data.deployments.forEach((dep: DeploymentItem) => {
        lines.push(`    - environment: ${dep.environment || 'production'}`);
        if (dep.url) lines.push(`      url: ${dep.url}`);
        if (dep.server_name) lines.push(`      server_name: ${dep.server_name}`);
        if (dep.server_ip) lines.push(`      server_ip: ${dep.server_ip}`);
        if (dep.os) lines.push(`      os: ${formatYamlString(dep.os)}`);
        if (dep.execution_type) lines.push(`      execution_type: ${dep.execution_type}`);
        if (dep.port) lines.push(`      port: ${dep.port}`);
        if (dep.notes) lines.push(`      notes: ${formatYamlString(dep.notes)}`);
      });
    }

    lines.push('');
    return lines.join('\n');
  }

  function copyToClipboard() {
    navigator.clipboard.writeText(yamlOutput);
    copied = true;
    setTimeout(() => (copied = false), 2500);
  }

  function downloadFile() {
    const blob = new Blob([yamlOutput], { type: 'text/yaml;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'project-info.yml';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  function loadPreset(preset: 'web' | 'api' | 'job' | 'clear') {
    if (preset === 'clear') {
      kind = 'Component';
      name = '';
      description = '';
      owner = '';
      domain = '';
      tags = '';
      type = 'service';
      lifecycle = 'production';
      system = '';
      docsDir = '/docs';
      docsIndex = 'index.md';
      deployments = [];
      jenkinsPipelines = [];
      links = [];
      dependencies = [];
      return;
    }

    if (preset === 'web') {
      kind = 'Component';
      name = 'meu-web-app';
      description = 'Aplicação Web Frontend desenvolvida em React/Svelte para usuários internos.';
      owner = 'team-frontend';
      domain = 'customer-portal';
      tags = 'frontend, svelte, web, user-interface';
      type = 'website';
      lifecycle = 'production';
      system = 'customer-portal';
      docsDir = '/docs';
      docsIndex = 'index.md';
      deployments = [
        {
          environment: 'production',
          server_name: 'srv-web-prod01',
          server_ip: '10.0.1.50',
          os: 'Linux Ubuntu 22.04 LTS',
          execution_type: 'Docker',
          port: '80',
          url: 'https://app.empresa.com',
          notes: 'Servidor web com Nginx e SSL'
        }
      ];
      jenkinsPipelines = [
        {
          name: 'Build e Deploy Frontend',
          environment: 'production',
          job: 'frontend/deploy-prod',
          server_url: ''
        }
      ];
      links = [
        { title: 'Protótipo Figma', url: 'https://figma.com', icon: 'dashboard' }
      ];
      dependencies = [
        { component: 'meu-servico-api' }
      ];
    } else if (preset === 'api') {
      kind = 'API';
      name = 'meu-servico-api';
      description = 'Microsserviço de Backend responsável pela gestão de pagamentos e transações.';
      owner = 'team-backend';
      domain = 'payments';
      tags = 'python, fastapi, postgresql, rest-api';
      type = 'service';
      lifecycle = 'production';
      system = 'payment-gateway';
      docsDir = '/docs';
      docsIndex = 'index.md';
      deployments = [
        {
          environment: 'production',
          server_name: 'srv-api-prod01',
          server_ip: '10.0.2.100',
          os: 'Linux Red Hat 9',
          execution_type: 'Docker',
          port: '8080',
          url: 'https://api.empresa.com/v1',
          notes: 'Cluster de microsserviços em container'
        }
      ];
      jenkinsPipelines = [
        {
          name: 'CI/CD Pipeline Backend',
          environment: 'production',
          job: 'backend/api-deploy-job',
          server_url: ''
        }
      ];
      links = [
        { title: 'Swagger API Spec', url: 'https://api.empresa.com/docs', icon: 'api' }
      ];
      dependencies = [
        { component: 'auth-service' }
      ];
    } else if (preset === 'job') {
      kind = 'Component';
      name = 'worker-processamento-diario';
      description = 'Job assíncrono para consolidação diária de relatórios e notificações batch.';
      owner = 'team-data';
      domain = 'analytics';
      tags = 'cronjob, python, batch, worker';
      type = 'cronjob';
      lifecycle = 'production';
      system = 'data-lake';
      docsDir = '/docs';
      docsIndex = 'index.md';
      deployments = [
        {
          environment: 'production',
          server_name: 'srv-worker-prod01',
          server_ip: '10.0.3.20',
          os: 'Linux Ubuntu 22.04 LTS',
          execution_type: 'VM',
          port: '',
          url: '',
          notes: 'Executado via cron no horário da meia-noite'
        }
      ];
      jenkinsPipelines = [
        {
          name: 'Deploy Cronjob Worker',
          environment: 'production',
          job: 'jobs/worker-deploy',
          server_url: ''
        }
      ];
      links = [];
      dependencies = [];
    }
  }

  function addDeployment() {
    deployments = [
      ...deployments,
      {
        environment: 'production',
        server_name: '',
        server_ip: '',
        os: 'Linux Ubuntu 22.04 LTS',
        execution_type: 'Docker',
        port: '',
        url: '',
        notes: ''
      }
    ];
  }

  function removeDeployment(index: number) {
    deployments = deployments.filter((_, i) => i !== index);
  }

  function addJenkinsPipeline() {
    jenkinsPipelines = [
      ...jenkinsPipelines,
      { name: '', environment: 'production', job: '', server_url: '' }
    ];
  }

  function removeJenkinsPipeline(index: number) {
    jenkinsPipelines = jenkinsPipelines.filter((_, i) => i !== index);
  }

  function addLink() {
    links = [...links, { title: '', url: '', icon: 'link' }];
  }

  function removeLink(index: number) {
    links = links.filter((_, i) => i !== index);
  }

  function addDependency() {
    dependencies = [...dependencies, { component: '' }];
  }

  function removeDependency(index: number) {
    dependencies = dependencies.filter((_, i) => i !== index);
  }
</script>

<div class="space-y-6 pb-16">
  <!-- Toolbar: Presets & Layout Mode Control -->
  <div class="plate p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
    <!-- Presets Rápido -->
    <div class="flex flex-wrap items-center gap-2">
      <div class="flex items-center gap-1.5 mr-2">
        <Sparkles class="w-4 h-4 t-visor shrink-0" />
        <span class="text-xs font-bold uppercase tracking-wider t-muted">{$t('tools.builder.presetLabel')}</span>
      </div>
      <button on:click={() => loadPreset('web')} class="btn btn-sm btn-ghost text-xs">
        {$t('tools.builder.presetWeb')}
      </button>
      <button on:click={() => loadPreset('api')} class="btn btn-sm btn-ghost text-xs">
        {$t('tools.builder.presetApi')}
      </button>
      <button on:click={() => loadPreset('job')} class="btn btn-sm btn-ghost text-xs">
        {$t('tools.builder.presetJob')}
      </button>
      <button on:click={() => loadPreset('clear')} class="btn btn-sm px-2 text-xs opacity-75 hover:opacity-100 flex items-center gap-1">
        <RefreshCw class="w-3 h-3" />
        {$t('tools.builder.presetCustom')}
      </button>
    </div>

    <!-- Seletor de Modo de Divisão de Layout -->
    <div class="flex items-center gap-2 border-t md:border-t-0 md:border-l border-[var(--line)] pt-3 md:pt-0 md:pl-4">
      <span class="text-xs font-bold uppercase tracking-wider t-muted hidden lg:inline">
        {$t('tools.builder.layoutLabel')}
      </span>
      <div class="inline-flex rounded-lg p-1 bg-[var(--bg)] border border-[var(--line)]">
        <button
          on:click={() => (layoutMode = 'cols')}
          title={$t('tools.builder.layoutCols')}
          aria-label={$t('tools.builder.layoutCols')}
          class="btn btn-sm px-2.5 py-1 text-xs flex items-center gap-1.5 rounded {layoutMode === 'cols' ? 'btn-primary' : 'btn-ghost'}"
        >
          <Columns class="w-3.5 h-3.5" />
          <span class="hidden sm:inline">{$t('tools.builder.layoutCols')}</span>
        </button>

        <button
          on:click={() => (layoutMode = 'rows')}
          title={$t('tools.builder.layoutRows')}
          aria-label={$t('tools.builder.layoutRows')}
          class="btn btn-sm px-2.5 py-1 text-xs flex items-center gap-1.5 rounded {layoutMode === 'rows' ? 'btn-primary' : 'btn-ghost'}"
        >
          <Rows class="w-3.5 h-3.5" />
          <span class="hidden sm:inline">{$t('tools.builder.layoutRows')}</span>
        </button>

        <button
          on:click={() => {
            layoutMode = 'drawer';
            drawerOpen = true;
          }}
          title={$t('tools.builder.layoutDrawer')}
          aria-label={$t('tools.builder.layoutDrawer')}
          class="btn btn-sm px-2.5 py-1 text-xs flex items-center gap-1.5 rounded {layoutMode === 'drawer' ? 'btn-primary' : 'btn-ghost'}"
        >
          <PanelBottom class="w-3.5 h-3.5" />
          <span class="hidden sm:inline">{$t('tools.builder.layoutDrawer')}</span>
        </button>
      </div>
    </div>
  </div>

  <!-- Layout Container: Split Columns vs Split Rows vs Drawer -->
  <div class={layoutMode === 'cols' ? 'grid grid-cols-1 lg:grid-cols-12 gap-8' : 'space-y-8'}>

    <!-- Formulário do Builder -->
    <div class={layoutMode === 'cols' ? 'lg:col-span-7 space-y-6' : 'space-y-6 max-w-5xl mx-auto'}>

      <!-- Sec 1: Identificação & Metadados -->
      <div class="plate p-6 space-y-4">
        <h3 class="text-sm font-bold uppercase tracking-wider t-visor flex items-center gap-2">
          {$t('tools.builder.secMetadata')}
        </h3>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div class="space-y-1">
            <label for="builder-name" class="label">{$t('tools.builder.name')} *</label>
            <input
              id="builder-name"
              type="text"
              bind:value={name}
              placeholder={$t('tools.builder.namePlaceholder')}
              class="input text-sm"
            />
            <p class="text-[11px] t-muted">{$t('tools.builder.nameHelp')}</p>
          </div>

          <div class="space-y-1">
            <label for="builder-kind" class="label">{$t('tools.builder.kind')} *</label>
            <select id="builder-kind" bind:value={kind} class="input text-sm">
              {#each kindOptions as opt}
                <option value={opt}>{opt}</option>
              {/each}
            </select>
            <p class="text-[11px] t-muted">{$t('tools.builder.kindHelp')}</p>
          </div>

          <div class="space-y-1">
            <label for="builder-owner" class="label">{$t('tools.builder.owner')} *</label>
            <input
              id="builder-owner"
              type="text"
              bind:value={owner}
              placeholder={$t('tools.builder.ownerPlaceholder')}
              class="input text-sm"
            />
          </div>

          <div class="space-y-1">
            <label for="builder-domain" class="label">{$t('tools.builder.domain')}</label>
            <input
              id="builder-domain"
              type="text"
              bind:value={domain}
              placeholder={$t('tools.builder.domainPlaceholder')}
              class="input text-sm"
            />
          </div>
        </div>

        <div class="space-y-1">
          <label for="builder-tags" class="label">{$t('tools.builder.tags')}</label>
          <input
            id="builder-tags"
            type="text"
            bind:value={tags}
            placeholder={$t('tools.builder.tagsPlaceholder')}
            class="input text-sm"
          />
        </div>

        <div class="space-y-1">
          <label for="builder-description" class="label">{$t('tools.builder.description')}</label>
          <textarea
            id="builder-description"
            bind:value={description}
            rows="2"
            placeholder={$t('tools.builder.descriptionPlaceholder')}
            class="input text-sm resize-y"
          ></textarea>
        </div>
      </div>

      <!-- Sec 2: Especificação & Ciclo de Vida -->
      <div class="plate p-6 space-y-4">
        <h3 class="text-sm font-bold uppercase tracking-wider t-visor flex items-center gap-2">
          {$t('tools.builder.secSpec')}
        </h3>

        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div class="space-y-1">
            <label for="builder-type" class="label">{$t('tools.builder.type')} *</label>
            <select id="builder-type" bind:value={type} class="input text-sm">
              {#each typeOptions as opt}
                <option value={opt}>{opt}</option>
              {/each}
            </select>
            <p class="text-[11px] t-muted">{$t('tools.builder.typeHelp')}</p>
          </div>

          <div class="space-y-1">
            <label for="builder-lifecycle" class="label">{$t('tools.builder.lifecycle')} *</label>
            <select id="builder-lifecycle" bind:value={lifecycle} class="input text-sm">
              {#each lifecycleOptions as opt}
                <option value={opt}>{opt}</option>
              {/each}
            </select>
            <p class="text-[11px] t-muted">{$t('tools.builder.lifecycleHelp')}</p>
          </div>

          <div class="space-y-1">
            <label for="builder-system" class="label">{$t('tools.builder.system')}</label>
            <input
              id="builder-system"
              type="text"
              bind:value={system}
              placeholder={$t('tools.builder.systemPlaceholder')}
              class="input text-sm"
            />
          </div>
        </div>
      </div>

      <!-- Sec 3: Documentação Técnica (TechDocs) -->
      <div class="plate p-6 space-y-4">
        <h3 class="text-sm font-bold uppercase tracking-wider t-visor flex items-center gap-2">
          {$t('tools.builder.secDocs')}
        </h3>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div class="space-y-1">
            <label for="builder-docsdir" class="label">{$t('tools.builder.docsDir')}</label>
            <input
              id="builder-docsdir"
              type="text"
              bind:value={docsDir}
              placeholder="/docs"
              class="input text-sm font-mono"
            />
          </div>

          <div class="space-y-1">
            <label for="builder-docsindex" class="label">{$t('tools.builder.docsIndex')}</label>
            <input
              id="builder-docsindex"
              type="text"
              bind:value={docsIndex}
              placeholder="index.md"
              class="input text-sm font-mono"
            />
          </div>
        </div>
      </div>

      <!-- Sec 4: Deployments -->
      <div class="plate p-6 space-y-4">
        <div class="flex items-center justify-between gap-4">
          <h3 class="text-sm font-bold uppercase tracking-wider t-visor">
            {$t('tools.builder.secDeployments')}
          </h3>
          <button on:click={addDeployment} class="btn btn-sm btn-ghost text-xs flex items-center gap-1">
            <Plus class="w-3.5 h-3.5" />
            <span>{$t('tools.builder.addDeployment')}</span>
          </button>
        </div>

        {#if deployments.length === 0}
          <p class="text-xs t-muted italic">{ $t('tools.builder.noDeployments') }</p>
        {:else}
          <div class="space-y-4">
            {#each deployments as dep, i}
              <div class="plate plate-deep p-4 space-y-3 relative group">
                <button
                  on:click={() => removeDeployment(i)}
                  title="Remover Ambiente"
                  aria-label="Remover Ambiente"
                  class="absolute top-3 right-3 text-red-400 hover:text-red-300 p-1 transition-colors"
                >
                  <Trash2 class="w-4 h-4" />
                </button>

                <span class="inline-block text-[11px] font-mono font-bold uppercase px-2 py-0.5 rounded bg-[var(--card)] border border-[var(--line)]">
                  # {i + 1} - {dep.environment || 'production'}
                </span>

                <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                  <div class="space-y-1">
                    <label for={`dep-env-${i}`} class="label text-[11px]">{$t('tools.builder.envName')}</label>
                    <select id={`dep-env-${i}`} bind:value={dep.environment} class="input text-xs">
                      {#each environmentOptions as envOpt}
                        <option value={envOpt}>{envOpt}</option>
                      {/each}
                    </select>
                  </div>

                  <div class="space-y-1">
                    <label for={`dep-server-${i}`} class="label text-[11px]">{$t('tools.builder.serverName')}</label>
                    <input
                      id={`dep-server-${i}`}
                      type="text"
                      bind:value={dep.server_name}
                      placeholder="ex: srv-prod-01"
                      class="input text-xs font-mono"
                    />
                  </div>

                  <div class="space-y-1">
                    <label for={`dep-ip-${i}`} class="label text-[11px]">{$t('tools.builder.serverIp')}</label>
                    <input
                      id={`dep-ip-${i}`}
                      type="text"
                      bind:value={dep.server_ip}
                      placeholder="ex: 192.168.1.50"
                      class="input text-xs font-mono"
                    />
                  </div>

                  <div class="space-y-1">
                    <label for={`dep-[exec]-${i}`} class="label text-[11px]">{$t('tools.builder.executionType')}</label>
                    <select id={`dep-[exec]-${i}`} bind:value={dep.execution_type} class="input text-xs">
                      {#each executionTypeOptions as execOpt}
                        <option value={execOpt}>{execOpt}</option>
                      {/each}
                    </select>
                  </div>

                  <div class="space-y-1">
                    <label for={`dep-os-${i}`} class="label text-[11px]">{$t('tools.builder.os')}</label>
                    <input
                      id={`dep-os-${i}`}
                      type="text"
                      bind:value={dep.os}
                      placeholder="ex: Ubuntu 22.04 LTS"
                      class="input text-xs"
                    />
                  </div>

                  <div class="space-y-1">
                    <label for={`dep-port-${i}`} class="label text-[11px]">{$t('tools.builder.port')}</label>
                    <input
                      id={`dep-port-${i}`}
                      type="text"
                      bind:value={dep.port}
                      placeholder="ex: 8080"
                      class="input text-xs font-mono"
                    />
                  </div>
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div class="space-y-1">
                    <label for={`dep-url-${i}`} class="label text-[11px]">{$t('tools.builder.url')}</label>
                    <input
                      id={`dep-url-${i}`}
                      type="text"
                      bind:value={dep.url}
                      placeholder="ex: http://srv-prod-01:8080"
                      class="input text-xs font-mono"
                    />
                  </div>

                  <div class="space-y-1">
                    <label for={`dep-notes-${i}`} class="label text-[11px]">{$t('tools.builder.notes')}</label>
                    <input
                      id={`dep-notes-${i}`}
                      type="text"
                      bind:value={dep.notes}
                      placeholder="ex: Cluster principal com backup automático"
                      class="input text-xs"
                    />
                  </div>
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </div>

      <!-- Sec 5: Jenkins Pipelines -->
      <div class="plate p-6 space-y-4">
        <div class="flex items-center justify-between gap-4">
          <h3 class="text-sm font-bold uppercase tracking-wider t-visor">
            {$t('tools.builder.secJenkins')}
          </h3>
          <button on:click={addJenkinsPipeline} class="btn btn-sm btn-ghost text-xs flex items-center gap-1">
            <Plus class="w-3.5 h-3.5" />
            <span>{$t('tools.builder.addPipeline')}</span>
          </button>
        </div>

        {#if jenkinsPipelines.length === 0}
          <p class="text-xs t-muted italic">{$t('tools.builder.noPipelines')}</p>
        {:else}
          <div class="space-y-3">
            {#each jenkinsPipelines as pipe, j}
              <div class="plate plate-deep p-3 flex flex-col sm:flex-row items-stretch sm:items-center gap-3 relative group">
                <div class="grid grid-cols-1 sm:grid-cols-3 gap-2 flex-1">
                  <input
                    type="text"
                    bind:value={pipe.name}
                    placeholder={$t('tools.builder.pipelineName')}
                    class="input text-xs"
                  />
                  <select bind:value={pipe.environment} class="input text-xs">
                    {#each environmentOptions as envOpt}
                      <option value={envOpt}>{envOpt}</option>
                    {/each}
                  </select>
                  <input
                    type="text"
                    bind:value={pipe.job}
                    placeholder={$t('tools.builder.jobPath')}
                    class="input text-xs font-mono"
                  />
                </div>
                <button
                  on:click={() => removeJenkinsPipeline(j)}
                  title="Remover Pipeline"
                  aria-label="Remover Pipeline"
                  class="text-red-400 hover:text-red-300 p-1 transition-colors self-end sm:self-center"
                >
                  <Trash2 class="w-4 h-4" />
                </button>
              </div>
            {/each}
          </div>
        {/if}
      </div>

      <!-- Sec 6: Links & Dependências -->
      <div class="plate p-6 space-y-6">
        <!-- Useful Links -->
        <div class="space-y-4">
          <div class="flex items-center justify-between gap-4">
            <h3 class="text-sm font-bold uppercase tracking-wider t-visor">
              {$t('tools.builder.secLinks')}
            </h3>
            <button on:click={addLink} class="btn btn-sm btn-ghost text-xs flex items-center gap-1">
              <Plus class="w-3.5 h-3.5" />
              <span>{$t('tools.builder.addLink')}</span>
            </button>
          </div>

          {#if links.length === 0}
            <p class="text-xs t-muted italic">{$t('tools.builder.noLinks')}</p>
          {:else}
            <div class="space-y-3">
              {#each links as link, l}
                <div class="plate plate-deep p-3 flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
                  <input
                    type="text"
                    bind:value={link.title}
                    placeholder={$t('tools.builder.linkTitle')}
                    class="input text-xs flex-1"
                  />
                  <input
                    type="text"
                    bind:value={link.url}
                    placeholder={$t('tools.builder.linkUrl')}
                    class="input text-xs font-mono flex-1"
                  />
                  <select bind:value={link.icon} class="input text-xs w-28">
                    {#each iconOptions as ico}
                      <option value={ico}>{ico}</option>
                    {/each}
                  </select>
                  <button
                    on:click={() => removeLink(l)}
                    title="Remover Link"
                    aria-label="Remover Link"
                    class="text-red-400 hover:text-red-300 p-1 transition-colors self-end sm:self-center"
                  >
                    <Trash2 class="w-4 h-4" />
                  </button>
                </div>
              {/each}
            </div>
          {/if}
        </div>

        <div class="border-t border-[var(--line)] pt-4 space-y-4">
          <div class="flex items-center justify-between gap-4">
            <h4 class="text-xs font-bold uppercase tracking-wider t-muted">
              Dependências de Software
            </h4>
            <button on:click={addDependency} class="btn btn-sm btn-ghost text-xs flex items-center gap-1">
              <Plus class="w-3.5 h-3.5" />
              <span>{$t('tools.builder.addDependency')}</span>
            </button>
          </div>

          {#if dependencies.length === 0}
            <p class="text-xs t-muted italic">{$t('tools.builder.noDependencies')}</p>
          {:else}
            <div class="space-y-2">
              {#each dependencies as dep, d}
                <div class="flex items-center gap-2">
                  <input
                    type="text"
                    bind:value={dep.component}
                    placeholder={$t('tools.builder.depComponent')}
                    class="input text-xs font-mono flex-1"
                  />
                  <button
                    on:click={() => removeDependency(d)}
                    title="Remover Dependência"
                    aria-label="Remover Dependência"
                    class="text-red-400 hover:text-red-300 p-1 transition-colors"
                  >
                    <Trash2 class="w-4 h-4" />
                  </button>
                </div>
              {/each}
            </div>
          {/if}
        </div>
      </div>

    </div>

    <!-- Live Preview (Side-by-side Col 5 mode or Stacked Horizontal Row mode) -->
    {#if layoutMode === 'cols' || layoutMode === 'rows'}
      <div class={layoutMode === 'cols' ? 'lg:col-span-5 space-y-4' : 'max-w-5xl mx-auto space-y-4'}>
        <div class={layoutMode === 'cols' ? 'sticky top-24 space-y-4' : 'space-y-4'}>
          <div class="plate p-5 space-y-4">
            <div class="flex items-center justify-between gap-2 border-b border-[var(--line)] pb-3">
              <div class="flex items-center gap-2">
                <FileCode class="w-4 h-4 t-visor" />
                <span class="text-xs font-bold uppercase tracking-wider text-[var(--txt)]">
                  {$t('tools.builder.livePreview')}
                </span>
              </div>
              <span class="inline-flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <CheckCircle2 class="w-3 h-3" />
                {$t('tools.builder.validYaml')}
              </span>
            </div>

            <!-- Code View Area -->
            <div class="relative rounded overflow-hidden border border-[var(--line)] bg-[#0d1117]">
              <pre class="p-4 font-mono text-xs text-gray-200 overflow-x-auto {layoutMode === 'cols' ? 'max-h-[600px]' : 'max-h-[500px]'} leading-relaxed select-all"><code>{yamlOutput}</code></pre>
            </div>

            <!-- Action Buttons -->
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
              <button
                on:click={copyToClipboard}
                class="btn btn-sm btn-ghost flex items-center justify-center gap-2 font-mono text-xs border border-[var(--line)]"
              >
                {#if copied}
                  <Check class="w-4 h-4 text-emerald-400" />
                  <span class="text-emerald-400 font-bold">{$t('tools.builder.copied')}</span>
                {:else}
                  <Copy class="w-4 h-4" />
                  <span>{$t('tools.builder.copyYaml')}</span>
                {/if}
              </button>

              <button
                on:click={downloadFile}
                class="btn btn-sm btn-primary flex items-center justify-center gap-2 text-xs"
              >
                <Download class="w-4 h-4" />
                <span>{$t('tools.builder.downloadYaml')}</span>
              </button>
            </div>
          </div>

          <div class="plate plate-deep p-4 text-xs t-muted space-y-1">
            <div class="flex items-center gap-1.5 font-bold t-txt">
              <HelpCircle class="w-3.5 h-3.5 t-visor" />
              <span>Onde salvar este arquivo?</span>
            </div>
            <p>
              Salve o arquivo gerado exatamente como <code class="font-mono text-emerald-400">project-info.yml</code> na raiz do repositório no GitLab. O Daileon irá indexá-lo na próxima sincronização.
            </p>
          </div>
        </div>
      </div>
    {/if}

  </div>

  <!-- Floating Sticky Footer Drawer (When layoutMode === 'drawer') -->
  {#if layoutMode === 'drawer'}
    <div class="fixed bottom-0 left-0 right-0 z-40 px-4 pb-2">
      <div class="max-w-5xl mx-auto plate border-t-2 border-[var(--line)] shadow-2xl backdrop-blur-2xl transition-all duration-300">
        <!-- Header da Gaveta -->
        <div class="p-3 bg-[var(--card)] flex items-center justify-between gap-4 border-b border-[var(--line)]">
          <div class="flex items-center gap-3">
            <button
              on:click={() => (drawerOpen = !drawerOpen)}
              class="flex items-center gap-2 font-bold text-xs t-txt hover:text-[var(--visor)]"
            >
              <FileCode class="w-4 h-4 t-visor" />
              <span>{$t('tools.builder.livePreview')}</span>
              {#if drawerOpen}
                <ChevronDown class="w-4 h-4" />
              {:else}
                <ChevronUp class="w-4 h-4" />
              {/if}
            </button>

            <span class="inline-flex items-center gap-1 text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <CheckCircle2 class="w-3 h-3" />
              Válido
            </span>
          </div>

          <div class="flex items-center gap-2">
            <button
              on:click={copyToClipboard}
              class="btn btn-sm btn-ghost px-2.5 text-xs font-mono border border-[var(--line)]"
            >
              {#if copied}
                <Check class="w-3.5 h-3.5 text-emerald-400" />
                <span class="text-emerald-400 font-bold">{$t('tools.builder.copied')}</span>
              {:else}
                <Copy class="w-3.5 h-3.5" />
                <span>{$t('tools.builder.copyYaml')}</span>
              {/if}
            </button>

            <button
              on:click={downloadFile}
              class="btn btn-sm btn-primary px-3 text-xs flex items-center gap-1"
            >
              <Download class="w-3.5 h-3.5" />
              <span>{$t('tools.builder.downloadYaml')}</span>
            </button>
          </div>
        </div>

        <!-- Conteúdo Expansível da Gaveta -->
        {#if drawerOpen}
          <div class="p-4 bg-[#0d1117] max-h-72 overflow-y-auto">
            <pre class="font-mono text-xs text-gray-200 leading-relaxed select-all"><code>{yamlOutput}</code></pre>
          </div>
        {/if}
      </div>
    </div>
  {/if}
</div>
