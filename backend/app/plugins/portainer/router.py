from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from sqlalchemy.orm import selectinload
from app.db.session import get_db
from app.db.models import Component
from app.api.auth import get_current_user
from app.plugins.portainer.service import (
    PortainerService,
    enabled_servers,
    find_server,
    get_effective_portainer_config,
    list_servers,
    mask_server,
    normalize_portainer_config,
    set_system_setting,
    unmask_server,
)

portainer_router = APIRouter(prefix="/plugins/portainer", tags=["portainer"])


class PortainerServerRequest(BaseModel):
    #: Ausente ao cadastrar um servidor novo; o backend sorteia.
    id: Optional[str] = None
    name: str = ""
    url: str
    api_key: str = ""
    username: str = ""
    password: str = ""
    enabled: bool = True


class PortainerConfigRequest(BaseModel):
    servers: List[PortainerServerRequest] = []


class ContainerActionRequest(BaseModel):
    action: str  # "start", "stop", "restart"


async def _resolve_server(db: AsyncSession, server_id: str) -> dict:
    """O servidor por trás de um `server_id` de rota, ou 404."""
    config = await get_effective_portainer_config(db)
    server = find_server(config, server_id)
    if not server:
        raise HTTPException(
            status_code=404,
            detail=f"Servidor Portainer '{server_id}' não encontrado."
        )
    return server


@portainer_router.get("/config")
async def get_portainer_config(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    config = await get_effective_portainer_config(db)
    return {"servers": [mask_server(s) for s in list_servers(config)]}


@portainer_router.post("/config")
async def save_portainer_config(
    payload: PortainerConfigRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    current = await get_effective_portainer_config(db)

    incoming = [
        unmask_server(s.model_dump(), find_server(current, s.id) if s.id else None)
        for s in payload.servers
    ]

    # Normalizar aqui é o que sorteia id para servidor novo e preenche o nome
    # padrão, deixando o registro pronto para as rotas por servidor.
    config = normalize_portainer_config({"servers": incoming})

    ids = [s["id"] for s in config["servers"]]
    if len(ids) != len(set(ids)):
        raise HTTPException(status_code=400, detail="Há servidores com o mesmo id.")

    await set_system_setting(db, "portainer_config", config)
    return {
        "message": "Configurações do Portainer salvas com sucesso!",
        "servers": [mask_server(s) for s in config["servers"]]
    }


@portainer_router.post("/test-connection")
async def test_portainer_connection(
    payload: PortainerServerRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Testa um servidor isolado — o que está sendo editado no formulário,
    ainda não necessariamente gravado."""
    current = await get_effective_portainer_config(db)
    data = unmask_server(
        payload.model_dump(),
        find_server(current, payload.id) if payload.id else None
    )
    return await PortainerService.test_connection(data)


@portainer_router.get("/servers")
async def list_portainer_servers(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Identificação dos servidores cadastrados, sem segredo algum — para as
    telas que precisam rotular a origem de um container."""
    config = await get_effective_portainer_config(db)
    return [
        {
            "id": s["id"],
            "name": s["name"],
            "url": s["url"],
            "enabled": s.get("enabled", True)
        }
        for s in list_servers(config)
    ]


@portainer_router.get("/endpoints")
async def list_portainer_endpoints(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    config = await get_effective_portainer_config(db)
    if not enabled_servers(config):
        return {"endpoints": [], "errors": []}

    endpoints, errors = await PortainerService.fetch_all_endpoints(config)
    return {"endpoints": endpoints, "errors": errors}


@portainer_router.get("/containers")
async def list_portainer_containers(
    endpoint_id: Optional[int] = None,
    server_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    config = await get_effective_portainer_config(db)

    # `server_id` recorta a consulta a um Portainer só.
    if server_id:
        server = find_server(config, server_id)
        if not server:
            raise HTTPException(
                status_code=404,
                detail=f"Servidor Portainer '{server_id}' não encontrado."
            )
        config = {"servers": [server]}

    if not enabled_servers(config):
        return {"containers": [], "errors": []}

    containers, errors = await PortainerService.fetch_all_containers(
        config, endpoint_id=endpoint_id
    )
    return {"containers": containers, "errors": errors}


@portainer_router.get("/catalog/{component_id}/containers")
async def get_component_containers(
    component_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    result = await db.execute(
        select(Component)
        .options(selectinload(Component.deployments))
        .where(Component.id == component_id)
    )
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Componente não encontrado")

    config = await get_effective_portainer_config(db)
    if not enabled_servers(config):
        return {
            "component_id": c.id,
            "component_name": c.name,
            "configured": False,
            "message": "Integração com Portainer não está configurada.",
            "containers": []
        }

    all_containers, errors = await PortainerService.fetch_all_containers(config)
    matched = PortainerService.match_containers_for_component(
        all_containers,
        component_name=c.name,
        deployments=c.deployments
    )

    return {
        "component_id": c.id,
        "component_name": c.name,
        "configured": True,
        "containers_count": len(matched),
        "containers": matched,
        # Servidores que não responderam. A resposta continua 200 com o que os
        # demais devolveram, em vez de sumir tudo por causa de um fora do ar.
        "errors": errors
    }


@portainer_router.get("/containers/{server_id}/{endpoint_id}/{container_id}/stats")
async def get_container_stats(
    server_id: str,
    endpoint_id: int,
    container_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    server = await _resolve_server(db, server_id)
    try:
        return await PortainerService.fetch_container_stats(server, endpoint_id, container_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter estatísticas do container: {str(e)}"
        )


@portainer_router.get("/containers/{server_id}/{endpoint_id}/{container_id}/logs")
async def get_container_logs(
    server_id: str,
    endpoint_id: int,
    container_id: str,
    tail: int = 150,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    server = await _resolve_server(db, server_id)
    try:
        return await PortainerService.fetch_container_logs(
            server, endpoint_id, container_id, tail=tail
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar logs do container: {str(e)}"
        )


@portainer_router.post("/containers/{server_id}/{endpoint_id}/{container_id}/action")
async def perform_container_action(
    server_id: str,
    endpoint_id: int,
    container_id: str,
    payload: ContainerActionRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """`server_id` é obrigatório de propósito: start/stop/restart em um
    ambiente homônimo do Portainer errado é um estrago silencioso."""
    server = await _resolve_server(db, server_id)
    try:
        return await PortainerService.execute_container_action(
            server, endpoint_id, container_id, payload.action
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao executar ação '{payload.action}' no container: {str(e)}"
        )
