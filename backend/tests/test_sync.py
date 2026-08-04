"""Testes de sincronização do crawler — sem rede.

Cobre a regressão do erro `greenlet_spawn has not been called`: em contexto
async, atribuir a uma coleção que nunca foi carregada dispara um lazy load
implícito e quebra a sincronização inteira.
"""
import asyncio
import tempfile
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import selectinload, undefer

from app.db.session import Base
from app.db.models import Component, DocFile

#: `Component.docs` não é carregada junto do componente e o conteúdo dos
#: documentos é `deferred` (ver `app/db/models.py`): quem for inspecionar os
#: documentos precisa pedi-los, e ainda dentro do contexto async — as asserções
#: rodam depois que a sessão fechou.
CARREGA_DOCS = selectinload(Component.docs).options(
    undefer(DocFile.content_markdown),
    undefer(DocFile.content_binary),
)
from app.gitlab.gitlab_crawler import (
    MAX_BINARY_DOC_BYTES,
    GitLabCrawlerService,
    ProjectListError,
    SyncMode,
    SyncProgress,
    doc_media_type,
    doc_title_from_path,
    doc_type_for,
    is_hidden_path,
    is_vendor_path,
    nested_sub_dirs,
)

MANIFEST = """
apiVersion: daileon/v1
kind: Component
metadata:
  name: pedido-service
  description: "Serviço de pedidos."
  tags: [java, spring]
  owner: time-pedidos
spec:
  type: service
  lifecycle: production
  solution: Strix
  docs:
    dir: /docs
  links:
    - title: Dashboard
      url: https://grafana.local/pedidos
  dependencies:
    - component: usuario-service
  deployments:
    - environment: production
      url: https://pedido.empresa.com
      server_name: srv-prod-app01
      server_ip: 10.0.1.10
      os: "Linux Ubuntu 22.04"
      execution_type: Docker
      port: 8080
"""

PROJECT = {
    "id": 4242,
    "name": "pedido-service",
    "default_branch": "main",
    "web_url": "https://gitlab.local/empresa/pedido-service",
    "description": "Serviço de pedidos.",
}


def _manifest_de(nome: str) -> str:
    """O `metadata.name` vence o nome do projeto, então cada fake precisa do seu."""
    return MANIFEST.replace("name: pedido-service", f"name: {nome}")


class FakeCrawler(GitLabCrawlerService):
    """Substitui todo o acesso à API do GitLab por conteúdo fixo."""

    projetos = [PROJECT]

    def _nome_de(self, project_id):
        for p in self.projetos:
            if p["id"] == project_id:
                return p["name"]
        return "desconhecido"

    async def fetch_file_content(self, project_id, file_path, ref="main"):
        return {
            "project-info.yml": _manifest_de(self._nome_de(project_id)),
            "README.md": "# Pedido Service",
            "docs/index.md": "# Visão geral",
            "CHANGELOG.md": "# Changelog",
        }.get(file_path)

    async def fetch_docs_tree(self, project_id, docs_dir, ref="main"):
        clean = docs_dir.strip("/")
        if clean == "docs":
            return [{"path": "docs/index.md", "name": "index.md", "type": "blob"}]
        elif not clean:
            return [
                {"path": "README.md", "name": "README.md", "type": "blob"},
                {"path": "docs/index.md", "name": "index.md", "type": "blob"},
                {"path": "CHANGELOG.md", "name": "CHANGELOG.md", "type": "blob"},
            ]
        return []

    async def fetch_projects(self, group_id=None):
        return list(self.projetos)

    async def fetch_manifest_paths(self, project_id: int, ref: str = "main"):
        return ["project-info.yml"]

    async def fetch_first_commit_date(self, project_id: int, ref: str = "main"):
        return datetime(2015, 3, 2, 8, 30)


@asynccontextmanager
async def _session(db_path: Path):
    # Banco em arquivo temporário: com aiosqlite, `:memory:` não sobrevive à
    # devolução da conexão ao pool.
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as db:
            yield db
    finally:
        await engine.dispose()


async def _sync(db_path: Path, times: int) -> Component:
    crawler = FakeCrawler(gitlab_url="https://gitlab.local", token="fake")

    async with _session(db_path) as db:
        for _ in range(times):
            await crawler.sync_all(db)

        components = (await db.execute(select(Component).options(CARREGA_DOCS))).scalars().all()
        assert len(components) == 1, "sincronizar de novo deve atualizar, não duplicar"

        component = components[0]
        # Materializa as coleções ainda dentro do contexto async
        _ = component.tags, component.links, component.dependencies, component.jenkins_pipelines, component.deployments, component.docs
        return component


