import pytest
from sqlalchemy import create_engine, text, inspect, select
from sqlalchemy.orm import Session
from app.db.session import Base
from app.db.models import Component
from app.db.init_db import auto_migrate_db

def test_auto_migrate_db_adds_missing_column(tmp_path):
    db_file = tmp_path / "test_legacy.db"
    db_url = f"sqlite:///{db_file}"
    engine = create_engine(db_url)

    # 1. Create all tables first using Base.metadata.create_all
    Base.metadata.create_all(engine)

    # 2. Re-create `components` table WITHOUT `manifest_path` (simulating legacy table)
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE components"))
        conn.execute(text("""
            CREATE TABLE components (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gitlab_project_id INTEGER,
                name VARCHAR(100),
                description TEXT,
                kind VARCHAR(50),
                type VARCHAR(50),
                lifecycle VARCHAR(50),
                owner VARCHAR(100),
                domain VARCHAR(100),
                solution VARCHAR(100),
                gitlab_url VARCHAR(500),
                default_branch VARCHAR(100),
                docs_dir VARCHAR(100),
                docs_index VARCHAR(100),
                has_manifest BOOLEAN,
                gitlab_created_at DATETIME,
                last_activity_at DATETIME,
                updated_at DATETIME
            )
        """))

    # Verify manifest_path does NOT exist in components table initially
    inspector = inspect(engine)
    cols_before = [c["name"] for c in inspector.get_columns("components")]
    assert "manifest_path" not in cols_before

    # 3. Run auto_migrate_db
    with engine.begin() as conn:
        auto_migrate_db(conn)

    # 4. Verify manifest_path column WAS added
    inspector = inspect(engine)
    cols_after = [c["name"] for c in inspector.get_columns("components")]
    assert "manifest_path" in cols_after

    # 5. Verify querying Component with manifest_path works in SQLAlchemy session
    with Session(engine) as session:
        comp = Component(
            gitlab_project_id=81,
            manifest_path="project-info.yml",
            name="toolkit-infra",
            gitlab_url="https://gitlab.com/toolkit-infra"
        )
        session.add(comp)
        session.commit()

        stmt = select(Component).where(
            Component.gitlab_project_id == 81,
            Component.manifest_path == "project-info.yml"
        )
        result = session.scalar(stmt)
        assert result is not None
        assert result.name == "toolkit-infra"
        assert result.manifest_path == "project-info.yml"


def test_auto_migrate_db_drops_legacy_unique_index(tmp_path):
    """Bancos anteriores ao suporte a monorepo têm gitlab_project_id UNIQUE.

    Enquanto o índice existir, o segundo `project-info.yml` de um mesmo
    repositório falha com IntegrityError no meio do sync.
    """
    db_file = tmp_path / "test_unique.db"
    engine = create_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(engine)

    # Recria o índice como era antes: único.
    with engine.begin() as conn:
        conn.execute(text("DROP INDEX ix_components_gitlab_project_id"))
        conn.execute(
            text("CREATE UNIQUE INDEX ix_components_gitlab_project_id ON components (gitlab_project_id)")
        )

    def uniqueness():
        idx = next(
            i for i in inspect(engine).get_indexes("components")
            if i["name"] == "ix_components_gitlab_project_id"
        )
        return bool(idx["unique"])

    assert uniqueness() is True

    with engine.begin() as conn:
        auto_migrate_db(conn)

    assert uniqueness() is False

    # Dois componentes do mesmo repositório, como num monorepo.
    with Session(engine) as session:
        for path, name in [("apps/web/project-info.yml", "web"), ("apps/api/project-info.yml", "api")]:
            session.add(Component(
                gitlab_project_id=5,
                manifest_path=path,
                name=name,
                gitlab_url="https://gitlab.local/nti/scsi",
            ))
        session.commit()

        assert len(session.scalars(
            select(Component).where(Component.gitlab_project_id == 5)
        ).all()) == 2


def test_auto_migrate_db_preserves_indexes_the_model_declares_unique(tmp_path):
    """A reconciliação segue o modelo nos dois sentidos, não só removendo."""
    db_file = tmp_path / "test_keep.db"
    engine = create_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(engine)

    before = {i["name"]: bool(i["unique"]) for i in inspect(engine).get_indexes("components")}
    with engine.begin() as conn:
        auto_migrate_db(conn)
    after = {i["name"]: bool(i["unique"]) for i in inspect(engine).get_indexes("components")}

    assert before == after
