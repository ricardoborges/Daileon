# 📄 Referência do `project-info.yml`

> **Contrato de metadados que cada repositório mantém junto ao código.** É a partir dele que o Daileon monta o registro do componente no catálogo, os links, as dependências e a origem das TechDocs.

---

## 1. Onde colocar o arquivo

| Item | Valor |
| --- | --- |
| **Nome do arquivo** | `project-info.yml` (exatamente assim — não há fallback para `.yaml` ou outros nomes) |
| **Local** | Raiz do repositório ou em subpastas de **Monorepos** (ex: `apps/strix-web/project-info.yml`, `apps/strix-api/project-info.yml`) |
| **Branch lida** | A `default_branch` do projeto no GitLab (normalmente `main`) |
| **Quando é lido** | A cada sincronização (botão de Sync no portal ou crawler agendado) |

💡 **Suporte a Monorepos:** O Daileon varre recursivamente todo o repositório GitLab. Caso o repositório possua múltiplos arquivos `project-info.yml` em subpastas, cada manifesto gerará um componente independente no catálogo, todos podendo ser agrupados na mesma `solution`!

Se o arquivo **não existir** — ou existir mas **falhar no parse** — o Daileon não quebra: ele cria um **registro sintético** com os dados nativos do GitLab (nome do repositório, descrição, tags do projeto) e marca o componente com `has_manifest = false`. Na interface isso aparece como *"Fallback sintético"* no lugar do selo `project-info.yml`.

---

## 2. Estrutura completa

```yaml
apiVersion: daileon/v1
kind: Component

metadata:
  name: pagamento-service
  description: "Serviço responsável pelo processamento de pagamentos e liquidação PIX."
  tags: [java, spring-boot, pix, finance]
  owner: team-payments
  domain: checkout

spec:
  type: service
  lifecycle: production
  solution: Strix

  docs:
    dir: /docs
    index: index.md

  links:
    - url: https://grafana.empresa.com/d/pagamentos
      title: Grafana Dashboard
      icon: dashboard

  dependencies:
    - component: usuario-service
    - component: notificacao-service

  jenkins:
    pipelines:
      - name: Pipeline de Produção
        environment: production
        job: "deployments/pagamento-prod"
      - name: Testes Automáticos
        environment: test
        job: "ci/pagamento-ci"
```


### 2.1. Mínimo viável

Só existe **um campo obrigatório**: `metadata.name`. Todo o resto tem valor padrão.

```yaml
metadata:
  name: pagamento-service
```

Esse arquivo é válido e produz um componente `Component` / `service` / `production`, dono `unassigned`, docs em `/docs`.

---

## 3. Campos

### 3.1. Raiz

| Campo | Tipo | Obrigatório | Padrão | Observações |
| --- | --- | --- | --- | --- |
| `apiVersion` | string | Não | `daileon/v1` | **Não é validado.** Qualquer string é aceita. Existe por convenção/versionamento futuro. |
| `kind` | string | Não | `Component` | **Conjunto aberto** — veja a seção 5. |
| `metadata` | objeto | **Sim** | — | |
| `spec` | objeto | Não | objeto vazio (tudo default) | |

### 3.2. `metadata`

| Campo | Tipo | Obrigatório | Padrão | Efeito |
| --- | --- | --- | --- | --- |
| `name` | string | **Sim** | — | Nome exibido no catálogo. **Sobrescreve o nome do repositório no GitLab.** |
| `description` | string | Não | descrição do projeto no GitLab | Se omitido ou vazio, cai para a descrição do GitLab. |
| `tags` | lista de strings | Não | `[]` | Vira filtro e entra na busca global. |
| `owner` | string | Não | `unassigned` | Time/pessoa responsável. É filtro no catálogo. |
| `domain` | string | Não | `null` | Agrupamento de negócio. |

### 3.3. `spec`