def _run_sync(times: int) -> Component:
    with tempfile.TemporaryDirectory() as tmp:
        return asyncio.run(_sync(Path(tmp) / "test.db", times))


def test_sync_projeto_novo():
    """Primeira sincronização: o componente ainda não existe no banco."""
    component = _run_sync(times=1)

    assert component.name == "pedido-service"
    assert component.has_manifest is True
    assert component.owner == "time-pedidos"
    assert component.solution == "Strix"
    assert sorted(t.name for t in component.tags) == ["java", "spring"]
    assert [l.title for l in component.links] == ["Dashboard"]
    assert [d.target_component_name for d in component.dependencies] == ["usuario-service"]
    assert len(component.deployments) == 1
    assert component.deployments[0].server_name == "srv-prod-app01"
    assert component.deployments[0].server_ip == "10.0.1.10"
    assert component.deployments[0].os == "Linux Ubuntu 22.04"
    assert component.deployments[0].execution_type == "Docker"
    assert component.deployments[0].port == "8080"
    assert sorted(d.relative_path for d in component.docs) == ["README.md", "index.md"]
    assert component.first_commit_at == datetime(2015, 3, 2, 8, 30)


def test_sync_idempotente():
    """Sincronizar duas vezes atualiza o registro existente sem duplicar."""
    component = _run_sync(times=2)

    assert sorted(t.name for t in component.tags) == ["java", "spring"]
    assert [l.title for l in component.links] == ["Dashboard"]
    assert sorted(d.relative_path for d in component.docs) == ["README.md", "index.md"]


BROKEN_PROJECT = {
    "id": 4243,
    "name": "projeto-quebrado",
    "default_branch": "main",
    "web_url": "https://gitlab.local/empresa/projeto-quebrado",
    "description": "Estoura durante o crawl.",
}


class PartiallyBrokenCrawler(FakeCrawler):
    """O primeiro projeto da lista estoura; o segundo tem que sincronizar mesmo assim."""

    projetos = [BROKEN_PROJECT, PROJECT]

    async def fetch_file_content(self, project_id, file_path, ref="main"):
        if project_id == BROKEN_PROJECT["id"]:
            raise RuntimeError("GitLab fora do ar")
        return await super().fetch_file_content(project_id, file_path, ref)


async def _sync_parcial(db_path: Path):
    crawler = PartiallyBrokenCrawler(gitlab_url="https://gitlab.local", token="fake")

    async with _session(db_path) as db:
        result = await crawler.sync_all(db)
        names = sorted(
            c.name for c in (await db.execute(select(Component))).scalars().all()
        )
        return result, names


def test_falha_em_um_projeto_nao_derruba_o_sync():
    """Um projeto quebrado é reportado, mas os demais continuam sincronizando."""
    with tempfile.TemporaryDirectory() as tmp:
        result, names = asyncio.run(_sync_parcial(Path(tmp) / "test.db"))

    assert result.synced == ["pedido-service"]
    assert names == ["pedido-service"], "o projeto quebrado não pode ficar meio gravado"

    assert len(result.failed) == 1
    failure = result.failed[0]
    assert failure.project_id == BROKEN_PROJECT["id"]
    assert failure.name == "projeto-quebrado"
    assert "GitLab fora do ar" in failure.error


# ------------------------------------------------------- rebuild / prune / progresso

SEGUNDO_PROJETO = {
    "id": 4244,
    "name": "usuario-service",
    "default_branch": "main",
    "web_url": "https://gitlab.local/empresa/usuario-service",
    "description": "Serviço de usuários.",
}


class DoisProjetosCrawler(FakeCrawler):
    projetos = [PROJECT, SEGUNDO_PROJETO]


class ListaVaziaCrawler(FakeCrawler):
    projetos = []


class RegistroDeProgresso(SyncProgress):
    """Coleta o que o crawler reportaria para a UI."""

    def __init__(self):
        self.linhas: list[tuple[str, str]] = []
        self.total = None
        self.passos = 0

    def log(self, level, message):
        self.linhas.append((level, message))

    def set_total(self, total):
        self.total = total

    def advance(self):
        self.passos += 1


async def _sync_com_recorte(db_path: Path, project_ids):
    crawler = DoisProjetosCrawler(gitlab_url="https://gitlab.local", token="x")
    progresso = RegistroDeProgresso()
    async with _session(db_path) as db:
        result = await crawler.run(
            db, mode=SyncMode.UPDATE, progress=progresso, project_ids=project_ids
        )
        nomes = sorted(
            c.name for c in (await db.execute(select(Component))).scalars().all()
        )
        return result, nomes, progresso


