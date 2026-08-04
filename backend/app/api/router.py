from typing import List, Optional
from urllib.parse import quote
from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import joinedload, undefer

from app.api.aggregations import build_group_detail, group_components
from app.api.graph import build_graph
from app.db.session import get_db
from app.db.models import Component, DocFile, Tag, ComponentDeployment
from app.gitlab.gitlab_crawler import (
    BINARY_DOC_TYPES,
    GitLabCrawlerService,
    ProjectListError,
    SyncMode,
    SyncOptions,
    doc_media_type,
)
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
    if tag:
        query = query.where(Component.tags.any(Tag.name == tag))

    result = await db.execute(query)
    components = result.scalars().all()

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
            "solution": c.solution,
            "system": c.system,
            "gitlab_url": c.gitlab_url,
            "manifest_path": c.manifest_path,
            "has_manifest": c.has_manifest,
            "docs_count": c.docs_count,
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
            "risks": [
                {
                    "id": r.id,
                    "severity": r.severity,
                    "category": r.category,
                    "title": r.title,
                    "description": r.description,
                    "file_path": r.file_path,
                    "recommendation": r.recommendation,
                    "created_at": r.created_at.isoformat() if r.created_at else None
                }
                for r in c.risks
            ],
            "critical_risks_count": sum(1 for r in c.risks if r.severity == "critical"),
            "warning_risks_count": sum(1 for r in c.risks if r.severity == "warning"),
            "gitlab_created_at": c.gitlab_created_at.isoformat() if c.gitlab_created_at else None,
            "first_commit_at": c.first_commit_at.isoformat() if c.first_commit_at else None,
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
        "solution": c.solution,
        "system": c.system,
        "gitlab_url": c.gitlab_url,
        "default_branch": c.default_branch,
        "docs_dir": c.docs_dir,
        "docs_index": c.docs_index,
        "has_manifest": c.has_manifest,
        "manifest_path": c.manifest_path,
        "docs_count": c.docs_count,
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
        "risks": [
            {
                "id": r.id,
                "severity": r.severity,
                "category": r.category,
                "title": r.title,
                "description": r.description,
                "file_path": r.file_path,
                "recommendation": r.recommendation,
                "created_at": r.created_at.isoformat() if r.created_at else None
            }
            for r in c.risks
        ],
        "critical_risks_count": sum(1 for r in c.risks if r.severity == "critical"),
        "warning_risks_count": sum(1 for r in c.risks if r.severity == "warning"),
        "gitlab_created_at": c.gitlab_created_at.isoformat() if c.gitlab_created_at else None,
        "first_commit_at": c.first_commit_at.isoformat() if c.first_commit_at else None,
        "last_activity_at": c.last_activity_at.isoformat() if c.last_activity_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None
    }



@protected_router.get("/graph")
async def get_dependency_graph(
    root: Optional[int] = Query(None, description="Recorta na vizinhança deste componente"),
    depth: int = Query(1, ge=1, le=5, description="Saltos a partir de `root`"),
    domain: Optional[str] = None,
    solution: Optional[str] = None,
    include_isolated: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """Grafo de dependências declaradas nos `project-info.yml`.

    Sem parâmetros devolve o catálogo inteiro; `root`, `domain` e `solution`
    recortam o escopo (o primeiro informado vence, nesta ordem).
    """
    result = await db.execute(select(Component))
    components = result.scalars().all()

    graph = build_graph(
        components,
        root_id=root,
        depth=depth,
        domain=domain,
        solution=solution,
        include_isolated=include_isolated,
    )
    if graph is None:
        raise HTTPException(status_code=404, detail="Escopo não encontrado no catálogo")
    return graph


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
    return group_components(result.scalars().all(), "domain")


@protected_router.get("/domains/{domain_name}")
async def get_domain_detail(domain_name: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Component))
    detail = build_group_detail(result.scalars().all(), "domain", domain_name)
    if not detail:
        raise HTTPException(status_code=404, detail="Domínio não encontrado")
    return detail


@protected_router.get("/solutions")
async def list_solutions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Component))
    return group_components(result.scalars().all(), "solution")


@protected_router.get("/solutions/{solution_name}")
async def get_solution_detail(solution_name: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Component))
    detail = build_group_detail(result.scalars().all(), "solution", solution_name)
    if not detail:
        raise HTTPException(status_code=404, detail="Solução não encontrada")
    return detail



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
            "doc_type": d.doc_type or "markdown",
            "size_bytes": d.size_bytes,
            "updated_at": d.updated_at.isoformat() if d.updated_at else None
        }
        for d in docs
    ]


def _content_snippet(content: Optional[str], term: str, radius: int = 90) -> Optional[str]:
    """Trecho em torno da primeira ocorrência de `term`, para dar contexto ao resultado."""
    if not content:
        return None
    idx = content.lower().find(term.lower())
    if idx == -1:
        return None

    start = max(0, idx - radius)
    end = min(len(content), idx + len(term) + radius)
    snippet = " ".join(content[start:end].split())
    return f"{'…' if start > 0 else ''}{snippet}{'…' if end < len(content) else ''}"


