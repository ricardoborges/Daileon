from typing import List, Optional
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.db.session import get_db
from app.db.models import Component, DocFile, Tag
from app.gitlab.gitlab_crawler import SyncMode
from app.sync.jobs import SyncAlreadyRunning, sync_jobs
from app.api.auth import auth_router, get_current_user
from app.jenkins.jenkins_service import fetch_jenkins_job_status
from app.core.config import settings


api_router = APIRouter()
api_router.include_router(auth_router)

protected_router = APIRouter(dependencies=[Depends(get_current_user)])
api_router.include_router(protected_router)


@protected_router.get("/catalog")

async def list_components(
    owner: Optional[str] = None,
    type: Optional[str] = None,
    lifecycle: Optional[str] = None,
    tag: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(Component)
    if owner:
        query = query.where(Component.owner == owner)
    if type:
        query = query.where(Component.type == type)
    if lifecycle:
        query = query.where(Component.lifecycle == lifecycle)
    
    result = await db.execute(query)
    components = result.scalars().all()

    if tag:
        components = [c for c in components if any(t.name == tag for t in c.tags)]

    return [
        {
            "id": c.id,
            "gitlab_project_id": c.gitlab_project_id,
            "name": c.name,
            "description": c.description,
            "kind": c.kind,
            "type": c.type,
            "lifecycle": c.lifecycle,
            "owner": c.owner,
            "domain": c.domain,
            "system": c.system,
            "gitlab_url": c.gitlab_url,
            "has_manifest": c.has_manifest,
            "tags": [t.name for t in c.tags],
            "links": [{"title": l.title, "url": l.url, "icon": l.icon} for l in c.links],
            "dependencies": [d.target_component_name for d in c.dependencies],
            "gitlab_created_at": c.gitlab_created_at.isoformat() if c.gitlab_created_at else None,
            "last_activity_at": c.last_activity_at.isoformat() if c.last_activity_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None
        }
        for c in components
    ]

@protected_router.get("/catalog/{component_id}")
async def get_component(component_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Component).where(Component.id == component_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Component not found")
    
    return {
        "id": c.id,
        "gitlab_project_id": c.gitlab_project_id,
        "name": c.name,
        "description": c.description,
        "kind": c.kind,
        "type": c.type,
        "lifecycle": c.lifecycle,
        "owner": c.owner,
        "domain": c.domain,
        "system": c.system,
        "gitlab_url": c.gitlab_url,
        "default_branch": c.default_branch,
        "docs_dir": c.docs_dir,
        "docs_index": c.docs_index,
        "has_manifest": c.has_manifest,
        "tags": [t.name for t in c.tags],
        "links": [{"title": l.title, "url": l.url, "icon": l.icon} for l in c.links],
        "dependencies": [d.target_component_name for d in c.dependencies],
        "jenkins_pipelines": [
            {
                "id": p.id,
                "name": p.name,
                "environment": p.environment,
                "job": p.job,
                "server_url": p.server_url
            }
            for p in c.jenkins_pipelines
        ],
        "gitlab_created_at": c.gitlab_created_at.isoformat() if c.gitlab_created_at else None,
        "last_activity_at": c.last_activity_at.isoformat() if c.last_activity_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None
    }

@protected_router.get("/catalog/{component_id}/jenkins")
async def get_component_jenkins_status(component_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Component).where(Component.id == component_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Component not found")
    
    pipelines_status = []
    for pipe in c.jenkins_pipelines:
        status_info = await fetch_jenkins_job_status(pipe.job, server_url=pipe.server_url)
        pipelines_status.append({
            "id": pipe.id,
            "name": pipe.name,
            "environment": pipe.environment,
            "job": pipe.job,
            "server_url": pipe.server_url,
            "status_info": status_info
        })

    return {
        "component_id": c.id,
        "component_name": c.name,
        "jenkins_token_configured": bool(settings.JENKINS_API_TOKEN or settings.JENKINS_USER),
        "pipelines": pipelines_status
    }


@protected_router.get("/catalog/{component_id}/docs")
async def list_component_docs(component_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DocFile).where(DocFile.component_id == component_id))
    docs = result.scalars().all()
    return [
        {
            "id": d.id,
            "relative_path": d.relative_path,
            "title": d.title,
            "updated_at": d.updated_at.isoformat() if d.updated_at else None
        }
        for d in docs
    ]

@protected_router.get("/catalog/{component_id}/docs/{doc_path:path}")
async def get_component_doc_content(component_id: int, doc_path: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(DocFile).where(DocFile.component_id == component_id, DocFile.relative_path == doc_path)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document file not found")
    
    return {
        "id": doc.id,
        "relative_path": doc.relative_path,
        "title": doc.title,
        "content_markdown": doc.content_markdown,
        "updated_at": doc.updated_at.isoformat() if doc.updated_at else None
    }

class SyncRequest(BaseModel):
    mode: SyncMode = SyncMode.UPDATE


@protected_router.post("/sync", status_code=202)
async def trigger_sync(payload: Optional[SyncRequest] = Body(default=None)):
    """Dispara uma operação de catálogo e devolve na hora.

    O crawl leva minutos; o acompanhamento é por `GET /sync/status`.
    """
    mode = (payload or SyncRequest()).mode
    try:
        job = await sync_jobs.start(mode)
    except SyncAlreadyRunning as e:
        raise HTTPException(status_code=409, detail=str(e))

    return job.snapshot()


@protected_router.get("/sync/status")
async def sync_status(since: int = Query(0, ge=0)):
    """Estado da operação atual, com as linhas de log a partir de `since`."""
    job = sync_jobs.current
    if not job:
        return {"state": "idle", "logs": [], "cursor": 0}
    return job.snapshot(since=since)

@protected_router.get("/search")
async def global_search(q: str = Query(..., min_length=1), db: AsyncSession = Depends(get_db)):
    search_term = f"%{q}%"
    
    # Search components
    comp_stmt = select(Component).where(
        or_(
            Component.name.ilike(search_term),
            Component.description.ilike(search_term),
            Component.owner.ilike(search_term)
        )
    )
    comp_res = await db.execute(comp_stmt)
    components = comp_res.scalars().all()

    # Search docs
    doc_stmt = select(DocFile).where(
        or_(
            DocFile.title.ilike(search_term),
            DocFile.content_markdown.ilike(search_term)
        )
    )
    doc_res = await db.execute(doc_stmt)
    docs = doc_res.scalars().all()

    return {
        "query": q,
        "components": [
            {
                "id": c.id,
                "name": c.name,
                "description": c.description,
                "type": c.type,
                "owner": c.owner
            }
            for c in components
        ],
        "docs": [
            {
                "id": d.id,
                "component_id": d.component_id,
                "relative_path": d.relative_path,
                "title": d.title
            }
            for d in docs
        ]
    }
