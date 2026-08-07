import json
import logging
from typing import Dict, Any, Optional
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.db.models import SystemSetting

logger = logging.getLogger(__name__)


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


async def get_effective_gitlab_config(db: AsyncSession) -> dict:
    """Retorna as configurações efetivas do GitLab (do banco de dados ou variáveis de ambiente)."""
    config = await get_system_setting(db, "gitlab_config")
    if config is not None:
        return config

    default_config = {
        "url": settings.GITLAB_URL or "https://gitlab.com",
        "read_token": settings.GITLAB_READ_TOKEN or "",
        "group_id": settings.GITLAB_GROUP_ID or "",
        "enabled": True,
    }

    if settings.GITLAB_URL or settings.GITLAB_READ_TOKEN:
        await set_system_setting(db, "gitlab_config", default_config)

    return default_config


async def test_gitlab_connection(config: Dict[str, Any]) -> Dict[str, Any]:
    """Testa a conexão com a API do GitLab usando a URL e token fornecidos."""
    url = (config.get("url") or "").rstrip("/")
    token = config.get("read_token") or ""
    group_id = config.get("group_id") or ""

    if not url:
        return {"success": False, "message": "A URL do GitLab é obrigatória."}

    headers = {}
    if token and token != "******":
        headers["PRIVATE-TOKEN"] = token

    try:
        async with httpx.AsyncClient(headers=headers, timeout=10.0) as client:
            if group_id:
                api_url = f"{url}/api/v4/groups/{group_id}"
            else:
                api_url = f"{url}/api/v4/user"

            resp = await client.get(api_url)

            if resp.status_code == 200:
                data = resp.json()
                name = data.get("name") or data.get("username") or group_id or "GitLab"
                return {
                    "success": True,
                    "message": f"Conexão com o GitLab realizada com sucesso! ({name})",
                }
            elif resp.status_code == 401 or resp.status_code == 403:
                return {
                    "success": False,
                    "message": "Falha na autenticação (Token inválido ou não autorizado).",
                }
            else:
                return {
                    "success": False,
                    "message": f"GitLab respondeu com status {resp.status_code}: {resp.text[:150]}",
                }
    except Exception as e:
        return {"success": False, "message": f"Erro de conexão com o GitLab: {str(e)}"}
