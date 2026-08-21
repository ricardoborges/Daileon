from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.db.models import Component
from app.api.auth import get_current_user, set_system_setting
from app.plugins.zabbix.service import (
    ZabbixService,
    get_effective_zabbix_config,
    ZABBIX_CONFIG_KEY,
    SEVERITY_MAP
)

zabbix_router = APIRouter(prefix="/plugins/zabbix", tags=["zabbix"])


class ZabbixConfigRequest(BaseModel):
    url: str
    api_token: Optional[str] = ""
    username: Optional[str] = ""
    password: Optional[str] = ""
    cache_ttl: int = 30
    enabled: bool = True


async def _get_zabbix_service(db: AsyncSession) -> ZabbixService:
    config = await get_effective_zabbix_config(db)
    if not config.get("enabled"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="A integração com o Zabbix não está habilitada."
        )
    return ZabbixService(
        url=config.get("url", ""),
        api_token=config.get("api_token"),
        username=config.get("username"),
        password=config.get("password"),
        cache_ttl=config.get("cache_ttl", 30)
    )


@zabbix_router.get("/config")
async def get_zabbix_config(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Retorna a configuração atual do Zabbix."""
    config = await get_effective_zabbix_config(db)
    return config


@zabbix_router.post("/config")
async def save_zabbix_config(
    req: ZabbixConfigRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Salva a configuração do Zabbix no banco de dados."""
    current = await get_effective_zabbix_config(db)
    data = req.model_dump()

    # Preservar credenciais caso venham mascaradas
    if data["api_token"] == "********":
        data["api_token"] = current.get("api_token", "")
    if data["password"] == "********":
        data["password"] = current.get("password", "")

    await set_system_setting(db, ZABBIX_CONFIG_KEY, data)
    return {"status": "ok", "message": "Configuração do Zabbix salva com sucesso."}


@zabbix_router.get("/status")
async def get_zabbix_status(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Testa a conexão com o Zabbix e retorna a versão e status."""
    try:
        service = await _get_zabbix_service(db)
        version = await service.get_version()
        return {
            "status": "connected",
            "version": version,
            "url": service.url
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@zabbix_router.get("/problems")
async def get_zabbix_problems(
    host_name: Optional[str] = Query(None),
    min_severity: int = Query(0, ge=0, le=5),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Lista os problemas ativos no Zabbix."""
    service = await _get_zabbix_service(db)
    host_ids = None

    if host_name:
        hosts = await service.get_hosts(host_names=[host_name])
        if hosts:
            host_ids = [h["hostid"] for h in hosts]
        else:
            return []

    problems = await service.get_active_problems(host_ids=host_ids, min_severity=min_severity)
    return problems


@zabbix_router.get("/component/{component_id}")
async def get_component_observability(
    component_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Retorna os dados completos de observabilidade Zabbix para um componente específico do catálogo."""
    query = select(Component).options(selectinload(Component.deployments)).where(Component.id == component_id)
    res = await db.execute(query)
    comp = res.scalar_one_or_none()

    if not comp:
        raise HTTPException(status_code=404, detail="Componente não encontrado.")

    # Tentar resolver o host name do Zabbix a partir do componente
    zabbix_host_name = None
    if comp.manifest_path:
        # Se houver manifest no spec
        pass  # Pode vir do project-info.yml

    # Fallback para server_name ou name do componente
    candidates = []
    if comp.name:
        candidates.append(comp.name)
    for dep in comp.deployments:
        if dep.server_name and dep.server_name not in candidates:
            candidates.append(dep.server_name)

    try:
        service = await _get_zabbix_service(db)
        matched_hosts = await service.get_hosts(host_names=candidates)
        
        if not matched_hosts:
            return {
                "matched": False,
                "candidates": candidates,
                "message": f"Nenhum host correspondente a {candidates} encontrado no Zabbix.",
                "status": "UNKNOWN",
                "problems": [],
                "metrics": None
            }

        host = matched_hosts[0]
        host_id = host["hostid"]
        problems = await service.get_active_problems(host_ids=[host_id])
        metrics = await service.get_host_metrics(host_id)

        # Calcular status global do componente baseado nas severidades ativas
        overall_status = "OK"
        if problems:
            max_sev = max([int(p.get("severity", 0)) for p in problems])
            if max_sev >= 4:
                overall_status = "CRITICAL"
            elif max_sev >= 2:
                overall_status = "WARNING"
            else:
                overall_status = "NOTICE"

        return {
            "matched": True,
            "host_id": host_id,
            "host_name": host.get("name"),
            "status": overall_status,
            "zabbix_available": host.get("available") == "1",
            "problems": problems,
            "metrics": metrics
        }
    except Exception as e:
        return {
            "matched": False,
            "error": str(e),
            "status": "UNKNOWN",
            "problems": [],
            "metrics": None
        }


@zabbix_router.post("/webhook")
async def receive_zabbix_webhook(payload: Dict[str, Any]):
    """Recebe eventos e alertas enviados via Webhook do Zabbix."""
    # Processar alerta recebido
    event_id = payload.get("eventid")
    subject = payload.get("subject", "Zabbix Alert")
    message = payload.get("message", "")
    
    return {
        "status": "received",
        "event_id": event_id,
        "message": f"Webhook processado com sucesso: {subject}"
    }
