# Terraflow Studio — Claude Code Context

## What this is
A Flask web app that generates modular Terraform/OpenTofu for Oracle Database@AWS (ODB@AWS) and DB@GCP. Users fill in a form, see live HCL output, and download a ZIP or push directly to GitHub.

## Stack
- **Backend**: Python 3.12 + Flask, Jinja2 templates for HCL, pure urllib (no requests)
- **Frontend**: Single HTML file (`templates/index.html`) — vanilla JS, no framework
- **Storage**: FileStore (JSON files in `data/`) or CouchDB (when COUCHDB_URL is set)
- **LLM**: `llm.py` — model-agnostic adapter (Anthropic, OpenAI, Gemini, Ollama)
- **GitHub**: `github.py` — pushes generated files via GitHub Contents API
- **Tests**: `tests/test_all.py` — 210 tests, run with `python -m unittest tests/test_all.py`

## Key files
| File | Purpose |
|------|---------|
| `app.py` | Flask app, all routes, all Terraform generators |
| `llm.py` | LLM provider adapter |
| `github.py` | GitHub API integration |
| `store.py` | FileStore / CouchDB storage backend |
| `templates/index.html` | Entire frontend (HTML + CSS + JS) |
| `templates/tf/` | Jinja2 templates for every HCL file |
| `.env` | Config — LLM key, GitHub token, CouchDB |

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

## JS state arrays (in index.html)
```js
awsNets, awsInfras, awsPeerings, awsClusters, awsAvmcs, awsOciDbs
gcpNets, gcpInfras, gcpClusters
```

## Adding a new AWS resource — checklist
1. Add Jinja2 templates in `templates/tf/<resource>/` (main, variables, outputs, tfvars)
2. Add Python context builder `_mod_ctx()` and generators in `app.py`
3. Add JS: `defAwsX(i)`, `readAwsX(i)`, `awsXCardHTML(d,i)`, `renderAwsXs()`, `addAwsX()`
4. Add state array `let awsXs = []`
5. Add tab in HTML tab bar + page div `id="aws-page-N"`
6. Wire into `buildPayload()`, `renderAll()`, `applyConfig()`
7. Wire into `generate_all()` in app.py
8. Add validate handler in `api_validate()`
9. Run `python -m unittest tests/test_all.py` — all 210 must pass

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
All 210 tests must pass before committing.

## Conventions
- Python functions named `mod0_*` = AWS ODB Network, `mod1_*` = Exadata Infra, etc.
- GCP functions prefixed `gcp0_*`, `gcp1_*`, `gcp2_*`
- OCI functions prefixed `oci_dbhome_*`, `oci_cdb_*`, `oci_pdb_*`
- JS card prefix: `an` = AWS net, `ai` = AWS infra, `ap` = AWS peering, `ac` = AWS cluster, `av` = AVMC, `od` = OCI DB
- GCP card prefix: `gn` = GCP net, `gi` = GCP infra, `gc` = GCP cluster
- `tf_bool(v)` converts Python bool to `true`/`false` string for HCL templates
- Never hardcode sensitive values in Jinja2 templates — use `sensitive = true` in variables
