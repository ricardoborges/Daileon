import logging
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, List, Dict, Any, Optional
from urllib.parse import quote
import httpx
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import (
    Component, Tag, ComponentLink, ComponentDependency, ComponentJenkinsPipeline, ComponentDeployment, DocFile, ComponentRisk, component_tags
)
from app.catalog.manifest import DaileonManifest
from app.plugins.gitlab.risk_scanner import scan_repository_tree, scan_file_content

logger = logging.getLogger(__name__)


def normalize_owner(raw: Optional[str]) -> str:
    """Normaliza a string do owner, extraindo o username caso seja um e-mail."""
    if not raw:
        return "unassigned"
    val = raw.strip()
    if "@" in val:
        val = val.split("@")[0].strip()
    return val.lower() if val else "unassigned"


VENDOR_DIRS = frozenset({
    "node_modules", "bower_components", "vendor", "site-packages",
    "__pycache__", "dist", "build", "target", "out",
})

IGNORE_MARKER = ".daileon-ignore"

DOC_EXTENSIONS = {
    ".md": "markdown",
    ".markdown": "markdown",
    ".pdf": "pdf",
    ".docx": "docx",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".gif": "image",
    ".webp": "image",
    ".bmp": "image",
}

BINARY_DOC_TYPES = frozenset({"pdf", "image", "docx"})
FALLBACK_DOC_TYPES = frozenset({"markdown", "pdf", "docx"})

DOC_MEDIA_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
}

MAX_BINARY_DOC_BYTES = 25 * 1024 * 1024


def extract_docx_text(b: bytes) -> str:
    if not b:
        return ""
    try:
        import io
        import zipfile
        import xml.etree.ElementTree as ET
        with zipfile.ZipFile(io.BytesIO(b)) as z:
            if "word/document.xml" not in z.namelist():
                return ""
            xml_content = z.read("word/document.xml")
            tree = ET.fromstring(xml_content)
            texts = [node.text for node in tree.iter() if node.tag.endswith("}t") and node.text]
            return " ".join(texts)
    except Exception as e:
        logger.warning(f"Falha ao extrair texto de arquivo .docx: {e}")
        return ""


def _extension_of(path: str) -> Optional[str]:
    lowered = path.lower()
    for ext in sorted(DOC_EXTENSIONS, key=len, reverse=True):
        if lowered.endswith(ext):
            return ext
    return None


def doc_type_for(path: str) -> Optional[str]:
    ext = _extension_of(path)
    return DOC_EXTENSIONS[ext] if ext else None


def doc_media_type(path: str) -> str:
    ext = _extension_of(path)
    return DOC_MEDIA_TYPES.get(ext or "", "application/octet-stream")


def doc_title_from_path(relative_path: str) -> str:
    name = relative_path.split("/")[-1]
    ext = _extension_of(name)
    if ext:
        name = name[: -len(ext)]
    return name.replace("_", " ").replace("-", " ").strip().title() or relative_path


def relative_segments(path: str, base: str = "") -> List[str]:
    clean_path = path.strip("/")
    clean_base = base.strip("/")
    if clean_base and clean_path.startswith(f"{clean_base}/"):
        clean_path = clean_path[len(clean_base) + 1:]
    elif clean_base and clean_path == clean_base:
        return []
    return [seg for seg in clean_path.split("/") if seg]


def is_hidden_path(path: str, base: str = "") -> bool:
    return any(seg.startswith(".") for seg in relative_segments(path, base)[:-1])


def is_vendor_path(path: str, base: str = "") -> bool:
    return any(seg.lower() in VENDOR_DIRS for seg in relative_segments(path, base)[:-1])


def ignored_dirs(tree: Iterable[Dict[str, Any]]) -> List[str]:
    marked = []
    for item in tree:
        if item.get("type") != "blob":
            continue
        if item.get("name", "").lower() != IGNORE_MARKER:
            continue
        path = item.get("path", "").strip("/")
        marked.append(path[: -len(IGNORE_MARKER)].strip("/"))
    return marked


def is_ignored_path(path: str, marked_dirs: Iterable[str]) -> bool:
    clean = path.strip("/")
    for marked in marked_dirs:
        if not marked:
            return True
        if clean == marked or clean.startswith(f"{marked}/"):
            return True
    return False


