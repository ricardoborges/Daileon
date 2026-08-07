# 🚀 Guia de Implantação e Operação do Daileon

Este guia instrui como configurar, implantar e operar o **Daileon** em ambientes de desenvolvimento e produção.

---

## 🔑 1. Variáveis de Ambiente

Crie o arquivo `.env` na raiz do projeto com base no `.env.example`:

```bash
cp .env.example .env
```

### Configurações Disponíveis:

| Variável | Descrição | Exemplo / Padrão |
| :--- | :--- | :--- |
| `GITLAB_URL` | URL base da sua instância do GitLab | `https://gitlab.com` |
| `GITLAB_READ_TOKEN` | Token com permissões `read_api` e `read_repository` | `glpat-xxxxxxxxxxxx` |
| `GITLAB_GROUP_ID` | (Opcional) ID ou caminho do grupo do GitLab para limitar a busca | `1234567` ou `sua-empresa` |
| `JENKINS_URL` | URL base da instância do Jenkins | `https://jenkins.empresa.com` |
| `JENKINS_USER` | Usuário/service account para API do Jenkins | `daileon-service` |
| `JENKINS_API_TOKEN` | Token de API REST do Jenkins para consultar status de builds | `11a2b3c4d5e6f7g8h9` |
| `DATABASE_URL` | String de conexão SQLAlchemy do banco | `sqlite+aiosqlite:///./data/daileon.db` |
| `API_URL` | Só em desenvolvimento: destino do proxy `/api` do Vite. Em produção não existe proxy — interface e API são a mesma origem | `http://localhost:8000` |


---

## 🐳 2. Implantação via Docker Compose (Recomendado)

O Daileon é distribuído como **um único contêiner**. O processo FastAPI atende
a API REST e também entrega a interface já compilada — não há servidor Node em
produção, nem porta separada para o frontend.

O `Dockerfile` na raiz faz isso em dois estágios: o primeiro compila o
SvelteKit para arquivos estáticos, o segundo monta a aplicação Python e copia
esses arquivos para `static_site/`, de onde o `main.py` os serve.

### 2.1. Executar o Contêiner

```bash
# 1. Configurar o token no .env
echo "GITLAB_READ_TOKEN=seu_token_aqui" > .env

# 2. Subir a aplicação
docker compose up -d --build
```

### 2.2. Verificar a Saúde do Serviço

```bash
docker compose ps
docker compose logs -f
curl http://localhost:8000/api/health
```

- **Portal Web UI**: [http://localhost:8000](http://localhost:8000)
- **API FastAPI / Swagger**: [http://localhost:8000/docs](http://localhost:8000/docs)

### 2.3. Volumes

| Caminho no host | No contêiner | Para quê |
| :--- | :--- | :--- |
| `./backend/data` | `/app/data` | Banco SQLite e dados persistentes |
| `./plugins` | `/app/plugins` | Plugins drop-in — **reservado**, ver [`plugins/README.md`](../plugins/README.md) |

---

## 💻 3. Execução em Modo de Desenvolvimento (Sem Docker)

Em desenvolvimento as duas metades sobem separadas, para aproveitar o
hot-reload do Vite. O navegador continua enxergando uma origem só: o Vite
encaminha `/api` para o FastAPI (ver `frontend/vite.config.js`).

### 3.1. Subindo o Backend (Python FastAPI)

```bash
cd backend

# Criar e ativar ambiente virtual
python -m venv venv

# Windows PowerShell:
.\venv\Scripts\activate

# Linux/macOS:
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Definir token do GitLab e rodar o servidor
export GITLAB_READ_TOKEN="seu_token"
python main.py
```
*O servidor iniciará em `http://localhost:8000`.*

---

### 3.2. Subindo o Frontend (SvelteKit)

Em um novo terminal:

```bash
cd frontend

# Instalar pacotes Node
npm install

# Iniciar servidor de desenvolvimento Vite
npm run dev
```
*A interface abrirá em `http://localhost:5173`.*

> Se o backend não estiver em `http://localhost:8000`, aponte o proxy com
> `API_URL` antes de subir o Vite.

### 3.3. Testando o Modo Produção Localmente

Para conferir o comportamento de porta única sem construir a imagem Docker:

```bash
cd frontend && npm run build
cp -r build ../backend/static_site
cd ../backend && uvicorn main:app --port 8000
```

O portal passa a responder em `http://localhost:8000`. `GET /api/health`
informa em `ui` se o backend encontrou a interface compilada. Apague
`backend/static_site/` para voltar ao modo só-API.

---

## 🔄 4. Como Adicionar o Daileon a um Novo Projeto

Para que o seu projeto seja catalogado no Daileon com metadados ricos:

1. **Crie o arquivo `project-info.yml` na raiz do seu repositório GitLab**:
   ```yaml
   apiVersion: daileon/v1
   kind: Component
   metadata:
     name: meu-servico
     description: "Descrição do serviço."
     tags: [node, express]
     owner: meu-time
   spec:
     type: service
     lifecycle: production
     docs:
       dir: /docs
   ```

   > Todos os campos e os valores aceitos estão detalhados na [Referência do `project-info.yml`](project-info-yml.md).

2. **Crie a pasta `/docs` no seu repositório** e adicione o arquivo `index.md`.

3. **Acione o botão "Sync GitLab"** na barra superior do Daileon Web UI.
