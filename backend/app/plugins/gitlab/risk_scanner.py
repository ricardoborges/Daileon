import re
import json
import xml.etree.ElementTree as ET
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

EXACT_PLACEHOLDERS = {"PASSWORD", "SECRET", "PASSPHRASE", "TOKEN", "YOUR_PASSWORD", "YOUR_SECRET", "MY_PASSWORD", "CHANGE_ME", "XXXX", "TODOME"}
SUBSTRING_PLACEHOLDERS = ("#{", "${", "{{", "<")

def is_placeholder(val: str) -> bool:
    if not val:
        return True
    val_upper = val.upper().strip()
    if val_upper in EXACT_PLACEHOLDERS:
        return True
    if any(p in val_upper for p in SUBSTRING_PLACEHOLDERS):
        return True
    if val_upper.startswith("YOUR_") or val_upper.startswith("MY_"):
        return True
    if len(val_upper) < 2:
        return True
    return False

class RiskFinding:
    def __init__(
        self,
        severity: str,
        category: str,
        title: str,
        description: str,
        recommendation: str,
        file_path: Optional[str] = None
    ):
        self.severity = severity
        self.category = category
        self.title = title
        self.description = description
        self.recommendation = recommendation
        self.file_path = file_path

    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "recommendation": self.recommendation,
            "file_path": self.file_path,
        }


def scan_repository_tree(tree: List[Dict[str, Any]]) -> List[RiskFinding]:
    """Escaneia a lista de caminhos de arquivos do repositório."""
    findings: List[RiskFinding] = []
    has_gitignore = False
    
    paths = [item.get("path", "") for item in tree if item.get("type") == "blob" or item.get("mode") == "040000"]
    
    for path in paths:
        path_lower = path.lower().strip()
        filename = path_lower.split("/")[-1]

        if filename == ".gitignore":
            has_gitignore = True
            continue

        if filename.startswith(".env"):
            is_example = any(ext in filename for ext in [".example", ".sample", ".template", ".dist", ".mock"])
            if not is_example:
                findings.append(RiskFinding(
                    severity="critical",
                    category="versioned_secret",
                    title="Arquivo de variáveis de ambiente (.env) versionado",
                    description=f"O arquivo '{path}' foi encontrado no repositório. Arquivos .env contêm segredos e credenciais reais de ambiente e nunca devem ser enviados ao Git.",
                    recommendation=f"Remova o arquivo do repositório executando 'git rm --cached {path}', adicione '{filename}' ao .gitignore e utilize variáveis de ambiente no servidor.",
                    file_path=path
                ))

        if any(filename.endswith(ext) for ext in [".pem", ".key", ".pfx", ".p12", ".asc"]) or filename in ["id_rsa", "id_ed25519", "id_ecdsa"]:
            if not filename.endswith(".pub"):
                findings.append(RiskFinding(
                    severity="critical",
                    category="versioned_secret",
                    title="Chave privada ou certificado SSL/TLS versionado",
                    description=f"O arquivo de chave ou certificado '{path}' foi encontrado no repositório.",
                    recommendation=f"Remova o arquivo '{path}' do repositório imediatamente, revogue/rotacione a chave afetada e armazene certificados em um cofre de segredos.",
                    file_path=path
                ))

        if filename == "secrets.json":
            findings.append(RiskFinding(
                severity="critical",
                category="versioned_secret",
                title="Arquivo User Secrets (.NET) versionado",
                description=f"O arquivo 'secrets.json' do .NET foi encontrado em '{path}'.",
                recommendation="O recurso User Secrets do .NET deve existir apenas localmente na máquina do desenvolvedor (%APPDATA%\\Microsoft\\UserSecrets\\ ou ~/.microsoft/usersecrets/). Remova o arquivo do repositório.",
                file_path=path
            ))

        if filename in ["gcp-key.json", "service-account.json", "credentials.json"] or path_lower.endswith(".aws/credentials") or filename == "kubeconfig" or path_lower.endswith(".kube/config"):
            findings.append(RiskFinding(
                severity="critical",
                category="cloud_credentials",
                title="Arquivo de credenciais de Cloud/Infraestrutura versionado",
                description=f"O arquivo de credenciais de nuvem '{path}' foi encontrado no repositório.",
                recommendation=f"Revogue as credenciais contidas em '{path}' imediatamente no console da Cloud e remova o arquivo do Git.",
                file_path=path
            ))

        if filename == "local_settings.py":
            findings.append(RiskFinding(
                severity="warning",
                category="versioned_secret",
                title="Arquivo local_settings.py (Python/Django) versionado",
                description=f"O arquivo '{path}' costuma conter senhas e SECRET_KEY locais e foi commitado no repositório.",
                recommendation="Adicione 'local_settings.py' ao .gitignore e utilize um arquivo de exemplo (local_settings.py.example).",
                file_path=path
            ))

        parts = path_lower.split("/")
        if any(part in ["venv", ".venv", "env", ".env_dir"] for part in parts[:-1]):
            if not any(f.file_path and ("/" + part + "/" in "/" + f.file_path.lower() + "/" or f.file_path.lower().startswith(part + "/")) for f in findings if f.title.startswith("Ambiente virtual Python")):
                venv_dir = next(part for part in parts if part in ["venv", ".venv", "env", ".env_dir"])
                findings.append(RiskFinding(
                    severity="warning",
                    category="unignored_env",
                    title="Ambiente virtual Python (venv) versionado",
                    description=f"A pasta de ambiente virtual '{venv_dir}' foi commitada no repositório.",
                    recommendation=f"Adicione '{venv_dir}/' ao .gitignore e remova o diretório do Git para evitar poluir o repositório com arquivos binários.",
                    file_path=path
                ))

    if not has_gitignore and len(paths) > 0:
        findings.append(RiskFinding(
            severity="warning",
            category="unignored_env",
            title="Arquivo .gitignore ausente",
            description="O repositório não possui um arquivo .gitignore na raiz.",
            recommendation="Crie um arquivo .gitignore adequado para as tecnologias utilizadas no projeto (.NET, Node.js, Python, etc.).",
            file_path=".gitignore"
        ))

    return findings


