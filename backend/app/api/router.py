from typing import List, Optional
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import joinedload

from app.db.session import get_db
from app.db.models import Component, DocFile, Tag, ComponentDeployment
from app.gitlab.gitlab_crawler import GitLabCrawlerService, SyncMode
from app.sync.jobs import SyncAlreadyRunning, sync_jobs
from app.api.auth import auth_router, get_current_user, get_system_setting, set_system_setting
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
            "docs_count": len(c.docs),
            "tags": [t.name for t in c.tags],
            "links": [{"title": l.title, "url": l.url, "icon": l.icon} for l in c.links],
            "dependencies": [d.target_component_name for d in c.dependencies],
            "deployments": [
                {
                    "id": dep.id,
                    "environment": dep.environment,
                    "url": dep.url,
                    "server_name": dep.server_name,
                    "server_ip": dep.server_ip,
                    "os": dep.os,
                    "execution_type": dep.execution_type,
                    "port": dep.port,
                    "notes": dep.notes
                }
                for dep in c.deployments
            ],
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
        "docs_count": len(c.docs),
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
        "deployments": [
            {
                "id": dep.id,
                "environment": dep.environment,
                "url": dep.url,
                "server_name": dep.server_name,
                "server_ip": dep.server_ip,
                "os": dep.os,
                "execution_type": dep.execution_type,
                "port": dep.port,
                "notes": dep.notes
            }
            for dep in c.deployments
        ],
        "gitlab_created_at": c.gitlab_created_at.isoformat() if c.gitlab_created_at else None,
        "last_activity_at": c.last_activity_at.isoformat() if c.last_activity_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None
    }


@protected_router.get("/servers")
async def list_servers(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ComponentDeployment)
        .options(joinedload(ComponentDeployment.component))
        .join(Component)
    )
    deployments = result.scalars().all()

    servers_map = {}
    for dep in deployments:
        if not dep.server_name and not dep.server_ip:
            continue
        
        server_key = dep.server_name or dep.server_ip
        if server_key not in servers_map:
            servers_map[server_key] = {
                "server_name": dep.server_name or dep.server_ip,
                "server_ip": dep.server_ip,
                "environments": set(),
                "components": []
            }
        
        s = servers_map[server_key]
        if dep.server_ip and not s["server_ip"]:
            s["server_ip"] = dep.server_ip
        if dep.environment:
            s["environments"].add(dep.environment)
            
        s["components"].append({
            "deployment_id": dep.id,
            "component_id": dep.component.id,
            "component_name": dep.component.name,
            "component_type": dep.component.type,
            "owner": dep.component.owner,
            "environment": dep.environment,
            "url": dep.url,
            "os": dep.os,
            "execution_type": dep.execution_type,
            "port": dep.port,
            "notes": dep.notes
        })

    servers_list = []
    for s_name, data in servers_map.items():
        servers_list.append({
            "server_name": data["server_name"],
            "server_ip": data["server_ip"],
            "environments": sorted(list(data["environments"])),
            "components_count": len(data["components"]),
            "components": data["components"]
        })

    servers_list.sort(key=lambda x: str(x["server_name"]).lower())
    return servers_list


@protected_router.get("/servers/{server_name}")
async def get_server_detail(server_name: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ComponentDeployment)
        .options(joinedload(ComponentDeployment.component))
        .join(Component)
    )
    deployments = result.scalars().all()

    target_deployments = []
    srv_ip = None
    environments = set()
    canonical_name = None

    for dep in deployments:
        dep_sname = dep.server_name or dep.server_ip
        if not dep_sname:
            continue

        match_name = dep.server_name and dep.server_name.lower() == server_name.lower()
        match_ip = dep.server_ip and dep.server_ip.lower() == server_name.lower()
        match_key = dep_sname.lower() == server_name.lower()

        if match_name or match_ip or match_key:
            if not canonical_name:
                canonical_name = dep.server_name or dep.server_ip
            if dep.server_ip and not srv_ip:
                srv_ip = dep.server_ip
            if dep.environment:
                environments.add(dep.environment)

            target_deployments.append({
                "deployment_id": dep.id,
                "component_id": dep.component.id,
                "component_name": dep.component.name,
                "component_type": dep.component.type,
                "owner": dep.component.owner,
                "environment": dep.environment,
                "url": dep.url,
                "os": dep.os,
                "execution_type": dep.execution_type,
                "port": dep.port,
                "notes": dep.notes
            })

    if not target_deployments:
        raise HTTPException(status_code=404, detail="Servidor não encontrado")

    return {
        "server_name": canonical_name or server_name,
        "server_ip": srv_ip,
        "environments": sorted(list(environments)),
        "components_count": len(target_deployments),
        "components": target_deployments
    }


