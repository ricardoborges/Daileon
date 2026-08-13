# Daileon — imagem única: o FastAPI serve a API e o build da interface.
#
# Estágio 1 compila o SvelteKit para arquivos estáticos; estágio 2 monta a
# aplicação Python e copia esses arquivos para dentro dela.

FROM node:20-alpine AS frontend

WORKDIR /build

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

# A interface compilada. `main.py` procura por ela exatamente aqui.
COPY --from=frontend /build/build ./static_site

# `data/`: destino do banco SQLite. Em produção um volume é montado por cima,
# mas o diretório precisa existir na imagem para que um `docker run` sem
# volume também suba.
#
# `plugins/`: plugins drop-in, também preenchido por volume (ver
# docker-compose.yml) — os builtin continuam em `app/plugins/`. O carregador
# ainda não existe; a pasta é reservada aqui para que instalar um plugin não
# exija reconstruir a imagem depois.
RUN mkdir -p /app/data /app/plugins

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
