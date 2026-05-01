# Terraflow Studio v5.1

**Oracle DB@Cloud · Terraform Generator**

A Python/Flask web app that generates production-ready, modular Terraform/OpenTofu code for Oracle Database@AWS (ODB@AWS) and Oracle Database@GCP (DB@GCP). Fill in the form, see live HCL output, and download a ZIP or push directly to GitHub.

---

## Features

- **Multi-cloud** — AWS and GCP tabs, switch with one click; Terraform or OpenTofu toggle
- **Multi-instance** — add as many networks, infras, peerings, and clusters as needed; all auto-wired in root `main.tf`
- **Live output** — Terraform HCL generates in real time as you fill in fields; file tree + syntax-highlighted code viewer
- **✦ Explain** — click Explain on any file to get an AI explanation of what that Terraform file does and why
- **✦ AI fill** — describe your infrastructure in plain English and the AI fills in the entire form
- **Region & AZ dropdowns** — populated from Oracle's official regional availability docs
- **Customer config persistence** — save/load configs by customer name; FileStore (default) or CouchDB backend
- **Validation** — per-field inline errors with card highlighting; VALIDATE & GENERATE ALL button per tab
- **Testing** — 🧪 Test button runs 220 functional checks + mock Terraform validator against any saved or current config
- **GitHub push** — push generated Terraform directly to a GitHub repo via the Contents API
- **Docker Compose** — single `docker compose up` for app + CouchDB

---

## Supported Resources

### AWS (`hashicorp/aws ≥ 6.15.0`)

| Tab | Resource | Default module name |
|-----|----------|---------------------|
| 1 | `aws_odb_network` | `odb_network` |
| 2 | `aws_odb_cloud_exadata_infrastructure` | `odb_exaInfra` |
| 3 | `aws_odb_network_peering_connection` | `odb_peering` |
| 4 | `aws_odb_cloud_vm_cluster` | `odb_vmcluster` |
| 5 | `aws_odb_cloud_autonomous_vm_cluster` | `odb_avmcluster` |
| 6 | OCI DB Home / CDB / PDB (via `oracle/oci` provider) | `oci_db_home` / `oci_cdb` / `oci_pdb` |

### GCP (`hashicorp/google ≥ 7.0`, `oracle/oci ≥ 7.29.0`)

| Tab | Resource | Default module name |
|-----|----------|---------------------|
| A | `google_oracle_database_odb_network` + client & backup subnets | `gcp_network` |
| C | `google_oracle_database_cloud_exadata_infrastructure` | `gcp_infra` |
| D | `google_oracle_database_exadb_vm_cluster` | `gcp_cluster` |

---

## Generated Output Structure

### AWS

```
terraflow-studio-aws/
├── main.tf                    # root — wires all modules, outputs id + arn for each
├── terraform.tfvars
└── modules/
    ├── odb_network/           # aws_odb_network
    ├── odb_exaInfra/          # aws_odb_cloud_exadata_infrastructure
    ├── odb_peering/           # aws_odb_network_peering_connection
    ├── odb_vmcluster/         # aws_odb_cloud_vm_cluster
    ├── odb_avmcluster/        # aws_odb_cloud_autonomous_vm_cluster
    ├── oci_db_home/           # oci_db_home
    ├── oci_cdb/               # oci_database (CDB)
    └── oci_pdb/               # oci_pluggable_database (PDB)
```

Each module: `main.tf`, `variables.tf`, `outputs.tf`, `terraform.tfvars`.

### GCP

```
terraflow-studio-gcp/
├── main.tf
├── terraform.tfvars
└── modules/
    ├── gcp_network/           # google_oracle_database_odb_network
    ├── gcp_network_client_subnet/   # google_oracle_database_odb_subnet (CLIENT_SUBNET)
    ├── gcp_network_backup_subnet/   # google_oracle_database_odb_subnet (BACKUP_SUBNET)
    ├── gcp_infra/             # google_oracle_database_cloud_exadata_infrastructure
    └── gcp_cluster/           # google_oracle_database_exadb_vm_cluster
```

