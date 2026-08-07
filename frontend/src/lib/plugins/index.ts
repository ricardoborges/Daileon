import { pluginRegistry } from './registry';
import JenkinsTab from './jenkins/JenkinsTab.svelte';
import CommitsTab from './gitlab/CommitsTab.svelte';
import LdapConfig from './ldap/LdapConfig.svelte';
import PortainerConfig from './portainer/PortainerConfig.svelte';
import PortainerTab from './portainer/PortainerTab.svelte';

import { Shield, FolderGit2, PlayCircle, Activity } from 'lucide-svelte';

export function initializeFrontendPlugins() {
  // Plugin 1: LDAP
  pluginRegistry.register({
    id: 'ldap',
    name: 'LDAP / Active Directory',
    version: '1.0.0',
    description: 'Autenticação centralizada e consulta de usuários via protocolo LDAP.',
    category: 'auth',
    icon: Shield,
    configComponent: LdapConfig
  });

  // Plugin 2: GitLab
  pluginRegistry.register({
    id: 'gitlab',
    name: 'GitLab SCM & Catalog',
    version: '1.0.0',
    description: 'Descoberta automatizada de projetos, leitura de project-info.yml e varredura de riscos.',
    category: 'scm',
    icon: FolderGit2,
    tabs: [
      {
        id: 'commits',
        label: 'Commits',
        component: CommitsTab,
        isVisible: (component) => Boolean(component.gitlab_project_id)
      }
    ]
  });

  // Plugin 3: Jenkins
  pluginRegistry.register({
    id: 'jenkins',
    name: 'Jenkins CI/CD',
    version: '1.0.0',
    description: 'Monitoramento em tempo real do status de jobs e pipelines de integração contínua.',
    category: 'cicd',
    icon: PlayCircle,
    tabs: [
      {
        id: 'jenkins',
        label: 'Jenkins',
        component: JenkinsTab,
        isVisible: (component) => Boolean((component as any).jenkins_pipelines && (component as any).jenkins_pipelines.length > 0)
      }
    ]
  });

  // Plugin 4: Portainer
  pluginRegistry.register({
    id: 'portainer',
    name: 'Portainer Observability',
    version: '1.0.0',
    description: 'Observabilidade de containers Docker, métricas de CPU/RAM em tempo real e logs.',
    category: 'observability',
    icon: Activity,
    configComponent: PortainerConfig,
    tabs: [
      {
        id: 'portainer',
        label: 'Portainer',
        component: PortainerTab,
        isVisible: () => true
      }
    ]
  });
}


initializeFrontendPlugins();

export { pluginRegistry };
