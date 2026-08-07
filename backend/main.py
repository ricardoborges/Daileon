from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.session import engine, Base
from app.db.init_db import auto_migrate_db
from app.api.router import api_router
from app.core.plugins import plugin_manager
from app.plugins import register_builtin_plugins

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {
        "message": "Daileon API Service is running",
        "docs": "/docs",
        "plugins": plugin_manager.list_plugins()
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
