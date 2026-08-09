# Terraflow Studio — Claude Code Context

## What this is
A Flask web app that generates modular Terraform/OpenTofu for Oracle Database@AWS,
Database@Azure and Database@GCP, plus the OCI database layer (DB Home/CDB/PDB) and
Data Guard networking. Users fill in a form, see live HCL output, and download a ZIP
or push straight to GitHub.

## Architecture — one package per cloud
The codebase is organised so **a change to one cloud cannot reach another**. Some
duplication between clouds is accepted as the price of that.

```
core/          helpers · pages · selftest        knows about no cloud
  ^
oci/           database · dataguard · routes · selftest · templates/ · pages/
  ^                                            depends on core only
clouds/aws/    generator · validator · schema · selftest · routes · templates/ · pages/
clouds/gcp/    ... same shape
clouds/azure/  ... same shape
clouds/registry.py   imports the clouds; nothing imports it back
```

**OCI sits below the clouds, not beside them.** All three cloud packages use it for
DB Home/CDB/PDB and Data Guard; it uses none of them. Its Data Guard templates were
once named `aws_dg_*` but contain only `oci_core_*` resources and declare only the
`oracle/oci` provider — they were never AWS-specific.

`tests/test_architecture.py` enforces all of this (53 tests, real AST inspection
rather than grep). If you break the layering, those fail before anything else does.

### What lives in a cloud package
| File | Purpose |
|------|---------|
| `generator.py` | Builds the HCL files. `generate_<cloud>_tf(data) -> {path: content}` |
| `validator.py` | `validate(data, errors)` — payload rules for `/api/validate` |
| `schema.py` | Terraform provider resource schema, consumed by `tf_validator.py` |
| `selftest.py` | `/api/test` checks + `collect_cidrs()` + `SECURITY_PROMPT_LINE` |
| `routes.py` | Flask Blueprint owning the product page route |
| `templates/` | Jinja2 → **Terraform**, via `core.helpers.make_renderer` |
| `pages/` | Jinja2 → **HTML**, via the blueprint's `template_folder` |

Two Jinja trees per package on purpose: they render different languages for
different consumers. A `.html` under `templates/` or a `.j2` under `pages/` is a
silent mistake, and there is a test for each.

Each package renders **only its own** templates — separate loaders, so reaching for
another cloud's raises `TemplateNotFound` rather than quietly working.

## Shared modules (top level)
| File | Purpose |
|------|---------|
| `app.py` | App factory, blueprint registration, shared API routes |
| `clouds/registry.py` | One `CloudSpec` per cloud: generator, zip name, validator, selftest |
| `regions.py` | Loads `config/<cloud>_regions.json` — region/AZ catalogues |
| `tf_validator.py` | Static HCL validation; merges the three `schema.py` files |
| `llm.py` | Model-agnostic LLM adapter (Anthropic, OpenAI, Gemini, Ollama, OCI GenAI) |
| `rag.py` | Dual-backend RAG (ChromaDB or BM25) |
| `github.py` | Pushes generated files via the GitHub Contents API |
| `store.py` | FileStore (JSON under `data/`) or CouchDB |
| `templates/` | Pages serving no single cloud: `home`, `cidr`, `config`, `hub`, `rag` |

## Routes
| Route | Served by | Purpose |
|-------|-----------|---------|
| `GET /` | `app.py` | Product chooser |
| `GET /aws` | `clouds/aws/routes.py` | ODB@AWS |
| `GET /gcp` | `clouds/gcp/routes.py` | DB@GCP |
| `GET /azure` | `clouds/azure/routes.py` | DB@Azure |
| `GET /oci` | `oci/routes.py` | OCI Database (DB Home/CDB/PDB) |
| `GET /dg` | `oci/routes.py` | Data Guard networking |
| `GET /cidr` | `app.py` | CIDR planner — entirely client-side, posts to no API |
| `GET /hub`, `/rag`, `/config` | `app.py` | Multicloud hub, RAG admin, settings |

## Region / AZ catalogues
`config/<cloud>_regions.json` — edit these to add a region or zone; no code change.
Loaded and validated by `regions.py`, injected into the page so dropdowns populate
on first paint, and used by the generators for the paired OCI provider region. One
schema for all three clouds: `region`, `label`, `zones`, `status`, plus optional
`group` (Azure) and `oci_label` / `oci_region`.

Malformed config raises `RegionConfigError` at load rather than rendering an empty
dropdown. Azure sets `zones_are_region_scoped` because it numbers zones per region —
`"1"` in `eastus` is unrelated to `"1"` in `uksouth`.

**14 of 22 AWS regions have `oci_region: null`** and fall back to `us-ashburn-1`.
That predates the config file; the file makes it visible rather than guessing at
identifiers. `eu-west-1 → eu-frankfurt-1` also looks wrong (the catalogue pairs
Ireland with Dublin) and is preserved deliberately — changing it changes generated
Terraform.