@protected_router.get("/domains")
async def list_domains(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Component))
    components = result.scalars().all()

    domains_map = {}
    for c in components:
        if not c.domain or not c.domain.strip():
            continue

        domain_key = c.domain.strip()
        if domain_key not in domains_map:
            domains_map[domain_key] = {
                "domain": domain_key,
                "systems": set(),
                "owners": set(),
                "components": []
            }

        d = domains_map[domain_key]
        if c.system:
            d["systems"].add(c.system)
        if c.owner:
            d["owners"].add(c.owner)

        d["components"].append({
            "id": c.id,
            "gitlab_project_id": c.gitlab_project_id,
            "name": c.name,
            "description": c.description,
            "kind": c.kind,
            "type": c.type,
            "lifecycle": c.lifecycle,
            "owner": c.owner,
            "system": c.system,
            "gitlab_url": c.gitlab_url,
            "has_manifest": c.has_manifest,
            "docs_count": len(c.docs)
        })

    domains_list = []
    for d_name, data in domains_map.items():
        domains_list.append({
            "domain": data["domain"],
            "systems": sorted(list(data["systems"])),
            "owners": sorted(list(data["owners"])),
            "components_count": len(data["components"]),
            "components": data["components"]
        })

    domains_list.sort(key=lambda x: str(x["domain"]).lower())
    return domains_list


@protected_router.get("/domains/{domain_name}")
async def get_domain_detail(domain_name: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Component))
    components = result.scalars().all()

    target_components = []
    systems = set()
    owners = set()
    canonical_domain = None

    for c in components:
        if not c.domain or not c.domain.strip():
            continue

        if c.domain.strip().lower() == domain_name.strip().lower():
            if not canonical_domain:
                canonical_domain = c.domain.strip()
            if c.system:
                systems.add(c.system)
            if c.owner:
                owners.add(c.owner)

            target_components.append({
                "id": c.id,
                "gitlab_project_id": c.gitlab_project_id,
                "name": c.name,
                "description": c.description,
                "kind": c.kind,
                "type": c.type,
                "lifecycle": c.lifecycle,
                "owner": c.owner,
                "system": c.system,
                "gitlab_url": c.gitlab_url,
                "has_manifest": c.has_manifest,
                "docs_count": len(c.docs),
                "tags": [t.name for t in c.tags],
                "deployments_count": len(c.deployments)
            })

    if not target_components:
        raise HTTPException(status_code=404, detail="Domínio não encontrado")

    return {
        "domain": canonical_domain or domain_name,
        "systems": sorted(list(systems)),
        "owners": sorted(list(owners)),
        "components_count": len(target_components),
        "components": target_components
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


@protected_router.get("/catalog/{component_id}/commits")
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

class OrgConfigRequest(BaseModel):
    name: str = ""
    acronym: str = ""

async def get_effective_org_config(db: AsyncSession) -> dict:
    config = await get_system_setting(db, "org_config")
    if config is None:
        config = {
            "name": settings.ORGANIZATION_NAME,
            "acronym": settings.ORGANIZATION_ACRONYM
        }
        if settings.ORGANIZATION_NAME or settings.ORGANIZATION_ACRONYM:
            await set_system_setting(db, "org_config", config)
    else:
        updated = False
        if settings.ORGANIZATION_NAME and not config.get("name"):
            config["name"] = settings.ORGANIZATION_NAME
            updated = True
        if settings.ORGANIZATION_ACRONYM and not config.get("acronym"):
            config["acronym"] = settings.ORGANIZATION_ACRONYM
            updated = True
        if updated:
            await set_system_setting(db, "org_config", config)

    return config

@api_router.get("/org-config")
async def get_org_config(db: AsyncSession = Depends(get_db)):
    return await get_effective_org_config(db)

@protected_router.post("/org-config")
async def update_org_config(payload: OrgConfigRequest, db: AsyncSession = Depends(get_db)):
    data = payload.model_dump()
    await set_system_setting(db, "org_config", data)
    return {"message": "Configurações da organização salvas com sucesso!"}
