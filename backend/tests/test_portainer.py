import pytest
from app.plugins.portainer.service import (
    PortainerService,
    _clean_base_url,
    enabled_servers,
    find_server,
    mask_server,
    normalize_portainer_config,
    unmask_server,
)

def test_clean_base_url():
    assert _clean_base_url("http://portainer.local:9000/") == "http://portainer.local:9000"
    assert _clean_base_url("portainer.company.com:9443") == "http://portainer.company.com:9443"
    assert _clean_base_url("https://portainer.company.com:9443/") == "https://portainer.company.com:9443"

def test_match_containers_by_name():
    containers = [
        {
            "id": "c1",
            "name": "strix-backend",
            "endpoint_id": 1,
            "stack_name": "strix",
            "service_name": "backend"
        },
        {
            "id": "c2",
            "name": "other-app",
            "endpoint_id": 1,
            "stack_name": "other",
            "service_name": "app"
        }
    ]

    matched = PortainerService.match_containers_for_component(containers, "strix-backend")
    assert len(matched) == 1
    assert matched[0]["id"] == "c1"



@pytest.mark.anyio
async def test_test_connection_empty_url():
    res = await PortainerService.test_connection({"url": ""})
    assert res["success"] is False
    assert "não configurada" in res["message"]

def test_match_containers_by_deployment_ip_and_port():
    containers = [
        {
            "id": "c1",
            "name": "random-name-app",
            "endpoint_id": 1,
            "endpoint_name": "srv-prod-01",
            "endpoint_public_url": "10.0.1.10:9000",
            "raw_ports": [{"IP": "0.0.0.0", "PublicPort": 8080, "PrivatePort": 80}],
            "stack_name": "unknown",
            "service_name": "unknown"
        },
        {
            "id": "c2",
            "name": "other-app",
            "endpoint_id": 1,
            "endpoint_name": "srv-prod-02",
            "endpoint_public_url": "10.0.1.20:9000",
            "raw_ports": [{"IP": "0.0.0.0", "PublicPort": 3000, "PrivatePort": 3000}],
            "stack_name": "unknown",
            "service_name": "unknown"
        }
    ]

    deployments = [
        {
            "server_ip": "10.0.1.10",
            "port": "8080"
        }
    ]

    matched = PortainerService.match_containers_for_component(
        containers,
        component_name="unmatched-name",
        deployments=deployments
    )
    assert len(matched) == 1
    assert matched[0]["id"] == "c1"

def test_match_containers_by_deployment_url():
    containers = [
        {
            "id": "c1",
            "name": "api-service",
            "endpoint_id": 1,
            "endpoint_public_url": "http://192.168.1.50:9000",
            "raw_ports": [{"IP": "0.0.0.0", "PublicPort": 9090, "PrivatePort": 8080}],
            "stack_name": "",
            "service_name": ""
        }
    ]

    deployments = [
        {
            "url": "http://192.168.1.50:9090/health"
        }
    ]

    matched = PortainerService.match_containers_for_component(
        containers,
        component_name="custom-api",
        deployments=deployments
    )
    assert len(matched) == 1
    assert matched[0]["id"] == "c1"

def test_match_containers_by_deployment_port_only():
    containers = [
        {
            "id": "c1",
            "name": "unmatched-container",
            "raw_ports": [{"IP": "0.0.0.0", "PublicPort": 5000, "PrivatePort": 5000}],
            "stack_name": "",
            "service_name": ""
        }
    ]

    deployments = [
        {
            "port": "5000"
        }
    ]

    matched = PortainerService.match_containers_for_component(
        containers,
        component_name="random-comp",
        deployments=deployments
    )
    assert len(matched) == 1
    assert matched[0]["id"] == "c1"



# -- Vários servidores Portainer -------------------------------------------

def test_normalize_migrates_legacy_single_server():
    """Instalações antigas gravaram um servidor único com `url` na raiz."""
    legacy = {
        "url": "http://portainer.local:9000",
        "api_key": "ptr_abc",
        "username": "",
        "password": "",
        "enabled": True,
    }

    config = normalize_portainer_config(legacy)

    assert len(config["servers"]) == 1
    server = config["servers"][0]
    assert server["url"] == "http://portainer.local:9000"
    assert server["api_key"] == "ptr_abc"
    assert server["enabled"] is True
    assert server["id"]
    assert server["name"]


def test_normalize_handles_empty_and_garbage():
    assert normalize_portainer_config(None) == {"servers": []}
    assert normalize_portainer_config({}) == {"servers": []}
    assert normalize_portainer_config({"servers": []}) == {"servers": []}
    # Entradas que não são dicionário são descartadas em vez de explodir.
    assert normalize_portainer_config({"servers": ["lixo", None]}) == {"servers": []}


