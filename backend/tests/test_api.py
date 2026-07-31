import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "Daileon API" in response.json()["message"]

def test_list_catalog():
    response = client.get("/api/catalog")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2
    assert data[0]["name"] == "pagamento-service"

def test_get_component_detail():
    response = client.get("/api/catalog/1")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "pagamento-service"
    assert "java" in data["tags"]

def test_get_component_docs():
    response = client.get("/api/catalog/1/docs")
    assert response.status_code == 200
    docs = response.json()
    assert len(docs) >= 2

def test_get_doc_content():
    response = client.get("/api/catalog/1/docs/index.md")
    assert response.status_code == 200
    doc = response.json()
    assert doc["title"] == "Visão Geral da Arquitetura"
    assert "sequenceDiagram" in doc["content_markdown"]

def test_search():
    response = client.get("/api/search?q=PIX")
    assert response.status_code == 200
    data = response.json()
    assert len(data["components"]) > 0 or len(data["docs"]) > 0
