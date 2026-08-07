import logging
from typing import Dict, List, Optional, Type, Any
from fastapi import FastAPI, APIRouter

from app.core.plugins.plugin_interface import BasePlugin, AuthProviderPlugin, ScmCrawlerPlugin, IntegrationPlugin

logger = logging.getLogger("daileon.plugins")

class PluginManager:
    """Gerenciador central de plugins do Daileon."""

    def __init__(self):
        self._plugins: Dict[str, BasePlugin] = {}
        self._auth_providers: Dict[str, AuthProviderPlugin] = {}
        self._scm_crawlers: Dict[str, ScmCrawlerPlugin] = {}
        self._integrations: Dict[str, IntegrationPlugin] = {}

    def register_plugin(self, plugin: BasePlugin) -> None:
        """Registra uma instância de plugin no gerenciador."""
        pid = plugin.plugin_id
        if pid in self._plugins:
            logger.warning(f"Plugin '{pid}' já registrado. Sobrescrevendo...")
            
        self._plugins[pid] = plugin
        logger.info(f"Plugin registrado: {plugin.name} ({pid}) v{plugin.version}")

        if isinstance(plugin, AuthProviderPlugin):
            self._auth_providers[pid] = plugin
        if isinstance(plugin, ScmCrawlerPlugin):
            self._scm_crawlers[pid] = plugin
        if isinstance(plugin, IntegrationPlugin):
            self._integrations[pid] = plugin

    def get_plugin(self, plugin_id: str) -> Optional[BasePlugin]:
        return self._plugins.get(plugin_id)

    def get_auth_provider(self, plugin_id: str) -> Optional[AuthProviderPlugin]:
        return self._auth_providers.get(plugin_id)

    def get_scm_crawler(self, plugin_id: str) -> Optional[ScmCrawlerPlugin]:
        return self._scm_crawlers.get(plugin_id)

    def list_plugins(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": p.plugin_id,
                "name": p.name,
                "version": p.version,
                "type": p.__class__.__name__,
                "category": getattr(p, "category", "auth" if isinstance(p, AuthProviderPlugin) else "scm" if isinstance(p, ScmCrawlerPlugin) else "general"),
                "has_router": p.router is not None,
                "status": "active"
            }
            for p in self._plugins.values()
        ]

    def register_routes(self, master_router: APIRouter) -> None:
        """Monta os roteadores de todos os plugins no roteador principal da API."""
        for p in self._plugins.values():
            if p.router:
                master_router.include_router(p.router)
                logger.info(f"Rotas do plugin '{p.plugin_id}' montadas com sucesso.")

    async def initialize_all(self) -> None:
        """Executa a rotina de inicialização de cada plugin registrado."""
        for p in self._plugins.values():
            try:
                await p.initialize()
            except Exception as e:
                logger.error(f"Erro ao inicializar plugin '{p.plugin_id}': {e}")


plugin_manager = PluginManager()