@protected_router.get("/catalog/{component_id}/docs-search")
async def search_component_docs(
    component_id: int,
    q: str = Query(..., min_length=2),
    db: AsyncSession = Depends(get_db)
):
    """Busca restrita aos documentos deste componente: caminho, título e conteúdo."""
    term = f"%{q}%"
    result = await db.execute(
        select(DocFile)
        # O texto entra no resultado, como trecho em torno do acerto.
        .options(undefer(DocFile.content_markdown))
        .where(
            DocFile.component_id == component_id,
            or_(
                DocFile.relative_path.ilike(term),
                DocFile.title.ilike(term),
                DocFile.content_markdown.ilike(term)
            )
        )
    )
    docs = result.scalars().all()

    items = []
    for d in docs:
        # `in_name` separa o acerto visível — caminho ou título — do acerto só no
        # corpo do texto: quem digita um nome de arquivo espera ele em primeiro.
        needle = q.lower()
        in_name = needle in d.relative_path.lower() or needle in (d.title or "").lower()
        items.append({
            "id": d.id,
            "relative_path": d.relative_path,
            "title": d.title,
            "doc_type": d.doc_type or "markdown",
            "in_name": in_name,
            "snippet": _content_snippet(d.content_markdown, q)
        })

    items.sort(key=lambda i: (not i["in_name"], i["relative_path"].lower()))
    return {"query": q, "results": items}


async def _load_doc(component_id: int, doc_path: str, db: AsyncSession, content_column) -> DocFile:
    """Carrega um documento com apenas a coluna de conteúdo que o chamador usa.

    As duas colunas de conteúdo são `deferred`; pedir a errada aqui traria um
    PDF inteiro para uma resposta que só devolve texto.
    """
    result = await db.execute(
        select(DocFile)
        .options(undefer(content_column))
        .where(DocFile.component_id == component_id, DocFile.relative_path == doc_path)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document file not found")
    return doc


@protected_router.get("/catalog/{component_id}/docs-raw/{doc_path:path}")
async def get_component_doc_raw(component_id: int, doc_path: str, db: AsyncSession = Depends(get_db)):
    """Bytes originais de um documento binário (PDF, DOCX ou imagem), para o navegador."""
    doc = await _load_doc(component_id, doc_path, db, DocFile.content_binary)
    if doc.doc_type not in BINARY_DOC_TYPES or doc.content_binary is None:
        raise HTTPException(status_code=404, detail="Document has no binary content")

    filename = doc.relative_path.split("/")[-1]
    return Response(
        content=doc.content_binary,
        media_type=doc_media_type(doc.relative_path),
        headers={"Content-Disposition": f'inline; filename="{quote(filename)}"'}
    )


@protected_router.get("/catalog/{component_id}/docs/{doc_path:path}")
async def get_component_doc_content(component_id: int, doc_path: str, db: AsyncSession = Depends(get_db)):
    doc = await _load_doc(component_id, doc_path, db, DocFile.content_markdown)

    return {
        "id": doc.id,
        "relative_path": doc.relative_path,
        "title": doc.title,
        "doc_type": doc.doc_type or "markdown",
        "size_bytes": doc.size_bytes,
        # Binário não tem texto para devolver aqui; o cliente busca `docs-raw`.
        "content_markdown": doc.content_markdown if doc.doc_type not in BINARY_DOC_TYPES else None,
        "updated_at": doc.updated_at.isoformat() if doc.updated_at else None
    }

class SyncRequest(BaseModel):
    mode: SyncMode = SyncMode.UPDATE
    #: Vazio ou ausente = catálogo inteiro.
    project_ids: Optional[List[int]] = None
    #: Pasta a varrer no lugar da declarada em `spec.docs.dir`. Vazio = manter
    #: o que o manifesto diz.
    docs_dir: Optional[str] = None
    #: Indexar as imagens encontradas na varredura da documentação.
    index_images: bool = True


@protected_router.get("/sync/projects")
async def list_syncable_projects(db: AsyncSession = Depends(get_db)):
    """Projetos do GitLab que podem ser sincronizados individualmente.

    Vem do GitLab, e não do catálogo, para que um projeto ainda não importado
    também possa ser escolhido. `in_catalog` diz quais já estão no catálogo.
    """
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


@protected_router.post("/sync", status_code=202)
async def trigger_sync(payload: Optional[SyncRequest] = Body(default=None)):
    """Dispara uma operação de catálogo e devolve na hora.

    O crawl leva minutos; o acompanhamento é por `GET /sync/status`.
    """
    request = payload or SyncRequest()
    project_ids = request.project_ids or None

    # `rebuild` apaga o catálogo antes de importar e `prune` decide o que
    # remover comparando com a lista inteira do GitLab: restringir qualquer uma
    # das duas a alguns projetos apagaria todo o resto.
    if project_ids and request.mode != SyncMode.UPDATE:
        raise HTTPException(
            status_code=400,
            detail=f"A seleção de projetos só vale para o modo '{SyncMode.UPDATE.value}'.",
        )

    docs_dir = (request.docs_dir or "").strip()
    if ".." in docs_dir.split("/"):
        raise HTTPException(
            status_code=400,
            detail="A pasta de documentação não pode sair da raiz do repositório.",
        )

    options = SyncOptions(
        docs_dir=docs_dir or None,
        index_images=request.index_images,
    )

    # Ambas descrevem um repositório — onde ficam os documentos dele, se as
    # imagens dele valem o espaço no banco. Aplicá-las ao catálogo inteiro
    # reescreveria a `docs_dir` de todo mundo com o caminho de um só.
    if (options.docs_dir is not None or not options.index_images) and not project_ids:
        raise HTTPException(
            status_code=400,
            detail="A pasta de documentação e a indexação de imagens só valem "
                   "para uma seleção de projetos.",
        )

    try:
        job = await sync_jobs.start(request.mode, project_ids=project_ids, options=options)
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
                "title": d.title,
                "doc_type": d.doc_type or "markdown"
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
