"""Testes de sincronização do crawler — sem rede.

Cobre a regressão do erro `greenlet_spawn has not been called`: em contexto
async, atribuir a uma coleção que nunca foi carregada dispara um lazy load
implícito e quebra a sincronização inteira.
"""
import asyncio
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.db.session import Base
from app.db.models import Component
from app.gitlab.gitlab_crawler import (
    GitLabCrawlerService,
    ProjectListError,
    SyncMode,
    SyncProgress,
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

        components = (await db.execute(select(Component))).scalars().all()
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
        component = (await db.execute(select(Component))).scalars().first()
        _ = component.docs
        return component


def test_sync_fallback_docs_sem_pasta_docs():
    """Quando a pasta /docs não existe, o crawler faz a busca fallback por arquivos .md no projeto todo."""
    with tempfile.TemporaryDirectory() as tmp:
        component = asyncio.run(_sync_fallback_docs(Path(tmp) / "test.db"))

    assert sorted(d.relative_path for d in component.docs) == ["CHANGELOG.md", "README.md"]

