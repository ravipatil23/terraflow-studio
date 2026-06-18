# Oracle Database@Cloud — Reusable Terraform Blueprints

Hand-fillable, standalone Terraform for **Oracle Database@AWS / @Azure / @GCP**, the
**OCI database stack** (DB Home/CDB/PDB), and **Data Guard** (multi-AZ and cross-region).
Unlike the rest of this repo (which *generates* HCL through the Terraflow Studio web app),
these are plain `.tf` files you copy and run. **You only edit `terraform.tfvars`.**

```
blueprints/
  # ── Provision the cloud infrastructure (network → infra → VM cluster) ──
  db-at-aws/                Oracle Database@AWS    (ODB Network → Exadata Infra → VM Cluster, + optional peering)
  db-at-azure/              Oracle Database@Azure  (VNet → Exadata Infra → VM Cluster)
  db-at-gcp/                Oracle Database@GCP    (ODB Network → Exadata Infra → VM Cluster)

  # ── Layer the database on an existing VM cluster ──
  oci-database/             DB Home → CDB → optional PDB (oracle/oci)

  # ── Data Guard networking between two existing VM clusters ──
  multi-az-dataguard/       Same-region DR  (LPG-peered: LPG pair + NSG rules)
  cross-region-dataguard/   Cross-region DR (Hub VCN + DRG + remote peering)
```

A typical flow: provision with a `db-at-*` blueprint → create databases with `oci-database`
on the cluster `ocid` it outputs → optionally add a `*-dataguard` blueprint between two clusters.

## Design

Each `db-at-*` blueprint is a root module that calls small child modules under `modules/`,
driven by **map variables**. To add a second network, infra, or cluster, you add another entry
to the relevant map in `terraform.tfvars` — no `.tf` edits, no copy-paste of resource blocks.
Resources wire together by **map keys**, not hardcoded IDs (e.g. `infra_ref` / `network_key`),
and DB server IDs/OCIDs are **auto-discovered** from the Exadata infrastructure via a data source.

The OCI-layer blueprints take OCIDs of *existing* resources as input:

- **`oci-database`** — chains DB Home → CDB → optional PDB on an existing VM cluster (`vm_cluster_ocid`).
- **`multi-az-dataguard` / `cross-region-dataguard`** — build the OCI network path between two
  existing VM cluster VCNs so Data Guard redo can flow. Neither manages the existing cluster VCN
  route tables (you add the one DG route by hand after apply — each README explains).

## Usage

```bash
cd blueprints/<blueprint>      # e.g. db-at-aws, oci-database, multi-az-dataguard
# edit terraform.tfvars  (oci-database also takes passwords via TF_VAR_* env vars)
terraform init
terraform plan
terraform apply
```

(OpenTofu works too: `tofu init && tofu plan && tofu apply`.)

## Provider versions

| Blueprint | Provider | Version |
|-----------|----------|---------|
| db-at-aws | `hashicorp/aws`     | `>= 6.15.0` |
| db-at-azure | `hashicorp/azurerm` | `>= 4.9.0`  |
| db-at-gcp | `hashicorp/google`  | `>= 6.0.0`  |
| oci-database | `oracle/oci` | `>= 6.0.0` |
| multi-az-dataguard | `oracle/oci` | `>= 6.0.0` |
| cross-region-dataguard | `oracle/oci` | `>= 6.0.0` |

Terraform `>= 1.5.0` (or OpenTofu `>= 1.6.0`) — the map variables use optional object attributes.

## Authentication (set before `terraform apply`)

- **AWS** — standard AWS credential chain (`aws configure`, `AWS_PROFILE`, env vars, or an instance role).
- **Azure** — `az login`, plus `subscription_id` in `terraform.tfvars`. The resource group must already exist.
- **GCP** — `gcloud auth application-default login` (or `GOOGLE_APPLICATION_CREDENTIALS`), plus `gcp_project`.
- **OCI blueprints** (`oci-database`, `*-dataguard`) — OCI auth via `~/.oci/config` or `OCI_*` env vars.
  Cross-region Data Guard must be authorized in **both** regions; `oci-database` takes DB passwords via
  `TF_VAR_admin_password` / `TF_VAR_pdb_admin_password`.

See each blueprint's own `README.md` for cloud-specific notes and gotchas.

## CI

`.github/workflows/blueprints-validate.yml` runs `terraform fmt -check` and
`terraform validate` against every blueprint on any change under `blueprints/**`.