def test_sync_restrito_a_um_projeto():
    """Com recorte, os demais projetos nem são visitados."""
    with tempfile.TemporaryDirectory() as tmp:
        result, nomes, progresso = asyncio.run(
            _sync_com_recorte(Path(tmp) / "test.db", [SEGUNDO_PROJETO["id"]])
        )

    assert result.synced == ["usuario-service"]
    assert nomes == ["usuario-service"], "pedido-service estava fora do recorte"
    # O total da barra tem que refletir o recorte, não a lista inteira.
    assert progresso.total == 1
    assert progresso.passos == 1


def test_sync_restrito_avisa_sobre_projeto_inexistente():
    with tempfile.TemporaryDirectory() as tmp:
        result, nomes, progresso = asyncio.run(
            _sync_com_recorte(Path(tmp) / "test.db", [PROJECT["id"], 999999])
        )

    assert result.synced == ["pedido-service"]
    assert nomes == ["pedido-service"]
    assert any(
        nivel == "warn" and "999999" in mensagem for nivel, mensagem in progresso.linhas
    )


def test_sync_sem_recorte_percorre_tudo():
    """`project_ids=None` continua sendo o caminho do catálogo inteiro."""
    with tempfile.TemporaryDirectory() as tmp:
        _, nomes, progresso = asyncio.run(_sync_com_recorte(Path(tmp) / "test.db", None))

    assert nomes == ["pedido-service", "usuario-service"]
    assert progresso.total == 2


async def _rebuild(db_path: Path):
    async with _session(db_path) as db:
        # Popula com dois projetos...
        await DoisProjetosCrawler(gitlab_url="https://gitlab.local", token="x").sync_all(db)

        # ...e reconstrói a partir de um GitLab que só tem um.
        progresso = RegistroDeProgresso()
        result = await FakeCrawler(gitlab_url="https://gitlab.local", token="x").run(
            db, mode=SyncMode.REBUILD, progress=progresso
        )
        nomes = sorted(
            c.name for c in (await db.execute(select(Component))).scalars().all()
        )
        return result, nomes, progresso


def test_rebuild_apaga_o_catalogo_antes_de_importar():
    """O que sumiu do GitLab não sobrevive a um rebuild."""
    with tempfile.TemporaryDirectory() as tmp:
        result, nomes, progresso = asyncio.run(_rebuild(Path(tmp) / "test.db"))

    assert nomes == ["pedido-service"], "usuario-service saiu do GitLab e não pode restar"
    assert result.synced == ["pedido-service"]
    assert result.mode == "rebuild"

    # A UI precisa do total para sair da barra indeterminada.
    assert progresso.total == 1
    assert progresso.passos == 1
    assert any("Apagando" in m for _, m in progresso.linhas)


async def _prune(db_path: Path):
    async with _session(db_path) as db:
        await DoisProjetosCrawler(gitlab_url="https://gitlab.local", token="x").sync_all(db)

        progresso = RegistroDeProgresso()
        result = await FakeCrawler(gitlab_url="https://gitlab.local", token="x").run(
            db, mode=SyncMode.PRUNE, progress=progresso
        )
        nomes = sorted(
            c.name for c in (await db.execute(select(Component))).scalars().all()
        )
        return result, nomes, progresso


def test_prune_remove_apenas_os_orfaos():
    with tempfile.TemporaryDirectory() as tmp:
        result, nomes, progresso = asyncio.run(_prune(Path(tmp) / "test.db"))

    assert result.removed == ["usuario-service"]
    assert nomes == ["pedido-service"], "o projeto ativo não pode ser tocado"
    assert progresso.total == 1


async def _prune_lista_vazia(db_path: Path):
    async with _session(db_path) as db:
        await DoisProjetosCrawler(gitlab_url="https://gitlab.local", token="x").sync_all(db)

        erro = None
        try:
            await ListaVaziaCrawler(gitlab_url="https://gitlab.local", token="x").run(
                db, mode=SyncMode.PRUNE
            )
        except ProjectListError as e:
            erro = e

        nomes = sorted(
            c.name for c in (await db.execute(select(Component))).scalars().all()
        )
        return erro, nomes


def test_prune_aborta_quando_o_gitlab_nao_retorna_projetos():
    """Token sem permissão devolve lista vazia — não pode virar 'apague tudo'."""
    with tempfile.TemporaryDirectory() as tmp:
        erro, nomes = asyncio.run(_prune_lista_vazia(Path(tmp) / "test.db"))

    assert isinstance(erro, ProjectListError)
    assert nomes == ["pedido-service", "usuario-service"], "o catálogo tem que sobreviver"