| Campo | Tipo | Obrigatório | Padrão | Efeito |
| --- | --- | --- | --- | --- |
| `type` | string | Não | `service` | **Conjunto aberto** — veja a seção 5. Alimenta o filtro "Tipo". |
| `lifecycle` | string | Não | `production` | **Conjunto aberto, mas com 3 valores privilegiados** — veja a seção 5. |
| `solution` | string | Não | `null` | Solução à qual o componente pertence (agrupador de projetos). |
| `docs` | objeto | Não | `{dir: /docs, index: index.md}` | Ver 3.4. |
| `links` | lista | Não | `[]` | Ver 3.5. |
| `dependencies` | lista | Não | `[]` | Ver 3.6. |
| `jenkins` | objeto / lista | Não | `null` | Configuração de pipelines do Jenkins. Ver 3.7. |
| `deployments` | lista | Não | `[]` | Lista de ambientes e servidores de instalação. Ver 3.8. |

### 3.4. `spec.docs`

| Campo | Tipo | Padrão | Efeito |
| --- | --- | --- | --- |
| `dir` | string | `/docs` | Pasta varrida recursivamente atrás de documentos. Barras no início/fim são ignoradas — `/docs`, `docs` e `docs/` são equivalentes. Aceita subpastas (`documentacao/tecnica`). |
| `index` | string | `index.md` | Arquivo de entrada da documentação. ⚠️ Ver o alerta abaixo. |

> ⚠️ **Hoje o `index` não é honrado pela interface.** O valor é lido, gravado e exposto na API (`docs_index`), mas o frontend abre sempre `index.md` como página inicial das TechDocs. Se a sua pasta de docs não tiver um `index.md`, o link "Documentação" cairá em página vazia. Até que isso seja ajustado, **mantenha um `index.md`** na raiz do `docs.dir`.

Além da pasta de docs, o **`README.md` da raiz do repositório é sempre indexado**, tenha manifesto ou não.

**Extensões indexadas:** `.md`, `.markdown`, `.pdf` e imagens (`.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.bmp`). Qualquer outra coisa dentro da pasta — `.html`, `.xlsx`, `.txt`, `.css`, `.js`, fontes — é ignorada. `.svg` fica de fora de propósito, por poder carregar script embutido. PDFs e imagens acima de 25 MB são descartados com aviso no log.

> ⚠️ **Uma pasta de docs sem nenhum `.md` some da interface.** Se o `docs.dir` só tem planilha, HTML ou imagem, o componente aparece sem documentação navegável mesmo com o manifesto correto — as imagens ficam indexadas, mas não há página que as apresente. Comece pelo `index.md`.

**Quando a pasta não existe:** o Daileon cai num fallback e varre o repositório inteiro (ou a subpasta do componente, em monorepo) atrás de `.md` e `.pdf`. Imagens **não** entram nesse modo — sem a pasta delimitando o escopo, todo `src/assets/` viraria documentação. Diretórios ocultos (`.git`, `.github`) e de dependência/build (`node_modules`, `dist`, `target`, …) são pulados nos dois modos.

Para excluir uma pasta específica da varredura, veja a seção 4.

### 3.5. `spec.links`

Lista de objetos:

| Campo | Tipo | Obrigatório | Efeito |
| --- | --- | --- | --- |
| `url` | string | **Sim** | Destino do link (abre em nova aba). |
| `title` | string | **Sim** | Texto exibido. |
| `icon` | string | Não | **Aceito e armazenado, mas ainda não usado na renderização.** Todos os links exibem o mesmo ícone de link externo. |

Omitir `url` ou `title` em qualquer item **invalida o manifesto inteiro** e o componente vira sintético.

### 3.6. `spec.dependencies`

Lista de objetos declarando dependências internas ou de projetos externos:

```yaml
spec:
  dependencies:
    - component: BCadastro
    - external: IDEA 2
```

| Campo | Tipo | Obrigatório | Efeito |
| --- | --- | --- | --- |
| `component` | string | Não* | Nome do componente interno catalogado do qual este projeto depende. |
| `external` | string | Não* | Nome do projeto ou sistema externo do qual este depende (exibido em cor destacada no grafo). |

