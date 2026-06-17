# Oracle Database@Cloud — Reusable Terraform Blueprints

Hand-fillable, standalone Terraform for **Oracle Database@AWS**, **@Azure**, **@GCP**, and
**cross-region Data Guard**. Unlike the rest of this repo (which *generates* HCL through the
Terraflow Studio web app), these are plain `.tf` files you copy and run.
**You only edit `terraform.tfvars`.**

```
blueprints/
  db-at-aws/                Oracle Database@AWS    (ODB Network → Exadata Infra → VM Cluster, + optional peering)
  db-at-azure/              Oracle Database@Azure  (VNet → Exadata Infra → VM Cluster)
  db-at-gcp/                Oracle Database@GCP    (ODB Network → Exadata Infra → VM Cluster)
  cross-region-dataguard/   Cross-region Data Guard network path (OCI: Hub VCN + DRG + remote peering)
```

## Design

Each `db-at-*` blueprint is a root module that calls small child modules under `modules/`,
driven by **map variables**. To add a second network, infra, or cluster, you add another entry
to the relevant map in `terraform.tfvars` — no `.tf` edits, no copy-paste of resource blocks.

Resources are wired together by **map keys**, not hardcoded IDs:

- a VM cluster points at its infra and network via `infra_ref`/`infra_key` and `network_ref`/`network_key`
- DB server IDs/OCIDs are **auto-discovered** from the Exadata infrastructure via a data source

`cross-region-dataguard` is a two-region module set (primary + DR) that builds the OCI-side
network path between two *existing* Exadata VM clusters so Data Guard redo can flow — see its
own [README](cross-region-dataguard/README.md).

## Usage

```bash
cd blueprints/db-at-aws        # or db-at-azure / db-at-gcp / cross-region-dataguard
# edit terraform.tfvars
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
| cross-region-dataguard | `oracle/oci` | `>= 6.0.0` |

Terraform `>= 1.5.0` (or OpenTofu `>= 1.6.0`) — the map variables use optional object attributes.

## Authentication (set before `terraform apply`)

- **AWS** — standard AWS credential chain (`aws configure`, `AWS_PROFILE`, env vars, or an instance role).
- **Azure** — `az login`, plus `subscription_id` in `terraform.tfvars`. The resource group must already exist.
- **GCP** — `gcloud auth application-default login` (or `GOOGLE_APPLICATION_CREDENTIALS`), plus `gcp_project`.
- **Cross-region Data Guard** — OCI auth via `~/.oci/config` or `OCI_*` env vars, authorized in **both** regions.

See each blueprint's own `README.md` for cloud-specific notes and gotchas.

## CI

`.github/workflows/blueprints-validate.yml` runs `terraform fmt -check` and
`terraform validate` against every blueprint on any change under `blueprints/**`.