class SemPastaDocsCrawler(FakeCrawler):
    """Crawler para simular projeto sem a pasta /docs, ativando a busca fallback."""

    async def fetch_docs_tree(self, project_id, docs_dir, ref="main"):
        clean = docs_dir.strip("/")
        if clean == "docs":
            return []  # Sem pasta /docs
        elif not clean:
            return [
                {"path": "README.md", "name": "README.md", "type": "blob"},
                {"path": "CHANGELOG.md", "name": "CHANGELOG.md", "type": "blob"},
            ]
        return []


async def _sync_fallback_docs(db_path: Path):
    crawler = SemPastaDocsCrawler(gitlab_url="https://gitlab.local", token="fake")
    async with _session(db_path) as db:
        await crawler.sync_all(db)
        component = (await db.execute(select(Component).options(CARREGA_DOCS))).scalars().first()
        _ = component.docs
        return component


def test_sync_fallback_docs_sem_pasta_docs():
    """Quando a pasta /docs não existe, o crawler faz a busca fallback por arquivos .md no projeto todo."""
    with tempfile.TemporaryDirectory() as tmp:
        component = asyncio.run(_sync_fallback_docs(Path(tmp) / "test.db"))

    assert sorted(d.relative_path for d in component.docs) == ["CHANGELOG.md", "README.md"]


class DocsEmSubpastasCrawler(FakeCrawler):
    """Documentação organizada em subpastas, misturando Markdown e PDF."""

    async def fetch_docs_tree(self, project_id, docs_dir, ref="main"):
        if docs_dir.strip("/") != "docs":
            return []
        return [
            {"path": "docs/index.md", "name": "index.md", "type": "blob"},
            {"path": "docs/NTI-001 SIMBA/Troubleshooting.md", "name": "Troubleshooting.md", "type": "blob"},
            {"path": "docs/NTI-001 SIMBA/Relatorio_Tecnico.pdf", "name": "Relatorio_Tecnico.pdf", "type": "blob"},
            {"path": "docs/NTI-001 SIMBA/topologia.PNG", "name": "topologia.PNG", "type": "blob"},
            {"path": "docs/NTI-002 Gitlab/tela.jpeg", "name": "tela.jpeg", "type": "blob"},
            {"path": "docs/NTI-002 Gitlab/Thumbs.db", "name": "Thumbs.db", "type": "blob"},
            {"path": "docs/NTI-002 Gitlab/logo.svg", "name": "logo.svg", "type": "blob"},
            {"path": "docs/NTI-003 Airflow/Manual Enorme.pdf", "name": "Manual Enorme.pdf", "type": "blob"},
        ]

    async def fetch_file_content(self, project_id, file_path, ref="main"):
        if file_path == "docs/NTI-001 SIMBA/Troubleshooting.md":
            return "# Troubleshooting do SIMBA"
        return await super().fetch_file_content(project_id, file_path, ref=ref)

    async def fetch_file_bytes(self, project_id, file_path, ref="main"):
        if file_path == "docs/NTI-003 Airflow/Manual Enorme.pdf":
            return b"x" * (MAX_BINARY_DOC_BYTES + 1)
        if file_path.lower().endswith((".png", ".jpeg")):
            return b"\x89PNG bytes"
        return b"%PDF-1.7 conteudo"


async def _sync_docs_em_subpastas(db_path: Path):
    crawler = DocsEmSubpastasCrawler(gitlab_url="https://gitlab.local", token="fake")
    async with _session(db_path) as db:
        await crawler.sync_all(db)
        component = (await db.execute(select(Component).options(CARREGA_DOCS))).scalars().first()
        _ = component.docs
        return component