*\* Cada item deve informar `component` ou `external`.*

A dependência é gravada por nome. Quando definida com `external: <nome>`, o Daileon sinaliza o projeto com cor própria (verde/destaque) e forma diferenciada no grafo de dependências.

### 3.7. `spec.jenkins`

Mapeamento de pipelines CI/CD do Jenkins para exibição de status do último build, duração, gatilho, branch e indicador visual de sucesso/falha na aba **Pipelines (Jenkins)** do componente.

Permite dois formatos de escrita no YAML:

#### Formato com objeto e chave `pipelines`:

```yaml
spec:
  jenkins:
    server_url: "https://jenkins.suaempresa.com" # (Opcional) Override da URL base do Jenkins
    pipelines:
      - name: Pipeline de Produção
        environment: production
        job: "deployments/pagamento-prod"
      - name: Testes Automáticos
        environment: test
        job: "ci/pagamento-ci"
```

#### Formato direto com lista:

```yaml
spec:
  jenkins:
    - name: Pipeline de Produção
      environment: production
      job: "deployments/pagamento-prod"
    - name: Testes Automáticos
      environment: test
      job: "ci/pagamento-ci"
```

| Campo | Tipo | Obrigatório | Padrão | Efeito |
| --- | --- | --- | --- | --- |
| `name` | string | **Sim** | — | Nome de exibição da pipeline na UI. |
| `environment` | string | Não | `production` | Ambiente associado (ex: `production`, `staging`, `test`). Define a cor do selo visual. |
| `job` | string | **Sim** | — | Nome ou caminho do job no Jenkins. Pastas são suportadas (ex: `deployments/meu-job`). |
| `server_url` | string | Não | `null` | URL do servidor Jenkins, caso diferente do padrão configurado no `.env`. |

### 3.8. `spec.deployments`

Lista de informações sobre os ambientes de implantação, servidores e infraestrutura onde o projeto está rodando. Permite registrar a URL do ambiente, nome do servidor, IP, Sistema Operacional, modo de execução (VM, Docker, Bare Metal, etc.) e porta do serviço.

> 💡 **Evitando Redundância:** Não é necessário cadastrar as URLs de homologação ou produção na seção `spec.links` — o Daileon agrega automaticamente as URLs de `deployments` na visão geral de links do componente. Use `spec.links` apenas para recursos auxiliares (ex: Grafana Dashboard, Specs OpenAPI, Jira).

```yaml
spec:
  deployments:
    - environment: production
      url: https://pagamento.empresa.com
      server_name: srv-prod-app01
      server_ip: 10.0.1.50
      os: "Linux Ubuntu 22.04 LTS"
      execution_type: Docker
      port: 8080
      notes: Cluster Kubernetes principal
    - environment: homologação
      url: https://homolog-pagamento.empresa.com
      server_name: Arya
      server_ip: 10.43.210.55
      os: "Windows Server 2022"
      execution_type: VM
      port: 8080
      notes: Ambiente de homologação
```

| Campo | Tipo | Obrigatório | Padrão | Efeito |
| --- | --- | --- | --- | --- |
| `environment` | string | Não | `production` | Nome do ambiente (ex: `production`, `homologation`, `staging`, `test`, `dev`). |
| `url` | string | Não | `null` | URL pública ou interna de acesso ao ambiente. |
| `server_name` | string | Não | `null` | Nome do servidor ou host. Agrupado no catálogo global de Servidores. |
| `server_ip` | string | Não | `null` | Endereço IP do servidor. |
| `os` | string | Não | `null` | Sistema Operacional e versão (ex: `Linux Ubuntu 22.04 LTS`, `Windows Server 2022`). |
| `execution_type` | string | Não | `null` | Modo de execução do serviço (ex: `VM`, `Docker`, `Bare Metal`, `Kubernetes`). |
| `port` | número / string | Não | `null` | Porta em que o serviço escuta (ex: `8080`, `5173`, `443`). |
| `notes` | string | Não | `null` | Observações adicionais sobre o ambiente ou infraestrutura. |


