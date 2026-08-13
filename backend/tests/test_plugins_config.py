import pytest
from httpx import AsyncClient, ASGITransport
from main import app
from app.db.session import engine, Base, AsyncSessionLocal
from app.api.auth import create_access_token


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest.mark.anyio
async def test_builtin_plugins_registration():
    token = create_access_token({"sub": "admin", "is_admin": True})
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/plugins", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        data = res.json()
        plugin_ids = [p["id"] for p in data]
        assert "ldap" in plugin_ids
        assert "gitlab" in plugin_ids
        assert "jenkins" in plugin_ids
        assert "portainer" in plugin_ids


@pytest.mark.anyio
async def test_gitlab_plugin_config_flow():
    async with AsyncSessionLocal() as db:
        from app.plugins.gitlab.service import get_effective_gitlab_config, test_gitlab_connection

        # 1. Effective config loads defaults or env vars
        cfg = await get_effective_gitlab_config(db)
        assert "url" in cfg

        # 2. Test connection with empty URL
        test_res = await test_gitlab_connection({"url": ""})
        assert test_res["success"] is False


@pytest.mark.anyio
async def test_jenkins_plugin_config_flow():
    async with AsyncSessionLocal() as db:
        from app.plugins.jenkins.service import get_effective_jenkins_config, test_jenkins_connection

        # 1. Effective config loads defaults or env vars
        cfg = await get_effective_jenkins_config(db)
        assert "url" in cfg

        # 2. Test connection with empty URL
        test_res = await test_jenkins_connection({"url": ""})
        assert test_res["success"] is False


@pytest.mark.anyio
async def test_ldap_plugin_config_flow():
    async with AsyncSessionLocal() as db:
        from app.plugins.ldap.service import LDAPAuthService, get_effective_ldap_config

        cfg = await get_effective_ldap_config(db)
        assert "server_host" in cfg

        test_res = LDAPAuthService.test_connection({"server_host": ""})
        assert test_res["success"] is False


@pytest.mark.anyio
async def test_portainer_plugin_config_flow():
    async with AsyncSessionLocal() as db:
        from app.plugins.portainer.service import get_effective_portainer_config, PortainerService

        # A configuração é uma lista de servidores; cada um traz sua própria URL.
        cfg = await get_effective_portainer_config(db)
        assert "servers" in cfg
        assert all("url" in s and "id" in s for s in cfg["servers"])

        test_res = await PortainerService.test_connection({"url": ""})
        assert test_res["success"] is False