## Resources
**AWS** — `aws_odb_network`, `aws_odb_cloud_exadata_infrastructure`,
`aws_odb_network_peering_connection`, `aws_odb_cloud_vm_cluster`,
`aws_odb_cloud_autonomous_vm_cluster`, plus DB Home/CDB/PDB via `oracle/oci`.

**Azure** — `azurerm_virtual_network` (+ delegated subnet),
`azurerm_oracle_exadata_infrastructure`, `azurerm_oracle_cloud_vm_cluster`,
`azurerm_oracle_resource_anchor`.

**GCP** — `google_oracle_database_odb_network` + `google_oracle_database_odb_subnet`,
`google_oracle_database_cloud_exadata_infrastructure`,
`google_oracle_database_cloud_vm_cluster` (note: the template directory is named
`gcp_exadb_vm_cluster`, but the resource is `..._cloud_vm_cluster`).

The AWS and GCP roots emit **one `for_each` module per resource type**; instances
live in `terraform.auto.tfvars`, so adding one does not change `main.tf`. Azure still
emits one module per instance.

### Externally provisioned networks / infras (brownfield) — AWS only
An ODB Network or Exadata Infra card can be flagged **already provisioned outside
Terraform** (`is_existing` + `existing_id`, optional `existing_arn` for AVMCs):
- The entry is dropped from `aws_networks` / `aws_infras`, so Terraform creates nothing.
- Its ID is emitted as `existing_infra_ids` / `existing_odb_network_ids`, keyed by module name.
- `main.tf` gains a `locals` block merging managed module outputs with those maps, and
  every `infra_ref` / `network_ref` consumer resolves through `local.infra_ids` /
  `local.odb_network_ids`.
- Managed-only configs generate byte-identical output — the locals and variables appear
  only when at least one entry is external.
- `clouds/aws/validator.py` skips creation-field validation for external entries and
  requires `existing_id`.

**GCP and Azure have no brownfield support.** GCP is the harder one: its ODB network
module creates the network *and both subnets*, so an existing network is a triple
(`odb_network_name`, `client_subnet_name`, `backup_subnet_name`), not one ID.

### Azure VM Cluster gotchas (`azurerm_oracle_cloud_vm_cluster`)
Nearly every argument is `ForceNew` and `Update()` handles only `tags` and
`file_system_configuration`, so **drift proposes destroying the cluster**.

Three optional arguments are `ForceNew` *without* being `Computed`, which makes them
the ones that diff against an empty config:
- `backup_subnet_cidr` — never leave blank. The service assigns `192.168.252.0/22`,
  which then differs from a `null` config and replaces the cluster on the next plan.
  Always emitted explicitly.
- `gi_version` — a **major-version selector**. Oracle resolves `19.0.0.0` to the
  running release (`19.32.0.0.0`) and stores that, and it moves again with every
  quarterly patch, so no pinned value stays matching.
- `scan_listener_port_tcp_ssl` — emitted as `null` unless a port is set; guarded only
  in that case.

All three are covered by `lifecycle.ignore_changes`. The `Computed` optional arguments
(`cluster_name`, `domain`, `time_zone`, `system_version`, `zone_id`, …) adopt the state
value when config omits them and are deliberately **not** guarded.

AWS and GCP need none of this: the AWS provider keeps input and resolved value in
separate fields (`gi_version` / `gi_version_computed`), and GCP marks `giVersion`
`ignore_read`.

### Autonomous VM Cluster gotchas (`aws_odb_cloud_autonomous_vm_cluster`)
- Its `maintenance_window` takes **only** `preference` + `days_of_week`, `hours_of_day`,
  `lead_time_in_weeks`, `months`, `weeks_of_month`. `patching_mode`,
  `is_custom_action_timeout_enabled` and `custom_action_timeout_in_mins` belong to the
  **Exadata Infrastructure's** maintenance_window, not this one.
- It accepts the **id pair or the arn pair, never both** — and a `null` value still
  counts as present, so the unused pair must be omitted, not set to `null`
  (`use_arn_pair` in `_mod4_ctx` picks one at generation time).
- `db_servers` is **required**; always emit it, even for an empty manual list.

## JS state arrays
```js
// clouds/aws/pages/aws.html
awsNets, awsInfras, awsPeerings, awsClusters, awsAvmcs, awsOciDbs
// clouds/gcp/pages/gcp.html
gcpNets, gcpInfras, gcpClusters
// clouds/azure/pages/azure.html
azureVnets, azureInfras, azureClusters
```
The pages are **standalone** — none extends or includes another. That is the only
reason they can live in separate packages; if one grows an `{% extends %}`, the parent
must stay reachable from every blueprint.

## Adding a new AWS resource — checklist
1. Add Jinja2 templates in `clouds/aws/templates/aws_<resource>/` (main, variables, outputs, tfvars)
2. Add the context builder and generators in `clouds/aws/generator.py`
3. In `clouds/aws/pages/aws.html`: `defAwsX(i)`, `addAwsX()`, `readAwsX(i)`,
   `awsXCardHTML(d,i)`, `renderAwsXs()`, state array
