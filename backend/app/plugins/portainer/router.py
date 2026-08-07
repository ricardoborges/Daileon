from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models import Component
from app.api.auth import get_current_user
from app.plugins.portainer.service import (
    PortainerService,
    get_effective_portainer_config,
    set_system_setting
)

portainer_router = APIRouter(prefix="/plugins/portainer", tags=["portainer"])


class PortainerConfigRequest(BaseModel):
    url: str
    api_key: str = ""
    username: str = ""
    password: str = ""
    enabled: bool = True


class ContainerActionRequest(BaseModel):
    action: str  # "start", "stop", "restart"


@portainer_router.get("/config")
async def get_portainer_config(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    config = await get_effective_portainer_config(db)
    res = dict(config)
    if res.get("password"):
        res["password"] = "******"
    if res.get("api_key"):
        res["api_key_masked"] = "******" if len(res["api_key"]) > 4 else res["api_key"]
    return res


@portainer_router.post("/config")
async def save_portainer_config(
    payload: PortainerConfigRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    current = await get_effective_portainer_config(db)
    new_data = payload.model_dump()

    if new_data.get("password") == "******":
        new_data["password"] = current.get("password", "")
    if new_data.get("api_key") == "******":
        new_data["api_key"] = current.get("api_key", "")

    await set_system_setting(db, "portainer_config", new_data)
    return {"message": "Configurações do Portainer salvas com sucesso!"}


@portainer_router.post("/test-connection")
async def test_portainer_connection(
    payload: PortainerConfigRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    current = await get_effective_portainer_config(db)
    data = payload.model_dump()

    if data.get("password") == "******":
        data["password"] = current.get("password", "")
    if data.get("api_key") == "******":
        data["api_key"] = current.get("api_key", "")

    result = await PortainerService.test_connection(data)
    return result


@portainer_router.get("/endpoints")
async def list_portainer_endpoints(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    config = await get_effective_portainer_config(db)
    if not config.get("enabled", True):
        return []
    try:
        endpoints = await PortainerService.fetch_endpoints(config)
        return endpoints
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao consultar endpoints do Portainer: {str(e)}"
        )


@portainer_router.get("/containers")
async def list_portainer_containers(
    endpoint_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    config = await get_effective_portainer_config(db)
    if not config.get("enabled", True):
        return []
    try:
        containers = await PortainerService.fetch_containers(config, endpoint_id=endpoint_id)
        return containers
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao consultar containers do Portainer: {str(e)}"
        )


@portainer_router.get("/catalog/{component_id}/containers")
async def get_component_containers(
    component_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    result = await db.execute(select(Component).where(Component.id == component_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Componente não encontrado")

    config = await get_effective_portainer_config(db)
    if not config.get("enabled", True) or (not config.get("url") and not config.get("api_key")):
        return {
            "component_id": c.id,
            "component_name": c.name,
            "configured": False,
            "message": "Integração com Portainer não está configurada.",
            "containers": []
        }

    try:
        all_containers = await PortainerService.fetch_containers(config)
        matched = PortainerService.match_containers_for_component(
            all_containers,
            component_name=c.name
        )

        return {
            "component_id": c.id,
            "component_name": c.name,
            "configured": True,
            "portainer_url": config.get("url", ""),
            "containers_count": len(matched),
            "containers": matched
        }
    except Exception as e:
        return {
            "component_id": c.id,
            "component_name": c.name,
            "configured": True,
            "error": str(e),
            "containers": []
        }


@portainer_router.get("/containers/{endpoint_id}/{container_id}/stats")
async def get_container_stats(
    endpoint_id: int,
    container_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    config = await get_effective_portainer_config(db)
    try:
        stats = await PortainerService.fetch_container_stats(config, endpoint_id, container_id)
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter estatísticas do container: {str(e)}"
        )


@portainer_router.get("/containers/{endpoint_id}/{container_id}/logs")
async def get_container_logs(
    endpoint_id: int,
    container_id: str,
    tail: int = 150,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    config = await get_effective_portainer_config(db)
    try:
        logs_data = await PortainerService.fetch_container_logs(config, endpoint_id, container_id, tail=tail)
        return logs_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar logs do container: {str(e)}"
        )


@portainer_router.post("/containers/{endpoint_id}/{container_id}/action")
async def perform_container_action(
    endpoint_id: int,
    container_id: str,
    payload: ContainerActionRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    config = await get_effective_portainer_config(db)
    try:
        res = await PortainerService.execute_container_action(
            config, endpoint_id, container_id, payload.action
        )
        return res
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao executar ação '{payload.action}' no container: {str(e)}"
        )