def scan_file_content(path: str, content: str) -> List[RiskFinding]:
    findings: List[RiskFinding] = []
    if not content:
        return findings

    path_lower = path.lower().strip()
    filename = path_lower.split("/")[-1]

    if filename.startswith("appsettings") and filename.endswith(".json"):
        try:
            data = json.loads(content)
            _scan_appsettings_json(path, data, findings)
        except Exception as e:
            logger.debug(f"Não foi possível fazer parse de JSON em {path}: {e}")

    elif filename in ["web.config", "app.config"] or filename.endswith(".config"):
        try:
            _scan_dotnet_config_xml(path, content, findings)
        except Exception as e:
            logger.debug(f"Não foi possível fazer parse de XML em {path}: {e}")

    elif "config/" in path_lower and filename.endswith(".json"):
        try:
            data = json.loads(content)
            _scan_node_config_json(path, data, findings)
        except Exception as e:
            logger.debug(f"Não foi possível fazer parse de JSON em Node config {path}: {e}")

    elif filename in ["local_settings.py", "settings.py", "config.py"]:
        _scan_python_settings(path, content, findings)

    return findings


def _scan_appsettings_json(path: str, data: Any, findings: List[RiskFinding], current_prefix: str = ""):
    if isinstance(data, dict):
        for key, value in data.items():
            full_key = f"{current_prefix}:{key}" if current_prefix else key
            key_lower = key.lower()
            
            if key_lower == "connectionstrings" and isinstance(value, dict):
                for conn_name, conn_str in value.items():
                    if isinstance(conn_str, str) and ("password=" in conn_str.lower() or "pwd=" in conn_str.lower()):
                        match = re.search(r'(?:password|pwd)\s*=\s*([^;]+)', conn_str, re.IGNORECASE)
                        if match:
                            pwd_val = match.group(1).strip()
                            if not is_placeholder(pwd_val):
                                findings.append(RiskFinding(
                                    severity="critical",
                                    category="hardcoded_connection_string",
                                    title=f"String de conexão com senha hardcoded em appsettings",
                                    description=f"A conexão '{conn_name}' no arquivo '{path}' contém credenciais de banco de dados em texto plano.",
                                    recommendation=f"Substitua a senha em '{conn_name}' por substituição por variável de ambiente (ex: ConnectionStrings__{conn_name} no .NET).",
                                    file_path=path
                                ))

            elif any(k in key_lower for k in ["secret", "password", "pwd", "apikey", "api_key", "token", "privatekey", "clientsecret"]) and isinstance(value, str):
                if not is_placeholder(value):
                    findings.append(RiskFinding(
                        severity="critical",
                        category="versioned_secret",
                        title=f"Secret/Token hardcoded em appsettings ({full_key})",
                        description=f"A chave '{full_key}' no arquivo '{path}' possui um valor de segredo em texto plano.",
                        recommendation=f"Remova o valor fixo da chave '{full_key}' e utilize variáveis de ambiente ou Secret Manager em produção.",
                        file_path=path
                    ))

            elif isinstance(value, (dict, list)):
                _scan_appsettings_json(path, value, findings, full_key)

    elif isinstance(data, list):
        for item in data:
            _scan_appsettings_json(path, item, findings, current_prefix)


