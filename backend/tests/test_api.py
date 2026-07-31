import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Component, ComponentDependency, ComponentLink, DocFile, Tag
from main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        # Autentica e injeta o token nos cabeçalhos padrão do client
        login_res = c.post("/api/auth/login", json={
            "username": settings.ADMIN_USERNAME,
            "password": settings.ADMIN_PASSWORD
        })
        token = login_res.json()["access_token"]
        c.headers["Authorization"] = f"Bearer {token}"
        yield c



@pytest.fixture(scope="module")
def component(client):
    """Componente de teste. A aplicação não popula mais nada sozinha, então a
    própria suíte grava o que vai consultar — escrita síncrona no mesmo arquivo
    sqlite para não disputar o event loop do TestClient."""
    engine = create_engine(settings.DATABASE_URL.replace("+aiosqlite", ""))
    try:
        with Session(engine) as db:
            c = Component(
                gitlab_project_id=1,
                name="componente-de-teste",
                description="Componente usado apenas pela suíte de testes.",
                owner="time-de-teste",
                gitlab_url="https://gitlab.local/teste/componente-de-teste",
                has_manifest=True,
                tags=[Tag(name="python")],
            )
            db.add(c)
            db.flush()

            db.add(ComponentLink(component_id=c.id, title="Dashboard", url="https://grafana.local/teste", icon="dashboard"))
            db.add(ComponentDependency(source_component_id=c.id, target_component_name="outro-componente"))
            db.add(DocFile(
                component_id=c.id,
                relative_path="README.md",
                title="README",
                content_markdown="# Componente de teste",
            ))
            db.add(DocFile(
                component_id=c.id,
                relative_path="index.md",
                title="Visão Geral",
                content_markdown="# Visão Geral\n\n```mermaid\nsequenceDiagram\n    A->>B: ping\n```",
            ))
            db.commit()
            return {"id": c.id, "name": c.name}
    finally:
        engine.dispose()


def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Daileon API" in response.json()["message"]

def test_list_catalog(client, component):
    response = client.get("/api/catalog")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert [c["name"] for c in data] == [component["name"]]

def test_get_component_detail(client, component):
    response = client.get(f"/api/catalog/{component['id']}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == component["name"]
    assert "python" in data["tags"]
    assert data["dependencies"] == ["outro-componente"]

def test_get_component_detail_inexistente(client):
    assert client.get("/api/catalog/99999").status_code == 404

def test_get_component_docs(client, component):
    response = client.get(f"/api/catalog/{component['id']}/docs")
    assert response.status_code == 200
    docs = response.json()
    assert sorted(d["relative_path"] for d in docs) == ["README.md", "index.md"]

def test_get_doc_content(client, component):
    response = client.get(f"/api/catalog/{component['id']}/docs/index.md")
    assert response.status_code == 200
    doc = response.json()
    assert doc["title"] == "Visão Geral"
    assert "sequenceDiagram" in doc["content_markdown"]

def test_search(client, component):
    response = client.get("/api/search?q=teste")
    assert response.status_code == 200
    data = response.json()
    assert [c["name"] for c in data["components"]] == [component["name"]]
    assert [d["title"] for d in data["docs"]] == ["README"]
