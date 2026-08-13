from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.db.session import engine, Base
from app.db.init_db import auto_migrate_db
from app.api.router import api_router
from app.core.plugins import plugin_manager
from app.plugins import register_builtin_plugins

#: Build do SvelteKit (`adapter-static`), copiado para cá pelo Dockerfile.
#: Ausente em desenvolvimento, onde o Vite serve a interface em :5173 e
#: encaminha `/api` para cá.
FRONTEND_DIR = Path(__file__).resolve().parent / "static_site"

# Register builtin plugins (LDAP, GitLab, Jenkins)
register_builtin_plugins()
plugin_manager.register_routes(api_router)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB tables and auto-migrate missing columns
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(auto_migrate_db)

    # Initialize all registered plugins
    await plugin_manager.initialize_all()

    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

# Interface e API são servidas pela mesma origem, então não há requisição
# cross-origin para liberar — daí a ausência de CORSMiddleware aqui.

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get(f"{settings.API_V1_STR}/health")
async def health():
    """Estado do serviço. Usado pelo healthcheck do container."""
    return {
        "status": "ok",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "ui": FRONTEND_DIR.joinpath("index.html").is_file(),
        "plugins": plugin_manager.list_plugins()
    }


def _index_response() -> FileResponse:
    """`index.html` sem cache: o HTML referencia os assets versionados e
    precisa ser rebuscado a cada deploy, senão o navegador serve a versão
    anterior indefinidamente."""
    return FileResponse(
        FRONTEND_DIR / "index.html",
        headers={"cache-control": "no-cache"}
    )


def mount_frontend(app: FastAPI) -> None:
    """Serve o build do SvelteKit, se ele estiver presente.

    Precisa ser chamado depois de todas as rotas de API: o catch-all abaixo
    responde por qualquer caminho não reclamado por elas.
    """
    if not FRONTEND_DIR.joinpath("index.html").is_file():
        return

    # Assets com hash no nome — imutáveis, cache longo é seguro.
    assets_dir = FRONTEND_DIR / "_app"
    if assets_dir.is_dir():
        app.mount("/_app", StaticFiles(directory=assets_dir), name="assets")

    # `api_route` com HEAD explícito: o decorador `get` do FastAPI registra só
    # o método pedido, e probes de load balancer costumam usar HEAD.
    @app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
    async def spa_index():
        return _index_response()

    @app.api_route("/{resource:path}", methods=["GET", "HEAD"], include_in_schema=False)
    async def spa_fallback(resource: str):
        # Um caminho `/api/...` que chegou até aqui não existe. Devolver o
        # index.html faria o cliente receber HTML no lugar de JSON.
        if resource.startswith(settings.API_V1_STR.strip("/") + "/"):
            raise HTTPException(status_code=404, detail="Not Found")

        # Arquivo real do build (favicon.svg, daileon-logo.svg, ...).
        # `resolve()` normaliza `..`; a checagem de parentesco barra qualquer
        # tentativa de sair do diretório do build.
        root = FRONTEND_DIR.resolve()
        candidate = (root / resource).resolve()
        if candidate.is_file() and root in candidate.parents:
            return FileResponse(candidate)

        # Rota do lado do cliente (/catalog/12/docs/guia.md): o roteamento é
        # do SvelteKit, aqui só devolvemos a aplicação.
        return _index_response()


if not FRONTEND_DIR.joinpath("index.html").is_file():
    @app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
    async def root():
        return {
            "message": "Daileon API Service is running",
            "docs": "/docs",
            "ui": "não compilada — rode `npm run dev` em frontend/",
        }


mount_frontend(app)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
