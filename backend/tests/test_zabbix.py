import pytest
from unittest.mock import AsyncMock, patch
from app.plugins.zabbix.service import ZabbixService, SEVERITY_MAP
from app.plugins.zabbix.plugin import ZabbixPlugin
from app.catalog.manifest import DaileonManifest


def test_zabbix_plugin_metadata():
    plugin = ZabbixPlugin()
    assert plugin.plugin_id == "zabbix"
    assert plugin.name == "Zabbix Infrastructure & Observability"
    assert plugin.category == "observability"
    assert plugin.router is not None


def test_zabbix_severity_mapping():
    assert SEVERITY_MAP["5"]["name"] == "Disaster"
    assert SEVERITY_MAP["4"]["color"] == "red"
    assert SEVERITY_MAP["2"]["name"] == "Warning"


@pytest.mark.anyio
async def test_zabbix_service_version_mock():
    service = ZabbixService(url="http://mock-zabbix/zabbix", api_token="test-token")
    
    with patch.object(service, "_rpc_call", new_callable=AsyncMock) as mock_rpc:
        mock_rpc.return_value = "7.0.0"
        version = await service.get_version()
        assert version == "7.0.0"
        mock_rpc.assert_called_once_with("apiinfo.version", {})


@pytest.mark.anyio
async def test_zabbix_get_active_problems():
    service = ZabbixService(url="http://mock-zabbix/zabbix", api_token="test-token")
    
    mock_problems_raw = [
        {
            "eventid": "1001",
            "name": "High CPU utilization on srv-prod-01",
            "severity": "4",
            "clock": "1700000000"
        }
    ]
    
    with patch.object(service, "_rpc_call", new_callable=AsyncMock) as mock_rpc:
        mock_rpc.return_value = mock_problems_raw
        problems = await service.get_active_problems()
        assert len(problems) == 1
        assert problems[0]["severity_name"] == "High"
        assert problems[0]["severity_color"] == "red"


def test_manifest_zabbix_spec_parsing():
    yaml_content = """
apiVersion: daileon/v1
kind: Component
metadata:
  name: test-service
spec:
  type: service
  zabbix:
    host_name: srv-test-01
    host_group: Production Services
"""
    manifest = DaileonManifest.parse_yaml(yaml_content)
    assert manifest.spec.zabbix is not None
    assert manifest.spec.zabbix.host_name == "srv-test-01"
    assert manifest.spec.zabbix.host_group == "Production Services"
