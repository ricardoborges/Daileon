import pytest
from app.plugins.portainer.service import PortainerService, _clean_base_url
from app.catalog.manifest import DaileonManifest

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

def test_match_containers_by_manifest_spec():
    containers = [
        {
            "id": "c1",
            "name": "custom-container-name",
            "endpoint_id": 2,
            "stack_name": "my-stack",
            "service_name": "web"
        }
    ]

    spec = {
        "container_name": "custom-container-name",
        "endpoint_id": 2
    }

    matched = PortainerService.match_containers_for_component(containers, "any-component-name", spec_portainer=spec)
    assert len(matched) == 1
    assert matched[0]["id"] == "c1"

def test_manifest_portainer_parsing():
    yaml_content = """
apiVersion: daileon/v1
kind: Component
metadata:
  name: strix-api
spec:
  type: service
  portainer:
    container_name: "strix-api-container"
    stack_name: "strix-prod"
    endpoint_id: 1
"""
    manifest = DaileonManifest.parse_yaml(yaml_content)
    assert manifest.spec.portainer is not None
    assert manifest.spec.portainer.container_name == "strix-api-container"
    assert manifest.spec.portainer.stack_name == "strix-prod"
    assert manifest.spec.portainer.endpoint_id == 1

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