def scoped_docs_dir(sub_dir: str, docs_dir: str) -> str:
    if not sub_dir:
        return docs_dir
    clean = docs_dir.strip("/")
    return f"{sub_dir}/{clean}" if clean else f"{sub_dir}/docs"


def nested_sub_dirs(own_sub_dir: str, all_sub_dirs: Iterable[str]) -> List[str]:
    own = own_sub_dir.strip("/")
    prefix = f"{own}/" if own else ""
    return sorted(
        d for d in {s.strip("/") for s in all_sub_dirs}
        if d and d != own and d.startswith(prefix)
    )


def parse_gitlab_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def commit_datetime(commit: Dict[str, Any]) -> Optional[datetime]:
    return parse_gitlab_datetime(
        commit.get("committed_date") or commit.get("created_at")
    )


def extract_commit_author(commit: Dict[str, Any]) -> Optional[str]:
    email = commit.get("author_email") or commit.get("committer_email")
    if email and "@" in email:
        username = email.split("@")[0].strip().lower()
        if username:
            return username

    raw_author = commit.get("author_name") or commit.get("author_email")
    if raw_author:
        norm = normalize_owner(raw_author)
        return norm if norm != "unassigned" else None
    return None


class SyncMode(str, Enum):
    UPDATE = "update"
    REBUILD = "rebuild"
    PRUNE = "prune"


@dataclass(frozen=True)
class SyncOptions:
    docs_dir: Optional[str] = None
    index_images: bool = True


class ProjectListError(RuntimeError):
    pass


class SyncProgress:
    def log(self, level: str, message: str) -> None:
        pass

    def set_total(self, total: int) -> None:
        pass

    def advance(self) -> None:
        pass


@dataclass
class SyncFailure:
    project_id: Optional[int]
    name: str
    error: str


@dataclass
class SyncResult:
    mode: str = SyncMode.UPDATE.value
    synced: List[str] = field(default_factory=list)
    failed: List[SyncFailure] = field(default_factory=list)
    removed: List[str] = field(default_factory=list)


