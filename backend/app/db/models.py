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

class ComponentLink(Base):
    __tablename__ = "component_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    component_id: Mapped[int] = mapped_column(Integer, ForeignKey("components.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(100))
    url: Mapped[str] = mapped_column(String(500))
    icon: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    component: Mapped["Component"] = relationship("Component", back_populates="links")

class ComponentDependency(Base):
    __tablename__ = "component_dependencies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_component_id: Mapped[int] = mapped_column(Integer, ForeignKey("components.id", ondelete="CASCADE"))
    target_component_name: Mapped[str] = mapped_column(String(100))

    component: Mapped["Component"] = relationship("Component", back_populates="dependencies")

class DocFile(Base):
    __tablename__ = "doc_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    component_id: Mapped[int] = mapped_column(Integer, ForeignKey("components.id", ondelete="CASCADE"))
    relative_path: Mapped[str] = mapped_column(String(300), index=True) # e.g. "index.md", "architecture/setup.md"
    title: Mapped[str] = mapped_column(String(200))
    content_markdown: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    component: Mapped["Component"] = relationship("Component", back_populates="docs")

class Component(Base):
    __tablename__ = "components"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    gitlab_project_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    kind: Mapped[str] = mapped_column(String(50), default="Component") # Component, API, Library
    type: Mapped[str] = mapped_column(String(50), default="service") # service, website, library, cronjob
    lifecycle: Mapped[str] = mapped_column(String(50), default="production") # production, experimental, deprecated
    owner: Mapped[str] = mapped_column(String(100), default="unassigned", index=True)
    domain: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    system: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    gitlab_url: Mapped[str] = mapped_column(String(500))
    default_branch: Mapped[str] = mapped_column(String(100), default="main")
    docs_dir: Mapped[str] = mapped_column(String(100), default="/docs")
    docs_index: Mapped[str] = mapped_column(String(100), default="index.md")
    has_manifest: Mapped[bool] = mapped_column(default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tags: Mapped[List[Tag]] = relationship("Tag", secondary=component_tags, lazy="selectin")
    links: Mapped[List[ComponentLink]] = relationship("ComponentLink", back_populates="component", cascade="all, delete-orphan", lazy="selectin")
    dependencies: Mapped[List[ComponentDependency]] = relationship("ComponentDependency", back_populates="component", cascade="all, delete-orphan", lazy="selectin")
    docs: Mapped[List[DocFile]] = relationship("DocFile", back_populates="component", cascade="all, delete-orphan", lazy="selectin")
