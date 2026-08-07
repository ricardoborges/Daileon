from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models import Component
from app.api.auth import get_current_user
from app.plugins.gitlab.crawler import GitLabCrawlerService, ProjectListError

gitlab_router = APIRouter(tags=["gitlab"])

@gitlab_router.get("/catalog/{component_id}/commits", dependencies=[Depends(get_current_user)])
async def get_component_commits(component_id: int, days: int = Query(365, ge=7, le=730), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Component).where(Component.id == component_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Component not found")

    crawler = GitLabCrawlerService()
    commits_data = await crawler.fetch_project_commits(c.gitlab_project_id, days=days)

    return {
        "component_id": c.id,
        "component_name": c.name,
        "gitlab_project_id": c.gitlab_project_id,
        **commits_data
    }

@gitlab_router.get("/sync/projects", dependencies=[Depends(get_current_user)])
async def list_syncable_projects(db: AsyncSession = Depends(get_db)):
    """Projetos do GitLab que podem ser sincronizados individualmente."""
    crawler = GitLabCrawlerService()
    try:
        projects = await crawler.fetch_projects()
    except ProjectListError as e:
        raise HTTPException(status_code=502, detail=str(e))

    known = set((await db.execute(select(Component.gitlab_project_id))).scalars().all())
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
