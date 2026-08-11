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
    component?: string;
    external?: string;
    resource?: string;
    isExternal?: boolean;
    isResource?: boolean;
    type?: 'component' | 'external' | 'resource';
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
  let solution = 'Strix';
  
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

  let dependents: DependencyItem[] = [
    { component: 'IDEA 2', external: 'IDEA 2', isExternal: true }
  ];

  let copied = false;

  const kindOptions = ['Component', 'API', 'Library', 'Resource', 'System'];
  const typeOptions = ['service', 'website', 'library', 'cronjob', 'database', 'mobile', 'cli'];
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
    solution,
    docsDir,
    docsIndex,
    deployments,
    jenkinsPipelines,
    links,
    dependencies,
    dependents
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
    if (data.solution) {
      lines.push(`  solution: ${data.solution}`);
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
        if (d.isResource || d.resource || d.type === 'resource') {
          lines.push(`    - resource: ${d.resource || d.component || d.external || ''}`);
        } else if (d.isExternal || d.external || d.type === 'external') {
          lines.push(`    - external: ${d.external || d.component || ''}`);
        } else if (d.component) {
          lines.push(`    - component: ${d.component}`);
        }
      });
    }

    if (data.dependents && data.dependents.length > 0) {
      lines.push('  ');
      lines.push('  dependents:');
      data.dependents.forEach((d: DependencyItem) => {
        if (d.isResource || d.resource || d.type === 'resource') {
          lines.push(`    - resource: ${d.resource || d.component || d.external || ''}`);
        } else if (d.isExternal || d.external || d.type === 'external') {
          lines.push(`    - external: ${d.external || d.component || ''}`);
        } else if (d.component) {
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

  function loadPreset(preset: 'web' | 'api' | 'job' | 'resource' | 'clear') {
    if (preset === 'clear') {
      kind = 'Component';
      name = '';
      description = '';
      owner = '';
      domain = '';
      tags = '';
      type = 'service';
      lifecycle = 'production';
      solution = '';
      docsDir = '/docs';
      docsIndex = 'index.md';
      deployments = [];
      jenkinsPipelines = [];
      links = [];
      dependencies = [];
      dependents = [];
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
      solution = 'customer-portal';
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
      solution = 'payment-gateway';
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
      solution = 'data-lake';
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
    } else if (preset === 'resource') {
      kind = 'Resource';
      name = 'bc-ccs';
      description = 'Serviço e recurso compartilhado de consulta de relacionamentos no CCS do BACEN.';
      owner = 'team-platform-engineering';
      domain = 'banking-services';
      tags = 'resource, bacen, ccs, shared-service';
      type = 'service';
      lifecycle = 'production';
      solution = 'bacen-integration';
      docsDir = '/docs';
      docsIndex = 'index.md';
      deployments = [
        {
          environment: 'production',
          server_name: 'srv-prod-res01',
          server_ip: '10.0.5.10',
          os: 'Linux Ubuntu 22.04 LTS',
          execution_type: 'Docker',
          port: '8443',
          url: 'https://bc-ccs.empresa.com',
          notes: 'Serviço de infraestrutura de consulta CCS'
        }
      ];
      jenkinsPipelines = [];
      links = [
        { title: 'Painel BACEN CCS', url: 'https://bc-ccs.empresa.com/status', icon: 'dashboard' }
      ];
      dependencies = [
        { resource: 'Credilink', isResource: true, type: 'resource' },
        { resource: 'enviosms', isResource: true, type: 'resource' }
      ];
      dependents = [
        { component: 'strix-api' }
      ];
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

  function addDependent() {
    dependents = [...dependents, { component: '' }];
  }

  function removeDependent(index: number) {
    dependents = dependents.filter((_, i) => i !== index);
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
      <button on:click={() => loadPreset('resource')} class="btn btn-sm btn-ghost text-xs">
        Recurso / Infra
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
        <div class="form-head">
          <h3>
            {$t('tools.builder.secMetadata')}
          </h3>
        </div>

        <div class="form-grid form-grid-2">
          <div class="form-row">
            <label for="builder-name" class="field-label">{$t('tools.builder.name')} <span class="t-alert">*</span></label>
            <input
              id="builder-name"
              type="text"
              bind:value={name}
              placeholder={$t('tools.builder.namePlaceholder')}
              class="field"
            />
            <p class="field-help">{$t('tools.builder.nameHelp')}</p>
          </div>

          <div class="form-row">
            <label for="builder-kind" class="field-label">{$t('tools.builder.kind')} <span class="t-alert">*</span></label>
            <select id="builder-kind" bind:value={kind} class="field">
              {#each kindOptions as opt}
                <option value={opt}>{opt}</option>
              {/each}
            </select>
            <p class="field-help">{$t('tools.builder.kindHelp')}</p>
          </div>

          <div class="form-row">
            <label for="builder-owner" class="field-label">{$t('tools.builder.owner')} <span class="t-alert">*</span></label>
            <input
              id="builder-owner"
              type="text"
              bind:value={owner}
              placeholder={$t('tools.builder.ownerPlaceholder')}
              class="field"
            />
          </div>

          <div class="form-row">
            <label for="builder-domain" class="field-label">{$t('tools.builder.domain')}</label>
            <input
              id="builder-domain"
              type="text"
              bind:value={domain}
              placeholder={$t('tools.builder.domainPlaceholder')}
              class="field"
            />
          </div>
        </div>

        <div class="form-row">
          <label for="builder-tags" class="field-label">{$t('tools.builder.tags')}</label>
          <input
            id="builder-tags"
            type="text"
            bind:value={tags}
            placeholder={$t('tools.builder.tagsPlaceholder')}
            class="field"
          />
        </div>

        <div class="form-row">
          <label for="builder-description" class="field-label">{$t('tools.builder.description')}</label>
          <textarea
            id="builder-description"
            bind:value={description}
            rows="2"
            placeholder={$t('tools.builder.descriptionPlaceholder')}
            class="field"
          ></textarea>
        </div>
      </div>

      <!-- Sec 2: Especificação & Ciclo de Vida -->
      <div class="plate p-6 space-y-4">
        <div class="form-head">
          <h3>
          {$t('tools.builder.secSpec')}
          </h3>
        </div>

        <div class="form-grid form-grid-3">
          <div class="form-row">
            <label for="builder-type" class="field-label">{$t('tools.builder.type')} <span class="t-alert">*</span></label>
            <select id="builder-type" bind:value={type} class="field">
              {#each typeOptions as opt}
                <option value={opt}>{opt}</option>
              {/each}
            </select>
            <p class="field-help">{$t('tools.builder.typeHelp')}</p>
          </div>

          <div class="form-row">
            <label for="builder-lifecycle" class="field-label">{$t('tools.builder.lifecycle')} <span class="t-alert">*</span></label>
            <select id="builder-lifecycle" bind:value={lifecycle} class="field">
              {#each lifecycleOptions as opt}
                <option value={opt}>{opt}</option>
              {/each}
            </select>
            <p class="field-help">{$t('tools.builder.lifecycleHelp')}</p>
          </div>

          <div class="form-row">
            <label for="builder-solution" class="field-label">{$t('tools.builder.solution')}</label>
            <input
              id="builder-solution"
              type="text"
              bind:value={solution}
              placeholder={$t('tools.builder.solutionPlaceholder')}
              class="field"
            />
          </div>
        </div>
      </div>

      <!-- Sec 3: Documentação Técnica (TechDocs) -->
      <div class="plate p-6 space-y-4">
        <div class="form-head">
          <h3>
          {$t('tools.builder.secDocs')}
          </h3>
        </div>

        <div class="form-grid form-grid-2">
          <div class="form-row">
            <label for="builder-docsdir" class="field-label">{$t('tools.builder.docsDir')}</label>
            <input
              id="builder-docsdir"
              type="text"
              bind:value={docsDir}
              placeholder="/docs"
              class="field field-mono"
            />
          </div>

          <div class="form-row">
            <label for="builder-docsindex" class="field-label">{$t('tools.builder.docsIndex')}</label>
            <input
              id="builder-docsindex"
              type="text"
              bind:value={docsIndex}
              placeholder="index.md"
              class="field field-mono"
            />
          </div>
        </div>
      </div>

      <!-- Sec 4: Deployments -->
      <div class="plate p-6 space-y-4">
        <div class="form-head">
          <h3>
            {$t('tools.builder.secDeployments')}
          </h3>
          <button on:click={addDeployment} class="btn btn-sm btn-ghost text-xs flex items-center gap-1">
            <Plus class="w-3.5 h-3.5" />
            <span>{$t('tools.builder.addDeployment')}</span>
          </button>
        </div>

        {#if deployments.length === 0}
          <p class="field-help italic">{ $t('tools.builder.noDeployments') }</p>
        {:else}
          <div class="space-y-4">
            {#each deployments as dep, i}
              <div class="plate plate-deep p-4 space-y-3 relative group">
                <button
                  on:click={() => removeDeployment(i)}
                  title="Remover Ambiente"
                  aria-label="Remover Ambiente"
                  class="absolute top-3 right-3 t-alert hover:opacity-70 p-1 transition-colors"
                >
                  <Trash2 class="w-4 h-4" />
                </button>

                <span class="inline-block text-[11px] font-mono font-bold uppercase px-2 py-0.5 rounded bg-[var(--card)] border border-[var(--line)]">
                  # {i + 1} - {dep.environment || 'production'}
                </span>

                <div class="form-grid form-grid-3">
                  <div class="form-row">
                    <label for={`dep-env-${i}`} class="field-label">{$t('tools.builder.envName')}</label>
                    <select id={`dep-env-${i}`} bind:value={dep.environment} class="field">
                      {#each environmentOptions as envOpt}
                        <option value={envOpt}>{envOpt}</option>
                      {/each}
                    </select>
                  </div>

                  <div class="form-row">
                    <label for={`dep-server-${i}`} class="field-label">{$t('tools.builder.serverName')}</label>
                    <input
                      id={`dep-server-${i}`}
                      type="text"
                      bind:value={dep.server_name}
                      placeholder="ex: srv-prod-01"
                      class="field field-mono"
                    />
                  </div>

                  <div class="form-row">
                    <label for={`dep-ip-${i}`} class="field-label">{$t('tools.builder.serverIp')}</label>
                    <input
                      id={`dep-ip-${i}`}
                      type="text"
                      bind:value={dep.server_ip}
                      placeholder="ex: 192.168.1.50"
                      class="field field-mono"
                    />
                  </div>

                  <div class="form-row">
                    <label for={`dep-[exec]-${i}`} class="field-label">{$t('tools.builder.executionType')}</label>
                    <select id={`dep-[exec]-${i}`} bind:value={dep.execution_type} class="field">
                      {#each executionTypeOptions as execOpt}
                        <option value={execOpt}>{execOpt}</option>
                      {/each}
                    </select>
                  </div>

                  <div class="form-row">
                    <label for={`dep-os-${i}`} class="field-label">{$t('tools.builder.os')}</label>
                    <input
                      id={`dep-os-${i}`}
                      type="text"
                      bind:value={dep.os}
                      placeholder="ex: Ubuntu 22.04 LTS"
                      class="field"
                    />
                  </div>

                  <div class="form-row">
                    <label for={`dep-port-${i}`} class="field-label">{$t('tools.builder.port')}</label>
                    <input
                      id={`dep-port-${i}`}
                      type="text"
                      bind:value={dep.port}
                      placeholder="ex: 8080"
                      class="field field-mono"
                    />
                  </div>
                </div>

                <div class="form-grid form-grid-2">
                  <div class="form-row">
                    <label for={`dep-url-${i}`} class="field-label">{$t('tools.builder.url')}</label>
                    <input
                      id={`dep-url-${i}`}
                      type="text"
                      bind:value={dep.url}
                      placeholder="ex: http://srv-prod-01:8080"
                      class="field field-mono"
                    />
                  </div>

                  <div class="form-row">
                    <label for={`dep-notes-${i}`} class="field-label">{$t('tools.builder.notes')}</label>
                    <input
                      id={`dep-notes-${i}`}
                      type="text"
                      bind:value={dep.notes}
                      placeholder="ex: Cluster principal com backup automático"
                      class="field"
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
        <div class="form-head">
          <h3>
            {$t('tools.builder.secJenkins')}
          </h3>
          <button on:click={addJenkinsPipeline} class="btn btn-sm btn-ghost text-xs flex items-center gap-1">
            <Plus class="w-3.5 h-3.5" />
            <span>{$t('tools.builder.addPipeline')}</span>
          </button>
        </div>

        {#if jenkinsPipelines.length === 0}
          <p class="field-help italic">{$t('tools.builder.noPipelines')}</p>
        {:else}
          <div class="space-y-3">
            {#each jenkinsPipelines as pipe, j}
              <div class="plate plate-deep p-3 flex flex-col sm:flex-row items-stretch sm:items-center gap-3 relative group">
                <div class="form-grid form-grid-3 flex-1">
                  <input
                    type="text"
                    bind:value={pipe.name}
                    placeholder={$t('tools.builder.pipelineName')}
                    class="field"
                  />
                  <select bind:value={pipe.environment} class="field">
                    {#each environmentOptions as envOpt}
                      <option value={envOpt}>{envOpt}</option>
                    {/each}
                  </select>
                  <input
                    type="text"
                    bind:value={pipe.job}
                    placeholder={$t('tools.builder.jobPath')}
                    class="field field-mono"
                  />
                </div>
                <button
                  on:click={() => removeJenkinsPipeline(j)}
                  title="Remover Pipeline"
                  aria-label="Remover Pipeline"
                  class="t-alert hover:opacity-70 p-1 transition-colors self-end sm:self-center"
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
          <div class="form-head">
            <h3>
              {$t('tools.builder.secLinks')}
            </h3>
            <button on:click={addLink} class="btn btn-sm btn-ghost text-xs flex items-center gap-1">
              <Plus class="w-3.5 h-3.5" />
              <span>{$t('tools.builder.addLink')}</span>
            </button>
          </div>

          {#if links.length === 0}
            <p class="field-help italic">{$t('tools.builder.noLinks')}</p>
          {:else}
            <div class="space-y-3">
              {#each links as link, l}
                <div class="plate plate-deep p-3 flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
                  <input
                    type="text"
                    bind:value={link.title}
                    placeholder={$t('tools.builder.linkTitle')}
                    class="field flex-1"
                  />
                  <input
                    type="text"
                    bind:value={link.url}
                    placeholder={$t('tools.builder.linkUrl')}
                    class="field field-mono flex-1"
                  />
                  <select bind:value={link.icon} class="field w-full sm:w-36">
                    {#each iconOptions as ico}
                      <option value={ico}>{ico}</option>
                    {/each}
                  </select>
                  <button
                    on:click={() => removeLink(l)}
                    title="Remover Link"
                    aria-label="Remover Link"
                    class="t-alert hover:opacity-70 p-1 transition-colors self-end sm:self-center"
                  >
                    <Trash2 class="w-4 h-4" />
                  </button>
                </div>
              {/each}
            </div>
          {/if}
        </div>

        <div class="border-t border-[var(--line)] pt-4 space-y-4">
          <div class="form-head">
            <h3>
              Dependências de Software
            </h3>
            <button on:click={addDependency} class="btn btn-sm btn-ghost text-xs flex items-center gap-1">
              <Plus class="w-3.5 h-3.5" />
              <span>{$t('tools.builder.addDependency')}</span>
            </button>
          </div>

          {#if dependencies.length === 0}
            <p class="field-help italic">{$t('tools.builder.noDependencies')}</p>
          {:else}
            <div class="space-y-2">
              {#each dependencies as dep, d}
                <div class="flex items-center gap-2">
                  <input
                    type="text"
                    value={dep.isResource ? (dep.resource || '') : dep.isExternal ? (dep.external || '') : (dep.component || '')}
                    on:input={(e) => {
                      const val = e.currentTarget.value;
                      if (dep.isResource) {
                        dep.resource = val;
                      } else if (dep.isExternal) {
                        dep.external = val;
                      } else {
                        dep.component = val;
                      }
                    }}
                    placeholder={dep.isResource ? "Nome do recurso (ex: bc-ccs, Credilink)" : dep.isExternal ? "Nome do projeto externo (ex: Redmine)" : $t('tools.builder.depComponent')}
                    class="field field-mono flex-1"
                  />
                  <select
                    value={dep.isResource ? 'resource' : dep.isExternal ? 'external' : 'component'}
                    on:change={(e) => {
                      const mode = e.currentTarget.value;
                      const currentVal = dep.resource || dep.external || dep.component || '';
                      dep.isResource = mode === 'resource';
                      dep.isExternal = mode === 'external';
                      dep.resource = mode === 'resource' ? currentVal : '';
                      dep.external = mode === 'external' ? currentVal : '';
                      dep.component = mode === 'component' ? currentVal : '';
                    }}
                    class="field text-xs py-1 px-2 select-none bg-[var(--card)] border border-[var(--line)] rounded"
                  >
                    <option value="component">Componente</option>
                    <option value="external">Externo</option>
                    <option value="resource">Recurso</option>
                  </select>
                  <button
                    on:click={() => removeDependency(d)}
                    title="Remover Dependência"
                    aria-label="Remover Dependência"
                    class="t-alert hover:opacity-70 p-1 transition-colors"
                  >
                    <Trash2 class="w-4 h-4" />
                  </button>
                </div>
              {/each}
            </div>
          {/if}
        </div>

        <!-- Componentes Dependentes (Quem depende deste projeto) -->
        <div class="border-t border-[var(--line)] pt-4 space-y-4">
          <div class="form-head">
            <h3>
              Dependentes (Projetos que dependem do nosso)
            </h3>
            <button on:click={addDependent} class="btn btn-sm btn-ghost text-xs flex items-center gap-1">
              <Plus class="w-3.5 h-3.5" />
              <span>+ Adicionar Dependente</span>
            </button>
          </div>

          {#if dependents.length === 0}
            <p class="field-help italic">Nenhum componente dependente adicionado.</p>
          {:else}
            <div class="space-y-2">
              {#each dependents as dep, d}
                <div class="flex items-center gap-2">
                  <input
                    type="text"
                    value={dep.isResource ? (dep.resource || '') : dep.isExternal ? (dep.external || '') : (dep.component || '')}
                    on:input={(e) => {
                      const val = e.currentTarget.value;
                      if (dep.isResource) {
                        dep.resource = val;
                      } else if (dep.isExternal) {
                        dep.external = val;
                      } else {
                        dep.component = val;
                      }
                    }}
                    placeholder={dep.isResource ? "Nome do recurso dependente (ex: bc-ccs)" : dep.isExternal ? "Nome do projeto externo dependente (ex: IDEA 2)" : "Nome do componente dependente (ex: strix-api)"}
                    class="field field-mono flex-1"
                  />
                  <select
                    value={dep.isResource ? 'resource' : dep.isExternal ? 'external' : 'component'}
                    on:change={(e) => {
                      const mode = e.currentTarget.value;
                      const currentVal = dep.resource || dep.external || dep.component || '';
                      dep.isResource = mode === 'resource';
                      dep.isExternal = mode === 'external';
                      dep.resource = mode === 'resource' ? currentVal : '';
                      dep.external = mode === 'external' ? currentVal : '';
                      dep.component = mode === 'component' ? currentVal : '';
                    }}
                    class="field text-xs py-1 px-2 select-none bg-[var(--card)] border border-[var(--line)] rounded"
                  >
                    <option value="component">Componente</option>
                    <option value="external">Externo</option>
                    <option value="resource">Recurso</option>
                  </select>
                  <button
                    on:click={() => removeDependent(d)}
                    title="Remover Dependente"
                    aria-label="Remover Dependente"
                    class="t-alert hover:opacity-70 p-1 transition-colors"
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
              <span class="inline-flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded chip chip-ok">
                <CheckCircle2 class="w-3 h-3" />
                {$t('tools.builder.validYaml')}
              </span>
            </div>

            <!-- Code View Area -->
            <div class="relative rounded overflow-hidden border border-[var(--line)] code-slab">
              <pre class="p-4 font-mono text-xs t-txt overflow-x-auto {layoutMode === 'cols' ? 'max-h-[600px]' : 'max-h-[500px]'} leading-relaxed select-all"><code>{yamlOutput}</code></pre>
            </div>

            <!-- Action Buttons -->
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
              <button
                on:click={copyToClipboard}
                class="btn btn-sm btn-ghost flex items-center justify-center gap-2 font-mono text-xs border border-[var(--line)]"
              >
                {#if copied}
                  <Check class="w-4 h-4 t-ok" />
                  <span class="t-ok font-bold">{$t('tools.builder.copied')}</span>
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
              Salve o arquivo gerado exatamente como <code class="font-mono t-ok">project-info.yml</code> na raiz do repositório no GitLab. O Daileon irá indexá-lo na próxima sincronização.
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

            <span class="inline-flex items-center gap-1 text-[10px] font-mono px-1.5 py-0.5 rounded chip chip-ok">
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
                <Check class="w-3.5 h-3.5 t-ok" />
                <span class="t-ok font-bold">{$t('tools.builder.copied')}</span>
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
          <div class="p-4 code-slab max-h-72 overflow-y-auto">
            <pre class="font-mono text-xs t-txt leading-relaxed select-all"><code>{yamlOutput}</code></pre>
          </div>
        {/if}
      </div>
    </div>
  {/if}
</div>
