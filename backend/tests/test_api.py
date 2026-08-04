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
                solution="Strix",
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
            db.add(DocFile(
                component_id=c.id,
                relative_path="NTI-001 SIMBA/Relatorio Tecnico.pdf",
                title="Relatorio Tecnico",
                doc_type="pdf",
                content_markdown="",
                content_binary=b"%PDF-1.4 fake",
                size_bytes=13,
            ))
            db.add(DocFile(
                component_id=c.id,
                relative_path="NTI-001 SIMBA/topologia.png",
                title="Topologia",
                doc_type="image",
                content_markdown="",
                content_binary=b"\x89PNG fake",
                size_bytes=9,
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
    assert data[0]["docs_count"] == 4

def test_get_component_detail(client, component):
    response = client.get(f"/api/catalog/{component['id']}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == component["name"]
    assert data["docs_count"] == 4
    assert "python" in data["tags"]
    assert data["dependencies"] == ["outro-componente"]

def test_get_component_detail_inexistente(client):
    assert client.get("/api/catalog/99999").status_code == 404

def test_get_component_docs(client, component):
    response = client.get(f"/api/catalog/{component['id']}/docs")
    assert response.status_code == 200
    docs = response.json()
    assert sorted(d["relative_path"] for d in docs) == [
        "NTI-001 SIMBA/Relatorio Tecnico.pdf",
        "NTI-001 SIMBA/topologia.png",
        "README.md",
        "index.md",
    ]
    by_path = {d["relative_path"]: d for d in docs}
    assert by_path["index.md"]["doc_type"] == "markdown"
    assert by_path["NTI-001 SIMBA/Relatorio Tecnico.pdf"]["doc_type"] == "pdf"
    assert by_path["NTI-001 SIMBA/Relatorio Tecnico.pdf"]["size_bytes"] == 13
    assert by_path["NTI-001 SIMBA/topologia.png"]["doc_type"] == "image"

def test_get_doc_content(client, component):
    response = client.get(f"/api/catalog/{component['id']}/docs/index.md")
    assert response.status_code == 200
    doc = response.json()
    assert doc["title"] == "Visão Geral"
    assert "sequenceDiagram" in doc["content_markdown"]
    assert doc["doc_type"] == "markdown"

def test_get_doc_content_em_subpasta(client, component):
    """O caminho aninhado precisa sobreviver ao roteamento e à codificação da URL."""
    response = client.get(f"/api/catalog/{component['id']}/docs/NTI-001%20SIMBA/Relatorio%20Tecnico.pdf")
    assert response.status_code == 200
    doc = response.json()
    assert doc["doc_type"] == "pdf"
    # O texto não vem por aqui; o cliente busca os bytes em `docs-raw`.
    assert doc["content_markdown"] is None

def test_get_doc_raw_pdf(client, component):
    response = client.get(f"/api/catalog/{component['id']}/docs-raw/NTI-001%20SIMBA/Relatorio%20Tecnico.pdf")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content == b"%PDF-1.4 fake"

def test_get_doc_raw_imagem(client, component):
    response = client.get(f"/api/catalog/{component['id']}/docs-raw/NTI-001%20SIMBA/topologia.png")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content == b"\x89PNG fake"

def test_get_doc_raw_de_markdown_nao_existe(client, component):
    response = client.get(f"/api/catalog/{component['id']}/docs-raw/index.md")
    assert response.status_code == 404

def test_docs_search_por_nome(client, component):
    response = client.get(f"/api/catalog/{component['id']}/docs-search", params={"q": "topologia"})
    assert response.status_code == 200
    results = response.json()["results"]
    assert [r["relative_path"] for r in results] == ["NTI-001 SIMBA/topologia.png"]
    assert results[0]["in_name"] is True

def test_docs_search_por_conteudo_traz_trecho(client, component):
    response = client.get(f"/api/catalog/{component['id']}/docs-search", params={"q": "sequenceDiagram"})
    assert response.status_code == 200
    results = response.json()["results"]
    assert [r["relative_path"] for r in results] == ["index.md"]
    # Acerto só no corpo: a UI precisa do trecho para justificar o resultado.
    assert results[0]["in_name"] is False
    assert "sequenceDiagram" in results[0]["snippet"]

def test_docs_search_casa_com_a_pasta_no_caminho(client, component):
    response = client.get(f"/api/catalog/{component['id']}/docs-search", params={"q": "SIMBA"})
    assert response.status_code == 200
    results = response.json()["results"]
    assert [r["relative_path"] for r in results] == [
        "NTI-001 SIMBA/Relatorio Tecnico.pdf",
        "NTI-001 SIMBA/topologia.png",
    ]
    assert all(r["in_name"] for r in results)

def test_docs_search_poe_acerto_de_nome_antes_do_de_conteudo(client, component):
    """`componente` está no título de README e no corpo dos dois markdowns."""
    response = client.get(f"/api/catalog/{component['id']}/docs-search", params={"q": "componente"})
    assert response.status_code == 200
    flags = [r["in_name"] for r in response.json()["results"]]
    assert flags == sorted(flags, reverse=True)

def test_docs_search_ignora_docs_de_outro_componente(client, component):
    response = client.get("/api/catalog/99999/docs-search", params={"q": "README"})
    assert response.status_code == 200
    assert response.json()["results"] == []

def test_docs_search_exige_termo_minimo(client, component):
    response = client.get(f"/api/catalog/{component['id']}/docs-search", params={"q": "a"})
    assert response.status_code == 422

@pytest.mark.parametrize("mode", ["rebuild", "prune"])
def test_sync_recusa_recorte_em_modo_destrutivo(client, mode):
    """Restringir rebuild/prune a alguns projetos apagaria todo o resto."""
    response = client.post("/api/sync", json={"mode": mode, "project_ids": [1, 2]})
    assert response.status_code == 400
    assert "update" in response.json()["detail"]


def test_sync_projects_reporta_falha_do_gitlab(client, monkeypatch):
    """Sem GitLab acessível, a lista tem que falhar em vez de vir vazia."""
    from app.gitlab.gitlab_crawler import GitLabCrawlerService, ProjectListError

    async def explode(self, group_id=None):
        raise ProjectListError("GitLab respondeu 401 ao listar projetos")

    monkeypatch.setattr(GitLabCrawlerService, "fetch_projects", explode)
    response = client.get("/api/sync/projects")
    assert response.status_code == 502
    assert "401" in response.json()["detail"]


def test_sync_projects_marca_o_que_ja_esta_no_catalogo(client, component, monkeypatch):
    from app.gitlab.gitlab_crawler import GitLabCrawlerService

    async def projetos(self, group_id=None):
        return [
            {"id": 1, "name": "componente-de-teste", "path_with_namespace": "empresa/componente-de-teste"},
            {"id": 77, "name": "projeto-novo", "path_with_namespace": "empresa/projeto-novo"},
        ]

    monkeypatch.setattr(GitLabCrawlerService, "fetch_projects", projetos)
    response = client.get("/api/sync/projects")
    assert response.status_code == 200

    por_id = {p["id"]: p for p in response.json()}
    assert por_id[1]["in_catalog"] is True
    assert por_id[77]["in_catalog"] is False


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
    assert "Strix" in dom["solutions"]
    assert dom["components"][0]["name"] == component["name"]


def test_get_domain_detail(client, component):
    response = client.get("/api/domains/internal-tooling")
    assert response.status_code == 200
    data = response.json()
    assert data["domain"] == "internal-tooling"
    assert data["components_count"] == 1
    assert "Strix" in data["solutions"]
    assert data["components"][0]["name"] == component["name"]


def test_get_domain_detail_inexistente(client):
    response = client.get("/api/domains/dominio-inexistente-999")
    assert response.status_code == 404


def test_get_domain_detail_ignora_caixa(client, component):
    """A URL vem do usuário; o agrupamento não pode depender da grafia."""
    response = client.get("/api/domains/INTERNAL-TOOLING")
    assert response.status_code == 200
    assert response.json()["domain"] == "internal-tooling"


def test_list_solutions(client, component):
    response = client.get("/api/solutions")
    assert response.status_code == 200
    solutions = response.json()
    assert isinstance(solutions, list)
    sol = next(s for s in solutions if s["solution"] == "Strix")
    assert sol["components_count"] == 1
    assert "time-de-teste" in sol["owners"]
    assert "internal-tooling" in sol["domains"]
    assert sol["components"][0]["name"] == component["name"]


def test_get_solution_detail(client, component):
    response = client.get("/api/solutions/Strix")
    assert response.status_code == 200
    data = response.json()
    assert data["solution"] == "Strix"
    assert data["components_count"] == 1
    assert "internal-tooling" in data["domains"]
    assert data["components"][0]["name"] == component["name"]
    # Só o detalhe carrega tags e contagem de deployments.
    assert "python" in data["components"][0]["tags"]
    assert data["components"][0]["deployments_count"] == 1


def test_get_solution_detail_inexistente(client):
    response = client.get("/api/solutions/solucao-inexistente-999")
    assert response.status_code == 404






def test_get_dependency_graph(client, component):
    response = client.get("/api/graph")
    assert response.status_code == 200
    data = response.json()

    assert data["scope"]["kind"] == "catalog"
    # O componente de teste depende de um nome que não existe no catálogo:
    # os dois viram nó, e o alvo é reportado como não resolvido.
    nomes = sorted(n["name"] for n in data["nodes"])
    assert nomes == ["componente-de-teste", "outro-componente"]
    assert data["unresolved"] == ["outro-componente"]
    assert len(data["edges"]) == 1
    assert data["cycles"] == []


def test_get_dependency_graph_por_raiz(client, component):
    response = client.get(f"/api/graph?root={component['id']}&depth=1")
    assert response.status_code == 200
    data = response.json()

    assert data["scope"] == {"kind": "root", "value": component["name"], "depth": 1}
    assert [n["name"] for n in data["nodes"] if n["is_root"]] == [component["name"]]


def test_get_dependency_graph_escopo_inexistente(client):
    assert client.get("/api/graph?root=99999").status_code == 404
    assert client.get("/api/graph?domain=dominio-inexistente-999").status_code == 404
