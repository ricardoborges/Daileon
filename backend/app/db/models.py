from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base

component_tags = Table(
    "component_tags",
    Base.metadata,
    Column("component_id", Integer, ForeignKey("components.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)

class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True)

class SystemSetting(Base):
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True, index=True)
    value: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ComponentLink(Base):
    __tablename__ = "component_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    component_id: Mapped[int] = mapped_column(Integer, ForeignKey("components.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(100))
    url: Mapped[str] = mapped_column(String(500))
    icon: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    component: Mapped["Component"] = relationship("Component", back_populates="links", lazy="selectin")

class ComponentDependency(Base):
    __tablename__ = "component_dependencies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_component_id: Mapped[int] = mapped_column(Integer, ForeignKey("components.id", ondelete="CASCADE"))
    target_component_name: Mapped[str] = mapped_column(String(100))

    component: Mapped["Component"] = relationship("Component", back_populates="dependencies", lazy="selectin")

class ComponentJenkinsPipeline(Base):
    __tablename__ = "component_jenkins_pipelines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    component_id: Mapped[int] = mapped_column(Integer, ForeignKey("components.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(100))
    environment: Mapped[str] = mapped_column(String(50), default="production")
    job: Mapped[str] = mapped_column(String(300))
    server_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    component: Mapped["Component"] = relationship("Component", back_populates="jenkins_pipelines", lazy="selectin")

class ComponentDeployment(Base):
    __tablename__ = "component_deployments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    component_id: Mapped[int] = mapped_column(Integer, ForeignKey("components.id", ondelete="CASCADE"))
    environment: Mapped[str] = mapped_column(String(50), default="production")
    url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    server_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    server_ip: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    os: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    execution_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    port: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    component: Mapped["Component"] = relationship("Component", back_populates="deployments", lazy="selectin")

class DocFile(Base):
    __tablename__ = "doc_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    component_id: Mapped[int] = mapped_column(Integer, ForeignKey("components.id", ondelete="CASCADE"))
    relative_path: Mapped[str] = mapped_column(String(300), index=True) # e.g. "index.md", "architecture/setup.md"
    title: Mapped[str] = mapped_column(String(200))
    content_markdown: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    component: Mapped["Component"] = relationship("Component", back_populates="docs", lazy="selectin")

class Component(Base):
    __tablename__ = "components"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    gitlab_project_id: Mapped[int] = mapped_column(Integer, index=True)
    manifest_path: Mapped[Optional[str]] = mapped_column(String(300), nullable=True) # e.g. "project-info.yml" or "apps/strix-web/project-info.yml"
    name: Mapped[str] = mapped_column(String(100), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    kind: Mapped[str] = mapped_column(String(50), default="Component") # Component, API, Library
    type: Mapped[str] = mapped_column(String(50), default="service") # service, website, library, cronjob
    lifecycle: Mapped[str] = mapped_column(String(50), default="production") # production, experimental, deprecated
    owner: Mapped[str] = mapped_column(String(100), default="unassigned", index=True)
    domain: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    solution: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    @property
    def system(self) -> Optional[str]:
        return self.solution

    @system.setter
    def system(self, value: Optional[str]):
        self.solution = value
    gitlab_url: Mapped[str] = mapped_column(String(500))
    default_branch: Mapped[str] = mapped_column(String(100), default="main")
    docs_dir: Mapped[str] = mapped_column(String(100), default="/docs")
    docs_index: Mapped[str] = mapped_column(String(100), default="index.md")
    has_manifest: Mapped[bool] = mapped_column(default=False)
    gitlab_created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    #: Data do commit mais antigo do repositório. Projetos migrados para esta
    #: instância do GitLab têm `gitlab_created_at` igual à data da migração, o
    #: que os faz parecer novos; o primeiro commit preserva a idade real.
    first_commit_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_activity_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tags: Mapped[List[Tag]] = relationship("Tag", secondary=component_tags, lazy="selectin")
    links: Mapped[List[ComponentLink]] = relationship("ComponentLink", back_populates="component", cascade="all, delete-orphan", lazy="selectin")
    dependencies: Mapped[List[ComponentDependency]] = relationship("ComponentDependency", back_populates="component", cascade="all, delete-orphan", lazy="selectin")
    docs: Mapped[List[DocFile]] = relationship("DocFile", back_populates="component", cascade="all, delete-orphan", lazy="selectin")
    jenkins_pipelines: Mapped[List[ComponentJenkinsPipeline]] = relationship("ComponentJenkinsPipeline", back_populates="component", cascade="all, delete-orphan", lazy="selectin")
    deployments: Mapped[List[ComponentDeployment]] = relationship("ComponentDeployment", back_populates="component", cascade="all, delete-orphan", lazy="selectin")

