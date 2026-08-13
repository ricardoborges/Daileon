from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from fastapi import APIRouter

class BasePlugin(ABC):
    """Classe base para todos os plugins do Daileon."""
    
    @property
    @abstractmethod
    def plugin_id(self) -> str:
        """ID único do plugin (ex: 'ldap', 'gitlab', 'jenkins')."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Nome legível do plugin."""
        pass

    @property
    def version(self) -> str:
        """Versão do plugin."""
        return "1.0.0"

    @property
    def router(self) -> Optional[APIRouter]:
        """APIRouter opcional com os endpoints expostos pelo plugin."""
        return None

    async def initialize(self) -> None:
        """Hook chamado na inicialização do plugin."""
        pass


class AuthProviderPlugin(BasePlugin):
    """Interface para plugins de autenticação (LDAP, OAuth2, Keycloak, etc)."""
    
    @abstractmethod
    def authenticate(self, config: Dict[str, Any], username: str, password: str) -> Dict[str, Any]:
        """Tenta autenticar as credenciais fornecidas.
        Retorna ditado com 'success', 'user' e 'message'.
        """
        pass


class ScmCrawlerPlugin(BasePlugin):
    """Interface para provedores de código / SCM (GitLab, GitHub, Bitbucket)."""

    @abstractmethod
    async def fetch_projects(self) -> List[Dict[str, Any]]:
        """Busca lista de projetos/repositórios acessíveis."""
        pass


class IntegrationPlugin(BasePlugin):
    """Interface para plugins de integração (Jenkins, Portainer, Zabbix, etc)."""

    @property
    def category(self) -> str:
        """Categoria da integração: 'cicd', 'observability', 'infra', etc."""
        return "general"
