import json
import logging
import re
import urllib.parse
from typing import Dict, Any, Optional, List
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.db.models import SystemSetting

logger = logging.getLogger(__name__)

# Cache simples em memória para token JWT de autenticação por usuário/senha
_token_cache: Dict[str, tuple[float, str]] = {}


async def get_system_setting(db: AsyncSession, key: str) -> Optional[dict]:
    result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
    setting = result.scalar_one_or_none()
    if setting and setting.value:
        try:
            return json.loads(setting.value)
        except Exception:
            return None
    return None


async def set_system_setting(db: AsyncSession, key: str, value: dict):
    result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
    setting = result.scalar_one_or_none()
    json_str = json.dumps(value)
    if setting:
        setting.value = json_str
    else:
        setting = SystemSetting(key=key, value=json_str)
        db.add(setting)
    await db.commit()


async def get_effective_portainer_config(db: AsyncSession) -> dict:
    config = await get_system_setting(db, "portainer_config")
    if config is not None:
        return config

    default_config = {
        "url": settings.PORTAINER_URL or "http://localhost:9000",
        "api_key": settings.PORTAINER_API_KEY or "",
        "username": settings.PORTAINER_USER or "",
        "password": settings.PORTAINER_PASSWORD or "",
        "enabled": bool(settings.PORTAINER_API_KEY or (settings.PORTAINER_USER and settings.PORTAINER_PASSWORD))
    }

    if settings.PORTAINER_API_KEY or settings.PORTAINER_USER:
        await set_system_setting(db, "portainer_config", default_config)

    return default_config


def _clean_base_url(url: str) -> str:
    if not url or not url.strip():
        return ""
    cleaned = url.strip().rstrip("/")
    if not cleaned.startswith("http://") and not cleaned.startswith("https://"):
        cleaned = "http://" + cleaned
    return cleaned



async def _get_auth_headers(client: httpx.AsyncClient, config: dict) -> dict:
    base_url = _clean_base_url(config.get("url", ""))
    api_key = config.get("api_key", "").strip()
    username = config.get("username", "").strip()
    password = config.get("password", "").strip()

    if api_key:
        return {"X-API-Key": api_key}

    if username and password:
        auth_url = f"{base_url}/api/auth"
        try:
            resp = await client.post(auth_url, json={"Username": username, "Password": password})
            resp.raise_for_status()
            data = resp.json()
            jwt_token = data.get("jwt")
            if jwt_token:
                return {"Authorization": f"Bearer {jwt_token}"}
        except Exception as e:
            logger.error(f"Falha ao autenticar com usuário/senha no Portainer: {e}")
            raise RuntimeError(f"Falha na autenticação com Portainer: {e}")

    return {}


