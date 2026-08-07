from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models import Component
from app.api.auth import get_current_user
from app.plugins.gitlab.crawler import GitLabCrawlerService, ProjectListError
from app.plugins.gitlab.service import (
    get_effective_gitlab_config,
    set_system_setting,
    test_gitlab_connection,
)

gitlab_router = APIRouter(tags=["gitlab"])


class GitLabConfigRequest(BaseModel):
    url: str = "https://gitlab.com"
    read_token: str = ""
    group_id: str = ""
    enabled: bool = True


@gitlab_router.get("/plugins/gitlab/config")
async def get_gitlab_config(
    db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)
):
    config = await get_effective_gitlab_config(db)
    res = dict(config)
    if res.get("read_token"):
        res["read_token"] = "******"
    return res


@gitlab_router.post("/plugins/gitlab/config")
async def save_gitlab_config(
    payload: GitLabConfigRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    current = await get_effective_gitlab_config(db)
    new_data = payload.model_dump()

    if new_data.get("read_token") == "******":
        new_data["read_token"] = current.get("read_token", "")

    await set_system_setting(db, "gitlab_config", new_data)
    return {"message": "Configurações do GitLab salvas com sucesso!"}


@gitlab_router.post("/plugins/gitlab/config/test")
async def test_gitlab_config_endpoint(
    payload: GitLabConfigRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    current = await get_effective_gitlab_config(db)
    config = payload.model_dump()
    if config.get("read_token") == "******":
        config["read_token"] = current.get("read_token", "")

    res = await test_gitlab_connection(config)
    return res


@gitlab_router.get(
    "/catalog/{component_id}/commits", dependencies=[Depends(get_current_user)]
)
async def get_component_commits(
    component_id: int,
    days: int = Query(365, ge=7, le=730),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Component).where(Component.id == component_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Component not found")

    crawler = await GitLabCrawlerService.create(db)
    commits_data = await crawler.fetch_project_commits(
        c.gitlab_project_id, days=days
    )

    return {
        "component_id": c.id,
        "component_name": c.name,
        "gitlab_project_id": c.gitlab_project_id,
        **commits_data,
    }


@gitlab_router.get("/sync/projects", dependencies=[Depends(get_current_user)])
async def list_syncable_projects(db: AsyncSession = Depends(get_db)):
    """Projetos do GitLab que podem ser sincronizados individualmente."""
    crawler = await GitLabCrawlerService.create(db)
    try:
        projects = await crawler.fetch_projects()
    except ProjectListError as e:
        raise HTTPException(status_code=502, detail=str(e))

    known = set(
        (await db.execute(select(Component.gitlab_project_id))).scalars().all()
    )
    return sorted(
        (
            {
                "id": p.get("id"),
                "name": p.get("name") or "",
                "path": p.get("path_with_namespace") or "",
                "web_url": p.get("web_url"),
                "in_catalog": p.get("id") in known,
            }
            for p in projects
            if p.get("id") is not None
        ),
        key=lambda p: (p["path"] or p["name"]).lower(),
    )