---

## 4. Excluindo pastas da indexação: `.daileon-ignore`

O manifesto diz onde o Daileon **deve** olhar. O `.daileon-ignore` diz onde ele **não** deve.

| Item | Valor |
| --- | --- |
| **Nome do arquivo** | `.daileon-ignore` |
| **Local** | Dentro de qualquer pasta que você queira excluir |
| **Conteúdo** | **Irrelevante.** O arquivo nunca é lido — pode ficar vazio ou explicar o motivo para quem vier depois |
| **Escopo** | A pasta que o contém **e tudo abaixo dela**, recursivamente |
| **Efeito** | Nada ali dentro é indexado como documentação, nem gera componente a partir de um `project-info.yml` |

O caso mais comum é uma pasta de docs que carrega peso morto — protótipo HTML com imagens, anexos de outra época:

```
docs/
├── index.md
├── arquitetura.md
└── Prototipo/
    ├── .daileon-ignore        ← só isso
    ├── index.html
    └── images/logo.png
```

Resultado: as TechDocs mostram `index.md` e `arquitetura.md`; `Prototipo/` some do portal e continua no repositório.

Em monorepo, o marcador também tira um subprojeto inteiro do catálogo:

```
apps/
├── novo/project-info.yml      → vira componente
└── legado/
    ├── .daileon-ignore        → não vira componente
    └── project-info.yml
```

> ⚠️ **Um `.daileon-ignore` na raiz do repositório remove o projeto do catálogo.** É consistente com a regra — o escopo é a pasta que o contém, e na raiz isso é tudo — mas o efeito é grande e silencioso: no próximo sync o componente e a documentação dele desaparecem do portal. Use quando for exatamente essa a intenção; para excluir só a documentação, marque a pasta de docs.

Cada exclusão é registrada no log do backend em nível `INFO`, então um marcador esquecido não vira um sumiço inexplicado:

```
Ignoring manifest under .daileon-ignore: apps/legado/project-info.yml
Skipping docs of project 5: 'docs/Prototipo' is marked with .daileon-ignore.
Project Strix has .daileon-ignore at the repository root; nothing will be indexed.
```

**Marcar a pasta de docs não aciona o fallback.** Uma pasta que não existe faz o Daileon varrer o repositório atrás de documentação (ver 3.4); uma pasta marcada, não — é ausência deliberada, e varrer em volta contrariaria o pedido. O `README.md` da raiz continua sendo indexado nesse caso; para excluí-lo também, o marcador precisa estar na raiz.

---

## 5. Os conjuntos de valores: abertos ou fechados?

Esta é a resposta curta: **todos os campos de classificação (`kind`, `type`, `lifecycle`, `apiVersion`) são strings livres.** Não existe enum, `Literal` ou validação de domínio no parser — o que você escrever é aceito e gravado como veio.

O que muda entre eles é **o quanto o resto do sistema reconhece o valor**:

### `kind` — totalmente aberto, convenção `Component` / `API` / `Library`

| | |
| --- | --- |
| Validação | Nenhuma |
| Padrão | `Component` |
| Convenção do projeto | `Component`, `API`, `Library` |
| Uso atual | Apenas armazenado. **Não é exibido, filtrado nem usado em nenhuma tela hoje.** |

Ou seja: hoje `kind` é praticamente decorativo. Fica reservado para quando o catálogo passar a separar APIs e bibliotecas em visões próprias. **Recomendação:** fique nos três valores da convenção para não gerar dívida quando esse filtro existir.

### `type` — aberto, com efeito real de filtro

| | |
| --- | --- |
| Validação | Nenhuma |
| Padrão | `service` (quando o manifesto existe e omite o campo) |
| Convenção do projeto | `service`, `website`, `library`, `cronjob` |
| Uso atual | Exibido como chip no card e na página do componente; alimenta o filtro **"Tipo"** do catálogo e o contador "Serviços" na home. |

