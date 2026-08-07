from typing import Optional
from fastapi import APIRouter
from app.core.plugins.plugin_interface import IntegrationPlugin
from app.plugins.jenkins.router import jenkins_router

class JenkinsPlugin(IntegrationPlugin):
    @property
    def plugin_id(self) -> str:
        return "jenkins"

    @property
    def name(self) -> str:
        return "Jenkins CI/CD Integration"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def category(self) -> str:
        return "cicd"

    @property
    def router(self) -> Optional[APIRouter]:
        return jenkins_router