---

## Quick Start

```bash
git clone https://github.com/ravipatil23/terraflow-studio.git
cd terraflow-studio/odb_terraform_app

python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

python app.py
# open http://localhost:5000
```

---

## Docker Compose (recommended)

```bash
# Edit .env first — set COUCHDB_USER, COUCHDB_PASSWORD, and optionally LLM_API_KEY
docker compose up -d --build
# open http://localhost:5000
```

`docker-compose.yml` starts the Flask app and a CouchDB instance. The app auto-detects CouchDB at `$COUCHDB_URL` and falls back to FileStore if unreachable.

---

## AI Features

### ✦ Fill form with AI

Type a plain-English description in the AI bar at the top of the page:

> *"Production ExaDB in us-east-1 AZ use1-az6, X11M 2c/3s, 16-core VM cluster, GI 23.0.0.0, LICENSE_INCLUDED"*

The AI fills in all form fields and explains what it configured.

Supported LLM providers: **Anthropic**, **OpenAI**, **Gemini**, **Ollama** (local).

### ✦ Explain Terraform

Select any file in the output panel and click **✦ Explain**. The AI explains:
1. What the file does
2. Key resources or variables and their purpose
3. Notable configuration choices, cross-module dependencies, or gotchas

Both AI features are augmented by a **RAG knowledge base** (`rag_docs/`) covering ODB@AWS and DB@GCP resource schemas, immutable fields, provisioning times, and common pitfalls.

---

## Environment Variables

Copy `.env.example` to `.env` (or edit `.env` directly) and set:

```bash
# ── CouchDB ────────────────────────────────
COUCHDB_URL=http://couchdb:5984
COUCHDB_USER=admin
COUCHDB_PASSWORD=changeme
COUCHDB_DB=terraflow_studio_configs

# ── LLM provider ───────────────────────────
# Provider: anthropic | openai | gemini | ollama
LLM_PROVIDER=anthropic
LLM_API_KEY=sk-ant-...
LLM_MODEL=claude-opus-4-7
LLM_MAX_TOKENS=2048
LLM_TEMPERATURE=0.2
LLM_TIMEOUT=60

# Ollama only
# LLM_BASE_URL=http://localhost:11434

# ── Embeddings (optional — enables ChromaDB RAG) ──
# Provider: ollama | openai | gemini
# EMBEDDING_PROVIDER=ollama
# EMBEDDING_MODEL=nomic-embed-text
# EMBEDDING_BASE_URL=http://localhost:11434

# ── GitHub push ────────────────────────────
GITHUB_TOKEN=ghp_...
GITHUB_REPO=myorg/my-terraform-repo
GITHUB_BRANCH=main
GITHUB_BASE_PATH=terraform
```

If `LLM_API_KEY` is not set, AI features are disabled gracefully (the AI bar is hidden).
If `GITHUB_TOKEN` is not set, the Push to Git button is disabled.

---

## RAG Knowledge Base

Terraform generation advice is grounded in a curated knowledge base in `rag_docs/`:

| File | Contents |
|------|----------|
| `aws_odb_network.md` | CIDR constraints, DNS gotchas, s3_access defaults |
| `aws_exadata_infra.md` | Shapes, maintenance windows, NON_ROLLING patching |
| `aws_vm_cluster.md` | Required fields, db_servers data source, immutable fields |
| `aws_peering_avmcluster.md` | Peering limits, AVM cluster reserved ports |
| `aws_gotchas.md` | Comprehensive AWS pitfalls reference |
| `gcp_resources.md` | Full GCP resource schemas, immutable fields, CIDR rules |
| `gcp_gotchas.md` | grid_image_id vs gi_version, time_zone block syntax, etc. |
| `constraints_valid_values.md` | Valid enums, ranges, and format rules across both clouds |
| `example_configurations.md` | Reference configurations (prod, dev, multi-env, HA) |
| `oci_database.md` | OCI DB Home / CDB / PDB resource reference |

