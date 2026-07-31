import pytest
from fastapi.testclient import TestClient
from app.core.config import settings
from main import app

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_break_glass_admin_login(client):
    # Tenta login com credenciais corretas do Break-Glass Admin
    res = client.post("/api/auth/login", json={
        "username": settings.ADMIN_USERNAME,
        "password": settings.ADMIN_PASSWORD
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["username"] == settings.ADMIN_USERNAME
    assert data["user"]["is_admin"] is True
    assert data["user"]["auth_type"] == "break_glass"

    # Testa endpoint /me com o token obtido
    token = data["access_token"]
    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["username"] == settings.ADMIN_USERNAME

def test_invalid_login(client):
    res = client.post("/api/auth/login", json={
        "username": "invalid_user",
        "password": "wrong_password"
    })
    assert res.status_code == 401

def test_unauthenticated_access_blocked(client):
    # Garante que requisições sem o token Bearer falham com 401 Unauthorized
    unauth_client = TestClient(app)
    res = unauth_client.get("/api/catalog")
    assert res.status_code == 401
    assert "Autenticação necessária" in res.json()["detail"]

def test_ldap_config_management(client):
    # Realiza login para obter o token Bearer
    login_res = client.post("/api/auth/login", json={
        "username": settings.ADMIN_USERNAME,
        "password": settings.ADMIN_PASSWORD
    })
    token = login_res.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # Salva configuração LDAP
    config_payload = {
        "enabled": True,
        "server_host": "ldap.example.com",
        "server_port": 389,
        "use_ssl": False,
        "bind_dn": "cn=admin,dc=example,dc=com",
        "bind_password": "secretpassword",
        "base_dn": "ou=users,dc=example,dc=com",
        "user_attribute": "uid"
    }
    save_res = client.post("/api/auth/ldap-config", json=config_payload, headers=auth_headers)
    assert save_res.status_code == 200

    # Obtém configuração e garante que a senha está mascarada
    get_res = client.get("/api/auth/ldap-config", headers=auth_headers)
    assert get_res.status_code == 200
    config_data = get_res.json()
    assert config_data["enabled"] is True
    assert config_data["server_host"] == "ldap.example.com"
    assert config_data["bind_password"] == "******"

def test_ldap_config_env_defaults(client, monkeypatch):
    # Testa se quando LDAP_SERVER_HOST é alterado no Settings, get_effective_ldap_config responde apropriadamente
    monkeypatch.setattr(settings, "LDAP_SERVER_HOST", "env.ldap.local")
    monkeypatch.setattr(settings, "LDAP_BIND_DN", "cn=env,dc=local")
    
    login_res = client.post("/api/auth/login", json={
        "username": settings.ADMIN_USERNAME,
        "password": settings.ADMIN_PASSWORD
    })
    token = login_res.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}
    
    get_res = client.get("/api/auth/ldap-config", headers=auth_headers)
    assert get_res.status_code == 200
    data = get_res.json()
    assert "server_host" in data


