Portal de desenvolvedores para catalogação de componentes.



#### 1. Integração com GitLab
Usado para sincronização de repositórios e projetos no catálogo.

| Variável | Descrição | Valor Padrão | Obrigatório? |
| :--- | :--- | :--- | :--- |
| `GITLAB_URL` | URL da instância do GitLab. | `https://gitlab.com` | Não |
| `GITLAB_READ_TOKEN` | Personal Access Token (PAT) com escopo de leitura (`read_api` / `read_repository`). Também aceita `GITLAB_TOKEN`. | `""` | Sim (para sincronizar com GitLab) |
| `GITLAB_GROUP_ID` | ID ou caminho do grupo/organização no GitLab cujos projetos serão importados. | `""` | Recomendado |

#### 2. Integração com Jenkins
Usado para consulta de status de pipelines CI/CD.

| Variável | Descrição | Valor Padrão | Obrigatório? |
| :--- | :--- | :--- | :--- |
| `JENKINS_URL` | URL da instância do Jenkins. | `https://jenkins.example.com` | Não |
| `JENKINS_USER` | Nome do usuário para autenticação na API do Jenkins. | `""` | Sim (se Jenkins estiver configurado) |
| `JENKINS_API_TOKEN` | Token de API do usuário do Jenkins. | `""` | Sim (se Jenkins estiver configurado) |

#### 3. Banco de Dados
| Variável | Descrição | Valor Padrão | Obrigatório? |
| :--- | :--- | :--- | :--- |
| `DATABASE_URL` | String de conexão SQLAlchemy. | `sqlite+aiosqlite:///./data/daileon.db` | Não |

#### 4. Autenticação e Segurança Local (Break-Glass)
Credenciais do administrador local e chave para assinatura de tokens JWT.

| Variável | Descrição | Valor Padrão | Obrigatório? |
| :--- | :--- | :--- | :--- |
| `ADMIN_USERNAME` | Usuário da conta de administração local. | `admin` | Não |
| `ADMIN_PASSWORD` | Senha da conta de administração local. | `admin123` | **Sim (alterar em produção)** |
| `SECRET_KEY` | Chave secreta para geração e validação dos JWTs. | `daileon-breakglass-secret-key-change-in-prod` | **Sim (alterar em produção)** |

#### 5. Autenticação LDAP / Active Directory
Configurações para integração com servidor LDAP corporativo.

| Variável | Descrição | Valor Padrão | Obrigatório? |
| :--- | :--- | :--- | :--- |
| `LDAP_ENABLED` | Habilita autenticação via LDAP (`true` ou `false`). | `false` | Não |
| `LDAP_SERVER_HOST` | Host ou IP do servidor LDAP. | `""` | Sim (se `LDAP_ENABLED=true`) |
| `LDAP_SERVER_PORT` | Porta de conexão do servidor LDAP. | `389` | Não |
| `LDAP_USE_SSL` | Habilita conexão SSL (`true` ou `false`). | `false` | Não |
| `LDAP_BIND_DN` | DN da conta de serviço usada para efetuar buscas no LDAP. | `""` | Sim (se LDAP exigir autenticação) |
| `LDAP_BIND_PASSWORD` | Senha da conta de serviço para o bind LDAP. | `""` | Sim (se LDAP exigir autenticação) |
| `LDAP_BASE_DN` | Base DN onde os usuários serão pesquisados (ex: `ou=users,dc=empresa,dc=com`). | `""` | Sim (se `LDAP_ENABLED=true`) |
| `LDAP_USER_ATTRIBUTE` | Atributo LDAP referente ao login do usuário (ex: `uid`, `sAMAccountName`). | `uid` | Não |

#### 6. Organização
| Variável | Descrição | Valor Padrão | Obrigatório? |
| :--- | :--- | :--- | :--- |
| `ORGANIZATION_NAME` | Nome da organização exibido na interface. Também aceita `ORG_NAME`. | `""` | Não |
| `ORGANIZATION_ACRONYM` | Sigla da organização. Também aceita `ORG_ACRONYM`. | `""` | Não |

---

## Como Executar

### Via Docker Compose (Recomendado)

Suba o backend e o frontend simultaneamente:

```bash
docker compose up -d --build
```

- **Frontend:** `http://localhost:5173`
- **Backend API:** `http://localhost:8000`
- **Documentação Swagger:** `http://localhost:8000/docs`

### Execução Manual para Desenvolvimento

#### Backend
```bash
cd backend
python -m venv .venv
# No Linux/macOS: source .venv/bin/activate
# No Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

#### Frontend
```bash
cd frontend
npm install
npm run dev
```