def test_sync_preserva_subpastas_e_indexa_pdf():
    with tempfile.TemporaryDirectory() as tmp:
        component = asyncio.run(_sync_docs_em_subpastas(Path(tmp) / "test.db"))

    por_caminho = {d.relative_path: d for d in component.docs}
    # O caminho relativo mantém a subpasta: é isso que a árvore do frontend usa.
    # `Thumbs.db` e `logo.svg` não têm extensão indexada e o PDF acima do limite
    # é descartado.
    assert sorted(por_caminho) == [
        "NTI-001 SIMBA/Relatorio_Tecnico.pdf",
        "NTI-001 SIMBA/Troubleshooting.md",
        "NTI-001 SIMBA/topologia.PNG",
        "NTI-002 Gitlab/tela.jpeg",
        "README.md",
        "index.md",
    ]

    pdf = por_caminho["NTI-001 SIMBA/Relatorio_Tecnico.pdf"]
    assert pdf.doc_type == "pdf"
    assert pdf.content_binary == b"%PDF-1.7 conteudo"
    assert pdf.size_bytes == len(b"%PDF-1.7 conteudo")
    assert pdf.title == "Relatorio Tecnico"

    imagem = por_caminho["NTI-001 SIMBA/topologia.PNG"]
    assert imagem.doc_type == "image"
    assert imagem.content_binary == b"\x89PNG bytes"
    assert imagem.title == "Topologia"

    markdown = por_caminho["NTI-001 SIMBA/Troubleshooting.md"]
    assert markdown.doc_type == "markdown"
    assert markdown.content_binary is None
    assert markdown.content_markdown == "# Troubleshooting do SIMBA"


def test_doc_type_for_reconhece_extensoes():
    assert doc_type_for("guia.md") == "markdown"
    assert doc_type_for("GUIA.MD") == "markdown"
    assert doc_type_for("notas.markdown") == "markdown"
    assert doc_type_for("relatorio.pdf") == "pdf"
    assert doc_type_for("diagrama.png") == "image"
    assert doc_type_for("foto.JPG") == "image"
    assert doc_type_for("captura.jpeg") == "image"
    assert doc_type_for("Thumbs.db") is None
    # SVG fica fora por ser executável dentro do navegador.
    assert doc_type_for("logo.svg") is None


def test_doc_media_type_por_extensao():
    assert doc_media_type("NTI-001/relatorio.pdf") == "application/pdf"
    assert doc_media_type("NTI-001/topologia.PNG") == "image/png"
    # `.jpeg` não pode ser resolvido pelo sufixo mais curto `.jpg`.
    assert doc_media_type("captura.jpeg") == "image/jpeg"
    assert doc_media_type("foto.jpg") == "image/jpeg"


def test_doc_title_from_path_usa_apenas_o_nome_do_arquivo():
    assert doc_title_from_path("NTI-001 SIMBA/relatorio_tecnico.pdf") == "Relatorio Tecnico"
    assert doc_title_from_path("guia-de-uso.md") == "Guia De Uso"
    # `.md` no meio do nome não pode ser removido, só o sufixo.
    assert doc_title_from_path("modelo.md") == "Modelo"


class SemManifestCrawler(FakeCrawler):
    """Crawler para simular projeto sem manifest (project-info.yml)."""

    async def fetch_file_content(self, project_id, file_path, ref="main"):
        if file_path == "project-info.yml":
            return None
        return await super().fetch_file_content(project_id, file_path, ref=ref)

    async def fetch_top_committer(self, project_id: int):
        return "gitlab.topcommitter"


async def _sync_sem_manifest(db_path: Path):
    crawler = SemManifestCrawler(gitlab_url="https://gitlab.local", token="fake")
    async with _session(db_path) as db:
        await crawler.sync_all(db)
        component = (await db.execute(select(Component))).scalars().first()
        return component


def test_sync_owner_inferido_pelos_commits():
    """Projeto sem manifest deve ter o owner inferido pelo maior número de commits."""
    with tempfile.TemporaryDirectory() as tmp:
        component = asyncio.run(_sync_sem_manifest(Path(tmp) / "test.db"))

    assert component.owner == "gitlab.topcommitter"


def test_normalize_owner_e_extract_commit_author():
    from app.gitlab.gitlab_crawler import normalize_owner, extract_commit_author

    # Testes de normalize_owner
    assert normalize_owner("ricardo.silva@company.com") == "ricardo.silva"
    assert normalize_owner("  Ricardo.Borges@Company.COM ") == "ricardo.borges"
    assert normalize_owner("team-backend") == "team-backend"
    assert normalize_owner("") == "unassigned"
    assert normalize_owner(None) == "unassigned"

    # Testes de extract_commit_author
    commit_com_email = {
        "author_email": "ricardo.silva@company.com",
        "author_name": "Ricardo Oliveira Borges da Silva"
    }
    assert extract_commit_author(commit_com_email) == "ricardo.silva"

    commit_so_nome = {
        "author_name": "ricardo.silva"
    }
    assert extract_commit_author(commit_so_nome) == "ricardo.silva"

    commit_nome_completo_sem_email = {
        "author_name": "Ricardo Borges"
    }
    assert extract_commit_author(commit_nome_completo_sem_email) == "ricardo borges"


