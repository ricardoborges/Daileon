from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, Table, Column, LargeBinary, func, select
from sqlalchemy.orm import Mapped, column_property, mapped_column, relationship
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
    component_id: Mapped[int] = mapped_column(Integer, ForeignKey("components.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(100))
    url: Mapped[str] = mapped_column(String(500))
    icon: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    component: Mapped["Component"] = relationship("Component", back_populates="links", lazy="raise")

class ComponentDependency(Base):
    __tablename__ = "component_dependencies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_component_id: Mapped[int] = mapped_column(Integer, ForeignKey("components.id", ondelete="CASCADE"), index=True)
    target_component_name: Mapped[str] = mapped_column(String(100))

    component: Mapped["Component"] = relationship("Component", back_populates="dependencies", lazy="raise")

class ComponentJenkinsPipeline(Base):
    __tablename__ = "component_jenkins_pipelines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    component_id: Mapped[int] = mapped_column(Integer, ForeignKey("components.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    environment: Mapped[str] = mapped_column(String(50), default="production")
    job: Mapped[str] = mapped_column(String(300))
    server_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    component: Mapped["Component"] = relationship("Component", back_populates="jenkins_pipelines", lazy="raise")

class ComponentDeployment(Base):
    __tablename__ = "component_deployments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    component_id: Mapped[int] = mapped_column(Integer, ForeignKey("components.id", ondelete="CASCADE"), index=True)
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
    component_id: Mapped[int] = mapped_column(Integer, ForeignKey("components.id", ondelete="CASCADE"), index=True)
    relative_path: Mapped[str] = mapped_column(String(300), index=True) # e.g. "index.md", "architecture/setup.md"
    title: Mapped[str] = mapped_column(String(200))
    # "markdown" ou "pdf". Documentos binários guardam string vazia aqui e o
    # conteúdo em `content_binary`: bancos criados antes desta coluna existir
    # têm `content_markdown` NOT NULL e o auto-migrate do SQLite não relaxa isso.
    doc_type: Mapped[str] = mapped_column(String(20), default="markdown")
    # As duas colunas de conteúdo somam a quase totalidade do banco (PDFs e
    # imagens embutidos), e quase toda consulta quer apenas os metadados do
    # documento. Ficam `deferred` para que um `select(DocFile)` não as traga:
    # quem precisa do conteúdo pede `undefer` explicitamente. `raiseload` faz
    # o esquecimento falhar com uma mensagem clara em vez de emitir I/O
    # implícito, que numa sessão async quebraria com `MissingGreenlet`.
    content_markdown: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, deferred=True, deferred_raiseload=True
    )
    content_binary: Mapped[Optional[bytes]] = mapped_column(
        LargeBinary, nullable=True, deferred=True, deferred_raiseload=True
    )
    size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    component: Mapped["Component"] = relationship("Component", back_populates="docs", lazy="raise")

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
    # Ao contrário das demais coleções, esta é grande e cara, e nenhuma tela
    # mostra os documentos junto do componente — só quantos são, que vem de
    # `docs_count`. Carregar sob demanda aqui traria os documentos de todo o
    # catálogo em cada listagem, então quem quiser a coleção pede
    # `selectinload(Component.docs)` e assume o custo conscientemente.
    docs: Mapped[List[DocFile]] = relationship("DocFile", back_populates="component", cascade="all, delete-orphan", lazy="raise")
    jenkins_pipelines: Mapped[List[ComponentJenkinsPipeline]] = relationship("ComponentJenkinsPipeline", back_populates="component", cascade="all, delete-orphan", lazy="selectin")
    deployments: Mapped[List[ComponentDeployment]] = relationship("ComponentDeployment", back_populates="component", cascade="all, delete-orphan", lazy="selectin")
    risks: Mapped[List["ComponentRisk"]] = relationship("ComponentRisk", back_populates="component", cascade="all, delete-orphan", lazy="selectin")


class ComponentRisk(Base):
    __tablename__ = "component_risks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    component_id: Mapped[int] = mapped_column(Integer, ForeignKey("components.id", ondelete="CASCADE"), index=True)
    severity: Mapped[str] = mapped_column(String(20)) # "critical", "warning", "info"
    category: Mapped[str] = mapped_column(String(50)) # "versioned_secret", "unignored_env", "cloud_credentials", "hardcoded_connection_string"
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    file_path: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    recommendation: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    component: Mapped["Component"] = relationship("Component", back_populates="risks", lazy="raise")


#: Contagem de documentos sem tocar em `Component.docs`. Declarada fora da
#: classe porque a subconsulta precisa referenciar `Component.id`, que só passa
#: a existir depois que o mapeamento é construído.
Component.docs_count = column_property(
    select(func.count(DocFile.id))
    .where(DocFile.component_id == Component.id)
    .correlate_except(DocFile)
    .scalar_subquery(),
    deferred=False,
)