class PortainerService:

    @staticmethod
    async def test_connection(config: dict) -> dict:
        url = _clean_base_url(config.get("url", ""))
        if not url:
            return {"success": False, "message": "URL do Portainer não configurada."}

        try:
            async with httpx.AsyncClient(timeout=8.0, verify=False) as client:
                headers = await _get_auth_headers(client, config)
                
                # Checa status ou endpoints
                resp = await client.get(f"{url}/api/status", headers=headers)
                version = "Desconhecida"
                if resp.status_code == 200:
                    status_data = resp.json()
                    version = status_data.get("Version", "N/A")

                ep_resp = await client.get(f"{url}/api/endpoints", headers=headers)
                ep_resp.raise_for_status()
                endpoints = ep_resp.json()

                return {
                    "success": True,
                    "message": f"Conexão com Portainer estabelecida com sucesso! Versão: {version}",
                    "version": version,
                    "endpoints_count": len(endpoints) if isinstance(endpoints, list) else 0
                }
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (401, 403):
                return {"success": False, "message": "Falha de autenticação (401/403). Verifique a API Key ou Usuário/Senha."}
            return {"success": False, "message": f"Erro HTTP {e.response.status_code} ao conectar com Portainer."}
        except Exception as e:
            return {"success": False, "message": f"Não foi possível conectar ao Portainer em {url}: {str(e)}"}

    @staticmethod
    async def fetch_endpoints(config: dict) -> List[dict]:
        url = _clean_base_url(config.get("url", ""))
        async with httpx.AsyncClient(timeout=8.0, verify=False) as client:
            headers = await _get_auth_headers(client, config)
            resp = await client.get(f"{url}/api/endpoints", headers=headers)
            resp.raise_for_status()
            data = resp.json()

            endpoints = []
            if isinstance(data, list):
                for ep in data:
                    endpoints.append({
                        "id": ep.get("Id"),
                        "name": ep.get("Name"),
                        "type": ep.get("Type"),
                        "status": ep.get("Status"), # 1 = up, 2 = down
                        "public_url": ep.get("PublicURL") or ep.get("URL")
                    })
            return endpoints

    @staticmethod
    async def fetch_containers(config: dict, endpoint_id: Optional[int] = None) -> List[dict]:
        url = _clean_base_url(config.get("url", ""))
        async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
            headers = await _get_auth_headers(client, config)

            target_endpoints = []
            if endpoint_id is not None:
                target_endpoints.append({"id": endpoint_id, "name": f"Endpoint #{endpoint_id}", "public_url": ""})
            else:
                endpoints_list = await PortainerService.fetch_endpoints(config)
                target_endpoints = [
                    {
                        "id": ep["id"],
                        "name": ep["name"],
                        "public_url": ep.get("public_url", "")
                    }
                    for ep in endpoints_list
                    if ep.get("status") == 1 or ep.get("status") is None
                ]

            all_containers = []
            for ep in target_endpoints:
                ep_id = ep["id"]
                ep_name = ep["name"]
                ep_public_url = ep.get("public_url", "")
                try:
                    c_resp = await client.get(f"{url}/api/endpoints/{ep_id}/docker/containers/json?all=true", headers=headers)
                    if c_resp.status_code != 200:
                        continue
                    containers_raw = c_resp.json()

                    if isinstance(containers_raw, list):
                        for c in containers_raw:
                            names = c.get("Names", [])
                            primary_name = names[0].lstrip("/") if names else c.get("Id", "")[:12]
                            labels = c.get("Labels", {}) or {}

                            ports = []
                            raw_ports = c.get("Ports", []) or []
                            for p in raw_ports:
                                pub = p.get("PublicPort")
                                priv = p.get("PrivatePort")
                                ptype = p.get("Type", "tcp")
                                if pub and priv:
                                    ports.append(f"{pub}:{priv}/{ptype}")
                                elif priv:
                                    ports.append(f"{priv}/{ptype}")

                            network_settings = c.get("NetworkSettings", {}) or {}
                            networks = network_settings.get("Networks", {}) or {}
                            network_ips = []
                            if isinstance(networks, dict):
                                for net_val in networks.values():
                                    if isinstance(net_val, dict) and net_val.get("IPAddress"):
                                        network_ips.append(net_val.get("IPAddress"))

                            all_containers.append({
                                "id": c.get("Id"),
                                "short_id": c.get("Id", "")[:12],
                                "name": primary_name,
                                "all_names": [n.lstrip("/") for n in names],
                                "endpoint_id": ep_id,
                                "endpoint_name": ep_name,
                                "endpoint_public_url": ep_public_url,
                                "raw_ports": raw_ports,
                                "network_ips": network_ips,
                                "image": c.get("Image"),
                                "state": c.get("State", "unknown").lower(), # running, exited, paused, restarting
                                "status": c.get("Status", ""), # "Up 2 hours", "Exited (0) 5 minutes ago"
                                "created": c.get("Created"),
                                "ports": ports,
                                "stack_name": labels.get("com.docker.compose.project") or labels.get("io.portainer.stack.name") or "",
                                "service_name": labels.get("com.docker.compose.service") or "",
                                "labels": labels
                            })
                except Exception as e:
                    logger.warning(f"Erro ao buscar containers do endpoint {ep_id} no Portainer: {e}")

            return all_containers

    @staticmethod
    def match_containers_for_component(
        containers: List[dict],
        component_name: str,
        spec_portainer: Optional[dict] = None,
        deployments: Optional[List[Any]] = None
    ) -> List[dict]:
        matched = []
        matched_ids = set()
        name_lower = component_name.lower().replace("_", "-")

        explicit_container = (spec_portainer.get("container_name") or "").lower() if spec_portainer else ""
        explicit_stack = (spec_portainer.get("stack_name") or "").lower() if spec_portainer else ""
        explicit_ep = spec_portainer.get("endpoint_id") if spec_portainer else None

        # Processa deployments do catálogo (extrai IPs e Portas alvos)
        parsed_deployments = []
        if deployments:
            for dep in deployments:
                if isinstance(dep, dict):
                    server_ip = dep.get("server_ip")
                    port = dep.get("port")
                    server_name = dep.get("server_name")
                    url = dep.get("url")
                else:
                    server_ip = getattr(dep, "server_ip", None)
                    port = getattr(dep, "port", None)
                    server_name = getattr(dep, "server_name", None)
                    url = getattr(dep, "url", None)

                target_ips = set()
                if server_ip and str(server_ip).strip():
                    target_ips.add(str(server_ip).strip().lower())
                if server_name and str(server_name).strip():
                    target_ips.add(str(server_name).strip().lower())

                target_ports = set()
                if port is not None and str(port).strip():
                    for p_str in re.findall(r'\d+', str(port)):
                        target_ports.add(p_str)

                if url and str(url).strip():
                    try:
                        parsed = urllib.parse.urlparse(str(url).strip())
                        if parsed.hostname:
                            target_ips.add(parsed.hostname.lower())
                        if parsed.port:
                            target_ports.add(str(parsed.port))
                    except Exception:
                        pass

                if target_ips or target_ports:
                    parsed_deployments.append({
                        "target_ips": target_ips,
                        "target_ports": target_ports
                    })

        for c in containers:
            c_id = c.get("id")
            if not c_id or c_id in matched_ids:
                continue

            c_name = c["name"].lower().replace("_", "-")
            c_stack = (c.get("stack_name") or "").lower().replace("_", "-")
            c_service = (c.get("service_name") or "").lower().replace("_", "-")

            # 1. Checa correspondência explícita do manifesto (spec.portainer)
            if spec_portainer:
                if explicit_ep is None or c.get("endpoint_id") == explicit_ep:
                    if explicit_container and explicit_container in c_name:
                        matched.append(c)
                        matched_ids.add(c_id)
                        continue
                    if explicit_stack and explicit_stack == c_stack:
                        matched.append(c)
                        matched_ids.add(c_id)
                        continue

            # 2. Checa correspondência via Deployments do Catálogo (IP e Porta)
            if parsed_deployments:
                c_ports = set()
                for rp in c.get("raw_ports", []) or []:
                    if rp.get("PublicPort"):
                        c_ports.add(str(rp["PublicPort"]))
                    if rp.get("PrivatePort"):
                        c_ports.add(str(rp["PrivatePort"]))
                for p_str in c.get("ports", []) or []:
                    for num in re.findall(r'\d+', str(p_str)):
                        c_ports.add(num)

                c_hosts_ips = set()
                if c.get("endpoint_name"):
                    c_hosts_ips.add(str(c["endpoint_name"]).lower())
                if c.get("endpoint_public_url"):
                    ep_url = str(c["endpoint_public_url"]).lower()
                    c_hosts_ips.add(ep_url)
                    try:
                        p_url = urllib.parse.urlparse(ep_url if "://" in ep_url else f"http://{ep_url}")
                        if p_url.hostname:
                            c_hosts_ips.add(p_url.hostname.lower())
                    except Exception:
                        pass

                for net_ip in c.get("network_ips", []) or []:
                    c_hosts_ips.add(str(net_ip).lower())

                for rp in c.get("raw_ports", []) or []:
                    rp_ip = rp.get("IP")
                    if rp_ip and rp_ip not in ("0.0.0.0", "::", "127.0.0.1"):
                        c_hosts_ips.add(str(rp_ip).lower())

                dep_matched = False
                for p_dep in parsed_deployments:
                    t_ips = p_dep["target_ips"]
                    t_ports = p_dep["target_ports"]

                    port_matched = bool(t_ports and t_ports.intersection(c_ports))
                    ip_matched = False

                    if t_ips:
                        for tip in t_ips:
                            if tip in ("0.0.0.0", "*"):
                                ip_matched = True
                                break
                            if tip in c_hosts_ips:
                                ip_matched = True
                                break
                            for c_host in c_hosts_ips:
                                if tip in c_host or c_host in tip:
                                    ip_matched = True
                                    break
                            if ip_matched:
                                break
                    else:
                        ip_matched = True

                    if t_ips and t_ports:
                        if ip_matched and port_matched:
                            dep_matched = True
                            break
                    elif t_ports and not t_ips:
                        if port_matched:
                            dep_matched = True
                            break
                    elif t_ips and not t_ports:
                        if ip_matched and (c_name == name_lower or name_lower in c_name or c_stack == name_lower or c_service == name_lower):
                            dep_matched = True
                            break

                if dep_matched:
                    matched.append(c)
                    matched_ids.add(c_id)
                    continue

            # 3. Checa correspondência por convenção (nome do componente igual ao container, serviço docker-compose ou stack)
            if c_name == name_lower or c_name.startswith(f"{name_lower}-") or c_name.endswith(f"-{name_lower}") or f"-{name_lower}-" in c_name:
                matched.append(c)
                matched_ids.add(c_id)
                continue
            if c_stack == name_lower:
                matched.append(c)
                matched_ids.add(c_id)
                continue
            if c_service == name_lower:
                matched.append(c)
                matched_ids.add(c_id)
                continue

        return matched

    @staticmethod
    async def fetch_container_stats(config: dict, endpoint_id: int, container_id: str) -> dict:
        url = _clean_base_url(config.get("url", ""))
        async with httpx.AsyncClient(timeout=8.0, verify=False) as client:
            headers = await _get_auth_headers(client, config)
            resp = await client.get(
                f"{url}/api/endpoints/{endpoint_id}/docker/containers/{container_id}/stats?stream=false",
                headers=headers
            )
            resp.raise_for_status()
            data = resp.json()

            # Cálculo do CPU %
            cpu_percent = 0.0
            cpu_stats = data.get("cpu_stats", {})
            precpu_stats = data.get("precpu_stats", {})

            cpu_usage = cpu_stats.get("cpu_usage", {}).get("total_usage", 0)
            precpu_usage = precpu_stats.get("cpu_usage", {}).get("total_usage", 0)
            cpu_delta = cpu_usage - precpu_usage

            system_usage = cpu_stats.get("system_cpu_usage", 0)
            presystem_usage = precpu_stats.get("system_cpu_usage", 0)
            system_delta = system_usage - presystem_usage

            online_cpus = cpu_stats.get("online_cpus") or len(cpu_stats.get("cpu_usage", {}).get("percpu_usage", []) or [1])
            if system_delta > 0 and cpu_delta > 0:
                cpu_percent = round((cpu_delta / system_delta) * online_cpus * 100.0, 2)

            # Cálculo de Memória
            memory_stats = data.get("memory_stats", {})
            mem_raw = memory_stats.get("usage", 0)
            cache_bytes = memory_stats.get("stats", {}).get("cache", 0)
            mem_usage_bytes = max(0, mem_raw - cache_bytes)
            mem_limit_bytes = memory_stats.get("limit", 1)

            mem_usage_mb = round(mem_usage_bytes / (1024 * 1024), 2)
            mem_limit_mb = round(mem_limit_bytes / (1024 * 1024), 2)
            mem_percent = round((mem_usage_bytes / mem_limit_bytes) * 100.0, 2) if mem_limit_bytes > 0 else 0.0

            # Redes
            networks = data.get("networks", {})
            rx_bytes = sum(net.get("rx_bytes", 0) for net in networks.values())
            tx_bytes = sum(net.get("tx_bytes", 0) for net in networks.values())

            return {
                "container_id": container_id,
                "endpoint_id": endpoint_id,
                "cpu_percent": cpu_percent,
                "memory_usage_mb": mem_usage_mb,
                "memory_limit_mb": mem_limit_mb,
                "memory_percent": mem_percent,
                "rx_kb": round(rx_bytes / 1024, 1),
                "tx_kb": round(tx_bytes / 1024, 1),
                "online_cpus": online_cpus
            }

    @staticmethod
    async def fetch_container_logs(config: dict, endpoint_id: int, container_id: str, tail: int = 100) -> dict:
        url = _clean_base_url(config.get("url", ""))
        async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
            headers = await _get_auth_headers(client, config)
            resp = await client.get(
                f"{url}/api/endpoints/{endpoint_id}/docker/containers/{container_id}/logs?stdout=true&stderr=true&timestamps=true&tail={tail}",
                headers=headers
            )
            resp.raise_for_status()

            raw_text = resp.text
            # Remove cabeçalhos binários multiplexados do Docker se houver
            clean_lines = []
            for line in raw_text.splitlines():
                # Docker log header costuma ser 8 bytes não-ASCII no início
                cleaned = re.sub(r'^[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]+', '', line).strip()
                if cleaned:
                    clean_lines.append(cleaned)

            return {
                "container_id": container_id,
                "endpoint_id": endpoint_id,
                "lines_count": len(clean_lines),
                "logs": "\n".join(clean_lines)
            }

    @staticmethod
    async def execute_container_action(config: dict, endpoint_id: int, container_id: str, action: str) -> dict:
        valid_actions = ("start", "stop", "restart")
        if action not in valid_actions:
            raise ValueError(f"Ação inválida '{action}'. Ações permitidas: {valid_actions}")

        url = _clean_base_url(config.get("url", ""))
        async with httpx.AsyncClient(timeout=15.0, verify=False) as client:
            headers = await _get_auth_headers(client, config)
            resp = await client.post(
                f"{url}/api/endpoints/{endpoint_id}/docker/containers/{container_id}/{action}",
                headers=headers
            )
            if resp.status_code not in (200, 204):
                resp.raise_for_status()

            action_labels = {"start": "iniciado", "stop": "parado", "restart": "reiniciado"}
            return {
                "success": True,
                "container_id": container_id,
                "action": action,
                "message": f"Container {action_labels.get(action, action)} com sucesso."
            }
