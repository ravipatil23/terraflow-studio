# Terraflow Studio — Claude Code Context

## What this is
A Flask web app that generates modular Terraform/OpenTofu for Oracle Database@AWS (ODB@AWS) and DB@GCP. Users fill in a form, see live HCL output, and download a ZIP or push directly to GitHub.

## Stack
- **Backend**: Python 3.12 + Flask, Jinja2 templates for HCL, pure urllib (no requests)
- **Frontend**: Split HTML templates — `home.html` (chooser), `base.html` (shared chrome/JS), `aws.html`, `gcp.html` — vanilla JS, no framework
- **Storage**: FileStore (JSON files in `data/`) or CouchDB (when COUCHDB_URL is set)
- **LLM**: `llm.py` — model-agnostic adapter (Anthropic, OpenAI, Gemini, Ollama)
- **GitHub**: `github.py` — pushes generated files via GitHub Contents API
- **Tests**: `tests/test_all.py` — 220 tests, run with `python -m unittest tests/test_all.py`

## Routes
| Route | Template | Purpose |
|-------|----------|---------|
| `GET /` | `home.html` | Product chooser landing page |
| `GET /aws` | `aws.html` | ODB@AWS product page |
| `GET /gcp` | `gcp.html` | DB@GCP product page |

## Key files
| File | Purpose |
|------|---------|
| `app.py` | Flask app, all routes, all Terraform generators |
| `llm.py` | LLM provider adapter |
| `github.py` | GitHub API integration |
| `store.py` | FileStore / CouchDB storage backend |
| `templates/home.html` | Product chooser landing page (standalone, no base) |
| `templates/base.html` | Shared Jinja2 base — CSS, header, customer bar, LLM bar, output panel, shared JS |
| `templates/aws.html` | ODB@AWS product page (extends base) |
| `templates/gcp.html` | DB@GCP product page (extends base) |
| `templates/index.html` | Legacy monolithic template (kept for reference, not served) |
| `templates/tf/` | Jinja2 templates for every HCL file |
| `.env` | Config — LLM key, GitHub token, CouchDB |

## Template block architecture (base.html blocks)
| Block | Contents |
|-------|---------|
| `body_class` | `gcp` for GCP page; empty for AWS (default orange theme) |
| `cloud_nav` | Active cloud badge + link to the other product page |
| `provider_badge` | Provider version string in header |
| `product_tabs` | Tab bar for the product's resource types |
| `product_pages` | Form pages (`.page` divs) for each resource type |
| `product_data` | Region/zone data arrays + select-HTML helpers |
| `product_state` | State arrays, factory/add/read/card/render functions |
| `product_orchestration` | `const cloud`, `switchTab`, `buildPayload`, `applyConfig`, `renderAll` |
| `product_seed` | Initial `push(def*())` calls to pre-populate one of each resource |

## Terraform template directories
```
templates/tf/
  aws_odb_network/        aws_exadata_infra/      aws_peering/
  aws_vm_cluster/         aws_avmcluster/         aws_root/
  oci_db_home/            oci_cdb/                oci_pdb/
  gcp_odb_network/        gcp_odb_subnet/         gcp_exadb_infra/
  gcp_exadb_vm_cluster/   gcp_root/
```

## AWS resources (tabs 1–6)
1. `aws_odb_network` — ODB Network
2. `aws_odb_cloud_exadata_infrastructure` — Exadata Infra
3. `aws_odb_network_peering_connection` — Network Peering
4. `aws_odb_cloud_vm_cluster` — VM Cluster
5. `aws_odb_cloud_autonomous_vm_cluster` — Autonomous VM Cluster
6. DB Home / CDB / PDB — via `oracle/oci` provider

## GCP resources (tabs A, C, D)
A. `google_oracle_database_odb_network` + subnets
C. `google_oracle_database_cloud_exadata_infrastructure`
D. `google_oracle_database_exadb_vm_cluster`

## JS state arrays
```js
// aws.html
awsNets, awsInfras, awsPeerings, awsClusters, awsAvmcs, awsOciDbs
// gcp.html
gcpNets, gcpInfras, gcpClusters
```

## Adding a new AWS resource — checklist
1. Add Jinja2 templates in `templates/tf/<resource>/` (main, variables, outputs, tfvars)
2. Add Python context builder `_mod_ctx()` and generators in `app.py`
3. In `templates/aws.html` `product_state` block: add `defAwsX(i)`, `addAwsX()`, `readAwsX(i)`, `awsXCardHTML(d,i)`, `renderAwsXs()`, state array
4. Add tab in `product_tabs` block + page div in `product_pages` block
5. Wire into `buildPayload()`, `renderAll()`, `applyConfig()` in `product_orchestration` block
6. Wire into `generate_all()` in app.py
7. Add validate handler in `api_validate()`
8. Run `python -m unittest tests/test_all.py` — all 220 must pass

## Running locally
```bash
pip install -r requirements.txt
python app.py
# open http://localhost:5000
```

## Running with Docker
```bash
# Edit .env first (set passwords, LLM key, GitHub token)
docker compose up -d --build
# open http://localhost:5000
```

## Environment variables (.env)
```
# CouchDB
COUCHDB_USER, COUCHDB_PASSWORD, COUCHDB_DB

# LLM (anthropic | openai | gemini | ollama)
LLM_PROVIDER, LLM_API_KEY, LLM_MODEL, LLM_BASE_URL
LLM_MAX_TOKENS=2048, LLM_TEMPERATURE=0.2, LLM_TIMEOUT=60

# GitHub integration
GITHUB_TOKEN, GITHUB_REPO, GITHUB_BRANCH=main, GITHUB_BASE_PATH=terraform
```

## Test command
```bash
python -m unittest tests/test_all.py
```
All 220 tests must pass before committing.

## Conventions
- Python functions named `mod0_*` = AWS ODB Network, `mod1_*` = Exadata Infra, etc.
- GCP functions prefixed `gcp0_*`, `gcp1_*`, `gcp2_*`
- OCI functions prefixed `oci_dbhome_*`, `oci_cdb_*`, `oci_pdb_*`
- JS card prefix: `an` = AWS net, `ai` = AWS infra, `ap` = AWS peering, `ac` = AWS cluster, `av` = AVMC, `od` = OCI DB
- GCP card prefix: `gn` = GCP net, `gi` = GCP infra, `gc` = GCP cluster
- `tf_bool(v)` converts Python bool to `true`/`false` string for HCL templates
- Never hardcode sensitive values in Jinja2 templates — use `sensitive = true` in variables


## RAG layer
- `rag.py` — dual-backend RAG engine; auto-selects ChromaDB or BM25 at runtime
  - **ChromaDB** (semantic): used when `chromadb` is installed AND `EMBEDDING_PROVIDER` is set
  - **BM25** (lexical): pure-Python fallback, no extra deps required
- `rag_docs/*.md` — knowledge base (git-tracked, 8 markdown files)
- `data/chroma/` — ChromaDB persistent store (runtime, not in git)
- `data/rag_index.json` — BM25 index (runtime, not in git)
- `/api/rag/stats` — index statistics (includes `backend: 'chroma'|'bm25'`)
- `/api/rag/rebuild` — force re-index of rag_docs/
- `/api/rag/search` — search (POST `{query, k}`)
- `/api/llm/fill` augments the LLM system prompt with top-5 retrieved chunks via `rag.build_context()`
- Embedding vars: `EMBEDDING_PROVIDER` (ollama|openai|gemini), `EMBEDDING_MODEL`, `EMBEDDING_BASE_URL`