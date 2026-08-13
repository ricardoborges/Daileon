import json
import logging
import time
from typing import Dict, Any, Optional, List
import httpx
import urllib.parse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.db.models import SystemSetting

logger = logging.getLogger(__name__)

# Simple in-memory cache: {cache_key: (timestamp, data)}
_jenkins_cache: Dict[str, tuple[float, Dict[str, Any]]] = {}
CACHE_TTL_SECONDS = 15


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


async def get_effective_jenkins_config(db: AsyncSession) -> dict:
    """Retorna as configurações efetivas do Jenkins (do banco de dados ou variáveis de ambiente)."""
    config = await get_system_setting(db, "jenkins_config")
    if config is not None:
        return config

    default_config = {
        "url": settings.JENKINS_URL or "https://jenkins.example.com",
        "user": settings.JENKINS_USER or "",
        "api_token": settings.JENKINS_API_TOKEN or "",
        "enabled": True,
    }

    if settings.JENKINS_URL or settings.JENKINS_USER or settings.JENKINS_API_TOKEN:
        await set_system_setting(db, "jenkins_config", default_config)

    return default_config


async def test_jenkins_connection(config: Dict[str, Any]) -> Dict[str, Any]:
    """Testa a conexão com o Jenkins usando a URL, usuário e token fornecidos."""
    base_url = (config.get("url") or "").rstrip("/")
    user = config.get("user") or ""
    token = config.get("api_token") or ""

    if not base_url:
        return {"success": False, "message": "A URL do Jenkins é obrigatória."}

    auth = (user, token) if (user or token) and token != "******" else None
    api_url = f"{base_url}/api/json"

    try:
        async with httpx.AsyncClient(timeout=8.0, verify=False) as client:
            resp = await client.get(api_url, auth=auth)
            if resp.status_code == 200:
                data = resp.json()
                mode = data.get("mode") or "Jenkins"
                return {
                    "success": True,
                    "message": f"Conexão com o Jenkins realizada com sucesso! (Modo: {mode})",
                }
            elif resp.status_code == 401 or resp.status_code == 403:
                return {
                    "success": False,
                    "message": "Falha na autenticação (Usuário ou API Token incorretos).",
                }
            else:
                return {
                    "success": False,
                    "message": f"Jenkins respondeu com status {resp.status_code}: {resp.text[:150]}",
                }
    except Exception as e:
        return {"success": False, "message": f"Erro ao conectar no Jenkins: {str(e)}"}


def normalize_jenkins_url(raw_url: Optional[str], base_url: str) -> Optional[str]:
    """Garante que qualquer URL gerada ou retornada pelo Jenkins utilize o esquema e host/porta de base_url."""
    if not raw_url:
        return None
    base_clean = base_url.rstrip("/")
    parsed_base = urllib.parse.urlparse(base_clean)
    parsed_url = urllib.parse.urlparse(raw_url)

    if not parsed_url.netloc:
        return f"{base_clean}/{raw_url.lstrip('/')}"

    base_path = parsed_base.path.rstrip("/")
    raw_path = parsed_url.path
    if base_path and not raw_path.startswith(base_path):
        final_path = f"{base_path}/{raw_path.lstrip('/')}"
    else:
        final_path = raw_path

    rebuilt = parsed_url._replace(
        scheme=parsed_base.scheme, netloc=parsed_base.netloc, path=final_path
    )
    return urllib.parse.urlunparse(rebuilt)


def get_jenkins_candidate_api_urls(
    base_url: str, job_name: str
) -> List[tuple[str, str]]:
    """Gera candidatos de URLs para a REST API do Jenkins.

    Retorna uma lista de tuplas (api_url, web_job_url).
    """
    base = base_url.rstrip("/")
    clean_name = urllib.parse.unquote(job_name).strip("/")

    candidates: List[tuple[str, str]] = []
    seen = set()

    def add_candidate(api_path: str, web_path: str):
        full_api = f"{base}/{api_path.lstrip('/')}/lastBuild/api/json"
        full_web = f"{base}/{web_path.lstrip('/')}"
        if full_api not in seen:
            seen.add(full_api)
            candidates.append((full_api, full_web))

    if clean_name.startswith("view/"):
        add_candidate(clean_name, clean_name)

    raw_parts = [p.strip() for p in clean_name.split("/") if p.strip()]
    filtered_parts = [p for p in raw_parts if p not in ("job", "view")]

    if len(filtered_parts) >= 2:
        folder_path = "job/" + "/job/".join(filtered_parts)
        add_candidate(folder_path, folder_path)

        view_path = f"view/{filtered_parts[0]}/job/" + "/job/".join(filtered_parts[1:])
        add_candidate(view_path, view_path)

        direct_path = f"job/{filtered_parts[-1]}"
        add_candidate(direct_path, direct_path)

    elif len(filtered_parts) == 1:
        direct_path = f"job/{filtered_parts[0]}"
        add_candidate(direct_path, direct_path)

    if raw_parts:
        raw_path = "job/" + "/job/".join(raw_parts)
        add_candidate(raw_path, raw_path)

    return candidates


