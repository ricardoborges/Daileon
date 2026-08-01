import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Component, ComponentDependency, ComponentDeployment, ComponentLink, DocFile, Tag
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
                domain="internal-tooling",
                system="platform-engineering",
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
            db.add(ComponentDeployment(
                component_id=c.id,
                environment="production",
                server_name="srv-teste-01",
                server_ip="10.0.0.1",
                os="Linux",
                execution_type="docker",
                port="8080"
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
    assert data[0]["docs_count"] == 2

def test_get_component_detail(client, component):
    response = client.get(f"/api/catalog/{component['id']}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == component["name"]
    assert data["docs_count"] == 2
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

def test_get_org_config_unauthenticated():
    from fastapi.testclient import TestClient
    from main import app
    unauth_client = TestClient(app)
    response = unauth_client.get("/api/org-config")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "acronym" in data

def test_list_servers(client, component):
    response = client.get("/api/servers")
    assert response.status_code == 200
    servers = response.json()
    assert isinstance(servers, list)
    assert len(servers) >= 1
    srv = next(s for s in servers if s["server_name"] == "srv-teste-01")
    assert srv["server_ip"] == "10.0.0.1"
    assert len(srv["components"]) == 1
    comp_info = srv["components"][0]
    assert comp_info["component_name"] == component["name"]
    assert comp_info["component_id"] == component["id"]


def test_get_server_detail(client, component):
    response = client.get("/api/servers/srv-teste-01")
    assert response.status_code == 200
    data = response.json()
    assert data["server_name"] == "srv-teste-01"
    assert data["server_ip"] == "10.0.0.1"
    assert data["components_count"] == 1
    assert data["components"][0]["component_name"] == component["name"]


def test_get_server_detail_inexistente(client):
    response = client.get("/api/servers/srv-inexistente-999")
    assert response.status_code == 404


def test_list_domains(client, component):
    response = client.get("/api/domains")
    assert response.status_code == 200
    domains = response.json()
    assert isinstance(domains, list)
    assert len(domains) >= 1
    dom = next(d for d in domains if d["domain"] == "internal-tooling")
    assert dom["components_count"] == 1
    assert "time-de-teste" in dom["owners"]
    assert "platform-engineering" in dom["systems"]
    assert dom["components"][0]["name"] == component["name"]


def test_get_domain_detail(client, component):
    response = client.get("/api/domains/internal-tooling")
    assert response.status_code == 200
    data = response.json()
    assert data["domain"] == "internal-tooling"
    assert data["components_count"] == 1
    assert "platform-engineering" in data["systems"]
    assert data["components"][0]["name"] == component["name"]


def test_get_domain_detail_inexistente(client):
    response = client.get("/api/domains/dominio-inexistente-999")
    assert response.status_code == 404




