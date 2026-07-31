import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
import httpx
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import (
    Component, Tag, ComponentLink, ComponentDependency, DocFile, component_tags
)
from app.catalog.manifest import DaileonManifest

logger = logging.getLogger(__name__)


class SyncMode(str, Enum):
    """As três operações que o painel de configuração expõe."""

    UPDATE = "update"    # atualiza o que existe e importa o que é novo
    REBUILD = "rebuild"  # apaga o catálogo e importa tudo de novo
    PRUNE = "prune"      # remove o que não existe mais no GitLab


class ProjectListError(RuntimeError):
    """A listagem de projetos do GitLab falhou.

    Importa distinguir isso de "o GitLab não tem projetos": a lista incompleta
    não pode ser usada como referência do que existe.
    """


class SyncProgress:
    """Canal de progresso. A implementação padrão descarta tudo.

    Mantém o crawler desacoplado de quem observa (job em memória, testes, CLI).
    """

    def log(self, level: str, message: str) -> None:
        """`level`: info | ok | warn | error."""

    def set_total(self, total: int) -> None:
        """Número de passos da operação — sai da fase indeterminada."""

    def advance(self) -> None:
        """Um passo concluído (com sucesso ou não)."""


@dataclass
class SyncFailure:
    project_id: Optional[int]
    name: str
    error: str


@dataclass
class SyncResult:
    """Resultado de uma sincronização completa.

    Guarda apenas nomes, e não instâncias de `Component`: um rollback expira
    todos os objetos da sessão, e ler um atributo expirado em contexto async
    dispara I/O implícito (greenlet_spawn).
    """
    mode: str = SyncMode.UPDATE.value
    synced: List[str] = field(default_factory=list)
    failed: List[SyncFailure] = field(default_factory=list)
    removed: List[str] = field(default_factory=list)