def _scan_dotnet_config_xml(path: str, content: str, findings: List[RiskFinding]):
    root = ET.fromstring(content)
    
    for conn in root.findall(".//connectionStrings/add"):
        conn_str = conn.attrib.get("connectionString", "")
        conn_name = conn.attrib.get("name", "DefaultConnection")
        if ("password=" in conn_str.lower() or "pwd=" in conn_str.lower()):
            match = re.search(r'(?:password|pwd)\s*=\s*([^;]+)', conn_str, re.IGNORECASE)
            if match:
                pwd_val = match.group(1).strip()
                if not is_placeholder(pwd_val):
                    findings.append(RiskFinding(
                        severity="critical",
                        category="hardcoded_connection_string",
                        title="String de conexão com senha hardcoded em Web.config/App.config",
                        description=f"A string de conexão '{conn_name}' no arquivo '{path}' contém senha de banco de dados em texto claro.",
                        recommendation=f"Utilize autenticação integrada (Integrated Security=True) ou recupere a string de conexão via variáveis de ambiente/Vault.",
                        file_path=path
                    ))

    for setting in root.findall(".//appSettings/add"):
        key = setting.attrib.get("key", "")
        val = setting.attrib.get("value", "")
        key_lower = key.lower()
        if any(k in key_lower for k in ["password", "secret", "apikey", "privatekey", "token"]):
            if not is_placeholder(val):
                findings.append(RiskFinding(
                    severity="critical",
                    category="versioned_secret",
                    title=f"Segredo hardcoded em appSettings no Web.config ({key})",
                    description=f"A chave '{key}' em appSettings no arquivo '{path}' contém um valor sensível configurado de forma estática.",
                    recommendation=f"Remova o valor estático de '{key}' do repositório e configure via ConfigurationManager/EnvironmentVariables.",
                    file_path=path
                ))


def _scan_node_config_json(path: str, data: Any, findings: List[RiskFinding]):
    if isinstance(data, dict):
        for key, value in data.items():
            key_lower = key.lower()
            if any(k in key_lower for k in ["secret", "password", "pwd", "apikey", "api_key", "token", "privatekey", "clientsecret"]) and isinstance(value, str):
                if not is_placeholder(value):
                    findings.append(RiskFinding(
                        severity="critical",
                        category="versioned_secret",
                        title=f"Secret hardcoded em arquivo de configuração Node.js ({key})",
                        description=f"O arquivo '{path}' possui a propriedade '{key}' com um valor de segredo hardcoded.",
                        recommendation=f"Utilize 'process.env.{key.upper()}' para injetar o valor dinamicamente em runtime.",
                        file_path=path
                    ))
            elif isinstance(value, dict):
                _scan_node_config_json(path, value, findings)


def _scan_python_settings(path: str, content: str, findings: List[RiskFinding]):
    patterns = [
        (r'SECRET_KEY\s*=\s*[\'"]([^\'"]+)[\'"]', "SECRET_KEY de produto/projeto hardcoded em Python"),
        (r'(?:DB_PASSWORD|DATABASE_PASSWORD|POSTGRES_PASSWORD|MYSQL_PASSWORD)\s*=\s*[\'"]([^\'"]+)[\'"]', "Senha de banco de dados hardcoded em Python"),
    ]
    for pattern, title in patterns:
        matches = re.finditer(pattern, content, re.IGNORECASE)
        for match in matches:
            val = match.group(1)
            if not is_placeholder(val):
                findings.append(RiskFinding(
                    severity="critical",
                    category="versioned_secret",
                    title=title,
                    description=f"O arquivo '{path}' possui uma atribuição estática de credencial/segredo.",
                    recommendation="Utilize 'os.environ.get(...)' ou a biblioteca 'python-dotenv' em conjunto com um arquivo .env não-versionado.",
                    file_path=path
                ))
