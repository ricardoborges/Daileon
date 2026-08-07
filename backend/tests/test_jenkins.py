import pytest
from app.catalog.manifest import DaileonManifest, ManifestSpec, ManifestJenkinsPipeline
from app.plugins.jenkins.service import format_jenkins_job_url, fetch_jenkins_job_status, get_jenkins_candidate_api_urls, normalize_jenkins_url

def test_jenkins_url_candidate_generation():
    base = "https://jenkins.csi.mpba.mp.br"
    
    # Test User Job input: "Strix/job/Strix%20master%20branch"
    candidates = get_jenkins_candidate_api_urls(base, "Strix/job/Strix%20master%20branch")
    api_urls = [c[0] for c in candidates]
    
    assert "https://jenkins.csi.mpba.mp.br/job/Strix/job/Strix master branch/lastBuild/api/json" in api_urls
    assert "https://jenkins.csi.mpba.mp.br/view/Strix/job/Strix master branch/lastBuild/api/json" in api_urls
    assert "https://jenkins.csi.mpba.mp.br/job/Strix master branch/lastBuild/api/json" in api_urls

def test_normalize_jenkins_url():
    base_env_url = "https://jenkins.company.com"
    internal_build_url = "http://jenkins-internal:8080/job/Strix/job/Strix%20master%20branch/2025/"
    
    normalized = normalize_jenkins_url(internal_build_url, base_env_url)
    assert normalized == "https://jenkins.company.com/job/Strix/job/Strix%20master%20branch/2025/"

    # Test relative path
    rel_normalized = normalize_jenkins_url("job/Strix/2025", base_env_url)
    assert rel_normalized == "https://jenkins.company.com/job/Strix/2025"

def test_jenkins_url_formatting():
    base = "https://jenkins.company.com"
    
    url1 = format_jenkins_job_url(base, "simple-job")
    assert url1.startswith("https://jenkins.company.com/")
    assert "simple-job" in url1


def test_manifest_jenkins_parsing():
    yaml_content = """
apiVersion: daileon/v1
kind: Component
metadata:
  name: test-component
spec:
  type: service
  jenkins:
    pipelines:
      - name: Pipeline de Produção
        environment: production
        job: "deployments/prod-job"
      - name: Pipeline de Teste
        environment: test
        job: "ci/test-job"
"""
    manifest = DaileonManifest.parse_yaml(yaml_content)
    pipelines = manifest.spec.get_jenkins_pipelines()
    assert len(pipelines) == 2
    assert pipelines[0].name == "Pipeline de Produção"
    assert pipelines[0].environment == "production"
    assert pipelines[0].job == "deployments/prod-job"

def test_manifest_jenkins_list_format_parsing():
    yaml_content = """
apiVersion: daileon/v1
kind: Component
metadata:
  name: test-component
spec:
  type: service
  jenkins:
    - name: Prod Direct
      environment: production
      job: "prod-job"
"""
    manifest = DaileonManifest.parse_yaml(yaml_content)
    pipelines = manifest.spec.get_jenkins_pipelines()
    assert len(pipelines) == 1
    assert pipelines[0].name == "Prod Direct"
    assert pipelines[0].job == "prod-job"

@pytest.mark.anyio
async def test_fetch_jenkins_status_not_configured(monkeypatch):

    from app.core.config import settings
    monkeypatch.setattr(settings, "JENKINS_USER", "")
    monkeypatch.setattr(settings, "JENKINS_API_TOKEN", "")

    res = await fetch_jenkins_job_status("some-job")
    assert res["status"] == "NOT_CONFIGURED"
    assert res["configured"] is False