**RAG auto-builds on first use.** No manual setup required — the index is created from `rag_docs/` at startup if it doesn't exist. To force a rebuild: `POST /api/rag/rebuild`.

Two backends are supported:
- **BM25** (default) — pure Python, no extra dependencies
- **ChromaDB** (semantic) — install `chromadb` and set `EMBEDDING_PROVIDER`

---

## API Reference

### Core generation

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Product chooser landing page |
| `GET` | `/aws` | ODB@AWS product page |
| `GET` | `/gcp` | DB@GCP product page |
| `POST` | `/api/generate` | Generate a single file; returns `{ content }` |
| `POST` | `/api/validate` | Validate fields for one tab; returns `{ valid, errors }` |
| `POST` | `/api/download` | Stream ZIP of all generated files |

### Config persistence

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/config/save` | Save full payload for `{ customer, cloud }` |
| `GET` | `/api/config/load/<customer>/<cloud>` | Load saved config |
| `GET` | `/api/config/list` | List all saved customers |
| `DELETE` | `/api/config/delete/<customer>/<cloud>` | Delete a config |
| `GET` | `/api/config/backend` | Returns active backend name |

### AI

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/llm/fill` | Fill form from natural language; returns `{ payload, explanation }` |
| `POST` | `/api/llm/explain` | Explain a Terraform file; body: `{ content, filename }`; returns `{ explanation }` |
| `GET` | `/api/llm/status` | Returns LLM provider availability |

### RAG

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/rag/stats` | Index statistics (`backend`, `n_chunks`, `n_docs`) |
| `POST` | `/api/rag/rebuild` | Force re-index of `rag_docs/` |
| `POST` | `/api/rag/search` | Search; body: `{ query, k }`; returns top-k chunks |

### Testing & GitHub

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/test` | Run functional tests against a payload or saved config |
| `POST` | `/api/tf-validate` | Run mock Terraform structural validator |
| `POST` | `/api/github/push` | Push generated files to GitHub repo |
| `GET` | `/api/github/status` | Returns GitHub integration status |

### `/api/validate` tab numbers

| `tab` | Resource |
|-------|----------|
| `0` | AWS ODB Network |
| `1` | AWS Exadata Infrastructure |
| `2` | AWS Network Peering |
| `3` | AWS VM Cluster |
| `4` | AWS Autonomous VM Cluster |
| `10` | GCP ODB Network |
| `12` | GCP Exadata Infrastructure |
| `13` | GCP VM Cluster |

---

## Mock Terraform Validator

Pure-Python structural validator — no Terraform binary required. Simulates `terraform validate` across 8 check groups:

| Group | What is checked |
|-------|----------------|
| File Structure | All 4 files present per module |
| HCL Syntax | Balanced `{}[]()`, no empty assignments |
| Provider | Correct provider source + version constraint declared |
| Resource Schema | Resource types match ODB provider schemas; required arguments present |
| Variable Resolution | Every `var.<n>` in `main.tf` resolves to a declared variable |
| Output Validity | Outputs reference known resource attributes |
| Module Cross-References | `source` paths correct; `module.<n>.<attr>` resolves to declared outputs |
| tfvars Completeness | Variables without tfvars values flagged as warnings |

---

## Test Suite

220 tests — run with:

```bash
python -m unittest tests/test_all.py
```

