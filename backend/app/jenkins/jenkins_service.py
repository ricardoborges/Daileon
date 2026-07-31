import logging
import time
from typing import Dict, Any, Optional, List
import httpx
import urllib.parse

from app.core.config import settings

logger = logging.getLogger(__name__)

# Simple in-memory cache: {cache_key: (timestamp, data)}
_jenkins_cache: Dict[str, tuple[float, Dict[str, Any]]] = {}
CACHE_TTL_SECONDS = 15


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
        scheme=parsed_base.scheme,
        netloc=parsed_base.netloc,
        path=final_path
    )
    return urllib.parse.urlunparse(rebuilt)


def get_jenkins_candidate_api_urls(base_url: str, job_name: str) -> List[tuple[str, str]]:
    """Gera candidatos de URLs para a REST API do Jenkins.
    
    Retorna uma lista de tuplas (api_url, web_job_url).
    Lida com unquote de %20, remoção de segmentos redundantes ('job', 'view')
    e tenta tanto caminhos por Pastas (Folders), Visões (Views) quanto Jobs Diretos.
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

    # 1. Se o usuário forneceu explicitamente um caminho com view/ (ex: view/Strix/job/Strix master branch)
    if clean_name.startswith("view/"):
        add_candidate(clean_name, clean_name)

    # 2. Dividir em segmentos e filtrar palavras chave
    raw_parts = [p.strip() for p in clean_name.split("/") if p.strip()]
    filtered_parts = [p for p in raw_parts if p not in ("job", "view")]

    if len(filtered_parts) >= 2:
        # Ex: ["Strix", "Strix master branch"] ou ["Strix", "PROD deploy"]
        # Estrutura por Folder: /job/Strix/job/Strix master branch
        folder_path = "job/" + "/job/".join(filtered_parts)
        add_candidate(folder_path, folder_path)

        # Estrutura por View: /view/Strix/job/Strix master branch
        view_path = f"view/{filtered_parts[0]}/job/" + "/job/".join(filtered_parts[1:])
        add_candidate(view_path, view_path)

        # Estrutura por Job Direto (última parte): /job/Strix master branch
        direct_path = f"job/{filtered_parts[-1]}"
        add_candidate(direct_path, direct_path)

    elif len(filtered_parts) == 1:
        # Ex: ["Strix master branch"]
        direct_path = f"job/{filtered_parts[0]}"
        add_candidate(direct_path, direct_path)

    # 3. Fallback raw parts se nenhum acima for suficiente
    if raw_parts:
        raw_path = "job/" + "/job/".join(raw_parts)
        add_candidate(raw_path, raw_path)

    return candidates

def format_jenkins_job_url(base_url: str, job_name: str) -> str:
    candidates = get_jenkins_candidate_api_urls(base_url, job_name)
    raw_url = candidates[0][1] if candidates else f"{base_url.rstrip('/')}/job/{job_name}"
    return normalize_jenkins_url(raw_url, base_url) or raw_url

async def fetch_jenkins_job_status(job_name: str, server_url: Optional[str] = None) -> Dict[str, Any]:
    """Consulta a REST API do Jenkins testando os candidatos de URL até encontrar o job."""
    base_url = server_url or settings.JENKINS_URL
    cache_key = f"{base_url}::{job_name}"
    
    now = time.time()
    if cache_key in _jenkins_cache:
        ts, cached_data = _jenkins_cache[cache_key]
        if now - ts < CACHE_TTL_SECONDS:
            return cached_data

    user = settings.JENKINS_USER
    token = settings.JENKINS_API_TOKEN

    if not token and not user:
        result = {
            "job": job_name,
            "configured": False,
            "status": "NOT_CONFIGURED",
            "message": "JENKINS_API_TOKEN não configurado nas variáveis de ambiente.",
            "last_build": None
        }
        _jenkins_cache[cache_key] = (now, result)
        return result

    candidate_urls = get_jenkins_candidate_api_urls(base_url, job_name)
    auth = (user, token) if user or token else None

    last_error_message = f"Job '{job_name}' não encontrado no Jenkins."
    last_status = "NOT_FOUND"
    last_job_url = normalize_jenkins_url(candidate_urls[0][1] if candidate_urls else base_url, base_url)

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
                        "last_build": None
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
                    status = raw_result.upper()  # SUCCESS, FAILURE, UNSTABLE, ABORTED
                else:
                    status = "UNKNOWN"

                # Parse actions for causes and git branch info
                causes = []
                branch = None
                commit = None

                actions = data.get("actions", [])
                for action in actions:
                    if not isinstance(action, dict):
                        continue
                    # Causes
                    if "causes" in action and isinstance(action["causes"], list):
                        for c in action["causes"]:
                            if "shortDescription" in c:
                                causes.append(c["shortDescription"])
                    # Git info
                    if "lastBuiltRevision" in action and isinstance(action["lastBuiltRevision"], dict):
                        rev = action["lastBuiltRevision"]
                        commit = rev.get("SHA1")
                        branches = rev.get("branch", [])
                        if branches and isinstance(branches, list):
                            branch = branches[0].get("name")

                raw_build_url = data.get("url") or f"{norm_job_url}/{data.get('number')}"
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
                        "display_name": data.get("displayName") or f"#{data.get('number')}",
                        "causes": causes,
                        "branch": branch,
                        "commit": commit[:7] if commit else None
                    }
                }
                _jenkins_cache[cache_key] = (now, res)
                return res

            # Se todos os candidatos deram 404:
            res = {
                "job": job_name,
                "configured": True,
                "status": "NOT_FOUND",
                "message": f"Job '{job_name}' não encontrado no Jenkins. Testadas {len(candidate_urls)} URLs de API.",
                "job_url": last_job_url,
                "last_build": None
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
            "last_build": None
        }
        _jenkins_cache[cache_key] = (now, res)
        return res