O filtro é montado **dinamicamente a partir dos valores presentes no catálogo** — então um `type: lambda` novo simplesmente aparece como mais uma opção no dropdown. Isso é flexível, mas significa que erros de digitação viram categorias fantasma (`servcie` vira um filtro próprio). Padronize dentro do time.

⚠️ **Componentes sintéticos recebem `type: unknown`, não `service`.** O padrão `service` só vale para manifestos que existem e omitem o campo. Repositórios sem `project-info.yml` entram como `unknown` justamente para não inflar o contador de serviços com projetos que nunca se declararam. Se um componente seu aparece como `unknown`, o caminho é declarar o `type` no manifesto.

### `lifecycle` — aberto, mas só 3 valores ganham tratamento visual

| | |
| --- | --- |
| Validação | Nenhuma |
| Padrão | `production` |
| Valores reconhecidos | `production`, `experimental`, `deprecated` (comparação *case-insensitive*) |
| Uso atual | Chip colorido + LED de status; filtro **"Lifecycle"**; contador "Em produção" na home. |

Aqui a diferença importa de verdade:

| Valor | Rótulo exibido | Cor |
| --- | --- | --- |
| `production` | Produção | verde (ok) |
| `experimental` | Experimental | âmbar (crest) |
| `deprecated` | Depreciado | vermelho (alert) |
| *qualquer outro* | o texto cru, sem tradução | **sem cor, sem LED** |

Um `lifecycle: homologacao` funciona e é filtrável, mas aparece apagado, sem indicador de status. **Fique nos três valores** salvo necessidade real.

### `apiVersion` — aberto e sem uso

Nenhuma verificação de compatibilidade é feita. Escrever `apiVersion: sei-la/v9` não gera erro nem aviso. Mantenha `daileon/v1`.

---

## 6. Comportamentos que costumam surpreender

1. **Campos desconhecidos são silenciosamente ignorados.** Escrever `ownr:` em vez de `owner:` não gera erro — o campo errado é descartado e o `owner` fica `unassigned`. Não há aviso na interface; confira o resultado no catálogo após o sync.
2. **`metadata.name` sobrescreve o nome do repositório.** O card do catálogo mostra o nome do manifesto, não o do GitLab.
3. **Tags do GitLab só são usadas quando não há manifesto.** Se o `project-info.yml` existir com `tags` vazio, o componente fica **sem tags** — as tags nativas do projeto no GitLab são ignoradas. É tudo ou nada.
4. **Links e dependências são recriados a cada sync.** O que sumiu do arquivo some do portal; não há acúmulo histórico.
5. **Manifesto inválido = componente sintético, sem alarde.** O erro vai para o log do backend (`Could not parse project-info.yml in project <nome>`) e o componente aparece marcado como "Fallback sintético". Se um componente aparecer sem os metadados esperados, esse é o primeiro lugar a olhar.
6. **Nem todo anexo do `docs.dir` é indexado.** Só `.md`, `.markdown`, `.pdf` e imagens entram — planilhas, HTML e `.txt` são descartados em silêncio. Uma pasta de docs cheia, mas sem nenhum `.md`, resulta em componente sem documentação visível. Ver 3.4.
7. **`.daileon-ignore` na raiz apaga o componente do catálogo.** O marcador exclui a pasta que o contém — na raiz, isso é o repositório inteiro, e no próximo sync o projeto some do portal. Ver 4.

---

## 7. Limites de tamanho

O banco define limites por coluna. Em SQLite (padrão de desenvolvimento) eles **não são aplicados**; em PostgreSQL, um valor acima do limite **falha a sincronização daquele componente**. Vale respeitá-los desde já:

| Campo | Limite |
| --- | --- |
| `metadata.name` | 100 caracteres |
| `metadata.description` | sem limite (texto livre) |
| cada item de `metadata.tags` | 50 |
| `metadata.owner` | 100 |
| `metadata.domain` | 100 |
| `kind`, `type`, `lifecycle` | 50 cada |
| `spec.solution` | 100 |
| `spec.docs.dir`, `spec.docs.index` | 100 cada |
| `links[].title` | 100 |
| `links[].url` | 500 |
| `links[].icon` | 50 |
| `dependencies[].component` | 100 |
| `jenkins.pipelines[].name` | 100 |
| `jenkins.pipelines[].environment` | 50 |
| `jenkins.pipelines[].job` | 300 |
| `jenkins.pipelines[].server_url` | 500 |

---

## 8. Exemplos

### 8.1. Microsserviço com documentação, observabilidade e CI/CD Jenkins

```yaml
apiVersion: daileon/v1
kind: Component

metadata:
  name: pagamento-service
  description: "Processamento de pagamentos e liquidação PIX."
  tags: [java, spring-boot, pix, finance]
  owner: team-payments
  domain: checkout

spec:
  type: service
  lifecycle: production
  solution: Strix

  docs:
    dir: /docs
    index: index.md

  links:
    - url: https://grafana.empresa.com/d/pagamentos
      title: Grafana Dashboard
      icon: dashboard
    - url: https://api-docs.empresa.com/pagamento-service
      title: OpenAPI Spec
      icon: api

  dependencies:
    - component: usuario-service
    - component: notificacao-service

  jenkins:
    pipelines:
      - name: Pipeline de Produção
        environment: production
        job: "deployments/pagamento-prod"
      - name: Pipeline de Homologação
        environment: staging
        job: "deployments/pagamento-staging"
      - name: Testes Automáticos (CI)
        environment: test
        job: "ci/pagamento-ci"
```


### 8.2. Biblioteca compartilhada, docs fora do padrão

```yaml
apiVersion: daileon/v1
kind: Library

metadata:
  name: commons-logging-br
  description: "Padronização de logs estruturados para os serviços Java."
  tags: [java, observabilidade, biblioteca]
  owner: team-platform-engineering
  domain: internal-tooling

spec:
  type: library
  lifecycle: experimental
  docs:
    dir: documentacao/tecnica
    index: index.md
```

### 8.3. Componente em descontinuação

```yaml
metadata:
  name: relatorio-legado
  description: "Gerador de relatórios em lote. Substituído por relatorio-service."
  owner: team-data

spec:
  type: cronjob
  lifecycle: deprecated
  dependencies:
    - component: relatorio-service
```

---

## 9. Checklist antes de commitar

- [ ] Arquivo se chama `project-info.yml` e está na raiz do repositório.
- [ ] `metadata.name` preenchido e único no catálogo.
- [ ] `owner` aponta para um time real (evite deixar `unassigned`).
- [ ] `lifecycle` é `production`, `experimental` ou `deprecated`.
- [ ] `type` segue a convenção do time (`service`, `website`, `library`, `cronjob`, …).
- [ ] Existe um `index.md` na raiz da pasta indicada em `docs.dir`.
- [ ] Se há `.daileon-ignore` no repositório, ele está na pasta certa — e **não** na raiz, salvo se a intenção for tirar o projeto do catálogo.
- [ ] Todo item de `links` tem `url` **e** `title`.
- [ ] YAML válido — rode um lint ou cole em um validador antes de commitar.
- [ ] Após o merge, rode o Sync no portal e confira se o componente aparece com o selo `project-info.yml` (e não como "Fallback sintético").

---

## 10. Referência do schema no código

| O que | Onde |
| --- | --- |
| Modelo Pydantic do manifesto | [`backend/app/catalog/manifest.py`](../backend/app/catalog/manifest.py) |
| Leitura do arquivo e mapeamento para o banco | [`backend/app/gitlab/gitlab_crawler.py`](../backend/app/gitlab/gitlab_crawler.py) |
| Tabelas e limites de coluna | [`backend/app/db/models.py`](../backend/app/db/models.py) |

Ver também: [Arquitetura](arquitetura.md) · [Implantação](implantacao.md)
