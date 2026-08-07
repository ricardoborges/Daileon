from app.core.plugins.plugin_interface import BasePlugin, AuthProviderPlugin, ScmCrawlerPlugin, IntegrationPlugin
from app.core.plugins.manager import plugin_manager, PluginManager

__all__ = [
    "BasePlugin",
    "AuthProviderPlugin",
    "ScmCrawlerPlugin",
    "IntegrationPlugin",
    "plugin_manager",
    "PluginManager",
]
