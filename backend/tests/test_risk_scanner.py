import pytest
from app.gitlab.risk_scanner import scan_repository_tree, scan_file_content

def test_scan_repository_tree_detects_versioned_env():
    tree = [
        {"path": ".gitignore", "type": "blob"},
        {"path": "backend/.env", "type": "blob"},
        {"path": "frontend/.env.local", "type": "blob"},
        {"path": "frontend/.env.example", "type": "blob"}, # Deve ignorar .example
    ]
    findings = scan_repository_tree(tree)
    
    env_findings = [f for f in findings if f.category == "versioned_secret" and ".env" in f.title]
    assert len(env_findings) == 2
    paths = [f.file_path for f in env_findings]
    assert "backend/.env" in paths
    assert "frontend/.env.local" in paths
    assert "frontend/.env.example" not in paths


def test_scan_repository_tree_detects_keys_and_secrets():
    tree = [
        {"path": ".gitignore", "type": "blob"},
        {"path": "certs/server.pem", "type": "blob"},
        {"path": "src/secrets.json", "type": "blob"},
        {"path": "gcp-key.json", "type": "blob"},
        {"path": "venv/bin/python", "type": "blob"},
    ]
    findings = scan_repository_tree(tree)
    
    titles = [f.title for f in findings]
    assert any("Chave privada" in t for t in titles)
    assert any("User Secrets" in t for t in titles)
    assert any("Cloud/Infraestrutura" in t for t in titles)
    assert any("venv" in t for t in titles)


def test_scan_appsettings_json_detects_hardcoded_passwords():
    content = """
    {
      "ConnectionStrings": {
        "DefaultConnection": "Server=myServerAddress;Database=myDataBase;User Id=myUsername;Password=SuperSecretPass123!;"
      },
      "Jwt": {
        "Secret": "VeryLongSecretKeyForJwtTokenGeneration999!"
      },
      "Logging": {
        "LogLevel": {
          "Default": "Information"
        }
      }
    }
    """
    findings = scan_file_content("backend/appsettings.json", content)
    
    assert len(findings) == 2
    categories = [f.category for f in findings]
    assert "hardcoded_connection_string" in categories
    assert "versioned_secret" in categories


def test_scan_dotnet_web_config_detects_xml_passwords():
    content = """<?xml version="1.0" encoding="utf-8"?>
    <configuration>
      <connectionStrings>
        <add name="SqlConn" connectionString="Data Source=sql.corp;Initial Catalog=DB;User ID=admin;Password=MyRealPassword123" />
      </connectionStrings>
      <appSettings>
        <add key="SmtpPassword" value="SecretMailPassword" />
        <add key="PlaceholderKey" value="#{SMTP_PASS}#" />
      </appSettings>
    </configuration>
    """
    findings = scan_file_content("Web.config", content)
    
    assert len(findings) == 2
    titles = [f.title for f in findings]
    assert any("Web.config/App.config" in t for t in titles)
    assert any("SmtpPassword" in t for t in titles)