| Class | Coverage |
|-------|----------|
| `TestHelpers` | `is_ref`, `parse_list`, `tf_bool` |
| `TestAwsOdbNetwork` | `mod0_*` — all 4 file generators |
| `TestAwsExadataInfra` | `mod1_*` — shapes, maintenance window |
| `TestAwsPeering` | `mod2_*` |
| `TestAwsVmCluster` | `mod3_*` — ARN/ID modes, db_servers, license |
| `TestAwsAvmCluster` | `mod4_*` — autonomous VM cluster |
| `TestAwsRoot` | Multi-network/infra/peering/cluster wiring |
| `TestGcpOdbNetwork` | `gcp0_*` |
| `TestGcpOdbSubnet` | Client + backup subnet generators |
| `TestGcpExadataInfra` | `gcp2_*` |
| `TestGcpVmCluster` | `gcp1_*` — grid_image_id, exascale_db_storage_vault, shape_attribute |
| `TestGcpRoot` | Subnet auto-wiring, multi-cluster |
| `TestGenerateAll` | End-to-end AWS + GCP, backward-compat |
| `TestDefaultNormalisers` | `_aws_*_defaults`, `_gcp_*_defaults` |
| `TestApiRoutes` | All HTTP routes, all tabs, pass + fail |
| `TestFileStore` | `_slug`, CRUD, multi-cloud, overwrite |
| `TestConfigApiRoutes` | Mocked storage — save/load/list/delete |
| `TestCouchDBStore` | Fully mocked urllib — all operations |
| `TestApiTestRoute` | `/api/test` — validation, wiring, multi-network |
| `TestTFValidator` | HCL syntax, schema, var resolution, cross-refs |

---

## Project Structure

```
odb_terraform_app/
├── app.py                  # Flask app — all routes and Terraform generators
├── llm.py                  # LLM provider adapter (Anthropic, OpenAI, Gemini, Ollama)
├── rag.py                  # RAG engine — BM25 or ChromaDB backend
├── github.py               # GitHub Contents API integration
├── store.py                # FileStore + CouchDBStore backends
├── tf_validator.py         # Mock Terraform structural validator
├── requirements.txt
├── docker-compose.yml
├── .env                    # Config (not in git)
├── rag_docs/               # Knowledge base markdown files (10 files, git-tracked)
├── data/                   # Runtime data — configs, RAG index (not in git)
├── templates/
│   ├── home.html           # Product chooser landing page
│   ├── base.html           # Shared layout — header, LLM bar, output panel, JS
│   ├── aws.html            # ODB@AWS product page (extends base)
│   ├── gcp.html            # DB@GCP product page (extends base)
│   └── tf/                 # Jinja2 Terraform templates
│       ├── aws_odb_network/
│       ├── aws_exadata_infra/
│       ├── aws_peering/
│       ├── aws_vm_cluster/
│       ├── aws_avmcluster/
│       ├── aws_root/
│       ├── oci_db_home/
│       ├── oci_cdb/
│       ├── oci_pdb/
│       ├── gcp_odb_network/
│       ├── gcp_odb_subnet/
│       ├── gcp_exadb_infra/
│       ├── gcp_exadb_vm_cluster/
│       └── gcp_root/
└── tests/
    └── test_all.py         # 220 tests across 20 classes
```

---

## AWS Region & AZ Reference

| AWS Region | Location | AZ IDs |
|------------|----------|--------|
| `us-east-1` | N. Virginia | `use1-az4`, `use1-az6` |
| `us-east-2` | Ohio | `use2-az1`, `use2-az2` |
| `us-west-2` | Oregon | `usw2-az3`, `usw2-az4` |
| `eu-central-1` | Frankfurt | `euc1-az1`, `euc1-az2` |
| `ap-northeast-1` | Tokyo | `apne1-az1`, `apne1-az4` |

Source: [Oracle Regional Availability for ODB@AWS](https://docs.oracle.com/en-us/iaas/Content/database-at-aws/oaaws-regions.htm)

## GCP Region Reference

| GCP Region | Location | Oracle Zone examples |
|------------|----------|----------------------|
| `us-east4` | N. Virginia | `us-east4-b-r1` |
| `us-central1` | Iowa | `us-central1-a-r1` |
| `europe-west1` | Belgium | — |
| `europe-west4` | Netherlands | — |
| `europe-west3` | Frankfurt | `europe-west3-b-r1` |
| `europe-west2` | London | `europe-west2-c-r2` |
| `asia-northeast1` | Tokyo | — |
| `australia-southeast1` | Sydney | — |
| `southamerica-east1` | São Paulo | — |

Source: [Oracle Regional Availability for DB@GCP](https://docs.oracle.com/en-us/iaas/Content/database-at-gcp/get-started-regions.htm)
