<script lang="ts">
  import { t } from '$lib/i18n';
  import { Copy, Check, Download, FileCode, BookOpen, Layers, Server, Terminal, Shield, Workflow, Link as LinkIcon, Cpu } from 'lucide-svelte';

  const defaultTemplateYaml = `apiVersion: daileon/v1
kind: Component
metadata:
  name: meu-projeto-exemplo
  description: "Descrição sucinta do propósito do projeto e das tecnologias utilizadas."
  tags:
    - python
    - fastapi
    - sveltekit
    - dev-portal
    - gitlab
  owner: team-platform-engineering
  domain: internal-tooling

spec:
  type: website
  lifecycle: production
  system: platform-engineering
  
  docs:
    dir: /docs
    index: index.md
  
  links:
    - url: http://localhost:8000/docs
      title: FastAPI OpenAPI Specs
      icon: api

  dependencies:
    - component: gitlab-api

  jenkins:
    pipelines:
      - name: Pipeline de Produção
        environment: production
        job: "deployments/daileon-prod"
      - name: Testes Automáticos & CI
        environment: test
        job: "ci/daileon-ci"

  deployments:
    - environment: production
      url: http://localhost:5173
      server_name: srv-prod-portal01
      server_ip: 192.168.10.100
      os: "Linux Ubuntu 22.04 LTS"
      execution_type: Docker
      port: 5173
      notes: "Ambiente principal de produção"
      
    - environment: test
      url: http://localhost:8000
      server_name: srv-test-portal01
      server_ip: 192.168.20.100
      os: "Windows Server 2022"
      execution_type: VM
      port: 8000
      notes: "Servidor de testes local"
`;

  let copied = false;

  function copyTemplate() {
    navigator.clipboard.writeText(defaultTemplateYaml);
    copied = true;
    setTimeout(() => (copied = false), 2500);
  }

  function downloadTemplate() {
    const blob = new Blob([defaultTemplateYaml], { type: 'text/yaml;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'project-info.yml';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }
</script>

<div class="space-y-8">
  <!-- Visualizador & Ações do Template -->
  <div class="grid grid-cols-1 lg:grid-cols-12 gap-8">
    
    <!-- Code Viewer (Left 7 Cols) -->
    <div class="lg:col-span-7 space-y-4">
      <div class="plate p-6 space-y-4">
        <div class="flex flex-wrap items-center justify-between gap-4 border-b border-[var(--line)] pb-3">
          <div class="flex items-center gap-2">
            <FileCode class="w-4 h-4 t-visor" />
            <span class="text-sm font-bold tracking-tight text-[var(--txt)]">
              project-info.yml (Template de Referência)
            </span>
          </div>

          <div class="flex items-center gap-2">
            <button
              on:click={copyTemplate}
              class="btn btn-sm btn-ghost flex items-center gap-1.5 text-xs font-mono border border-[var(--line)]"
            >
              {#if copied}
                <Check class="w-3.5 h-3.5 t-ok" />
                <span class="t-ok font-bold">{$t('tools.template.copied')}</span>
              {:else}
                <Copy class="w-3.5 h-3.5" />
                <span>{$t('tools.template.copyTemplate')}</span>
              {/if}
            </button>

            <button
              on:click={downloadTemplate}
              class="btn btn-sm btn-primary flex items-center gap-1.5 text-xs"
            >
              <Download class="w-3.5 h-3.5" />
              <span>{$t('tools.template.downloadTemplate')}</span>
            </button>
          </div>
        </div>

        <div class="rounded border border-[var(--line)] code-slab overflow-hidden">
          <pre class="p-5 font-mono text-xs t-txt overflow-x-auto max-h-[580px] leading-relaxed select-all"><code>{defaultTemplateYaml}</code></pre>
        </div>
      </div>
    </div>

    <!-- Guia Rápido & Instruções (Right 5 Cols) -->
    <div class="lg:col-span-5 space-y-6">
      <div class="plate p-6 space-y-4">
        <h3 class="text-sm font-bold uppercase tracking-wider t-visor flex items-center gap-2">
          <BookOpen class="w-4 h-4" />
          {$t('tools.template.guideTitle')}
        </h3>
        <p class="text-xs t-muted leading-relaxed">
          {$t('tools.template.guideSub')}
        </p>

        <div class="space-y-4 pt-2">
          <!-- Kind -->
          <div class="plate plate-deep p-3 space-y-1">
            <div class="flex items-center justify-between">
              <span class="font-mono text-xs font-bold t-ok">kind</span>
              <span class="text-[10px] font-mono uppercase chip chip-ok px-1.5 py-0.5">Component | API | Library | Resource</span>
            </div>
            <p class="text-[11px] t-muted">{$t('tools.template.kindDesc')}</p>
          </div>

          <!-- Type -->
          <div class="plate plate-deep p-3 space-y-1">
            <div class="flex items-center justify-between">
              <span class="font-mono text-xs font-bold t-visor">spec.type</span>
              <span class="text-[10px] font-mono uppercase chip chip-visor px-1.5 py-0.5">service | website | library | cronjob</span>
            </div>
            <p class="text-[11px] t-muted">{$t('tools.template.typeDesc')}</p>
          </div>

          <!-- Lifecycle -->
          <div class="plate plate-deep p-3 space-y-1">
            <div class="flex items-center justify-between">
              <span class="font-mono text-xs font-bold t-crest">spec.lifecycle</span>
              <span class="text-[10px] font-mono uppercase chip chip-crest px-1.5 py-0.5">production | experimental | deprecated</span>
            </div>
            <p class="text-[11px] t-muted">{$t('tools.template.lifecycleDesc')}</p>
          </div>

          <!-- Execution Type -->
          <div class="plate plate-deep p-3 space-y-1">
            <div class="flex items-center justify-between">
              <span class="font-mono text-xs font-bold t-iris">deployments[].execution_type</span>
              <span class="text-[10px] font-mono uppercase chip chip-iris px-1.5 py-0.5">Docker | VM | Bare-Metal | Serverless</span>
            </div>
            <p class="text-[11px] t-muted">{$t('tools.template.execDesc')}</p>
          </div>
        </div>
      </div>
    </div>

  </div>

  <!-- Detalhamento Extenso da Taxonomia -->
  <div class="plate p-8 space-y-6">
    <h3 class="text-base font-bold tracking-tight text-[var(--txt)] flex items-center gap-2 border-b border-[var(--line)] pb-4">
      <Layers class="w-5 h-5 t-visor" />
      <span>Estrutura Completa de Campos do Manifesto</span>
    </h3>

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      
      <!-- Metadata -->
      <div class="space-y-2">
        <div class="flex items-center gap-2 text-xs font-bold uppercase tracking-wider t-visor">
          <Shield class="w-4 h-4" />
          <span>metadata</span>
        </div>
        <ul class="text-xs space-y-1.5 t-dim font-mono">
          <li><b class="t-txt font-sans">name:</b> Nome único do repositório/serviço.</li>
          <li><b class="t-txt font-sans">description:</b> Explicação técnica do projeto.</li>
          <li><b class="t-txt font-sans">tags:</b> Lista de tecnologias e tags.</li>
          <li><b class="t-txt font-sans">owner:</b> Time ou mantenedor responsável.</li>
          <li><b class="t-txt font-sans">domain:</b> Domínio funcional de negócio.</li>
        </ul>
      </div>

      <!-- Spec & Docs -->
      <div class="space-y-2">
        <div class="flex items-center gap-2 text-xs font-bold uppercase tracking-wider t-visor">
          <Terminal class="w-4 h-4" />
          <span>spec & docs</span>
        </div>
        <ul class="text-xs space-y-1.5 t-dim font-mono">
          <li><b class="t-txt font-sans">type:</b> Tipo da aplicação (service/website/etc).</li>
          <li><b class="t-txt font-sans">lifecycle:</b> Fase do ciclo (production/etc).</li>
          <li><b class="t-txt font-sans">system:</b> Agrupador do sistema pai.</li>
          <li><b class="t-txt font-sans">docs.dir:</b> Pasta com docs Markdown (/docs).</li>
          <li><b class="t-txt font-sans">docs.index:</b> Arquivo principal de entrada.</li>
        </ul>
      </div>

      <!-- Deployments -->
      <div class="space-y-2">
        <div class="flex items-center gap-2 text-xs font-bold uppercase tracking-wider t-visor">
          <Server class="w-4 h-4" />
          <span>deployments</span>
        </div>
        <ul class="text-xs space-y-1.5 t-dim font-mono">
          <li><b class="t-txt font-sans">environment:</b> production, staging, test, dev.</li>
          <li><b class="t-txt font-sans">server_name:</b> Nome de host do servidor.</li>
          <li><b class="t-txt font-sans">server_ip:</b> IP de rede do servidor.</li>
          <li><b class="t-txt font-sans">os:</b> Sistema operacional da máquina.</li>
          <li><b class="t-txt font-sans">execution_type:</b> Docker, VM, Bare-Metal.</li>
          <li><b class="t-txt font-sans">port:</b> Porta alocada da aplicação.</li>
        </ul>
      </div>

      <!-- Jenkins -->
      <div class="space-y-2">
        <div class="flex items-center gap-2 text-xs font-bold uppercase tracking-wider t-visor">
          <Workflow class="w-4 h-4" />
          <span>jenkins</span>
        </div>
        <ul class="text-xs space-y-1.5 t-dim font-mono">
          <li><b class="t-txt font-sans">pipelines[].name:</b> Nome legível da pipeline.</li>
          <li><b class="t-txt font-sans">pipelines[].environment:</b> Ambiente associado.</li>
          <li><b class="t-txt font-sans">pipelines[].job:</b> Caminho do Job no Jenkins.</li>
        </ul>
      </div>

      <!-- Links & Dependencies -->
      <div class="space-y-2">
        <div class="flex items-center gap-2 text-xs font-bold uppercase tracking-wider t-visor">
          <LinkIcon class="w-4 h-4" />
          <span>links & dependencies</span>
        </div>
        <ul class="text-xs space-y-1.5 t-dim font-mono">
          <li><b class="t-txt font-sans">links[].url:</b> Endereço web externo/interno.</li>
          <li><b class="t-txt font-sans">links[].title:</b> Título exibido no card.</li>
          <li><b class="t-txt font-sans">links[].icon:</b> api, docs, dashboard, etc.</li>
          <li><b class="t-txt font-sans">dependencies[].component:</b> Nome de dependência.</li>
        </ul>
      </div>

    </div>
  </div>
</div>
