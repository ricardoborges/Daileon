# 🏛️ Arquitetura Técnica do Daileon

Este documento detalha a arquitetura interna, fluxo de dados, modelos de banco de dados e APIs do **Daileon**.

---

## 📐 1. Diagrama de Arquitetura

```mermaid
architecture-beta
    group user_layer(cloud, "Camada de Usuário")
    group fe_layer(internet, "Frontend App")
    group be_layer(server, "Backend Service")
    group data_layer(database, "Armazenamento & Integração")

    service browser(browser) in user_layer "Navegador Web"
    service svelte(server) in fe_layer "SvelteKit UI (Node/Vite)"
    service fastapi(server) in be_layer "FastAPI Python Backend"
    service crawler(server) in be_layer "GitLab Crawler Engine"
    service sqlite(database) in data_layer "SQLite / PostgreSQL DB"
    service gitlab(cloud) in data_layer "GitLab API v4"

    browser -- font: svelte "HTTP / REST"
    svelte -- font: fastapi "API Proxy /api"
    fastapi -- font: sqlite "SQLAlchemy Async"
    crawler -- font: gitlab "httpx REST Client"
    crawler -- font: sqlite "UPSERT Componentes & Docs"
```

---

## 🔧 2. Componentes da Solução

### 2.1. Backend Python (`backend/`)
- **FastAPI**: Framework web assíncrono para disponibilização da API REST.
- **GitLab Crawler Service (`app/gitlab/gitlab_crawler.py`)**:
  - Consome `/api/v4/projects` usando `GITLAB_READ_TOKEN`.
  - Baixa o arquivo `daileon.yml` bruto.
  - Baixa a árvore da pasta `/docs` (`/api/v4/projects/:id/repository/tree`).
  - Atualiza o banco de dados via inserções/atualizações assíncronas.
- **Schema Pydantic (`app/catalog/manifest.py`)**: Valida rigorosamente a estrutura YAML do manifesto.
- **ORMs SQLAlchemy (`app/db/models.py`)**:
  - `Component`: Registro principal do serviço/entidade.
  - `Tag`: Tags de busca e categorização.
  - `ComponentLink`: Links de observabilidade, métricas e APIs.
  - `ComponentDependency`: Grafo de dependências entre serviços.
  - `DocFile`: Conteúdo das documentações em Markdown indexadas.

### 2.2. Frontend SvelteKit (`frontend/`)
- **SvelteKit + TailwindCSS**: Interface fluida com suporte a temas escuros e componentes responsivos.
- **Leitor TechDocs (`src/lib/components/TechDocsViewer.svelte`)**:
  - Converte Markdown para HTML via `marked`.
  - Processa blocos `` ```mermaid `` e renderiza diagramas de sequência, classe e fluxo dinamicamente com `mermaid.js`.
- **API Client (`src/lib/api.ts`)**: Comunicação via `fetch` com o backend FastAPI.

---

## 🗄️ 3. Diagrama Entidade-Relacionamento (ERD)

```mermaid
erDiagram
    Component ||--o{ ComponentLink : "possui"
    Component ||--o{ ComponentDependency : "depende de"
    Component ||--o{ DocFile : "contém"
    Component }|--|{ Tag : "possui"

    Component {
        int id PK
        int gitlab_project_id UK
        string name
        string description
        string kind
        string type
        string lifecycle
        string owner
        string domain
        string gitlab_url
        string docs_dir
        boolean has_manifest
        datetime updated_at
    }

    DocFile {
        int id PK
        int component_id FK
        string relative_path
        string title
        text content_markdown
        datetime updated_at
    }

    ComponentLink {
        int id PK
        int component_id FK
        string title
        string url
        string icon
    }

    ComponentDependency {
        int id PK
        int source_component_id FK
        string target_component_name
    }

    Tag {
        int id PK
        string name UK
    }
```

---

## 🌐 4. Especificação dos Endpoints REST

| Método | Rota | Descrição |
| :--- | :--- | :--- |
| `GET` | `/api/catalog` | Lista todos os componentes catalogados (suporta filtros `owner`, `type`, `lifecycle`, `tag`) |
| `GET` | `/api/catalog/{id}` | Retorna os detalhes completos de um componente |
| `GET` | `/api/catalog/{id}/docs` | Retorna a lista de documentos Markdown de um componente |
| `GET` | `/api/catalog/{id}/docs/{path}` | Retorna o conteúdo de um documento específico |
| `POST` | `/api/sync` | Aciona manualmente a sincronização com o GitLab |
| `GET` | `/api/search?q={query}` | Realiza a busca unificada por serviços e dentro do texto das documentações |
