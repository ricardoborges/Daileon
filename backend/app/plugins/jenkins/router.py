from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models import Component
from app.api.auth import get_current_user
from app.core.config import settings
from app.plugins.jenkins.service import (
    fetch_jenkins_job_status,
    get_effective_jenkins_config,
    set_system_setting,
    test_jenkins_connection,
)

jenkins_router = APIRouter(tags=["jenkins"])


class JenkinsConfigRequest(BaseModel):
    url: str = "https://jenkins.example.com"
    user: str = ""
    api_token: str = ""
    enabled: bool = True


@jenkins_router.get("/plugins/jenkins/config")
async def get_jenkins_config(
    db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)
):
    config = await get_effective_jenkins_config(db)
    res = dict(config)
    if res.get("api_token"):
        res["api_token"] = "******"
    return res


@jenkins_router.post("/plugins/jenkins/config")
async def save_jenkins_config(
    payload: JenkinsConfigRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    current = await get_effective_jenkins_config(db)
    new_data = payload.model_dump()

    if new_data.get("api_token") == "******":
        new_data["api_token"] = current.get("api_token", "")

    await set_system_setting(db, "jenkins_config", new_data)
    return {"message": "Configurações do Jenkins salvas com sucesso!"}


@jenkins_router.post("/plugins/jenkins/config/test")
async def test_jenkins_config_endpoint(
    payload: JenkinsConfigRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    current = await get_effective_jenkins_config(db)
    config = payload.model_dump()
    if config.get("api_token") == "******":
        config["api_token"] = current.get("api_token", "")

    res = await test_jenkins_connection(config)
    return res


@jenkins_router.get(
    "/catalog/{component_id}/jenkins", dependencies=[Depends(get_current_user)]
)
async def get_component_jenkins_status(
    component_id: int, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Component).where(Component.id == component_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Component not found")

    pipelines_status = []
    for pipe in c.jenkins_pipelines:
        status_info = await fetch_jenkins_job_status(
            pipe.job, server_url=pipe.server_url, db=db
        )
        pipelines_status.append(
            {
                "id": pipe.id,
                "name": pipe.name,
                "environment": pipe.environment,
                "job": pipe.job,
                "server_url": pipe.server_url,
                "status_info": status_info,
            }
        )

    cfg = await get_effective_jenkins_config(db)
    token_configured = bool(cfg.get("api_token") or cfg.get("user"))

    return {
        "component_id": c.id,
        "component_name": c.name,
        "jenkins_token_configured": token_configured,
        "pipelines": pipelines_status,
    }