class MonorepoCrawler(FakeCrawler):
    """Crawler para simular repositório Monorepo com múltiplos manifestos project-info.yml em subpastas."""

    projetos = [PROJECT]

    async def fetch_manifest_paths(self, project_id: int, ref: str = "main"):
        return [
            "apps/strix-web/project-info.yml",
            "apps/strix-api/project-info.yml",
        ]

    async def fetch_file_content(self, project_id, file_path, ref="main"):
        if file_path == "apps/strix-web/project-info.yml":
            return """
apiVersion: daileon/v1
kind: Component
metadata:
  name: strix-web
  description: "Painel Web Strix"
  tags: [frontend, svelte]
  owner: team-frontend
  domain: vendas
spec:
  type: website
  solution: Strix
"""
        elif file_path == "apps/strix-api/project-info.yml":
            return """
apiVersion: daileon/v1
kind: Component
metadata:
  name: strix-api
  description: "API Backend Strix"
  tags: [backend, python]
  owner: team-backend
  domain: vendas
spec:
  type: service
  solution: Strix
"""
        return None


async def _sync_monorepo(db_path: Path):
    crawler = MonorepoCrawler(gitlab_url="https://gitlab.local", token="fake")
    async with _session(db_path) as db:
        await crawler.sync_all(db)
        components = (await db.execute(select(Component))).scalars().all()
        return components


def test_sync_monorepo_multiples_manifestos():
    """Testa a sincronização de um Monorepo contendo 2 arquivos project-info.yml em subpastas."""
    with tempfile.TemporaryDirectory() as tmp:
        components = asyncio.run(_sync_monorepo(Path(tmp) / "test.db"))

    assert len(components) == 2
    names = sorted(c.name for c in components)
    assert names == ["strix-api", "strix-web"]

    web = next(c for c in components if c.name == "strix-web")
    api = next(c for c in components if c.name == "strix-api")

    assert web.solution == "Strix"
    assert web.manifest_path == "apps/strix-web/project-info.yml"
    assert api.solution == "Strix"
    assert api.manifest_path == "apps/strix-api/project-info.yml"


def test_fetch_manifest_paths_paginacao_e_extensoes():
    """Testa a busca de manifestos com paginação e extensões .yml e .yaml."""
    crawler = GitLabCrawlerService(gitlab_url="https://gitlab.local", token="fake_token")

    async def run_test():
        from unittest.mock import patch, MagicMock

        page1_items = [{"type": "blob", "name": "project-info.yml", "path": "project-info.yml"}] + [
            {"type": "blob", "name": f"file_{i}.txt", "path": f"src/file_{i}.txt"} for i in range(99)
        ]
        page2_items = [
            {"type": "blob", "name": "project-info.yaml", "path": "subprojects/service-a/project-info.yaml"},
            {"type": "blob", "name": "PROJECT-INFO.YML", "path": "subprojects/service-b/PROJECT-INFO.YML"},
        ]

        async def mock_get(*args, **kwargs):
            url_arg = kwargs.get("url") or (args[1] if len(args) > 1 else args[0])
            target_url = str(url_arg)
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            if "page=1&" in target_url:
                mock_resp.json.return_value = page1_items
            elif "page=2&" in target_url:
                mock_resp.json.return_value = page2_items
            else:
                mock_resp.json.return_value = []
            return mock_resp

        with patch("httpx.AsyncClient.get", side_effect=mock_get):
            return await crawler.fetch_manifest_paths(100, ref="main")

    paths = asyncio.run(run_test())
    assert paths == [
        "project-info.yml",
        "subprojects/service-a/project-info.yaml",
        "subprojects/service-b/PROJECT-INFO.YML",
    ]


def test_is_hidden_path_ignora_diretorios_com_ponto():
    """Diretórios ocultos não guardam documentação técnica do projeto."""
    assert is_hidden_path(".github/CONTRIBUTING.md")
    assert is_hidden_path("docs/.drafts/rascunho.md")
    assert is_hidden_path(".git/refs/notes.md")

    assert not is_hidden_path("docs/index.md")
    assert not is_hidden_path("README.md")
    # O ponto é no arquivo, não num diretório do caminho.
    assert not is_hidden_path("docs/.hidden.md")

    # Um ponto no próprio diretório consultado foi escolha explícita de quem
    # configurou `docs.dir` — não pode descartar o conteúdo inteiro.
    assert not is_hidden_path(".config/docs/index.md", base=".config/docs")
    assert is_hidden_path(".config/docs/.old/index.md", base=".config/docs")


