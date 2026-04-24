# Terraflow Studio v5.1

**Oracle DB@Cloud · Terraform Generator**

A Python/Flask single-page application that generates production-ready, modular Terraform code for Oracle Database@AWS and Oracle Database@GCP (Oracle AI Database@Google Cloud). Fill in the form, click download — get a complete, wired Terraform module structure ready to `terraform init && apply`.

---

## Features

- **Multi-cloud** — AWS and GCP tabs, switch with one click
- **Multi-instance** — add as many networks, infras, peerings, and clusters as needed; all auto-wired in root `main.tf`
- **Region & AZ dropdowns** — populated from Oracle's official regional availability docs (live regions only, planned regions shown greyed out)
- **ARN-first wiring** — AWS VM clusters default to ARN-based cross-references; toggle to ID mode per cluster
- **db_servers** — AWS auto-discovers via `data.aws_odb_db_servers` (recommended) or manual OCID entry; GCP manual OCID entry generates `db_servers { ocid = "..." }` blocks
- **Customer config persistence** — save/load configs by customer name; FileStore (default) or CouchDB backend
- **Validation** — per-field inline errors with card highlighting; VALIDATE & GENERATE ALL button per tab
- **Testing** — 🧪 Test button runs functional checks + mock Terraform validator against any saved or current config

---

## Supported Resources

### AWS (`hashicorp/aws ≥ 6.15.0`)

| Tab | Resource | Default module name |
|-----|----------|---------------------|
| 1 | `aws_odb_network` | `odb_network` |
| 2 | `aws_odb_cloud_exadata_infrastructure` | `odb_exaInfra` |
| 3 | `aws_odb_network_peering_connection` | `odb_peering` |
| 4 | `aws_odb_cloud_vm_cluster` | `odb_vmcluster` |

### GCP (`hashicorp/google ≥ 6.0.0`)

| Tab | Resource | Default module name |
|-----|----------|---------------------|
| A | `google_oracle_database_odb_network` | `gcp_network` |
| B | `google_oracle_database_odb_subnet` (client + backup, embedded in Network tab) | auto-named |
| C | `google_oracle_database_cloud_exadata_infrastructure` | `gcp_infra` |
| D | `google_oracle_database_exadb_vm_cluster` | `gcp_cluster` |

---

## Generated Output Structure

### AWS

```
terraflow-studio-aws/
├── main.tf                    # root — wires all modules, outputs id + arn for each
├── terraform.tfvars           # root variable values
└── modules/
    ├── odb_network/
    │   ├── main.tf            # aws_odb_network resource
    │   ├── variables.tf
    │   ├── outputs.tf         # network_id, network_arn, oci_network_anchor_id, oci_vcn_id
    │   └── terraform.tfvars
    ├── odb_exaInfra/
    │   ├── main.tf            # aws_odb_cloud_exadata_infrastructure resource
    │   ├── variables.tf
    │   ├── outputs.tf         # infra_id, infra_arn, shape, compute_count
    │   └── terraform.tfvars
    ├── odb_peering/
    │   ├── main.tf            # aws_odb_network_peering_connection resource
    │   ├── variables.tf
    │   ├── outputs.tf
    │   └── terraform.tfvars
    └── odb_vmcluster/
        ├── main.tf            # aws_odb_cloud_vm_cluster + optional data.aws_odb_db_servers
        ├── variables.tf
        ├── outputs.tf
        └── terraform.tfvars
```

### GCP

```
terraflow-studio-gcp/
├── main.tf                    # root — wires all modules
├── terraform.tfvars
└── modules/
    ├── gcp_network/           # google_oracle_database_odb_network
    ├── gcp_client_subnet/     # google_oracle_database_odb_subnet (client)
    ├── gcp_backup_subnet/     # google_oracle_database_odb_subnet (backup)
    ├── gcp_infra/             # google_oracle_database_cloud_exadata_infrastructure
    └── gcp_cluster/           # google_oracle_database_exadb_vm_cluster
```

