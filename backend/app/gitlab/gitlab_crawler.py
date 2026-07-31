import logging
from typing import List, Dict, Any, Optional
import httpx
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import Component, Tag, ComponentLink, ComponentDependency, DocFile
from app.catalog.manifest import DaileonManifest

logger = logging.getLogger(__name__)

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
                
                try:
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        logger.error(f"Failed to fetch GitLab projects: {resp.status_code} - {resp.text}")
                        break
                    data = resp.json()
                    if not data:
                        break
                    projects.extend(data)
                    page += 1
                    if len(data) < per_page:
                        break
                except Exception as e:
                    logger.error(f"Error requesting GitLab projects: {e}")
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

        # Try to fetch daileon.yml
        raw_manifest = await self.fetch_file_content(project_id, "daileon.yml", ref=default_branch)
        manifest: Optional[DaileonManifest] = None
        has_manifest = False

        if raw_manifest:
            try:
                manifest = DaileonManifest.parse_yaml(raw_manifest)
                has_manifest = True
            except Exception as e:
                logger.warning(f"Could not parse daileon.yml in project {project_name}: {e}")

        # Check existing component in DB
        result = await db.execute(select(Component).where(Component.gitlab_project_id == project_id))
        component = result.scalar_one_or_none()

        if not component:
            component = Component(gitlab_project_id=project_id, name=project_name, gitlab_url=web_url)
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
        await db.execute(delete(ComponentDependency).where(ComponentDependency.component_id == component.id))
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

    async def sync_all(self, db: AsyncSession) -> List[Component]:
        projects = await self.fetch_projects()
        synced_components = []
        for p in projects:
            comp = await self.sync_project(db, p)
            synced_components.append(comp)
        return synced_components