def test_is_vendor_path_ignora_dependencias_e_build():
    assert is_vendor_path("node_modules/lib/project-info.yml")
    assert is_vendor_path("frontend/node_modules/x/project-info.yml")
    assert is_vendor_path("target/classes/project-info.yml")

    assert not is_vendor_path("project-info.yml")
    assert not is_vendor_path("apps/strix-api/project-info.yml")


def test_nested_sub_dirs_so_exclui_o_que_esta_abaixo():
    todos = {"", "apps/web", "apps/web/lib", "apps/api"}

    # Da raiz, todo subprojeto é de outro componente.
    assert nested_sub_dirs("", todos) == ["apps/api", "apps/web", "apps/web/lib"]
    # De `apps/web`, só o que está dentro dele; `apps/api` é irmão e nunca
    # aparece na varredura, e a raiz é ascendente — excluí-la zeraria tudo.
    assert nested_sub_dirs("apps/web", todos) == ["apps/web/lib"]
    assert nested_sub_dirs("apps/web/lib", todos) == []


def test_fetch_docs_tree_descarta_diretorios_ocultos():
    """A varredura da raiz alcança `.github`, `.gitlab` e afins."""
    crawler = GitLabCrawlerService(gitlab_url="https://gitlab.local", token="fake_token")

    async def run_test():
        from unittest.mock import patch, MagicMock

        itens = [
            {"type": "blob", "name": "README.md", "path": "README.md"},
            {"type": "blob", "name": "index.md", "path": "docs/index.md"},
            {"type": "blob", "name": "CONTRIBUTING.md", "path": ".github/CONTRIBUTING.md"},
            {"type": "blob", "name": "notas.md", "path": ".gitlab/notas.md"},
            {"type": "blob", "name": "rascunho.md", "path": "docs/.drafts/rascunho.md"},
            {"type": "tree", "name": "docs", "path": "docs"},
        ]

        async def mock_get(*args, **kwargs):
            url_arg = kwargs.get("url") or (args[1] if len(args) > 1 else args[0])
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = itens if "page=1&" in str(url_arg) else []
            return mock_resp

        with patch("httpx.AsyncClient.get", side_effect=mock_get):
            return await crawler.fetch_docs_tree(100, "/", ref="main")

    docs = asyncio.run(run_test())
    assert sorted(d["path"] for d in docs) == ["README.md", "docs/index.md"]


def _fetch_first_commit(headers, paginas, crawler=None):
    """Executa `fetch_first_commit_date` contra uma API do GitLab simulada.

    `paginas` recebe `(page, per_page)` e devolve os commits daquela página, ou
    `None` para simular uma requisição que falhou.
    """
    from unittest.mock import patch, MagicMock

    crawler = crawler or GitLabCrawlerService(
        gitlab_url="https://gitlab.local", token="fake_token"
    )

    async def run_test():
        async def mock_get(*args, **kwargs):
            url_arg = kwargs.get("url") or (args[1] if len(args) > 1 else args[0])
            url = str(url_arg)
            # Cuidado: `per_page=` também contém "page=".
            page = int(url.split("&page=")[1]) if "&page=" in url else 1
            per_page = int(url.split("&per_page=")[1].split("&")[0])
            resp = MagicMock()
            commits = paginas(page, per_page)
            resp.status_code = 200 if commits is not None else 500
            resp.headers = headers
            resp.json.return_value = commits if commits is not None else {}
            return resp

        with patch("httpx.AsyncClient.get", side_effect=mock_get):
            return await crawler.fetch_first_commit_date(100, ref="main")

    return asyncio.run(run_test())


def _repo_simulado(total_commits):
    """Um repositório do commit mais novo para o mais antigo, um por dia.

    O commit de índice 0 é de 2026-01-01 e o mais antigo, o de índice
    `total_commits - 1`, é de `2026-01-01` menos `total_commits - 1` dias.
    """
    def paginas(page, per_page):
        inicio = (page - 1) * per_page
        return [
            {
                "committed_date": (
                    datetime(2026, 1, 1) - timedelta(days=i)
                ).strftime("%Y-%m-%dT%H:%M:%S.000Z")
            }
            for i in range(inicio, min(inicio + per_page, total_commits))
        ]

    return paginas


def _data_do_commit_mais_antigo(total_commits):
    return datetime(2026, 1, 1) - timedelta(days=total_commits - 1)


def test_fetch_first_commit_date_vai_ate_a_ultima_pagina():
    """Com `per_page=1`, a última página guarda o commit mais antigo."""
    resultado = _fetch_first_commit(
        headers={"x-total-pages": "42"},
        paginas=_repo_simulado(42),
    )
    assert resultado is not None
    assert resultado.replace(tzinfo=None) == _data_do_commit_mais_antigo(42)