class GitLabCrawlerService:
    def __init__(self, gitlab_url: Optional[str] = None, token: Optional[str] = None):
        self.base_url = (gitlab_url or settings.GITLAB_URL).rstrip("/")
        self.token = token or settings.GITLAB_READ_TOKEN
        self.headers = {}
        if self.token:
            self.headers["PRIVATE-TOKEN"] = self.token

    async def fetch_projects(self, group_id: Optional[str] = None) -> List[Dict[str, Any]]:
        projects = []
        page = 1
        per_page = 100
        async with httpx.AsyncClient(headers=self.headers, timeout=20.0) as client:
            while True:
                if group_id or settings.GITLAB_GROUP_ID:
                    target_group = group_id or settings.GITLAB_GROUP_ID
                    url = f"{self.base_url}/api/v4/groups/{target_group}/projects?include_subgroups=true&page={page}&per_page={per_page}"
                else:
                    url = f"{self.base_url}/api/v4/projects?membership=true&page={page}&per_page={per_page}"
                
                # Uma falha aqui não pode virar lista vazia ou parcial: quem
                # chama usa esta lista como a verdade sobre o que existe no
                # GitLab, e `prune` apagaria o catálogo inteiro com base nela.
                try:
                    resp = await client.get(url)
                except Exception as e:
                    raise ProjectListError(f"Erro ao consultar o GitLab: {e}") from e

                if resp.status_code != 200:
                    raise ProjectListError(
                        f"GitLab respondeu {resp.status_code} ao listar projetos: {resp.text[:200]}"
                    )

                data = resp.json()
                if not data:
                    break
                projects.extend(data)
                page += 1
                if len(data) < per_page:
                    break
        return projects

    async def fetch_file_content(self, project_id: int, file_path: str, ref: str = "main") -> Optional[str]:
        encoded_path = file_path.replace("/", "%2F")
        url = f"{self.base_url}/api/v4/projects/{project_id}/repository/files/{encoded_path}/raw?ref={ref}"
        async with httpx.AsyncClient(headers=self.headers, timeout=15.0) as client:
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    return resp.text
            except Exception as e:
                logger.error(f"Error fetching file {file_path} for project {project_id}: {e}")
        return None

    async def fetch_docs_tree(self, project_id: int, docs_dir: str, ref: str = "main") -> List[Dict[str, Any]]:
        clean_dir = docs_dir.strip("/")
        url = f"{self.base_url}/api/v4/projects/{project_id}/repository/tree?path={clean_dir}&recursive=true&ref={ref}"
        async with httpx.AsyncClient(headers=self.headers, timeout=15.0) as client:
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    tree = resp.json()
                    return [item for item in tree if item.get("type") == "blob" and item.get("name", "").endswith(".md")]
            except Exception as e:
                logger.error(f"Error fetching docs tree for project {project_id}: {e}")
        return []

    async def sync_project(self, db: AsyncSession, project_data: Dict[str, Any]) -> Component:
        project_id = project_data["id"]
        project_name = project_data["name"]
        default_branch = project_data.get("default_branch", "main")
        web_url = project_data.get("web_url", "")
        description = project_data.get("description", "")

        # Try to fetch project-info.yml
        raw_manifest = await self.fetch_file_content(project_id, "project-info.yml", ref=default_branch)
        manifest: Optional[DaileonManifest] = None
        has_manifest = False

        if raw_manifest:
            try:
                manifest = DaileonManifest.parse_yaml(raw_manifest)
                has_manifest = True
            except Exception as e:
                logger.warning(f"Could not parse project-info.yml in project {project_name}: {e}")

        # Check existing component in DB
        result = await db.execute(select(Component).where(Component.gitlab_project_id == project_id))
        component = result.scalar_one_or_none()

        if not component:
            component = Component(gitlab_project_id=project_id, name=project_name, gitlab_url=web_url)
            # As coleções precisam ser inicializadas enquanto o objeto ainda é
            # transiente. Depois do flush() ele se torna persistente e atribuir
            # a uma coleção nunca carregada dispara um lazy load para calcular o
            # delta — I/O implícito, proibido em contexto async (greenlet_spawn).
            component.tags = []
            component.links = []
            component.dependencies = []
            component.docs = []
            db.add(component)

        component.gitlab_url = web_url
        component.default_branch = default_branch
        component.has_manifest = has_manifest

        if manifest:
            component.name = manifest.metadata.name
            component.description = manifest.metadata.description or description
            component.kind = manifest.kind
            component.type = manifest.spec.type
            component.lifecycle = manifest.spec.lifecycle
            component.owner = manifest.metadata.owner
            component.domain = manifest.metadata.domain
            component.system = manifest.spec.system
            component.docs_dir = manifest.spec.docs.dir
            component.docs_index = manifest.spec.docs.index
        else:
            component.name = project_name
            component.description = description
            component.kind = "Component"
            component.type = "service"
            component.lifecycle = "production"
            component.owner = "unassigned"
            component.docs_dir = "/docs"
            component.docs_index = "index.md"

        await db.flush()

        # Update Tags
        tag_names = manifest.metadata.tags if manifest else project_data.get("tag_list", [])
        tag_objects = []
        for t_name in tag_names:
            t_res = await db.execute(select(Tag).where(Tag.name == t_name))
            tag_obj = t_res.scalar_one_or_none()
            if not tag_obj:
                tag_obj = Tag(name=t_name)
                db.add(tag_obj)
                await db.flush()
            tag_objects.append(tag_obj)
        component.tags = tag_objects

        # Clear & Update Links
        await db.execute(delete(ComponentLink).where(ComponentLink.component_id == component.id))
        if manifest and manifest.spec.links:
            for link in manifest.spec.links:
                db.add(ComponentLink(component_id=component.id, title=link.title, url=link.url, icon=link.icon))

        # Clear & Update Dependencies
        await db.execute(delete(ComponentDependency).where(ComponentDependency.source_component_id == component.id))
        if manifest and manifest.spec.dependencies:
            for dep in manifest.spec.dependencies:
                db.add(ComponentDependency(source_component_id=component.id, target_component_name=dep.component))

        # Fetch and sync Documentation Files
        await db.execute(delete(DocFile).where(DocFile.component_id == component.id))
        
        # Also include README.md if present
        readme_content = await self.fetch_file_content(project_id, "README.md", ref=default_branch)
        if readme_content:
            db.add(DocFile(
                component_id=component.id,
                relative_path="README.md",
                title="README",
                content_markdown=readme_content
            ))

        # Sync docs directory
        docs_tree = await self.fetch_docs_tree(project_id, component.docs_dir, ref=default_branch)
        for doc_item in docs_tree:
            file_path = doc_item["path"]
            doc_content = await self.fetch_file_content(project_id, file_path, ref=default_branch)
            if doc_content:
                # Relative path from docs dir
                rel_path = file_path[len(component.docs_dir.strip('/')):].lstrip("/")
                if not rel_path:
                    rel_path = doc_item["name"]
                
                title = rel_path.split("/")[-1].replace(".md", "").replace("_", " ").replace("-", " ").title()
                db.add(DocFile(
                    component_id=component.id,
                    relative_path=rel_path,
                    title=title,
                    content_markdown=doc_content
                ))

        await db.commit()
        return component

    async def run(
        self,
        db: AsyncSession,
        mode: SyncMode = SyncMode.UPDATE,
        progress: Optional[SyncProgress] = None,
    ) -> SyncResult:
        """Ponto de entrada único das operações do painel de configuração."""
        progress = progress or SyncProgress()

        if mode == SyncMode.REBUILD:
            return await self.rebuild(db, progress)
        if mode == SyncMode.PRUNE:
            return await self.prune(db, progress)
        return await self.sync_all(db, progress)

    async def sync_all(
        self, db: AsyncSession, progress: Optional[SyncProgress] = None
    ) -> SyncResult:
        progress = progress or SyncProgress()
        result = SyncResult(mode=SyncMode.UPDATE.value)

        progress.log("info", "Consultando projetos no GitLab...")
        projects = await self.fetch_projects()
        progress.set_total(len(projects))
        progress.log("info", f"{len(projects)} projeto(s) para processar.")

        for p in projects:
            try:
                component = await self.sync_project(db, p)
                result.synced.append(component.name)
                progress.log("ok", f"Sincronizado: {component.name}")
            except Exception as e:
                # Um projeto quebrado não pode derrubar a sincronização inteira.
                # O commit é por projeto, então o rollback descarta só o que
                # ficou pendente deste — os anteriores já estão persistidos e o
                # próximo começa de uma sessão limpa.
                await db.rollback()
                logger.exception(
                    f"Failed to sync project {p.get('name')} ({p.get('id')})"
                )
                result.failed.append(SyncFailure(
                    project_id=p.get("id"),
                    name=p.get("name") or "unknown",
                    error=str(e),
                ))
                progress.log("error", f"Falhou: {p.get('name') or 'desconhecido'} — {e}")
            finally:
                progress.advance()

        return result

    async def rebuild(
        self, db: AsyncSession, progress: Optional[SyncProgress] = None
    ) -> SyncResult:
        """Apaga o catálogo e importa tudo do zero.

        A lista de projetos é buscada *antes* do wipe: se o GitLab estiver
        inacessível, o catálogo atual continua de pé em vez de virar um banco
        vazio que só a próxima sincronização bem-sucedida repovoaria.
        """
        progress = progress or SyncProgress()

        progress.log("info", "Consultando projetos no GitLab...")
        projects = await self.fetch_projects()
        progress.set_total(len(projects))
        progress.log("info", f"{len(projects)} projeto(s) encontrados.")

        progress.log("warn", "Apagando o catálogo atual...")
        await self._wipe(db)
        progress.log("ok", "Catálogo apagado.")

        result = SyncResult(mode=SyncMode.REBUILD.value)
        for p in projects:
            try:
                component = await self.sync_project(db, p)
                result.synced.append(component.name)
                progress.log("ok", f"Importado: {component.name}")
            except Exception as e:
                await db.rollback()
                logger.exception(
                    f"Failed to rebuild project {p.get('name')} ({p.get('id')})"
                )
                result.failed.append(SyncFailure(
                    project_id=p.get("id"),
                    name=p.get("name") or "unknown",
                    error=str(e),
                ))
                progress.log("error", f"Falhou: {p.get('name') or 'desconhecido'} — {e}")
            finally:
                progress.advance()

        return result

    async def prune(
        self, db: AsyncSession, progress: Optional[SyncProgress] = None
    ) -> SyncResult:
        """Remove do catálogo os componentes que não existem mais no GitLab."""
        progress = progress or SyncProgress()
        result = SyncResult(mode=SyncMode.PRUNE.value)

        progress.log("info", "Consultando projetos no GitLab...")
        projects = await self.fetch_projects()
        if not projects:
            # Sem esta guarda, um token sem permissão ou um grupo mal
            # configurado devolveria lista vazia e a limpeza apagaria tudo.
            raise ProjectListError(
                "O GitLab não retornou nenhum projeto. Limpeza abortada para "
                "não esvaziar o catálogo."
            )

        live_ids = {p["id"] for p in projects}
        progress.log("info", f"{len(live_ids)} projeto(s) ativos no GitLab.")

        components = (await db.execute(select(Component))).scalars().all()
        orphans = [c for c in components if c.gitlab_project_id not in live_ids]
        progress.set_total(len(orphans))

        if not orphans:
            progress.log("ok", "Nenhum componente órfão encontrado.")
            return result

        progress.log("warn", f"{len(orphans)} componente(s) órfãos a remover.")
        for component in orphans:
            # O nome precisa ser lido antes do commit, que expira o objeto.
            name = component.name
            try:
                await self._delete_component(db, component.id)
                await db.commit()
                result.removed.append(name)
                progress.log("warn", f"Removido: {name}")
            except Exception as e:
                await db.rollback()
                logger.exception(f"Failed to prune component {name}")
                result.failed.append(SyncFailure(
                    project_id=None, name=name, error=str(e)
                ))
                progress.log("error", f"Falhou ao remover {name} — {e}")
            finally:
                progress.advance()

        return result

    async def _wipe(self, db: AsyncSession) -> None:
        """Zera as tabelas do catálogo.

        A ordem filho -> pai é explícita porque o `ondelete=CASCADE` das FKs
        depende de `PRAGMA foreign_keys=ON`, que o SQLite não liga por padrão.
        """
        await db.execute(delete(DocFile))
        await db.execute(delete(ComponentLink))
        await db.execute(delete(ComponentDependency))
        await db.execute(component_tags.delete())
        await db.execute(delete(Tag))
        await db.execute(delete(Component))
        await db.commit()

    async def _delete_component(self, db: AsyncSession, component_id: int) -> None:
        await db.execute(delete(DocFile).where(DocFile.component_id == component_id))
        await db.execute(delete(ComponentLink).where(ComponentLink.component_id == component_id))
        await db.execute(
            delete(ComponentDependency).where(
                ComponentDependency.source_component_id == component_id
            )
        )
        await db.execute(
            component_tags.delete().where(component_tags.c.component_id == component_id)
        )
        await db.execute(delete(Component).where(Component.id == component_id))
