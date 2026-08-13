from typing import Optional
from fastapi import APIRouter
from app.core.plugins.plugin_interface import IntegrationPlugin
from app.plugins.portainer.router import portainer_router

class PortainerPlugin(IntegrationPlugin):
    @property
    def plugin_id(self) -> str:
        return "portainer"

    @property
    def name(self) -> str:
        return "Portainer Container Observability"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def category(self) -> str:
        return "observability"

    @property
    def router(self) -> Optional[APIRouter]:
        return portainer_router
