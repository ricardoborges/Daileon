from typing import Dict, Any, Optional
from fastapi import APIRouter
from app.core.plugins.plugin_interface import AuthProviderPlugin
from app.plugins.ldap.service import LDAPAuthService

class LDAPPlugin(AuthProviderPlugin):
    @property
    def plugin_id(self) -> str:
        return "ldap"

    @property
    def name(self) -> str:
        return "LDAP / Active Directory Authentication"

    @property
    def version(self) -> str:
        return "1.0.0"

    def authenticate(self, config: Dict[str, Any], username: str, password: str) -> Dict[str, Any]:
        return LDAPAuthService.authenticate(config, username, password)

    def test_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        return LDAPAuthService.test_connection(config)
