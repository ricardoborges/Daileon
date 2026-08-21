import time
import logging
from typing import Any, Dict, List, Optional
import httpx
from app.core.config import settings
from app.api.auth import get_system_setting, set_system_setting
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("daileon.plugins.zabbix")

ZABBIX_CONFIG_KEY = "zabbix_config"

# Severity mapping according to Zabbix standards
SEVERITY_MAP = {
    "0": {"name": "Not classified", "color": "gray", "level": 0},
    "1": {"name": "Information", "color": "blue", "level": 1},
    "2": {"name": "Warning", "color": "yellow", "level": 2},
    "3": {"name": "Average", "color": "orange", "level": 3},
    "4": {"name": "High", "color": "red", "level": 4},
    "5": {"name": "Disaster", "color": "purple", "level": 5},
}


async def get_effective_zabbix_config(db: AsyncSession) -> Dict[str, Any]:
    """Recupera as configurações gravadas no banco ou fallback para variáveis de ambiente."""
    db_config = await get_system_setting(db, ZABBIX_CONFIG_KEY)
    if not isinstance(db_config, dict):
        db_config = {}

    url = db_config.get("url") or settings.ZABBIX_URL
    api_token = db_config.get("api_token") or settings.ZABBIX_API_TOKEN
    username = db_config.get("username") or settings.ZABBIX_USER
    password = db_config.get("password") or settings.ZABBIX_PASSWORD
    cache_ttl = db_config.get("cache_ttl") if db_config.get("cache_ttl") is not None else settings.ZABBIX_CACHE_TTL
    enabled = db_config.get("enabled", True)

    return {
        "url": url,
        "api_token": api_token,
        "username": username,
        "password": password,
        "cache_ttl": cache_ttl,
        "enabled": enabled and bool(url and (api_token or username)),
    }


class ZabbixService:
    """Cliente assíncrono para a API JSON-RPC do Zabbix."""

    def __init__(self, url: str, api_token: Optional[str] = None, username: Optional[str] = None, password: Optional[str] = None, cache_ttl: int = 30):
        self.url = url.rstrip("/")
        if not self.url.endswith("/api_jsonrpc.php"):
            self.api_url = f"{self.url}/api_jsonrpc.php"
        else:
            self.api_url = self.url
        self.api_token = api_token
        self.username = username
        self.password = password
        self.cache_ttl = cache_ttl
        self._auth_token: Optional[str] = api_token
        self._cache: Dict[str, Dict[str, Any]] = {}

    def _get_cache(self, key: str) -> Optional[Any]:
        if key in self._cache:
            entry = self._cache[key]
            if time.time() - entry["timestamp"] < self.cache_ttl:
                return entry["data"]
        return None

    def _set_cache(self, key: str, data: Any) -> None:
        self._cache[key] = {"timestamp": time.time(), "data": data}

    async def _rpc_call(self, method: str, params: Dict[str, Any], auth: Optional[str] = None) -> Any:
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": 1,
        }
        
        token = auth or self._auth_token
        headers = {"Content-Type": "application/json-rpc"}
        if token and method != "apiinfo.version":
            payload["auth"] = token
            headers["Authorization"] = f"Bearer {token}"

        async with httpx.AsyncClient(timeout=10.0, verify=False, follow_redirects=True) as client:
            response = await client.post(self.api_url, json=payload, headers=headers)
            response.raise_for_status()
            res_json = response.json()
            
            if "error" in res_json:
                err_msg = res_json["error"].get("data") or res_json["error"].get("message", "Erro desconhecido na API do Zabbix.")
                raise Exception(f"Zabbix API Error: {err_msg}")
            
            return res_json.get("result")

    async def authenticate(self) -> str:
        """Autentica com usuário e senha caso o API Token não esteja configurado."""
        if self.api_token:
            self._auth_token = self.api_token
            return self.api_token
            
        if not self.username or not self.password:
            raise ValueError("Token API ou credenciais de usuário/senha são necessários para autenticar no Zabbix.")

        result = await self._rpc_call("user.login", {"username": self.username, "password": self.password})
        self._auth_token = str(result)
        return self._auth_token

    async def get_version(self) -> str:
        cache_key = "zabbix_version"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        res = await self._rpc_call("apiinfo.version", {})
        self._set_cache(cache_key, str(res))
        return str(res)

    async def get_hosts(self, host_names: Optional[List[str]] = None, host_ips: Optional[List[str]] = None, group_name: Optional[str] = None) -> List[Dict[str, Any]]:
        cache_key = f"hosts_{host_names}_{host_ips}_{group_name}"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        if not self._auth_token:
            await self.authenticate()

        params: Dict[str, Any] = {
            "output": ["hostid", "host", "name", "status", "available", "error"],
            "selectInterfaces": ["ip", "dns", "port", "main"],
        }
        if host_names:
            params["filter"] = {"name": host_names}
        if group_name:
            params["group"] = group_name

        result = await self._rpc_call("host.get", params)
        self._set_cache(cache_key, result or [])
        return result or []

    async def get_active_problems(self, host_ids: Optional[List[str]] = None, min_severity: int = 0) -> List[Dict[str, Any]]:
        cache_key = f"problems_{host_ids}_{min_severity}"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        if not self._auth_token:
            await self.authenticate()

        params: Dict[str, Any] = {
            "output": ["eventid", "objectid", "name", "severity", "clock", "r_clock"],
            "recent": True,
            "sortfield": ["eventid"],
            "sortorder": "DESC",
        }
        if host_ids:
            params["hostids"] = host_ids
        if min_severity > 0:
            params["severities"] = [str(s) for s in range(min_severity, 6)]

        problems = await self._rpc_call("problem.get", params)
        
        # Enriquecer com metadados de severidade
        enriched = []
        for p in problems or []:
            sev_info = SEVERITY_MAP.get(str(p.get("severity", 0)), SEVERITY_MAP["0"])
            enriched.append({
                "eventid": p.get("eventid"),
                "name": p.get("name"),
                "severity": p.get("severity"),
                "severity_name": sev_info["name"],
                "severity_color": sev_info["color"],
                "clock": int(p.get("clock", 0)),
            })

        self._set_cache(cache_key, enriched)
        return enriched

    async def get_host_metrics(self, host_id: str) -> Dict[str, Any]:
        """Obtém métricas consolidadas (CPU, RAM, Uptime) de um host específico."""
        cache_key = f"metrics_{host_id}"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        if not self._auth_token:
            await self.authenticate()

        # Buscar itens principais do host
        items = await self._rpc_call("item.get", {
            "output": ["itemid", "name", "key_", "lastvalue", "units", "lastclock"],
            "hostids": [host_id],
            "filter": {
                "status": "0"
            },
            "limit": 50
        })

        metrics = {
            "cpu_utilization": None,
            "memory_utilization": None,
            "disk_utilization": None,
            "uptime": None,
            "items": []
        }

        for item in items or []:
            key = item.get("key_", "").lower()
            val = item.get("lastvalue")
            
            if "system.cpu.util" in key or "cpu.util" in key:
                try:
                    metrics["cpu_utilization"] = round(float(val), 2)
                except (ValueError, TypeError):
                    pass
            elif "vm.memory.util" in key or "memory.size[available]" in key:
                try:
                    metrics["memory_utilization"] = round(float(val), 2)
                except (ValueError, TypeError):
                    pass
            elif "system.uptime" in key:
                metrics["uptime"] = val

            metrics["items"].append({
                "name": item.get("name"),
                "key": item.get("key_"),
                "value": val,
                "units": item.get("units")
            })

        self._set_cache(cache_key, metrics)
        return metrics
