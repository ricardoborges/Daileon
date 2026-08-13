# 📄 `project-info.yml` Reference

> **The metadata contract each repository keeps next to its code.** It is what Daileon uses to build the component record in the catalog, the links, the dependencies and the source of the TechDocs.

---

## 1. Where to place the file

| Item | Value |
| --- | --- |
| **File name** | `project-info.yml` (exactly that — there is no fallback to `.yaml` or any other name) |
| **Location** | Repository root or in subfolders of **monorepos** (e.g. `apps/strix-web/project-info.yml`, `apps/strix-api/project-info.yml`) |
| **Branch read** | The project's `default_branch` in GitLab (usually `main`) |
| **When it is read** | On every synchronization (Sync button in the portal or scheduled crawler) |

💡 **Monorepo support:** Daileon scans the whole GitLab repository recursively. If the repository holds multiple `project-info.yml` files in subfolders, each manifest produces an independent component in the catalog — and all of them can be grouped under the same `solution`!

If the file **does not exist** — or exists but **fails to parse** — Daileon does not break: it creates a **synthetic record** with GitLab's native data (repository name, description, project tags) and marks the component with `has_manifest = false`. In the interface this shows up as *"Synthetic fallback"* instead of the `project-info.yml` badge.

---

## 2. Full structure

```yaml
apiVersion: daileon/v1
kind: Component

metadata:
  name: payment-service
  description: "Service responsible for payment processing and PIX settlement."
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
    - url: https://grafana.company.com/d/payments
      title: Grafana Dashboard
      icon: dashboard

  dependencies:
    - component: user-service
    - component: notification-service

  jenkins:
    pipelines:
      - name: Production Pipeline
        environment: production
        job: "deployments/payment-prod"
      - name: Automated Tests
        environment: test
        job: "ci/payment-ci"
```


### 2.1. Minimum viable manifest

There is only **one required field**: `metadata.name`. Everything else has a default value.

```yaml
metadata:
  name: payment-service
```

That file is valid and produces a `Component` / `service` / `production` component, owner `unassigned`, docs under `/docs`.

---

## 3. Fields

### 3.1. Root

| Field | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `apiVersion` | string | No | `daileon/v1` | **Not validated.** Any string is accepted. It exists by convention / for future versioning. |
| `kind` | string | No | `Component` | **Open set** — see section 5. |
| `metadata` | object | **Yes** | — | |
| `spec` | object | No | empty object (all defaults) | |

### 3.2. `metadata`

| Field | Type | Required | Default | Effect |
| --- | --- | --- | --- | --- |
| `name` | string | **Yes** | — | Name shown in the catalog. **Overrides the repository name in GitLab.** |
| `description` | string | No | the project description in GitLab | If omitted or empty, falls back to the GitLab description. |
| `tags` | list of strings | No | `[]` | Becomes a filter and feeds the global search. |
| `owner` | string | No | `unassigned` | Team/person responsible. Acts as a catalog filter. |
| `domain` | string | No | `null` | Business grouping. |

### 3.3. `spec`

| Field | Type | Required | Default | Effect |
| --- | --- | --- | --- | --- |
| `type` | string | No | `service` | **Open set** — see section 5. Feeds the "Type" filter. |
| `lifecycle` | string | No | `production` | **Open set, but with 3 privileged values** — see section 5. |
| `solution` | string | No | `null` | Solution the component belongs to (project grouper). |
| `docs` | object | No | `{dir: /docs, index: index.md}` | See 3.4. |
| `links` | list | No | `[]` | See 3.5. |
| `dependencies` | list | No | `[]` | See 3.6. |
| `jenkins` | object / list | No | `null` | Jenkins pipeline configuration. See 3.7. |
| `deployments` | list | No | `[]` | List of environments and installation servers. See 3.8. |

### 3.4. `spec.docs`

| Field | Type | Default | Effect |
| --- | --- | --- | --- |
| `dir` | string | `/docs` | Folder scanned recursively for documents. Leading/trailing slashes are ignored — `/docs`, `docs` and `docs/` are equivalent. Subfolders are accepted (`documentation/technical`). |
| `index` | string | `index.md` | Entry file of the documentation. ⚠️ See the warning below. |