def format_jenkins_job_url(base_url: str, job_name: str) -> str:
    candidates = get_jenkins_candidate_api_urls(base_url, job_name)
    raw_url = (
        candidates[0][1] if candidates else f"{base_url.rstrip('/')}/job/{job_name}"
    )
    return normalize_jenkins_url(raw_url, base_url) or raw_url


async def fetch_jenkins_job_status(
    job_name: str,
    server_url: Optional[str] = None,
    db: Optional[AsyncSession] = None,
) -> Dict[str, Any]:
    """Consulta a REST API do Jenkins testando os candidatos de URL até encontrar o job."""
    cfg = None
    if db:
        cfg = await get_effective_jenkins_config(db)

    base_url = server_url or (cfg.get("url") if cfg else settings.JENKINS_URL)
    user = (cfg.get("user") if cfg else settings.JENKINS_USER) or ""
    token = (cfg.get("api_token") if cfg else settings.JENKINS_API_TOKEN) or ""

    cache_key = f"{base_url}::{job_name}"

    now = time.time()
    if cache_key in _jenkins_cache:
        ts, cached_data = _jenkins_cache[cache_key]
        if now - ts < CACHE_TTL_SECONDS:
            return cached_data

    if not token and not user:
        result = {
            "job": job_name,
            "configured": False,
            "status": "NOT_CONFIGURED",
            "message": "JENKINS_API_TOKEN não configurado nas variáveis de ambiente.",
            "last_build": None,
        }
        _jenkins_cache[cache_key] = (now, result)
        return result

    candidate_urls = get_jenkins_candidate_api_urls(base_url, job_name)
    auth = (user, token) if user or token else None

    last_job_url = normalize_jenkins_url(
        candidate_urls[0][1] if candidate_urls else base_url, base_url
    )

    try:
        async with httpx.AsyncClient(timeout=6.0, verify=False) as client:
            for api_url, job_url in candidate_urls:
                norm_job_url = normalize_jenkins_url(job_url, base_url)
                last_job_url = norm_job_url or job_url
                resp = await client.get(api_url, auth=auth)

                if resp.status_code == 401 or resp.status_code == 403:
                    res = {
                        "job": job_name,
                        "configured": True,
                        "status": "UNAUTHORIZED",
                        "message": "Falha na autenticação com a API do Jenkins. Verifique JENKINS_USER e JENKINS_API_TOKEN.",
                        "job_url": norm_job_url,
                        "last_build": None,
                    }
                    _jenkins_cache[cache_key] = (now, res)
                    return res

                if resp.status_code == 404:
                    continue

                resp.raise_for_status()
                data = resp.json()

                building = data.get("building", False)
                raw_result = data.get("result")

                if building:
                    status = "BUILDING"
                elif raw_result:
                    status = raw_result.upper()
                else:
                    status = "UNKNOWN"

                causes = []
                branch = None
                commit = None

                actions = data.get("actions", [])
                for action in actions:
                    if not isinstance(action, dict):
                        continue
                    if "causes" in action and isinstance(action["causes"], list):
                        for c in action["causes"]:
                            if "shortDescription" in c:
                                causes.append(c["shortDescription"])
                    if "lastBuiltRevision" in action and isinstance(
                        action["lastBuiltRevision"], dict
                    ):
                        rev = action["lastBuiltRevision"]
                        commit = rev.get("SHA1")
                        branches = rev.get("branch", [])
                        if branches and isinstance(branches, list):
                            branch = branches[0].get("name")

                raw_build_url = (
                    data.get("url") or f"{norm_job_url}/{data.get('number')}"
                )
                build_url = normalize_jenkins_url(raw_build_url, base_url)

                res = {
                    "job": job_name,
                    "configured": True,
                    "status": status,
                    "message": None,
                    "job_url": norm_job_url,
                    "last_build": {
                        "number": data.get("number"),
                        "url": build_url,
                        "building": building,
                        "result": raw_result,
                        "duration_ms": data.get("duration", 0),
                        "timestamp": data.get("timestamp"),
                        "display_name": data.get("displayName")
                        or f"#{data.get('number')}",
                        "causes": causes,
                        "branch": branch,
                        "commit": commit[:7] if commit else None,
                    },
                }
                _jenkins_cache[cache_key] = (now, res)
                return res

            res = {
                "job": job_name,
                "configured": True,
                "status": "NOT_FOUND",
                "message": f"Job '{job_name}' não encontrado no Jenkins. Testadas {len(candidate_urls)} URLs de API.",
                "job_url": last_job_url,
                "last_build": None,
            }
            _jenkins_cache[cache_key] = (now, res)
            return res

    except Exception as e:
        logger.warning(f"Erro ao consultar Jenkins para job '{job_name}': {e}")
        res = {
            "job": job_name,
            "configured": bool(token or user),
            "status": "UNREACHABLE",
            "message": f"Não foi possível conectar ao Jenkins ({base_url}): {str(e)}",
            "job_url": last_job_url,
            "last_build": None,
        }
        _jenkins_cache[cache_key] = (now, res)
        return res
