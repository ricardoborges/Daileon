from typing import Optional
from fastapi import APIRouter
from app.core.plugins.plugin_interface import IntegrationPlugin
from app.plugins.zabbix.router import zabbix_router

class ZabbixPlugin(IntegrationPlugin):
    @property
    def plugin_id(self) -> str:
        return "zabbix"

    @property
    def name(self) -> str:
        return "Zabbix Infrastructure & Observability"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def category(self) -> str:
        return "observability"

    @property
    def router(self) -> Optional[APIRouter]:
        return zabbix_router