> ⚠️ **Today `index` is not honored by the interface.** The value is read, stored and exposed in the API (`docs_index`), but the frontend always opens `index.md` as the TechDocs home page. If your docs folder has no `index.md`, the "Documentation" link will land on an empty page. Until this is fixed, **keep an `index.md`** at the root of `docs.dir`.

Besides the docs folder, the **repository root `README.md` is always indexed**, with or without a manifest.

**Indexed extensions:** `.md`, `.markdown`, `.pdf` and images (`.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.bmp`). Anything else inside the folder — `.html`, `.xlsx`, `.txt`, `.css`, `.js`, fonts — is ignored. `.svg` is left out on purpose, since it can carry embedded script. PDFs and images over 25 MB are discarded with a warning in the log.

> ⚠️ **A docs folder without any `.md` disappears from the interface.** If `docs.dir` only holds a spreadsheet, HTML or images, the component shows up without navigable documentation even with a correct manifest — the images stay indexed, but there is no page presenting them. Start with `index.md`.

**When the folder does not exist:** Daileon falls back to scanning the whole repository (or the component's subfolder, in a monorepo) for `.md` and `.pdf`. Images do **not** take part in this mode — without the folder bounding the scope, every `src/assets/` would turn into documentation. Hidden directories (`.git`, `.github`) and dependency/build ones (`node_modules`, `dist`, `target`, …) are skipped in both modes.

To exclude a specific folder from the scan, see section 4.

### 3.5. `spec.links`

List of objects:

| Field | Type | Required | Effect |
| --- | --- | --- | --- |
| `url` | string | **Yes** | Link target (opens in a new tab). |
| `title` | string | **Yes** | Displayed text. |
| `icon` | string | No | **Accepted and stored, but not used in rendering yet.** Every link shows the same external-link icon. |

Omitting `url` or `title` in any item **invalidates the whole manifest** and the component becomes synthetic.

### 3.6. `spec.dependencies` and `spec.dependents`

Declaration of direct dependencies (what this project consumes) and downstream dependents (internal or external projects, or infrastructure/service resources):

```yaml
spec:
  dependencies:
    - component: Redmine
    - resource: bc-ccs
    - resource: Credilink
    - resource: enviosms
    - resource: bcadastro

  dependents:
    - component: IDEA 2
```

| Field | Type | Required | Effect |
| --- | --- | --- | --- |
| `component` | string | No* | Name of the catalogued component or dependent. |
| `external` | string | No* | Name of the external project/system from another company (highlighted in green in the graph). |
| `resource` | string | No* | Name of the resource, service or infrastructure (e.g. `bc-ccs`, `Credilink`, `enviosms`, `bcadastro`). Rendered as a cylinder/resource shape in the graph. |

*\* Each item must provide `component`, `external` or `resource`.*

- **`dependencies`**: Components, external systems or resources our project depends on (`MyProject ---> Target`).
- **`dependents`**: Components, external systems or resources that depend on our project (`Dependent ---> MyProject`).

When an external system is declared with `external: <name>`, it is inserted into the graph and flagged as an external project. When a resource/service is declared with `resource: <name>`, it is drawn with the characteristic resource shape (`[( "resource" )]`) in the Mermaid graph.

### 3.7. `spec.jenkins`

Mapping of Jenkins CI/CD pipelines used to display the latest build status, duration, trigger, branch and a visual success/failure indicator on the component's **Pipelines (Jenkins)** tab.

Two YAML formats are supported:

#### Object format with a `pipelines` key:

```yaml
spec:
  jenkins:
    server_url: "https://jenkins.yourcompany.com" # (Optional) Override of the Jenkins base URL
    pipelines:
      - name: Production Pipeline
        environment: production
        job: "deployments/payment-prod"
      - name: Automated Tests
        environment: test
        job: "ci/payment-ci"
```

#### Direct list format:

```yaml
spec:
  jenkins:
    - name: Production Pipeline
      environment: production
      job: "deployments/payment-prod"
    - name: Automated Tests
      environment: test
      job: "ci/payment-ci"
```

| Field | Type | Required | Default | Effect |
| --- | --- | --- | --- | --- |
| `name` | string | **Yes** | — | Display name of the pipeline in the UI. |
| `environment` | string | No | `production` | Associated environment (e.g. `production`, `staging`, `test`). Defines the color of the visual badge. |
| `job` | string | **Yes** | — | Job name or path in Jenkins. Folders are supported (e.g. `deployments/my-job`). |
| `server_url` | string | No | `null` | Jenkins server URL, when different from the default configured in `.env`. |

### 3.8. `spec.deployments`

List of information about the deployment environments, servers and infrastructure where the project runs. It lets you record the environment URL, server name, IP, operating system, execution mode (VM, Docker, Bare Metal, etc.) and service port.

> 💡 **Avoiding redundancy:** There is no need to register staging or production URLs under `spec.links` — Daileon automatically aggregates the `deployments` URLs into the component's link overview. Use `spec.links` only for auxiliary resources (e.g. Grafana Dashboard, OpenAPI specs, Jira).

```yaml
spec:
  deployments:
    - environment: production
      url: https://payment.company.com
      server_name: srv-prod-app01
      server_ip: 10.0.1.50
      os: "Linux Ubuntu 22.04 LTS"
      execution_type: Docker
      port: 8080
      notes: Main Kubernetes cluster
    - environment: homologation
      url: https://homolog-payment.company.com
      server_name: Arya
      server_ip: 10.43.210.55
      os: "Windows Server 2022"
      execution_type: VM
      port: 8080
      notes: Homologation environment
```

| Field | Type | Required | Default | Effect |
| --- | --- | --- | --- | --- |
| `environment` | string | No | `production` | Environment name (e.g. `production`, `homologation`, `staging`, `test`, `dev`). |
| `url` | string | No | `null` | Public or internal URL used to reach the environment. |
| `server_name` | string | No | `null` | Server or host name. Grouped in the global Servers catalog. |
| `server_ip` | string | No | `null` | Server IP address. |
| `os` | string | No | `null` | Operating system and version (e.g. `Linux Ubuntu 22.04 LTS`, `Windows Server 2022`). |
| `execution_type` | string | No | `null` | Service execution mode (e.g. `VM`, `Docker`, `Bare Metal`, `Kubernetes`). |
| `port` | number / string | No | `null` | Port the service listens on (e.g. `8080`, `5173`, `443`). |
| `notes` | string | No | `null` | Additional notes about the environment or infrastructure. |


---

## 4. Excluding folders from indexing: `.daileon-ignore`

The manifest says where Daileon **should** look. `.daileon-ignore` says where it **should not**.

| Item | Value |
| --- | --- |
| **File name** | `.daileon-ignore` |
| **Location** | Inside any folder you want to exclude |
| **Content** | **Irrelevant.** The file is never read — it can be empty or explain the reason to whoever comes next |
| **Scope** | The folder containing it **and everything below it**, recursively |
| **Effect** | Nothing in there is indexed as documentation, nor generates a component from a `project-info.yml` |

The most common case is a docs folder carrying dead weight — an HTML prototype with images, attachments from another era:

```
docs/
├── index.md
├── architecture.md
└── Prototype/
    ├── .daileon-ignore        ← that's all
    ├── index.html
    └── images/logo.png
```

Result: the TechDocs show `index.md` and `architecture.md`; `Prototype/` disappears from the portal and stays in the repository.

In a monorepo, the marker also removes an entire subproject from the catalog:

```
apps/
├── new/project-info.yml       → becomes a component
└── legacy/
    ├── .daileon-ignore        → does not become a component
    └── project-info.yml
```

> ⚠️ **A `.daileon-ignore` at the repository root removes the project from the catalog.** It is consistent with the rule — the scope is the folder containing it, and at the root that is everything — but the effect is large and silent: on the next sync the component and its documentation vanish from the portal. Use it when that is exactly the intent; to exclude only the documentation, mark the docs folder.

Every exclusion is recorded in the backend log at `INFO` level, so a forgotten marker does not turn into an unexplained disappearance:

```
Ignoring manifest under .daileon-ignore: apps/legacy/project-info.yml
Skipping docs of project 5: 'docs/Prototype' is marked with .daileon-ignore.
Project Strix has .daileon-ignore at the repository root; nothing will be indexed.
```

**Marking the docs folder does not trigger the fallback.** A folder that does not exist makes Daileon scan the repository for documentation (see 3.4); a marked folder does not — that is a deliberate absence, and scanning around it would go against the request. The root `README.md` is still indexed in that case; to exclude it too, the marker must be at the root.

---

## 5. The value sets: open or closed?

Here is the short answer: **every classification field (`kind`, `type`, `lifecycle`, `apiVersion`) is a free string.** There is no enum, `Literal` or domain validation in the parser — whatever you write is accepted and stored as-is.

What differs between them is **how much the rest of the system recognizes the value**:

### `kind` — fully open, convention `Component` / `API` / `Library`

| | |
| --- | --- |
| Validation | None |
| Default | `Component` |
| Project convention | `Component`, `API`, `Library` |
| Current usage | Stored only. **It is not displayed, filtered or used on any screen today.** |

In other words: today `kind` is practically decorative. It is reserved for when the catalog starts separating APIs and libraries into their own views. **Recommendation:** stick to the three convention values so you don't create debt once that filter exists.

### `type` — open, with a real effect on filters and on the dependency graph

| | |
| --- | --- |
| Validation | None |
| Default | `service` (when the manifest exists and omits the field) |
| Project convention | `service`, `website`, `library`, `cronjob`, `database` |
| Current usage | Shown as a chip on the card and on the component page; feeds the catalog's **"Type"** filter and the "Services" counter on the home page. **Components with `type: database` get a cylinder (database) shape in the dependency graph.** |

The filter is built **dynamically from the values present in the catalog** — so a new `type: lambda` simply shows up as one more option in the dropdown. That is flexible, but it means typos become phantom categories (`servcie` becomes a filter of its own). Standardize within the team.

⚠️ **Synthetic components get `type: unknown`, not `service`.** The `service` default only applies to manifests that exist and omit the field. Repositories without a `project-info.yml` come in as `unknown`, precisely so they don't inflate the services counter with projects that never declared themselves. If one of your components shows up as `unknown`, the fix is to declare `type` in the manifest.

### `lifecycle` — open, but only 3 values get visual treatment

| | |
| --- | --- |
| Validation | None |
| Default | `production` |
| Recognized values | `production`, `experimental`, `deprecated` (*case-insensitive* comparison) |
| Current usage | Colored chip + status LED; **"Lifecycle"** filter; "In production" counter on the home page. |

Here the difference really matters:

| Value | Displayed label | Color |
| --- | --- | --- |
| `production` | Production | green (ok) |
| `experimental` | Experimental | amber (crest) |
| `deprecated` | Deprecated | red (alert) |
| *anything else* | the raw text, untranslated | **no color, no LED** |

A `lifecycle: homologation` works and is filterable, but shows up dimmed, with no status indicator. **Stick to the three values** unless you truly need otherwise.

### `apiVersion` — open and unused

No compatibility check is performed. Writing `apiVersion: whatever/v9` raises neither an error nor a warning. Keep `daileon/v1`.

---

## 6. Behaviors that tend to surprise

1. **Unknown fields are silently ignored.** Writing `ownr:` instead of `owner:` raises no error — the wrong field is discarded and `owner` stays `unassigned`. There is no warning in the interface; check the result in the catalog after the sync.
2. **`metadata.name` overrides the repository name.** The catalog card shows the manifest name, not the GitLab one.
3. **GitLab tags are only used when there is no manifest.** If `project-info.yml` exists with an empty `tags`, the component ends up **with no tags** — the project's native GitLab tags are ignored. It's all or nothing.
4. **Links and dependencies are recreated on every sync.** Whatever left the file leaves the portal; there is no historical accumulation.
5. **Invalid manifest = synthetic component, no fanfare.** The error goes to the backend log (`Could not parse project-info.yml in project <name>`) and the component appears marked as "Synthetic fallback". If a component shows up without the expected metadata, that is the first place to look.
6. **Not every attachment under `docs.dir` is indexed.** Only `.md`, `.markdown`, `.pdf` and images get in — spreadsheets, HTML and `.txt` are silently discarded. A full docs folder without a single `.md` results in a component with no visible documentation. See 3.4.
7. **`.daileon-ignore` at the root erases the component from the catalog.** The marker excludes the folder containing it — at the root, that is the whole repository, and on the next sync the project disappears from the portal. See 4.

---

## 7. Size limits

The database defines per-column limits. On SQLite (the development default) they are **not enforced**; on PostgreSQL, a value above the limit **fails the synchronization of that component**. It is worth respecting them from the start:

| Field | Limit |
| --- | --- |
| `metadata.name` | 100 characters |
| `metadata.description` | no limit (free text) |
| each item of `metadata.tags` | 50 |
| `metadata.owner` | 100 |
| `metadata.domain` | 100 |
| `kind`, `type`, `lifecycle` | 50 each |
| `spec.solution` | 100 |
| `spec.docs.dir`, `spec.docs.index` | 100 each |
| `links[].title` | 100 |
| `links[].url` | 500 |
| `links[].icon` | 50 |
| `dependencies[].component` | 100 |
| `jenkins.pipelines[].name` | 100 |
| `jenkins.pipelines[].environment` | 50 |
| `jenkins.pipelines[].job` | 300 |
| `jenkins.pipelines[].server_url` | 500 |

---

## 8. Examples

### 8.1. Microservice with documentation, observability and Jenkins CI/CD

```yaml
apiVersion: daileon/v1
kind: Component

metadata:
  name: payment-service
  description: "Payment processing and PIX settlement."
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
    - url: https://grafana.company.com/d/payments
      title: Grafana Dashboard
      icon: dashboard
    - url: https://api-docs.company.com/payment-service
      title: OpenAPI Spec
      icon: api

  dependencies:
    - component: user-service
    - component: notification-service

  jenkins:
    pipelines:
      - name: Production Pipeline
        environment: production
        job: "deployments/payment-prod"
      - name: Staging Pipeline
        environment: staging
        job: "deployments/payment-staging"
      - name: Automated Tests (CI)
        environment: test
        job: "ci/payment-ci"
```


### 8.2. Shared library, docs outside the default location

```yaml
apiVersion: daileon/v1
kind: Library

metadata:
  name: commons-logging-br
  description: "Standardization of structured logs for the Java services."
  tags: [java, observability, library]
  owner: team-platform-engineering
  domain: internal-tooling

spec:
  type: library
  lifecycle: experimental
  docs:
    dir: documentation/technical
    index: index.md
```

### 8.3. Component being discontinued

```yaml
metadata:
  name: legacy-report
  description: "Batch report generator. Replaced by report-service."
  owner: team-data

spec:
  type: cronjob
  lifecycle: deprecated
  dependencies:
    - component: report-service
```

---

## 9. Checklist before committing

- [ ] The file is named `project-info.yml` and sits at the repository root.
- [ ] `metadata.name` is filled in and unique in the catalog.
- [ ] `owner` points to a real team (avoid leaving it as `unassigned`).
- [ ] `lifecycle` is `production`, `experimental` or `deprecated`.
- [ ] `type` follows the team convention (`service`, `website`, `library`, `cronjob`, …).
- [ ] There is an `index.md` at the root of the folder given in `docs.dir`.
- [ ] If there is a `.daileon-ignore` in the repository, it is in the right folder — and **not** at the root, unless the intent is to remove the project from the catalog.
- [ ] Every `links` item has both `url` **and** `title`.
- [ ] Valid YAML — run a lint or paste it into a validator before committing.
- [ ] After the merge, run Sync in the portal and check that the component shows up with the `project-info.yml` badge (and not as "Synthetic fallback").

---

## 10. Schema reference in the code

| What | Where |
| --- | --- |
| Pydantic model of the manifest | [`backend/app/catalog/manifest.py`](../backend/app/catalog/manifest.py) |
| File reading and mapping to the database | [`backend/app/gitlab/gitlab_crawler.py`](../backend/app/gitlab/gitlab_crawler.py) |
| Tables and column limits | [`backend/app/db/models.py`](../backend/app/db/models.py) |

See also: [Architecture](architecture.md) · [Deployment](deployment.md)
