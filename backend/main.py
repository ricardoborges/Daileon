from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.core.config import settings
from app.db.session import engine, Base, AsyncSessionLocal
from app.db.models import Component, Tag, ComponentLink, ComponentDependency, DocFile
from app.api.router import api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed mock data if empty (so MVP portal works instantly without GitLab credentials)
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Component))
        if not result.scalars().first():
            t1 = Tag(name="java")
            t2 = Tag(name="spring-boot")
            t3 = Tag(name="pix")
            
            # Seed sample component 1
            c1 = Component(
                gitlab_project_id=101,
                name="pagamento-service",
                description="Serviço responsável pelo processamento de pagamentos e liquidação de PIX e Cartões.",
                kind="Component",
                type="service",
                lifecycle="production",
                owner="team-payments",
                domain="checkout",
                system="e-commerce-core",
                gitlab_url="https://gitlab.com/empresa/pagamento-service",
                default_branch="main",
                docs_dir="/docs",
                docs_index="index.md",
                has_manifest=True,
                tags=[t1, t2, t3]
            )
            db.add(c1)
            await db.flush()

            db.add(ComponentLink(component_id=c1.id, title="Grafana Dashboard", url="https://grafana.empresa.com/d/pagamentos", icon="dashboard"))
            db.add(ComponentLink(component_id=c1.id, title="OpenAPI Spec", url="https://api-docs.empresa.com/pagamento-service", icon="api"))
            db.add(ComponentDependency(source_component_id=c1.id, target_component_name="usuario-service"))
            db.add(ComponentDependency(source_component_id=c1.id, target_component_name="notificacao-service"))

            db.add(DocFile(
                component_id=c1.id,
                relative_path="README.md",
                title="README",
                content_markdown="# Pagamento Service\n\nEste serviço processa transações bancárias e PIX em tempo real.\n\n## Arquitetura\n- Framework: Spring Boot 3.2\n- Database: PostgreSQL\n- Queue: RabbitMQ"
            ))
            db.add(DocFile(
                component_id=c1.id,
                relative_path="index.md",
                title="Visão Geral da Arquitetura",
                content_markdown="# Arquitetura do Serviço de Pagamentos\n\nVisão geral dos fluxos de pagamento PIX e Cartão de Crédito.\n\n### Diagrama de Fluxo\n```mermaid\nsequenceDiagram\n    autonumber\n    Client->>Pagamento-Service: Criar Cobrança PIX\n    Pagamento-Service->>Banco-Central: Gerar QRCode\n    Banco-Central-->>Pagamento-Service: Payload PIX\n    Pagamento-Service-->>Client: QRCode & Copia e Cola\n```\n\n### Endpoints Principais\n- `POST /api/v1/pix/qrcode`\n- `GET /api/v1/pagamentos/{id}/status`"
            ))
            db.add(DocFile(
                component_id=c1.id,
                relative_path="setup.md",
                title="Guia de Configuração Local",
                content_markdown="# Guia de Instalação e Execução Local\n\n### Requisitos\n- Java 21\n- Docker & Docker Compose\n\n### Executando em desenvolvimento\n```bash\ndocker-compose up -d\n./mvnw spring-boot:run\n```"
            ))

            t4 = Tag(name="node")
            t5 = Tag(name="nest-js")
            t6 = Tag(name="oauth2")

            # Seed sample component 2
            c2 = Component(
                gitlab_project_id=102,
                name="usuario-service",
                description="API de gerenciamento de identidades, autenticação OAuth2 e perfis de clientes.",
                kind="Component",
                type="service",
                lifecycle="production",
                owner="team-auth",
                domain="security",
                system="e-commerce-core",
                gitlab_url="https://gitlab.com/empresa/usuario-service",
                default_branch="main",
                docs_dir="/docs",
                docs_index="index.md",
                has_manifest=True,
                tags=[t4, t5, t6]
            )
            db.add(c2)
            await db.flush()

            db.add(DocFile(
                component_id=c2.id,
                relative_path="README.md",
                title="README",
                content_markdown="# Usuario Service\n\nAPI de autenticação e perfis dos usuários do ecossistema."
            ))
            db.add(DocFile(
                component_id=c2.id,
                relative_path="index.md",
                title="Documentação de Autenticação",
                content_markdown="# Autenticação e Perfis\n\nUtilizamos JWT tokens assinados com RS256 para comunicação inter-serviços."
            ))

            await db.commit()

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
    return {"message": "Daileon API Service is running", "docs": "/docs"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