Each module gets `main.tf`, `variables.tf`, `outputs.tf`, and `terraform.tfvars`.

---

## Setup

```bash
# 1. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
python app.py
```

Open **http://localhost:5000**

### Optional: CouchDB backend

Set the `COUCHDB_URL` environment variable before starting to use CouchDB instead of the local filesystem for config persistence:

```bash
export COUCHDB_URL=http://localhost:5984
python app.py
```

The app auto-detects the backend at startup. If CouchDB is unreachable it falls back to FileStore silently.

---

## Production Deployment

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

### Docker

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "app.py"]
```

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ODB_DATA_DIR` | `data/` | FileStore directory |
| `COUCHDB_URL` | _(unset)_ | Enable CouchDB backend (e.g. `http://localhost:5984`) |
| `COUCHDB_DB` | `terraflow_studio_configs` | CouchDB database name |

---

## API Reference

### Core generation

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | SPA — main UI (`Cache-Control: no-store`) |
| `POST` | `/api/generate` | Generate a single file; returns `{ content }` |
| `POST` | `/api/validate` | Validate fields for one tab; returns `{ valid, errors, errors_by_module }` |
| `POST` | `/api/download` | Stream ZIP of all generated files |

### Config persistence

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/config/save` | Save full payload for `{ customer, cloud }` |
| `GET` | `/api/config/load/<customer>/<cloud>` | Load saved config |
| `GET` | `/api/config/list` | List all saved customers |
| `DELETE` | `/api/config/delete/<customer>/<cloud>` | Delete a config |
| `GET` | `/api/config/backend` | Returns active backend name |

### Testing

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/test` | Run functional tests against a payload or saved config |
| `POST` | `/api/tf-validate` | Run mock Terraform structural validator |

### `/api/generate` payload (multi-instance)

```json
{
  "cloud": "aws",
  "file_key": "modules/odb_network/main.tf",
  "aws_networks": [
    { "module_name": "odb_network", "display_name": "prod-net",
      "availability_zone_id": "use1-az6", "region": "us-east-1",
      "client_subnet_cidr": "10.2.0.0/24", "backup_subnet_cidr": "10.2.1.0/24",
      "s3_access": true, "zero_etl_access": false, "tags": {} }
  ],
  "aws_infras": [ { "module_name": "odb_exaInfra", ... } ],
  "aws_peerings": [ { "module_name": "odb_peering", "network_ref": "odb_network", ... } ],
  "aws_clusters": [ { "module_name": "odb_vmcluster", "vm_mode": "arn",
                      "infra_ref": "odb_exaInfra", "network_ref": "odb_network",
                      "db_servers_mode": "auto", ... } ]
}
```

Omit `file_key` to receive all files at once as `{ "files": { "<path>": "<content>", ... } }`.

### `/api/validate` tab numbers

| `tab` | Resource |
|-------|----------|
| `0` | AWS ODB Network |
| `1` | AWS Exadata Infrastructure |
| `2` | AWS Network Peering |
| `3` | AWS VM Cluster |
| `10` | GCP ODB Network |
| `12` | GCP Exadata Infrastructure |
| `13` | GCP VM Cluster |

---

## Mock Terraform Validator (`tf_validator.py`)

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

Run via the UI (🔬 Mock TF Validate tab in the test modal) or directly:

```python
from app import generate_all
from tf_validator import validate_terraform, summarise

files = generate_all({ "cloud": "aws", ... })
results = validate_terraform(files, "aws")
print(summarise(results))
```

---

## Test Suite

210 tests across 19 classes — run with:

```bash
python -m unittest tests/test_all.py -v
```