4. Add the tab and its page div in the same file
5. Wire into `buildPayload()`, `renderAll()`, `applyConfig()`
6. Wire into `generate_aws_tf()` in `clouds/aws/generator.py`
7. Add rules to `clouds/aws/validator.py`, and checks to `clouds/aws/selftest.py`
8. Run the suite — see below

## Adding a new cloud
1. `clouds/<cloud>/` with `generator.py`, `validator.py`, `schema.py`, `selftest.py`,
   `routes.py`, `templates/`, `pages/`
2. One `CloudSpec` line in `clouds/registry.py`
3. Register the blueprint in `app.py`
4. `config/<cloud>_regions.json`
5. Merge its schema in `tf_validator.py`

Nothing else should need to change. If it does, that is coupling worth removing.

## Tests
```bash
python -m unittest discover -s tests -p "test_*.py"     # 854 tests, all must pass
```
| File | Tests | Covers |
|------|-------|--------|
| `tests/test_all.py` | 488 | End-to-end generation, API routes, cross-cloud |
| `tests/test_azure.py` | 143 | Azure modules and validation |
| `tests/test_gcp.py` | 99 | GCP modules and validation |
| `tests/test_architecture.py` | 53 | Package layering and ownership rules |
| `tests/test_aws.py` | 42 | AWS modules and validation |
| `tests/test_regions.py` | 29 | Region catalogues and OCI region mapping |

For refactors, a passing suite is not sufficient evidence. Snapshot generated output
(`{path: sha256}`) for every config under `data/` before and after and diff it — that
technique caught two regressions during the package split that the suite missed.

## Conventions
- AWS generator functions: `mod0_*` = ODB Network, `mod1_*` = Exadata Infra, `mod2_*` =
  Peering, `mod3_*` = VM Cluster, `mod4_*` = AVMC
- GCP: `gcp_build_root_*`, `_gcp_*_defaults`; Azure: `azure_*`, `_azure_*_defaults`
- OCI: `oci_dbhome_*`, `oci_cdb_*`, `oci_pdb_*`
- JS card prefixes — AWS: `an` net, `ai` infra, `ap` peering, `ac` cluster, `av` AVMC,
  `od` OCI DB · GCP: `gn`, `gi`, `gc` · Azure: `av` vnet, `ai` infra, `ac` cluster
- `tf_bool(v)` converts a Python bool to `true`/`false` for HCL
- Never hardcode secrets in templates — use `sensitive = true` on the variable
- OCI payload keys are canonical (`dg_multi_az`, `oci_databases`); `<cloud>_`-prefixed
  variants are accepted as deprecated aliases so saved configs keep working

## RAG layer
- `rag.py` — dual backend, chosen at runtime:
  - **ChromaDB** (semantic) when `chromadb` is installed *and* `EMBEDDING_PROVIDER` is set
  - **BM25** (lexical) otherwise — pure Python, no extra deps
- `rag_docs/*.md` — knowledge base, 27 files, git-tracked
- `data/chroma/`, `data/rag_index.json` — runtime stores, not in git
- `/api/rag/stats` (includes `backend`), `/api/rag/rebuild`, `/api/rag/search`, `/api/rag/upload`
- `/api/llm/fill` augments the system prompt with the top 5 retrieved chunks

## Running
```bash
pip install -r requirements.txt && python app.py     # http://localhost:5000
docker compose up -d --build                         # edit .env first
```

## Environment variables (.env)
```
COUCHDB_USER, COUCHDB_PASSWORD, COUCHDB_DB
LLM_PROVIDER, LLM_API_KEY, LLM_MODEL, LLM_BASE_URL      # anthropic|openai|gemini|ollama|oci_genai
LLM_MAX_TOKENS=2048, LLM_TEMPERATURE=0.2, LLM_TIMEOUT=60
EMBEDDING_PROVIDER, EMBEDDING_MODEL, EMBEDDING_BASE_URL # ollama|openai|gemini
GITHUB_TOKEN, GITHUB_REPO, GITHUB_BRANCH=main, GITHUB_BASE_PATH=terraform
```

## Known loose ends
- `templates/base.html` (1875 lines) is **dead** — nothing extends, includes or renders
  it. The pages became standalone at some point and it was never removed.
- `/api/test` reports two spurious failures for `oci` and `dg` (`root main.tf generated`,
  `root terraform.auto.tfvars generated`): those products emit `dg_multi_az_*/main.tf`
  rather than a root module.
- `oci/__init__.py` exports 20 names, most underscore-prefixed, because the cloud
  generators reach into OCI internals (`_ocidb_filled`, `_mn_dbhome`). Worth narrowing.
- `app.py` still holds cloud-aware prompt text in `api_llm_ask` — the same shape as the
  `_collect_cidrs` bug that silently gave Azure no CIDR findings at all.
