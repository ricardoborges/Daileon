from typing import List, Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator
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
    component: Optional[str] = None
    external: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def prep_dict_or_str(cls, v):
        if isinstance(v, str):
            return {"component": v}
        return v

    def get_target_name(self) -> Optional[str]:
        if self.external:
            return self.external
        return self.component

    def is_external_dep(self) -> bool:
        return bool(self.external)

class ManifestJenkinsPipeline(BaseModel):
    name: str
    environment: str = "production"
    job: str
    server_url: Optional[str] = None

class ManifestJenkinsConfig(BaseModel):
    server_url: Optional[str] = None
    pipelines: List[ManifestJenkinsPipeline] = Field(default_factory=list)

class ManifestDeployment(BaseModel):
    environment: str = "production"
    url: Optional[str] = None
    server_name: Optional[str] = None
    server_ip: Optional[str] = None
    os: Optional[str] = None
    execution_type: Optional[str] = None
    port: Optional[Union[int, str]] = None
    notes: Optional[str] = None

    @field_validator("port", mode="before")
    @classmethod
    def prep_port(cls, v):
        if v is not None:
            return str(v)
        return v

class ManifestSpec(BaseModel):
    type: str = "service"
    lifecycle: str = "production"
    solution: Optional[str] = None
    system: Optional[str] = None
    docs: ManifestDocsConfig = Field(default_factory=ManifestDocsConfig)
    links: List[ManifestLink] = Field(default_factory=list)
    dependencies: List[ManifestDependency] = Field(default_factory=list)
    dependents: List[ManifestDependency] = Field(default_factory=list)
    jenkins: Optional[ManifestJenkinsConfig] = None
    deployments: List[ManifestDeployment] = Field(default_factory=list)


    def get_solution(self) -> Optional[str]:
        return self.solution or self.system

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
