# Oracle Database@GCP — Terraform Blueprint

A complete, standalone Terraform configuration for deploying **Oracle Database@Google Cloud**
(Oracle Exadata Database Service on Google Cloud Marketplace). You only edit
[`terraform.tfvars`](terraform.tfvars) — the `.tf` files are reusable as-is.

---

## Table of contents

1. [What this deploys](#1-what-this-deploys)
2. [Architecture](#2-architecture)
3. [Prerequisites](#3-prerequisites)
4. [Authentication](#4-authentication)
5. [Repository layout](#5-repository-layout)
6. [Quick start](#6-quick-start)
7. [Variable reference](#7-variable-reference)
   - [Top-level](#71-top-level-variables)
   - [`gcp_odb_networks`](#72-gcp_odb_networks)
   - [`gcp_exadata_infras`](#73-gcp_exadata_infras)
   - [`gcp_vm_clusters`](#74-gcp_vm_clusters)
8. [How resources are wired](#8-how-resources-are-wired)
9. [Scaling: adding more resources](#9-scaling-adding-more-resources)
10. [Outputs](#10-outputs)
11. [Day-2 operations](#11-day-2-operations)
12. [Destroying](#12-destroying)
13. [Troubleshooting](#13-troubleshooting)
14. [FAQ](#14-faq)

---

## 1. What this deploys

| Order | Resource | Terraform resource | Module |
|-------|----------|--------------------|--------|
| 1 | ODB Network + client subnet + backup subnet | `google_oracle_database_odb_network`, `google_oracle_database_odb_subnet` ×2 | `modules/odb-network` |
| 2 | Exadata Infrastructure | `google_oracle_database_cloud_exadata_infrastructure` | `modules/exadata-infra` |
| 3 | ExaDB VM Cluster | `google_oracle_database_cloud_vm_cluster` | `modules/vm-cluster` |

A data source (`google_oracle_database_db_servers`) sits between steps 2 and 3 to **auto-discover**
the DB server OCIDs from the infrastructure and hand them to the cluster — you never copy OCIDs by hand.

**Provider:** `hashicorp/google >= 6.0.0` · **Terraform:** `>= 1.5.0` (or OpenTofu `>= 1.6.0`).

---

## 2. Architecture

```
                          ┌─────────────────────────────────────────────┐
                          │              Your GCP project                │
                          │                                              │
  terraform.tfvars        │   ┌────────────────────────────────────┐    │
  ┌───────────────┐       │   │  ODB Network  (modules/odb-network) │    │
  │ gcp_odb_       │──────┼──▶│   ├─ client subnet  (CLIENT_SUBNET) │    │
  │   networks     │      │   │   └─ backup subnet  (BACKUP_SUBNET) │    │
  ├───────────────┤       │   └────────────────────────────────────┘    │
  │ gcp_exadata_   │──────┼──▶┌────────────────────────────────────┐     │
  │   infras       │      │   │  Exadata Infrastructure             │    │
  ├───────────────┤       │   │  (modules/exadata-infra)            │    │
  │ gcp_vm_        │       │   └──────────────┬─────────────────────┘    │
  │   clusters     │──────┼──▶┌───────────────▼─────────────────────┐    │
  └───────────────┘       │   │  data.google_oracle_database_       │    │
        map keys          │   │       db_servers  (auto-discovery)  │    │
   wire everything        │   └───────────────┬─────────────────────┘    │
                          │   ┌───────────────▼─────────────────────┐    │
                          │   │  ExaDB VM Cluster                   │    │
                          │   │  (modules/vm-cluster)               │    │
                          │   └─────────────────────────────────────┘    │
                          └─────────────────────────────────────────────┘
```

The three maps in `terraform.tfvars` are joined by **keys**, not by IDs:

```
gcp_vm_clusters["vmc1"].network_key = "net1"  ─▶ gcp_odb_networks["net1"]
gcp_vm_clusters["vmc1"].infra_key   = "infra1" ─▶ gcp_exadata_infras["infra1"]
```

---

## 3. Prerequisites

Before `terraform apply`:

1. **An Oracle Database@Google Cloud subscription.** Subscribe through the Google Cloud Marketplace
   (“Oracle Database@Google Cloud”) and complete the Oracle/Google account linking. This is a
   one-time, account-level step done outside Terraform.
2. **Enable the API:**
   ```bash
   gcloud services enable oracledatabase.googleapis.com --project=YOUR_PROJECT
   ```
3. **A VPC network** in the project to attach the ODB network to. Note its self-link
   (`projects/PROJECT/global/networks/NAME`) — you'll set it as `network` in the tfvars.
4. **IAM permissions** on the identity running Terraform. At minimum the Oracle Database admin role
   plus the ability to read/use the VPC:
   ```bash
   gcloud projects add-iam-policy-binding YOUR_PROJECT \
     --member="user:you@example.com" \
     --role="roles/oracledatabase.admin"
   ```
   (Compute network viewer/user roles are also needed to reference the VPC.)
5. **Capacity / quota** for the chosen shape and region. Exadata capacity is region- and
   zone-specific; confirm the **Oracle zone** (e.g. `us-east4-b-r1`) is available to you.
6. **Terraform `>= 1.5.0`** (the configuration uses optional object attributes).

---

## 4. Authentication

Use Application Default Credentials (ADC):

```bash
gcloud auth application-default login
gcloud config set project YOUR_PROJECT
```

Or point at a service-account key:

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
```

`gcp_project` and `gcp_region` in `terraform.tfvars` set the provider defaults; each map entry can
override them per-resource via its `project` / `location` fields.

---

## 5. Repository layout

```
db-at-gcp/
├── main.tf              # provider + module wiring (do not need to edit)
├── variables.tf         # variable definitions (do not need to edit)
├── outputs.tf           # outputs (do not need to edit)
├── terraform.tfvars     # ◀── YOU EDIT THIS
└── modules/
    ├── odb-network/     # ODB network + client & backup subnets
    ├── exadata-infra/   # Exadata infrastructure
    └── vm-cluster/      # ExaDB VM cluster
```

---

## 6. Quick start

```bash
cd blueprints/db-at-gcp

# 1. authenticate
gcloud auth application-default login

# 2. edit terraform.tfvars — set gcp_project, gcp_region, network self-link,
#    Oracle zone, CIDRs, and your real SSH public key

# 3. run
terraform init
terraform plan      # review what will be created
terraform apply
```

> **Heads-up on timing:** an Exadata infrastructure plus VM cluster can take **several hours** to
> provision. The modules set long `timeouts` (VM cluster create = 12h) so apply does not abort early.

---

## 7. Variable reference

### 7.1 Top-level variables

| Variable | Type | Required | Description |
|----------|------|----------|-------------|
| `gcp_project` | string | ✅ | Default project ID. Overridable per map entry via `project`. |
| `gcp_region`  | string | ✅ | Default region (e.g. `us-east4`). Overridable per map entry via `location`. |

### 7.2 `gcp_odb_networks`

Map of ODB networks. Each entry also creates a **client** and a **backup** subnet.
The map **key** is referenced by `gcp_vm_clusters[*].network_key`.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `odb_network_id` | string | — (required) | Unique network ID. Starts with a letter, ≤ 63 chars. |
| `network` | string | — (required) | VPC self-link: `projects/{project}/global/networks/{name}`. |
| `client_subnet_id` | string | — (required) | ID for the client subnet (lowercase letters/numbers/hyphens, ≤ 63 chars). |
| `client_cidr_range` | string | — (required) | Client CIDR. RFC1918, **/27 min, /22 max**. |
| `backup_subnet_id` | string | — (required) | ID for the backup subnet. |
| `backup_cidr_range` | string | — (required) | Backup CIDR. RFC1918, /27 min. Must **not** overlap the client CIDR. |
| `location` | string | `gcp_region` | Region override. |
| `project` | string | `gcp_project` | Project override. |
| `gcp_oracle_zone` | string | `""` | Oracle zone within the region, e.g. `us-east4-b-r1`. |
| `deletion_protection` | bool | `true` | Block deletion until set to `false`. |
| `labels` | map(string) | `{}` | Resource labels. |

### 7.3 `gcp_exadata_infras`

Map of Exadata infrastructures. The map **key** is referenced by `gcp_vm_clusters[*].infra_key`.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `cloud_exadata_infrastructure_id` | string | — (required) | Immutable unique ID. |
| `shape` | string | — (required) | `Exadata.X9M`, `Exadata.X10M`, or `Exadata.X11M`. |
| `compute_count` | number | — (required) | Compute nodes (2–32). |
| `storage_count` | number | — (required) | Storage servers (3–64). |
| `display_name` | string | `""` | Friendly name. |
| `gcp_oracle_zone` | string | `""` | Oracle zone, e.g. `us-east4-b-r1`. |
| `location` / `project` | string | region/project | Per-resource overrides. |
| `total_storage_size_gb` | number | `0` | `0`/null → shape default. |
| `customer_contacts` | list(string) | `[]` | Emails for maintenance notifications. |
| `mw_preference` | string | `NO_PREFERENCE` | `NO_PREFERENCE` or `CUSTOM_PREFERENCE`. |
| `mw_patching_mode` | string | `ROLLING` | `ROLLING` or `NONROLLING`. |
| `mw_is_custom_action_timeout_enabled` | bool | `false` | Enable custom action timeout. |
| `mw_custom_action_timeout_mins` | number | `15` | Custom action timeout. |
| `mw_lead_time_week` | number | `null` | Lead time in weeks. |
| `mw_days_of_week` / `mw_months` | list(string) | `[]` | Custom-window days/months. |
| `mw_hours_of_day` / `mw_weeks_of_month` | list(number) | `[]` | Custom-window hours/weeks. |
| `deletion_protection` | bool | `true` | Block deletion until `false`. |
| `labels` | map(string) | `{}` | Resource labels. |

> **Note:** `compute_count` and `storage_count` are under `lifecycle { ignore_changes }` in the
> module, so elastic scaling done outside Terraform won't trigger a destroy/recreate.

### 7.4 `gcp_vm_clusters`

Map of ExaDB VM clusters. `infra_key` and `network_key` must match keys in the two maps above.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `infra_key` | string | — (required) | Key into `gcp_exadata_infras`. |
| `network_key` | string | — (required) | Key into `gcp_odb_networks`. |
| `cloud_vm_cluster_id` | string | — (required) | Immutable unique ID. |
| `hostname_prefix` | string | — (required) | ≤ 12 chars, starts with a letter. |
| `cpu_core_count` | number | — (required) | Enabled CPU cores. |
| `memory_size_gb` | number | — (required) | Memory per node (GB). |
| `db_node_storage_size_gb` | number | — (required) | Local node storage per node (GB). |
| `data_storage_size_tb` | number | — (required) | Data storage (TB). |
| `ssh_public_keys` | list(string) | — (required) | SSH keys for node access. |
| `display_name` | string | `""` | Defaults to the cluster ID. |
| `location` / `project` | string | region/project | Per-resource overrides. |
| `gi_version` | string | `23.0.0.0` | Grid Infrastructure version. |
| `license_type` | string | `LICENSE_INCLUDED` | or `BRING_YOUR_OWN_LICENSE`. |
| `local_backup_enabled` | bool | `false` | Enable local backups. |
| `sparse_diskgroup_enabled` | bool | `false` | Enable sparse disk group. |
| `cluster_name` | string | `null` | Optional cluster name, ≤ 11 chars. |
| `node_count` | number | `null` | Number of nodes. |
| `ocpu_count` | number | `null` | Fractional OCPU allocation. |
| `disk_redundancy` | string | `null` | `HIGH` or `NORMAL`. |
| `time_zone` | string | `UTC` | e.g. `America/New_York`. |
| `scan_listener_port_tcp` | number | `null` | Default 1521, range 1024–8999. |
| `dco_diagnostics` / `dco_health` / `dco_incident_logs` | bool | `true` | Diagnostics collection toggles. |
| `deletion_protection` | bool | `true` | Block deletion until `false`. |
| `labels` | map(string) | `{}` | Resource labels. |

---

## 8. How resources are wired

You never paste a network name, infra self-link, or DB-server OCID. The root `main.tf` resolves them:

```hcl
# cluster → infra self-link (from the infra module output)
exadata_infrastructure = module.exadata_infra[each.value.infra_key].infra_self_link

# cluster → network + subnet names (from the network module outputs)
odb_network       = module.odb_network[each.value.network_key].odb_network_name
odb_subnet        = module.odb_network[each.value.network_key].client_subnet_name
backup_odb_subnet = module.odb_network[each.value.network_key].backup_subnet_name

# cluster → DB server OCIDs (auto-discovered from the infra)
db_server_ocids = data.google_oracle_database_db_servers.this[each.key].db_servers[*].properties[0].ocid
```

That's why the only thing you set in tfvars is the **key** (`infra_key = "infra1"`).

---

## 9. Scaling: adding more resources

**Add a second VM cluster on the same infra/network** — just add a map entry:

```hcl
gcp_vm_clusters = {
  vmc1 = { infra_key = "infra1", network_key = "net1", cloud_vm_cluster_id = "vmc-prod", ... }
  vmc2 = {                                   # ← new
    infra_key               = "infra1"
    network_key             = "net1"
    cloud_vm_cluster_id     = "vmc-reporting"
    hostname_prefix         = "rpt"
    cpu_core_count          = 8
    memory_size_gb          = 120
    db_node_storage_size_gb = 120
    data_storage_size_tb    = 4
    ssh_public_keys         = ["ssh-rsa AAAA... your-key"]
  }
}
```

**Add a whole second stack** in another region: add a `net2` to `gcp_odb_networks`, an `infra2` to
`gcp_exadata_infras` (with its own `location`/`gcp_oracle_zone`), and a `vmc3` pointing at them.
No `.tf` changes — `terraform plan` will show only the additions.

---

## 10. Outputs

| Output | Shape | Notes |
|--------|-------|-------|
| `odb_networks` | map keyed by network key | `odb_network_name`, `client_subnet_name`, `backup_subnet_name` |
| `exadata_infras` | map keyed by infra key | `infra_name`, `ocid` |
| `vm_clusters` | map keyed by cluster key | `vm_cluster_name`, **`ocid`** |
| `db_servers` | map keyed by cluster key | list of discovered DB server OCIDs |

```bash
terraform output vm_clusters
terraform output -json | jq '.vm_clusters.value.vmc1.ocid'
```

The cluster **`ocid`** is the handle you feed to the `oracle/oci` provider if you go on to create
DB Homes / CDBs / PDBs on the cluster.

---

## 11. Day-2 operations

- **Change CPU/memory/storage:** the VM cluster module marks `cpu_core_count`, `memory_size_gb`,
  `db_node_storage_size_gb`, `data_storage_size_tb`, `ssh_public_keys`, and `db_server_ocids` under
  `lifecycle { ignore_changes }`. This prevents drift (e.g. elastic scaling performed in the console)
  from forcing a destroy/recreate. To resize *through Terraform*, remove the relevant field from
  `ignore_changes` in `modules/vm-cluster/main.tf` first.
- **Add SSH keys:** because `ssh_public_keys` is in `ignore_changes`, key changes via tfvars are not
  applied by default — manage keys in the console, or remove it from `ignore_changes`.
- **State:** this blueprint uses local state by default. For team use, add a `backend "gcs"` block to
  `main.tf` and re-run `terraform init`.

---

## 12. Destroying

`deletion_protection` defaults to **`true`** on networks, infras, and clusters. To tear down:

```hcl
# in terraform.tfvars, set deletion_protection = false on the entries you want to remove
```
```bash
terraform apply      # apply the deletion_protection = false change first
terraform destroy
```

Destroy order is handled automatically (clusters → infra → network).

---

## 13. Troubleshooting

| Symptom | Likely cause / fix |
|---------|--------------------|
| `Error 403 ... oracledatabase.googleapis.com ... has not been used` | API not enabled — run the `gcloud services enable` command in §3. |
| `Error 403` / permission denied on apply | Missing `roles/oracledatabase.admin` or network roles on your identity. |
| `cannot delete ... deletion_protection is enabled` | Set `deletion_protection = false` for that entry and `apply` before `destroy`. |
| CIDR / subnet validation error | Client and backup CIDRs must be RFC1918, /27–/22, and non-overlapping. |
| Oracle zone not available | The `gcp_oracle_zone` isn't offered for your project/region — pick a valid zone. |
| Apply seems to hang for a long time | Expected — infra/cluster provisioning is measured in hours; the modules allow up to 12h. |
| `Invalid index` on `module.exadata_infra[...]` | A cluster's `infra_key`/`network_key` doesn't match an existing map key. |

Validate before applying:

```bash
terraform fmt -recursive
terraform validate
```

---

## 14. FAQ

**Do I ever edit the `.tf` files?**
Only for things the maps don't expose (custom backends, removing an `ignore_changes` entry). Routine
work — more clusters, different sizes, new regions — is all in `terraform.tfvars`.

**Can I run this with OpenTofu?**
Yes. Replace `terraform` with `tofu`; OpenTofu resolves `hashicorp/google` from its own registry.

**How do I create databases (CDB/PDB) on the cluster?**
Use the cluster `ocid` output with the `oracle/oci` provider. The main Terraflow Studio app can
generate that layer; this blueprint stops at the VM cluster.

**Is the state safe to commit?**
No — `terraform.tfstate` can contain sensitive values. Use a remote backend and keep state out of git.