| Class | Coverage |
|-------|----------|
| `TestHelpers` | `is_ref`, `parse_list`, `tf_bool` |
| `TestAwsOdbNetwork` | `mod0_*` — all 4 file generators |
| `TestAwsExadataInfra` | `mod1_*` — shapes, maintenance window |
| `TestAwsPeering` | `mod2_*` |
| `TestAwsVmCluster` | `mod3_*` — ARN/ID modes, db_servers, license |
| `TestAwsRoot` | Multi-network/infra/peering/cluster wiring |
| `TestGcpOdbNetwork` | `gcp0_*` |
| `TestGcpOdbSubnet` | Client + backup subnet generators |
| `TestGcpExadataInfra` | `gcp2_*` |
| `TestGcpVmCluster` | `gcp1_*` — db_servers blocks |
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
├── app.py                  # Flask app, all routes, Terraform generators
├── store.py                # FileStore + CouchDBStore backends
├── tf_validator.py         # Mock Terraform structural validator
├── requirements.txt
├── templates/
│   ├── index.html          # SPA — all UI, JS state, card builders
│   └── tf/                 # Jinja2 Terraform templates (36 files)
│       ├── aws_odb_network/
│       ├── aws_exadata_infra/
│       ├── aws_peering/
│       ├── aws_vm_cluster/
│       ├── aws_root/
│       ├── gcp_odb_network/
│       ├── gcp_odb_subnet/
│       ├── gcp_exadb_infra/
│       ├── gcp_exadb_vm_cluster/
│       └── gcp_root/
└── tests/
    └── test_all.py         # 210 tests across 19 classes
```

---

## AWS Region & AZ Reference

Live regions as of the Oracle docs (physical zone IDs shown where documented):

| AWS Region | Location | AZ IDs |
|------------|----------|--------|
| `us-east-1` | N. Virginia | `use1-az4`, `use1-az6` |
| `us-east-2` | Ohio | `use2-az1`, `use2-az2` |
| `us-west-2` | Oregon | `usw2-az3`, `usw2-az4` |
| `eu-central-1` | Frankfurt | `euc1-az1`, `euc1-az2` |
| `ap-northeast-1` | Tokyo | `apne1-az1`, `apne1-az4` |

Source: [Oracle Regional Availability for ODB@AWS](https://docs.oracle.com/en-us/iaas/Content/database-at-aws/oaaws-regions.htm)

## GCP Region Reference

15 live regions — physical zones documented where available:

| GCP Region | Location | Physical Zones | OCI Pair |
|------------|----------|---------------|----------|
| `us-east4` | N. Virginia | `us-east4-b-r1`, `us-east4-a-r2` | `us-ashburn-1` |
| `us-central1` | Iowa | — | `us-desmoines-1` |
| `us-west3` | Salt Lake City | — | `us-saltlake-2` |
| `northamerica-northeast1` | Montréal | — | `ca-montreal-1` |
| `northamerica-northeast2` | Toronto | — | `ca-toronto-1` |
| `europe-west3` | Frankfurt | `europe-west3-b-r1`, `europe-west3-a-r2` | `eu-frankfurt-1` |
| `europe-west2` | London | `europe-west2-c-r2`, `europe-west2-a-r1` | `uk-london-1` |
| `europe-west8` | Milan | `europe-west8-a-r1`, `europe-west8-b-r1` | `eu-milan-1` |
| `australia-southeast2` | Melbourne | `australia-southeast2-a-r2`, `australia-southeast2-b-r1` | `ap-melbourne-1` |
| `asia-south1` | Mumbai | — | `ap-mumbai-1` |
| `asia-south2` | Delhi | — | `ap-delhi-1` |
| `asia-northeast1` | Tokyo | — | `ap-tokyo-1` |
| `asia-northeast2` | Osaka | — | `ap-osaka-1` |
| `australia-southeast1` | Sydney | — | `ap-sydney-1` |
| `southamerica-east1` | São Paulo | — | `sa-saopaulo-1` |

Source: [Oracle Regional Availability for ODB@GCP](https://docs.oracle.com/en-us/iaas/Content/database-at-gcp/get-started-regions.htm)
