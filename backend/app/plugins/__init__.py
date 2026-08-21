import logging
from app.core.plugins import plugin_manager
from app.plugins.ldap import LDAPPlugin
from app.plugins.gitlab import GitLabPlugin
from app.plugins.jenkins import JenkinsPlugin
from app.plugins.portainer import PortainerPlugin
from app.plugins.zabbix import ZabbixPlugin

logger = logging.getLogger("daileon.plugins")

def register_builtin_plugins() -> None:
    """Registra todos os plugins builtin (LDAP, GitLab, Jenkins, Portainer, Zabbix) no PluginManager."""
    logger.info("Registrando plugins builtin...")
    plugin_manager.register_plugin(LDAPPlugin())
    plugin_manager.register_plugin(GitLabPlugin())
    plugin_manager.register_plugin(JenkinsPlugin())
    plugin_manager.register_plugin(PortainerPlugin())
    plugin_manager.register_plugin(ZabbixPlugin())