class GitLabCrawlerService:
    def __init__(
        self,
        gitlab_url: Optional[str] = None,
        token: Optional[str] = None,
        group_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        if config:
            self.base_url = (config.get("url") or settings.GITLAB_URL).rstrip("/")
            self.token = config.get("read_token") or settings.GITLAB_READ_TOKEN
            self.group_id = config.get("group_id") or settings.GITLAB_GROUP_ID
        else:
            self.base_url = (gitlab_url or settings.GITLAB_URL).rstrip("/")
            self.token = token or settings.GITLAB_READ_TOKEN
            self.group_id = group_id or settings.GITLAB_GROUP_ID

        self.headers = {}
        if self.token and self.token != "******":
            self.headers["PRIVATE-TOKEN"] = self.token

    @classmethod
    async def create(
        cls,
        db: AsyncSession,
        gitlab_url: Optional[str] = None,
        token: Optional[str] = None,
        group_id: Optional[str] = None,
    ):
        from app.plugins.gitlab.service import get_effective_gitlab_config
        config = await get_effective_gitlab_config(db)
        return cls(gitlab_url=gitlab_url, token=token, group_id=group_id, config=config)

    async def fetch_projects(self, group_id: Optional[str] = None) -> List[Dict[str, Any]]:
        projects = []
        page = 1
        per_page = 100
        target_group = group_id or self.group_id or settings.GITLAB_GROUP_ID
        async with httpx.AsyncClient(headers=self.headers, timeout=20.0) as client:
            while True:
                if target_group:
                    url = f"{self.base_url}/api/v4/groups/{target_group}/projects?include_subgroups=true&page={page}&per_page={per_page}"
                else:
                    url = f"{self.base_url}/api/v4/projects?membership=true&page={page}&per_page={per_page}"
                
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

    async def fetch_file_bytes(self, project_id: int, file_path: str, ref: str = "main") -> Optional[bytes]:
        encoded_path = file_path.replace("/", "%2F")
        url = f"{self.base_url}/api/v4/projects/{project_id}/repository/files/{encoded_path}/raw?ref={ref}"
        async with httpx.AsyncClient(headers=self.headers, timeout=60.0) as client:
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    return resp.content
            except Exception as e:
                logger.error(f"Error fetching binary file {file_path} for project {project_id}: {e}")
        return None

    async def fetch_docs_tree(
        self, project_id: int, docs_dir: str, ref: str = "main"
    ) -> Optional[List[Dict[str, Any]]]:
        clean_dir = docs_dir.strip("/")
        blobs = []
        page = 1
        per_page = 100
        max_pages = 20

        async with httpx.AsyncClient(headers=self.headers, timeout=15.0) as client:
            while page <= max_pages:
                if clean_dir:
                    url = f"{self.base_url}/api/v4/projects/{project_id}/repository/tree?path={quote(clean_dir, safe='')}&recursive=true&ref={ref}&page={page}&per_page={per_page}"
                else:
                    url = f"{self.base_url}/api/v4/projects/{project_id}/repository/tree?recursive=true&ref={ref}&page={page}&per_page={per_page}"
                try:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        tree = resp.json()
                        if not tree or not isinstance(tree, list):
                            break
                        blobs.extend(i for i in tree if i.get("type") == "blob")
                        page += 1
                        if len(tree) < per_page:
                            break
                    else:
                        break
                except Exception as e:
                    logger.error(f"Error fetching docs tree for project {project_id}: {e}")
                    break
            else:
                logger.warning(
                    f"Docs tree for project {project_id} truncated at {max_pages * per_page} entries "
                    f"(path={clean_dir or '/'}); some documents may be missing."
                )

        marked = ignored_dirs(blobs)
        if is_ignored_path(clean_dir, marked):
            logger.info(
                f"Skipping docs of project {project_id}: "
                f"'{clean_dir or '/'}' is marked with {IGNORE_MARKER}."
            )
            return None

        return [
            item
            for item in blobs
            if doc_type_for(item.get("name", ""))
            and not is_hidden_path(item.get("path", ""), clean_dir)
            and not is_vendor_path(item.get("path", ""), clean_dir)
            and not is_ignored_path(item.get("path", ""), marked)
        ]

    async def fetch_project_commits(self, project_id: int, days: int = 365) -> Dict[str, Any]:
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        since_dt = now - timedelta(days=days)
        since_iso = since_dt.isoformat()

        daily_counts: Dict[str, int] = {}
        author_counts: Dict[str, int] = {}
        total_commits = 0
        page = 1
        per_page = 100
        max_pages = 10

        async with httpx.AsyncClient(headers=self.headers, timeout=15.0) as client:
            while page <= max_pages:
                url = (
                    f"{self.base_url}/api/v4/projects/{project_id}/repository/commits"
                    f"?since={since_iso}&page={page}&per_page={per_page}"
                )
                try:
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        logger.warning(f"GitLab API returned {resp.status_code} fetching commits for project {project_id}")
                        break

                    data = resp.json()
                    if not data or not isinstance(data, list):
                        break

                    for commit in data:
                        commit_date_str = commit.get("committed_date") or commit.get("created_at")
                        if commit_date_str:
                            date_part = commit_date_str[:10]
                            daily_counts[date_part] = daily_counts.get(date_part, 0) + 1
                            total_commits += 1

                        author = extract_commit_author(commit)
                        if author:
                            author_counts[author] = author_counts.get(author, 0) + 1

                    page += 1
                    if len(data) < per_page:
                        break
                except Exception as e:
                    logger.error(f"Error fetching commits for project {project_id}: {e}")
                    break

        top_committer = max(author_counts, key=author_counts.get) if author_counts else None

        return {
            "project_id": project_id,
            "total_commits": total_commits,
            "top_committer": top_committer,
            "author_counts": author_counts,
            "since": since_iso,
            "until": now.isoformat(),
            "daily_counts": daily_counts
        }

    COMMIT_PAGE_SIZE = 100
    MAX_COMMIT_PAGE_PROBES = 24

    async def fetch_first_commit_date(self, project_id: int, ref: str = "main") -> Optional[datetime]:
        base = (
            f"{self.base_url}/api/v4/projects/{project_id}/repository/commits"
            f"?ref_name={ref}"
        )
        async with httpx.AsyncClient(headers=self.headers, timeout=15.0) as client:
            try:
                resp = await client.get(f"{base}&per_page=1")
                if resp.status_code != 200:
                    logger.warning(
                        f"GitLab returned {resp.status_code} fetching first commit for project {project_id}"
                    )
                    return None

                data = resp.json()
                if not isinstance(data, list) or not data:
                    return None

                total_pages = resp.headers.get("x-total-pages")
                if total_pages and str(total_pages).isdigit():
                    if int(total_pages) <= 1:
                        return commit_datetime(data[0])
                    last = await self._fetch_commits_page(
                        client, base, page=int(total_pages), per_page=1
                    )
                    return commit_datetime(last[0]) if last else None

                logger.debug(
                    f"Project {project_id} did not report x-total-pages; "
                    f"probing for the last page of commits."
                )
                oldest = await self._probe_oldest_commit(client, base, project_id)
                return commit_datetime(oldest) if oldest else None
            except Exception as e:
                logger.error(f"Error fetching first commit for project {project_id}: {e}")
                return None

    async def _fetch_commits_page(
        self, client: httpx.AsyncClient, base: str, page: int, per_page: int
    ) -> Optional[List[Dict[str, Any]]]:
        resp = await client.get(f"{base}&per_page={per_page}&page={page}")
        if resp.status_code != 200:
            return None
        data = resp.json()
        return data if isinstance(data, list) else None

    async def _probe_oldest_commit(
        self, client: httpx.AsyncClient, base: str, project_id: int
    ) -> Optional[Dict[str, Any]]:
        per_page = self.COMMIT_PAGE_SIZE
        probes = 0
        low, low_data = 0, None
        high = None

        page = 1
        while probes < self.MAX_COMMIT_PAGE_PROBES:
            data = await self._fetch_commits_page(client, base, page, per_page)
            probes += 1
            if data is None:
                return None
            if not data:
                high = page
                break
            low, low_data = page, data
            page *= 2

        while (
            high is not None
            and high - low > 1
            and probes < self.MAX_COMMIT_PAGE_PROBES
        ):
            mid = (low + high) // 2
            data = await self._fetch_commits_page(client, base, mid, per_page)
            probes += 1
            if data is None:
                return None
            if data:
                low, low_data = mid, data
            else:
                high = mid

        if high is None or high - low > 1 or low_data is None:
            logger.warning(
                f"Gave up looking for the last page of commits of project {project_id} "
                f"after {probes} requests; first commit date left unset."
            )
            return None
        return low_data[-1]

    async def fetch_top_committer(self, project_id: int) -> Optional[str]:
        async with httpx.AsyncClient(headers=self.headers, timeout=15.0) as client:
            url = f"{self.base_url}/api/v4/projects/{project_id}/repository/commits?per_page=100"
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list) and data:
                        author_counts: Dict[str, int] = {}
                        for commit in data:
                            author = extract_commit_author(commit)
                            if author:
                                author_counts[author] = author_counts.get(author, 0) + 1
                        if author_counts:
                            return max(author_counts, key=author_counts.get)
            except Exception as e:
                logger.error(f"Error fetching top committer for project {project_id}: {e}")
        return None

    async def fetch_manifest_paths(self, project_id: int, ref: str = "main") -> Optional[List[str]]:
        manifest_paths = []
        blobs = []
        page = 1
        per_page = 100
        max_pages = 50

        async with httpx.AsyncClient(headers=self.headers, timeout=15.0) as client:
            while page <= max_pages:
                url = (
                    f"{self.base_url}/api/v4/projects/{project_id}/repository/tree"
                    f"?recursive=true&ref={ref}&page={page}&per_page={per_page}"
                )
                try:
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        logger.warning(
                            f"GitLab API returned status {resp.status_code} fetching tree page {page} for project {project_id}"
                        )
                        break

                    tree = resp.json()
                    if not tree or not isinstance(tree, list):
                        break

                    blobs.extend(i for i in tree if i.get("type") == "blob")

                    for item in tree:
                        if item.get("type") != "blob":
                            continue
                        if item.get("name", "").lower() not in ("project-info.yml", "project-info.yaml"):
                            continue
                        path = item.get("path")
                        if not path or path in manifest_paths:
                            continue
                        if is_hidden_path(path) or is_vendor_path(path):
                            logger.debug(f"Ignoring manifest outside the source tree: {path}")
                            continue
                        manifest_paths.append(path)

                    page += 1
                    if len(tree) < per_page:
                        break
                except Exception as e:
                    logger.error(f"Error fetching tree page {page} for project {project_id}: {e}")
                    break
            else:
                logger.warning(
                    f"Repository tree for project {project_id} truncated at {max_pages * per_page} entries; "
                    f"manifests below that point were not discovered."
                )

        marked = ignored_dirs(blobs)
        if is_ignored_path("", marked):
            return None

        ignored_manifests = [p for p in manifest_paths if is_ignored_path(p, marked)]
        for path in ignored_manifests:
            logger.info(f"Ignoring manifest under {IGNORE_MARKER}: {path}")
        manifest_paths = [p for p in manifest_paths if p not in ignored_manifests]

        manifest_paths.sort(key=lambda p: (p.count("/"), p))
        return manifest_paths

    async def fetch_repo_tree(self, project_id: int, ref: str = "main") -> List[Dict[str, Any]]:
        blobs: List[Dict[str, Any]] = []
        page = 1
        per_page = 100
        max_pages = 30
        async with httpx.AsyncClient(headers=self.headers, timeout=15.0) as client:
            while page <= max_pages:
                url = (
                    f"{self.base_url}/api/v4/projects/{project_id}/repository/tree"
                    f"?recursive=true&ref={ref}&page={page}&per_page={per_page}"
                )
                try:
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        break
                    tree = resp.json()
                    if not tree or not isinstance(tree, list):
                        break
                    blobs.extend(tree)
                    page += 1
                    if len(tree) < per_page:
                        break
                except Exception as e:
                    logger.error(f"Error fetching repo tree for project {project_id}: {e}")
                    break
        return blobs

    async def sync_project(
        self,
        db: AsyncSession,
        project_data: Dict[str, Any],
        options: Optional[SyncOptions] = None,
    ) -> List[Component]:
        options = options or SyncOptions()
        project_id = project_data["id"]
        project_name = project_data["name"]
        default_branch = project_data.get("default_branch", "main")
        web_url = project_data.get("web_url", "")
        description = project_data.get("description", "")

        manifest_paths = await self.fetch_manifest_paths(project_id, ref=default_branch)
        if manifest_paths is None:
            logger.info(
                f"Project {project_name} has {IGNORE_MARKER} at the repository root; "
                f"nothing will be indexed."
            )
            manifest_paths = []
        elif not manifest_paths:
            manifest_paths = ["project-info.yml"]

        all_sub_dirs = {
            "/".join(p.split("/")[:-1]) if "/" in p else ""
            for p in manifest_paths
        }

        first_commit_at = await self.fetch_first_commit_date(project_id, ref=default_branch)
        repo_tree = await self.fetch_repo_tree(project_id, ref=default_branch)

        synced_components: List[Component] = []
        synced_ids: set = set()
        top_committer: Optional[str] = None

        for manifest_path in manifest_paths:
            raw_manifest = await self.fetch_file_content(project_id, manifest_path, ref=default_branch)
            manifest: Optional[DaileonManifest] = None
            has_manifest = False

            if raw_manifest:
                try:
                    manifest = DaileonManifest.parse_yaml(raw_manifest)
                    has_manifest = True
                except Exception as e:
                    logger.warning(f"Could not parse {manifest_path} in project {project_name}: {e}")

            component: Optional[Component] = None
            res = await db.execute(
                select(Component).where(
                    Component.gitlab_project_id == project_id,
                    Component.manifest_path == manifest_path
                )
            )
            component = res.scalar_one_or_none()

            if not component and manifest:
                res_name = await db.execute(
                    select(Component).where(
                        Component.gitlab_project_id == project_id,
                        Component.name == manifest.metadata.name
                    )
                )
                candidate = res_name.scalar_one_or_none()
                if candidate and candidate.id not in synced_ids:
                    component = candidate

            if not component:
                res_any = await db.execute(
                    select(Component).where(Component.gitlab_project_id == project_id)
                )
                existing = res_any.scalars().all()
                if len(existing) == 1 and not existing[0].manifest_path and existing[0].id not in synced_ids:
                    component = existing[0]

            if not component:
                component = Component(
                    gitlab_project_id=project_id,
                    manifest_path=manifest_path,
                    name=manifest.metadata.name if manifest else project_name,
                    gitlab_url=web_url
                )
                component.tags = []
                component.links = []
                component.dependencies = []
                component.jenkins_pipelines = []
                component.deployments = []
                component.docs = []
                db.add(component)

            component.manifest_path = manifest_path
            component.gitlab_url = web_url
            component.default_branch = default_branch
            component.has_manifest = has_manifest

            component.gitlab_created_at = parse_gitlab_datetime(project_data.get("created_at"))
            component.last_activity_at = parse_gitlab_datetime(project_data.get("last_activity_at"))
            component.first_commit_at = first_commit_at

            sub_dir = "/".join(manifest_path.split("/")[:-1]) if "/" in manifest_path else ""

            if manifest:
                component.name = manifest.metadata.name
                component.description = manifest.metadata.description or description
                component.kind = manifest.kind
                component.type = manifest.spec.type
                component.lifecycle = manifest.spec.lifecycle
                component.owner = normalize_owner(manifest.metadata.owner)
                component.domain = manifest.metadata.domain
                component.solution = manifest.spec.get_solution()

                component.docs_dir = scoped_docs_dir(sub_dir, manifest.spec.docs.dir)
                component.docs_index = manifest.spec.docs.index
            else:
                component.name = project_name
                component.description = description
                component.kind = "Component"
                component.type = "unknown"
                component.lifecycle = "production"
                component.owner = "unassigned"
                component.solution = None
                component.docs_dir = "/docs"
                component.docs_index = "index.md"

            if options.docs_dir is not None:
                component.docs_dir = scoped_docs_dir(sub_dir, options.docs_dir)

            if not component.owner or component.owner == "unassigned":
                if not top_committer:
                    top_committer = await self.fetch_top_committer(project_id)
                if top_committer:
                    component.owner = normalize_owner(top_committer)

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

            # Clear & Update Dependencies and Dependents
            await db.execute(delete(ComponentDependency).where(ComponentDependency.source_component_id == component.id))
            if manifest:
                if manifest.spec.dependencies:
                    for dep in manifest.spec.dependencies:
                        target_name = dep.get_target_name()
                        if target_name:
                            if dep.is_resource_dep():
                                res_query = await db.execute(select(Component).where(func.lower(Component.name) == target_name.lower()))
                                existing_res = res_query.scalars().first()
                                if not existing_res:
                                    new_res = Component(
                                        gitlab_project_id=0,
                                        manifest_path="",
                                        name=target_name,
                                        description="Recurso de infraestrutura / serviço compartilhado",
                                        kind="Resource",
                                        type="resource",
                                        lifecycle="production",
                                        owner="unassigned",
                                        has_manifest=False,
                                        docs_dir="/docs",
                                        docs_index="index.md",
                                        gitlab_url=""
                                    )
                                    db.add(new_res)
                                    await db.flush()

                            db.add(ComponentDependency(
                                source_component_id=component.id,
                                target_component_name=target_name,
                                is_external=dep.is_external_dep(),
                                is_resource=dep.is_resource_dep(),
                                is_dependent=False
                            ))
                if manifest.spec.dependents:
                    for dep in manifest.spec.dependents:
                        target_name = dep.get_target_name()
                        if target_name:
                            if dep.is_resource_dep():
                                res_query = await db.execute(select(Component).where(func.lower(Component.name) == target_name.lower()))
                                existing_res = res_query.scalars().first()
                                if not existing_res:
                                    new_res = Component(
                                        gitlab_project_id=0,
                                        manifest_path="",
                                        name=target_name,
                                        description="Recurso de infraestrutura / serviço compartilhado",
                                        kind="Resource",
                                        type="resource",
                                        lifecycle="production",
                                        owner="unassigned",
                                        has_manifest=False,
                                        docs_dir="/docs",
                                        docs_index="index.md",
                                        gitlab_url=""
                                    )
                                    db.add(new_res)
                                    await db.flush()

                            db.add(ComponentDependency(
                                source_component_id=component.id,
                                target_component_name=target_name,
                                is_external=dep.is_external_dep(),
                                is_resource=dep.is_resource_dep(),
                                is_dependent=True
                            ))

            # Clear & Update Jenkins Pipelines
            await db.execute(delete(ComponentJenkinsPipeline).where(ComponentJenkinsPipeline.component_id == component.id))
            if manifest:
                jenkins_pipelines = manifest.spec.get_jenkins_pipelines()
                for pipe in jenkins_pipelines:
                    db.add(ComponentJenkinsPipeline(
                        component_id=component.id,
                        name=pipe.name,
                        environment=pipe.environment,
                        job=pipe.job,
                        server_url=pipe.server_url
                    ))

            # Clear & Update Deployments
            await db.execute(delete(ComponentDeployment).where(ComponentDeployment.component_id == component.id))
            if manifest and manifest.spec.deployments:
                for dep in manifest.spec.deployments:
                    db.add(ComponentDeployment(
                        component_id=component.id,
                        environment=dep.environment,
                        url=dep.url,
                        server_name=dep.server_name,
                        server_ip=dep.server_ip,
                        os=dep.os,
                        execution_type=dep.execution_type,
                        port=str(dep.port) if dep.port is not None else None,
                        notes=dep.notes
                    ))

            # Fetch and sync Documentation Files
            await db.execute(delete(DocFile).where(DocFile.component_id == component.id))

            readme_path = f"{sub_dir}/README.md" if sub_dir else "README.md"
            readme_content = await self.fetch_file_content(project_id, readme_path, ref=default_branch)
            if not readme_content and sub_dir:
                readme_content = await self.fetch_file_content(project_id, "README.md", ref=default_branch)

            if readme_content:
                db.add(DocFile(
                    component_id=component.id,
                    relative_path="README.md",
                    title="README",
                    doc_type="markdown",
                    content_markdown=readme_content,
                    size_bytes=len(readme_content.encode("utf-8"))
                ))

            docs_tree = await self.fetch_docs_tree(project_id, component.docs_dir, ref=default_branch)
            is_fallback = False
            if docs_tree is None:
                docs_tree = []
            elif not docs_tree and component.docs_dir.strip("/"):
                if options.docs_dir is not None:
                    logger.warning(
                        f"Docs folder '{component.docs_dir}' of project {project_id} is empty or "
                        f"does not exist; no documents indexed from it."
                    )
                else:
                    docs_tree = await self.fetch_docs_tree(project_id, sub_dir, ref=default_branch) or []
                    is_fallback = True

            foreign_prefixes = [f"{d}/" for d in nested_sub_dirs(sub_dir, all_sub_dirs)]

            for doc_item in docs_tree:
                file_path = doc_item["path"]
                if file_path.lower().endswith("readme.md") and readme_content:
                    continue
                if any(file_path.startswith(prefix) for prefix in foreign_prefixes):
                    continue

                kind = doc_type_for(file_path) or "markdown"
                if is_fallback and kind not in FALLBACK_DOC_TYPES:
                    continue
                if kind == "image" and not options.index_images:
                    continue

                if kind in BINARY_DOC_TYPES:
                    doc_bytes = await self.fetch_file_bytes(project_id, file_path, ref=default_branch)
                    if not doc_bytes:
                        continue
                    if len(doc_bytes) > MAX_BINARY_DOC_BYTES:
                        logger.warning(
                            f"Skipping '{file_path}' of project {project_id}: "
                            f"{len(doc_bytes)} bytes exceeds the {MAX_BINARY_DOC_BYTES} byte limit for binary docs."
                        )
                        continue
                    if kind == "docx":
                        doc_content = extract_docx_text(doc_bytes)
                    else:
                        doc_content = None
                else:
                    doc_bytes = None
                    doc_content = await self.fetch_file_content(project_id, file_path, ref=default_branch)
                    if not doc_content:
                        continue

                clean_dir = component.docs_dir.strip("/")
                if is_fallback or not clean_dir or not file_path.startswith(clean_dir):
                    rel_path = file_path[len(sub_dir):].lstrip("/") if sub_dir and file_path.startswith(sub_dir) else file_path
                else:
                    rel_path = file_path[len(clean_dir):].lstrip("/")
                    if not rel_path:
                        rel_path = doc_item["name"]

                db.add(DocFile(
                    component_id=component.id,
                    relative_path=rel_path,
                    title=doc_title_from_path(rel_path),
                    doc_type=kind,
                    content_markdown=doc_content if doc_content is not None else "",
                    content_binary=doc_bytes,
                    size_bytes=len(doc_bytes) if doc_bytes is not None else len(doc_content.encode("utf-8"))
                ))

            await db.execute(delete(ComponentRisk).where(ComponentRisk.component_id == component.id))
            
            risk_findings = scan_repository_tree(repo_tree)

            target_config_files = []
            for item in repo_tree:
                if item.get("type") != "blob":
                    continue
                file_p = item.get("path", "")
                p_low = file_p.lower()
                f_name = p_low.split("/")[-1]
                if (f_name.startswith("appsettings") and f_name.endswith(".json")) or \
                   (f_name in ["web.config", "app.config"] or f_name.endswith(".config")) or \
                   ("config/" in p_low and f_name.endswith(".json")) or \
                   (f_name in ["local_settings.py", "settings.py", "config.py"]):
                    target_config_files.append(file_p)

            for cfg_path in target_config_files[:5]:
                cfg_content = await self.fetch_file_content(project_id, cfg_path, ref=default_branch)
                if cfg_content:
                    content_findings = scan_file_content(cfg_path, cfg_content)
                    risk_findings.extend(content_findings)

            for rf in risk_findings:
                db.add(ComponentRisk(
                    component_id=component.id,
                    severity=rf.severity,
                    category=rf.category,
                    title=rf.title,
                    description=rf.description,
                    file_path=rf.file_path,
                    recommendation=rf.recommendation
                ))

            await db.commit()
            synced_components.append(component)
            synced_ids.add(component.id)

        existing_all = (await db.execute(select(Component).where(Component.gitlab_project_id == project_id))).scalars().all()
        for c in existing_all:
            if c.id not in synced_ids:
                await self._delete_component(db, c.id)
                await db.commit()

        return synced_components

    async def run(
        self,
        db: AsyncSession,
        mode: SyncMode = SyncMode.UPDATE,
        progress: Optional[SyncProgress] = None,
        project_ids: Optional[Iterable[int]] = None,
        options: Optional[SyncOptions] = None,
    ) -> SyncResult:
        progress = progress or SyncProgress()

        if mode == SyncMode.REBUILD:
            return await self.rebuild(db, progress)
        if mode == SyncMode.PRUNE:
            return await self.prune(db, progress)
        return await self.sync_all(db, progress, project_ids=project_ids, options=options)

    async def sync_all(
        self,
        db: AsyncSession,
        progress: Optional[SyncProgress] = None,
        project_ids: Optional[Iterable[int]] = None,
        options: Optional[SyncOptions] = None,
    ) -> SyncResult:
        progress = progress or SyncProgress()
        options = options or SyncOptions()
        result = SyncResult(mode=SyncMode.UPDATE.value)

        progress.log("info", "Consultando projetos no GitLab...")
        projects = await self.fetch_projects()

        if project_ids is not None:
            wanted = {int(pid) for pid in project_ids}
            projects = [p for p in projects if p.get("id") in wanted]
            missing = wanted - {p.get("id") for p in projects}
            for pid in sorted(missing):
                progress.log("warn", f"Projeto {pid} não encontrado no GitLab; ignorado.")
            progress.log("info", f"Recorte: {len(projects)} de {len(wanted)} projeto(s) selecionado(s).")

        progress.set_total(len(projects))
        progress.log("info", f"{len(projects)} projeto(s) para processar.")

        for p in projects:
            try:
                components = await self.sync_project(db, p, options=options)
                for comp in components:
                    result.synced.append(comp.name)
                    progress.log("ok", f"Sincronizado: {comp.name}")
            except Exception as e:
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
                components = await self.sync_project(db, p)
                for comp in components:
                    result.synced.append(comp.name)
                    progress.log("ok", f"Importado: {comp.name}")
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
        progress = progress or SyncProgress()
        result = SyncResult(mode=SyncMode.PRUNE.value)

        progress.log("info", "Consultando projetos no GitLab...")
        projects = await self.fetch_projects()
        if not projects:
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
        await db.execute(delete(DocFile))
        await db.execute(delete(ComponentLink))
        await db.execute(delete(ComponentDependency))
        await db.execute(delete(ComponentJenkinsPipeline))
        await db.execute(delete(ComponentDeployment))
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
        await db.execute(delete(ComponentJenkinsPipeline).where(ComponentJenkinsPipeline.component_id == component_id))
        await db.execute(delete(ComponentDeployment).where(ComponentDeployment.component_id == component_id))
        await db.execute(
            component_tags.delete().where(component_tags.c.component_id == component_id)
        )
        await db.execute(delete(Component).where(Component.id == component_id))