def test_fetch_first_commit_date_com_commit_unico():
    """Uma página só: o commit mais novo também é o mais antigo."""
    resultado = _fetch_first_commit(
        headers={"x-total-pages": "1"},
        paginas=_repo_simulado(1),
    )
    assert resultado is not None
    assert resultado.replace(tzinfo=None) == datetime(2026, 1, 1)


def test_fetch_first_commit_date_sem_cabecalho_de_paginacao():
    """Sem `x-total-pages` a última página é encontrada por sondagem.

    O endpoint de commits costuma vir sem esse cabeçalho, então este é o
    caminho normal, não a exceção.
    """
    resultado = _fetch_first_commit(headers={}, paginas=_repo_simulado(350))
    assert resultado is not None
    assert resultado.replace(tzinfo=None) == _data_do_commit_mais_antigo(350)


def test_fetch_first_commit_date_sondagem_com_repo_de_uma_pagina():
    """Repositório menor que uma página: a primeira página já é a última."""
    resultado = _fetch_first_commit(headers={}, paginas=_repo_simulado(7))
    assert resultado is not None
    assert resultado.replace(tzinfo=None) == _data_do_commit_mais_antigo(7)


def test_fetch_first_commit_date_desiste_quando_a_sondagem_estoura_o_teto():
    """Sem chegar à última página, devolver um commit do meio seria pior.

    O teto de requisições é apertado aqui de propósito; na prática ele cobre
    repositórios muito maiores do que este.
    """
    crawler = GitLabCrawlerService(gitlab_url="https://gitlab.local", token="fake_token")
    crawler.MAX_COMMIT_PAGE_PROBES = 2

    resultado = _fetch_first_commit(
        headers={}, paginas=_repo_simulado(5000), crawler=crawler
    )
    assert resultado is None


def test_fetch_first_commit_date_nao_confunde_erro_com_fim_do_repositorio():
    """Uma requisição que falha não significa que a página está vazia."""
    def paginas(page, per_page):
        return None if page > 1 else _repo_simulado(5000)(page, per_page)

    assert _fetch_first_commit(headers={}, paginas=paginas) is None


class MonorepoDocsCrawler(FakeCrawler):
    """Monorepo com manifesto na raiz e em `apps/strix-api`.

    Nenhum dos dois tem pasta `docs/`, então ambos caem no fallback que varre
    a pasta inteira do componente — é aí que a raiz alcança o subprojeto.
    """

    projetos = [PROJECT]

    async def fetch_manifest_paths(self, project_id: int, ref: str = "main"):
        return ["project-info.yml", "apps/strix-api/project-info.yml"]

    async def fetch_file_content(self, project_id, file_path, ref="main"):
        conteudos = {
            "project-info.yml": _manifest_de("monorepo-raiz"),
            "apps/strix-api/project-info.yml": _manifest_de("strix-api"),
            "GUIA.md": "# Guia da raiz",
            "apps/strix-api/API.md": "# Guia da API",
        }
        return conteudos.get(file_path)

    async def fetch_docs_tree(self, project_id, docs_dir, ref="main"):
        clean = docs_dir.strip("/")
        arvore = [
            {"path": "GUIA.md", "name": "GUIA.md", "type": "blob"},
            {"path": "apps/strix-api/API.md", "name": "API.md", "type": "blob"},
        ]
        if clean == "docs" or clean == "apps/strix-api/docs":
            return []
        if not clean:
            return arvore
        return [i for i in arvore if i["path"].startswith(f"{clean}/")]


def test_sync_monorepo_nao_rouba_docs_do_subprojeto():
    """A documentação de `apps/strix-api` pertence a ele, não ao componente-raiz."""
    async def run_test(db_path):
        crawler = MonorepoDocsCrawler(gitlab_url="https://gitlab.local", token="fake")
        async with _session(db_path) as db:
            await crawler.sync_all(db)
            components = (await db.execute(select(Component).options(CARREGA_DOCS))).scalars().all()
            for c in components:
                _ = c.docs
            return components

    with tempfile.TemporaryDirectory() as tmp:
        components = asyncio.run(run_test(Path(tmp) / "test.db"))

    raiz = next(c for c in components if c.name == "monorepo-raiz")
    api = next(c for c in components if c.name == "strix-api")

    assert sorted(d.relative_path for d in raiz.docs) == ["GUIA.md"]
    assert sorted(d.relative_path for d in api.docs) == ["API.md"]