def test_normalize_preserves_existing_ids():
    """O id não pode ser re-sorteado a cada leitura: é ele que as rotas de
    stats/logs/ação usam para achar o servidor."""
    config = normalize_portainer_config({
        "servers": [{"id": "fixo123", "name": "Prod", "url": "http://a:9000"}]
    })
    assert config["servers"][0]["id"] == "fixo123"


def test_normalize_assigns_distinct_ids_to_new_servers():
    config = normalize_portainer_config({
        "servers": [
            {"name": "Prod", "url": "http://a:9000"},
            {"name": "Homolog", "url": "http://b:9000"},
        ]
    })
    ids = [s["id"] for s in config["servers"]]
    assert len(set(ids)) == 2
    assert all(ids)


def test_enabled_servers_skips_disabled_and_urlless():
    config = normalize_portainer_config({
        "servers": [
            {"id": "a", "name": "Prod", "url": "http://a:9000", "enabled": True},
            {"id": "b", "name": "Off", "url": "http://b:9000", "enabled": False},
            {"id": "c", "name": "Vazio", "url": "", "enabled": True},
        ]
    })
    assert [s["id"] for s in enabled_servers(config)] == ["a"]


def test_find_server():
    config = normalize_portainer_config({
        "servers": [{"id": "a", "name": "Prod", "url": "http://a:9000"}]
    })
    assert find_server(config, "a")["name"] == "Prod"
    assert find_server(config, "inexistente") is None


def test_mask_server_hides_both_secrets():
    """A API key vazava em texto puro na resposta de configuração."""
    masked = mask_server({
        "id": "a", "name": "Prod", "url": "http://a:9000",
        "api_key": "ptr_supersecreta", "password": "senha123",
    })
    assert masked["api_key"] == "******"
    assert masked["password"] == "******"
    assert "ptr_supersecreta" not in str(masked)
    assert "senha123" not in str(masked)


def test_unmask_restores_stored_secrets():
    stored = {"api_key": "ptr_real", "password": "senha_real"}
    incoming = {"api_key": "******", "password": "******", "url": "http://a:9000"}

    result = unmask_server(incoming, stored)

    assert result["api_key"] == "ptr_real"
    assert result["password"] == "senha_real"


def test_unmask_keeps_edited_secrets():
    stored = {"api_key": "ptr_antiga"}
    result = unmask_server({"api_key": "ptr_nova"}, stored)
    assert result["api_key"] == "ptr_nova"


def test_unmask_on_new_server_does_not_invent_secret():
    """Servidor novo não tem valor gravado: a máscara vira string vazia."""
    result = unmask_server({"api_key": "******", "password": "******"}, None)
    assert result["api_key"] == ""
    assert result["password"] == ""


@pytest.mark.anyio
async def test_fetch_all_containers_tags_origin_and_survives_failure(monkeypatch):
    """Um Portainer fora do ar não pode zerar a lista dos que responderam."""
    config = normalize_portainer_config({
        "servers": [
            {"id": "s1", "name": "Prod", "url": "http://a:9000"},
            {"id": "s2", "name": "Homolog", "url": "http://b:9000"},
        ]
    })

    async def fake_fetch(server, endpoint_id=None):
        if server["id"] == "s2":
            raise RuntimeError("connection refused")
        return [{"id": "c1", "name": "app", "endpoint_id": 1}]

    monkeypatch.setattr(PortainerService, "fetch_containers", fake_fetch)

    containers, errors = await PortainerService.fetch_all_containers(config)

    assert len(containers) == 1
    assert containers[0]["server_id"] == "s1"
    assert containers[0]["server_name"] == "Prod"
    assert len(errors) == 1
    assert errors[0]["server_id"] == "s2"
    assert "connection refused" in errors[0]["error"]


def test_match_keeps_same_container_id_from_different_servers():
    """Dois servidores podem devolver o mesmo id sem serem o mesmo container:
    a deduplicação não pode descartar o segundo."""
    containers = [
        {"id": "mesmo-id", "name": "app", "server_id": "s1", "server_name": "Prod",
         "endpoint_id": 1, "stack_name": "", "service_name": ""},
        {"id": "mesmo-id", "name": "app", "server_id": "s2", "server_name": "Homolog",
         "endpoint_id": 1, "stack_name": "", "service_name": ""},
    ]

    matched = PortainerService.match_containers_for_component(containers, "app")

    assert len(matched) == 2
    assert {m["server_id"] for m in matched} == {"s1", "s2"}




