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
| `API_URL` | Destino do proxy `/api` do frontend SvelteKit. No Docker Compose, use o hostname do serviço | `http://localhost:8000` / `http://backend:8000` |


---

## 🐳 2. Implantação via Docker Compose (Recomendado)

A forma mais rápida de colocar o Daileon no ar é utilizando o `docker-compose`.

### 2.1. Executar os Contêineres

```bash
# 1. Configurar o token no .env
echo "GITLAB_READ_TOKEN=seu_token_aqui" > .env

# 2. Subir a stack completa (Backend + Frontend)
docker-compose up -d --build
```

### 2.2. Verificar a Saúde dos Serviços

```bash
docker-compose ps
docker-compose logs -f
```

- **Portal Web UI**: [http://localhost:5173](http://localhost:5173)
- **API FastAPI / Swagger**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 💻 3. Execução em Modo de Desenvolvimento (Sem Docker)

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
