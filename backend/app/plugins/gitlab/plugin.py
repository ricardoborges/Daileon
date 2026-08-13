from typing import Optional, List, Dict, Any
from fastapi import APIRouter
from app.core.plugins.plugin_interface import ScmCrawlerPlugin
from app.plugins.gitlab.crawler import GitLabCrawlerService
from app.plugins.gitlab.router import gitlab_router

class GitLabPlugin(ScmCrawlerPlugin):
    @property
    def plugin_id(self) -> str:
        return "gitlab"

    @property
    def name(self) -> str:
        return "GitLab SCM & Catalog Crawler"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def router(self) -> Optional[APIRouter]:
        return gitlab_router

    async def fetch_projects(self) -> List[Dict[str, Any]]:
        crawler = GitLabCrawlerService()
        return await crawler.fetch_projects()
