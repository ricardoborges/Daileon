from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
import yaml

class ManifestMetadata(BaseModel):
    name: str
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    owner: str = "unassigned"
    domain: Optional[str] = None

class ManifestDocsConfig(BaseModel):
    dir: str = "/docs"
    index: str = "index.md"

class ManifestLink(BaseModel):
    url: str
    title: str
    icon: Optional[str] = None


class ManifestDependency(BaseModel):
    component: str

class ManifestJenkinsPipeline(BaseModel):
    name: str
    environment: str = "production"
    job: str
    server_url: Optional[str] = None

class ManifestJenkinsConfig(BaseModel):
    server_url: Optional[str] = None
    pipelines: List[ManifestJenkinsPipeline] = Field(default_factory=list)

class ManifestSpec(BaseModel):
    type: str = "service"
    lifecycle: str = "production"
    system: Optional[str] = None
    docs: ManifestDocsConfig = Field(default_factory=ManifestDocsConfig)
    links: List[ManifestLink] = Field(default_factory=list)
    dependencies: List[ManifestDependency] = Field(default_factory=list)
    jenkins: Optional[ManifestJenkinsConfig] = None

    @field_validator("jenkins", mode="before")
    @classmethod
    def prep_jenkins(cls, v):
        if isinstance(v, list):
            return {"pipelines": v}
        return v

    def get_jenkins_pipelines(self) -> List[ManifestJenkinsPipeline]:
        if not self.jenkins:
            return []
        return self.jenkins.pipelines


class DaileonManifest(BaseModel):
    apiVersion: str = "daileon/v1"
    kind: str = "Component"
    metadata: ManifestMetadata
    spec: ManifestSpec = Field(default_factory=ManifestSpec)


    @classmethod
    def parse_yaml(cls, yaml_content: str) -> "DaileonManifest":
        data = yaml.safe_load(yaml_content)
        return cls.model_validate(data)
