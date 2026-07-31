from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.db.session import get_db
from app.db.models import Component, DocFile, Tag
from app.gitlab.gitlab_crawler import GitLabCrawlerService

api_router = APIRouter()

@api_router.get("/catalog")
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
            "updated_at": c.updated_at.isoformat() if c.updated_at else None
        }
        for c in components
    ]

@api_router.get("/catalog/{component_id}")
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
        "updated_at": c.updated_at.isoformat() if c.updated_at else None
    }

@api_router.get("/catalog/{component_id}/docs")
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

@api_router.get("/catalog/{component_id}/docs/{doc_path:path}")
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

@api_router.post("/sync")
async def trigger_sync(db: AsyncSession = Depends(get_db)):
    crawler = GitLabCrawlerService()
    try:
        synced = await crawler.sync_all(db)
        return {"status": "success", "synced_count": len(synced)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync error: {str(e)}")

@api_router.get("/search")
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
