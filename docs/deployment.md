# 🚀 Daileon Deployment and Operations Guide

This guide explains how to configure, deploy and operate **Daileon** in development and production environments.

---

## 🔑 1. Environment Variables

Create the `.env` file at the root of the project based on `.env.example`:

```bash
cp .env.example .env
```

### Available Settings:

| Variable | Description | Example / Default |
| :--- | :--- | :--- |
| `GITLAB_URL` | Base URL of your GitLab instance | `https://gitlab.com` |
| `GITLAB_READ_TOKEN` | Token with `read_api` and `read_repository` permissions | `glpat-xxxxxxxxxxxx` |
| `GITLAB_GROUP_ID` | (Optional) GitLab group ID or path used to narrow the scan | `1234567` or `your-company` |
| `JENKINS_URL` | Base URL of the Jenkins instance | `https://jenkins.company.com` |
| `JENKINS_USER` | User/service account for the Jenkins API | `daileon-service` |
| `JENKINS_API_TOKEN` | Jenkins REST API token used to query build status | `11a2b3c4d5e6f7g8h9` |
| `DATABASE_URL` | SQLAlchemy connection string for the database | `sqlite+aiosqlite:///./data/daileon.db` |
| `API_URL` | Development only: target of Vite's `/api` proxy. There is no proxy in production — interface and API share the same origin | `http://localhost:8000` |


---

## 🐳 2. Deployment via Docker Compose (Recommended)

Daileon ships as **a single container**. The FastAPI process serves the REST
API and also delivers the already-built interface — there is no Node server in
production, nor a separate port for the frontend.

The root `Dockerfile` does this in two stages: the first builds SvelteKit into
static files, the second assembles the Python application and copies those
files into `static_site/`, where `main.py` serves them from.

### 2.1. Run the Container

```bash
# 1. Configure the token in .env
echo "GITLAB_READ_TOKEN=your_token_here" > .env

# 2. Start the application
docker compose up -d --build
```

### 2.2. Check Service Health

```bash
docker compose ps
docker compose logs -f
curl http://localhost:8000/api/health
```

- **Web UI Portal**: [http://localhost:8000](http://localhost:8000)
- **FastAPI / Swagger API**: [http://localhost:8000/docs](http://localhost:8000/docs)

### 2.3. Volumes

| Host path | In the container | What for |
| :--- | :--- | :--- |
| `./backend/data` | `/app/data` | SQLite database and persistent data |
| `./plugins` | `/app/plugins` | Drop-in plugins — **reserved**, see [`plugins/README.md`](../plugins/README.md) |

---

## 💻 3. Running in Development Mode (No Docker)

In development the two halves run separately, to take advantage of Vite's
hot-reload. The browser still sees a single origin: Vite forwards `/api` to
FastAPI (see `frontend/vite.config.js`).

### 3.1. Starting the Backend (Python FastAPI)

```bash
cd backend

# Create and activate the virtual environment
python -m venv venv

# Windows PowerShell:
.\venv\Scripts\activate

# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set the GitLab token and run the server
export GITLAB_READ_TOKEN="your_token"
python main.py
```
*The server will start at `http://localhost:8000`.*

---

### 3.2. Starting the Frontend (SvelteKit)

In a new terminal:

```bash
cd frontend

# Install Node packages
npm install

# Start the Vite development server
npm run dev
```
*The interface will open at `http://localhost:5173`.*

> If the backend is not at `http://localhost:8000`, point the proxy with
> `API_URL` before starting Vite.

### 3.3. Testing Production Mode Locally

To check the single-port behavior without building the Docker image:

```bash
cd frontend && npm run build
cp -r build ../backend/static_site
cd ../backend && uvicorn main:app --port 8000
```

The portal then responds at `http://localhost:8000`. `GET /api/health` reports
under `ui` whether the backend found the compiled interface. Delete
`backend/static_site/` to go back to API-only mode.

---

## 🔄 4. How to Add Daileon to a New Project

To get your project catalogued in Daileon with rich metadata:

1. **Create the `project-info.yml` file at the root of your GitLab repository**:
   ```yaml
   apiVersion: daileon/v1
   kind: Component
   metadata:
     name: my-service
     description: "Service description."
     tags: [node, express]
     owner: my-team
   spec:
     type: service
     lifecycle: production
     docs:
       dir: /docs
   ```

   > Every field and its accepted values are detailed in the [`project-info.yml` Reference](project-info-yml.md).

2. **Create the `/docs` folder in your repository** and add the `index.md` file.

3. **Click the "Sync GitLab" button** in the top bar of the Daileon Web UI.
