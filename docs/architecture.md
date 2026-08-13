# 🏛️ Daileon Technical Architecture

This document details the internal architecture, data flow, database models and APIs of **Daileon**.

---

## 📐 1. Architecture Diagram

Daileon is a **single process**: FastAPI serves the REST API and delivers the
already-built SPA, from the same origin and the same port.

```mermaid
architecture-beta
    group user_layer(cloud, "User Layer")
    group app_layer(server, "Daileon (single process, port 8000)")
    group data_layer(database, "Storage & Integration")

    service browser(browser) in user_layer "Web Browser"
    service spa(internet) in app_layer "SvelteKit SPA (static)"
    service fastapi(server) in app_layer "FastAPI Python"
    service crawler(server) in app_layer "GitLab Crawler Engine"
    service sqlite(database) in data_layer "SQLite / PostgreSQL DB"
    service gitlab(cloud) in data_layer "GitLab API v4"

    browser -- font: spa "GET / — static assets"
    browser -- font: fastapi "GET /api — REST + JWT"
    fastapi -- font: spa "serves the build"
    fastapi -- font: sqlite "SQLAlchemy Async"
    crawler -- font: gitlab "httpx REST Client"
    crawler -- font: sqlite "UPSERT Components & Docs"
```

### Why a single origin

The interface does not use server-side rendering: every piece of data comes
from a client-side `fetch`, authenticated with the token kept in the browser.
Since there was nothing to render before login, the Node runtime acted purely
as a proxy to FastAPI — a network hop that added nothing.

SvelteKit now builds with `adapter-static` (SPA with an `index.html` fallback)
and FastAPI serves the result. Direct consequences:

- one container and one port, instead of two of each;
- no CORS: there is no cross-origin request to allow;
- no `API_URL` in production — `/api` resolves on the origin itself;
- deep-link routing (`/catalog/12/docs/guide.md`) belongs to the client, with
  the server returning `index.html` for any path not claimed by the API
  (see `mount_frontend` in `backend/main.py`).

None of this changes the development workflow: Vite runs on `:5173` with
hot-reload and forwards `/api` to the backend on `:8000`.

---

## 🔧 2. Solution Components

### 2.1. Python Backend (`backend/`)
- **FastAPI**: Asynchronous web framework that exposes the REST API.
- **GitLab Crawler Service (`app/gitlab/gitlab_crawler.py`)**:
  - Consumes `/api/v4/projects` using `GITLAB_READ_TOKEN`.
  - Downloads the raw `project-info.yml` file.
  - Downloads the `/docs` folder tree (`/api/v4/projects/:id/repository/tree`).
  - Updates the database through asynchronous inserts/updates.
- **Pydantic Schema (`app/catalog/manifest.py`)**: Strictly validates the YAML structure of the manifest.
- **SQLAlchemy ORMs (`app/db/models.py`)**:
  - `Component`: Main record of the service/entity.
  - `Tag`: Tags for search and categorization.
  - `ComponentLink`: Observability, metrics and API links.
  - `ComponentDependency`: Dependency graph between services.
  - `DocFile`: Content of the indexed Markdown documentation.

### 2.2. SvelteKit Frontend (`frontend/`)
- **SvelteKit + TailwindCSS**: Fluid interface with dark theme support and responsive components.
- **Static build (`adapter-static`)**: Compiles to plain HTML/CSS/JS under `frontend/build/`, served by FastAPI. `src/routes/+layout.ts` turns SSR and prerender off — that is what allows a single `index.html` fallback to be generated.
- **TechDocs Reader (`src/lib/components/TechDocsViewer.svelte`)**:
  - Converts Markdown to HTML via `marked`.
  - Processes `` ```mermaid `` blocks and dynamically renders sequence, class and flow diagrams with `mermaid.js`.
- **API Client (`src/lib/api.ts`)**: Communicates with the FastAPI backend via `fetch`.

---

## 🗄️ 3. Entity-Relationship Diagram (ERD)

```mermaid
erDiagram
    Component ||--o{ ComponentLink : "has"
    Component ||--o{ ComponentDependency : "depends on"
    Component ||--o{ DocFile : "contains"
    Component }|--|{ Tag : "has"

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

## 🌐 4. REST Endpoint Specification

| Method | Route | Description |
| :--- | :--- | :--- |
| `GET` | `/api/catalog` | Lists every catalogued component (supports the `owner`, `type`, `lifecycle` and `tag` filters) |
| `GET` | `/api/catalog/{id}` | Returns the full details of a component |
| `GET` | `/api/catalog/{id}/docs` | Returns the list of Markdown documents of a component |
| `GET` | `/api/catalog/{id}/docs/{path}` | Returns the content of a specific document |
| `POST` | `/api/sync` | Triggers a catalog operation (`update`, `rebuild` or `prune`) and responds `202` right away |
| `GET` | `/api/sync/status?since={cursor}` | Progress of the running operation and the log lines not delivered yet |
| `GET` | `/api/search?q={query}` | Performs the unified search across services and inside the documentation text |
| `GET` | `/api/health` | Service state, registered plugins and whether the compiled interface was found |
