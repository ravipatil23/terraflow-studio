# Oracle Database@AWS — Terraform Blueprint

A complete, standalone Terraform configuration for deploying **Oracle Database@AWS**
(Oracle Exadata Database Service on AWS). You only edit [`terraform.tfvars`](terraform.tfvars) —
the `.tf` files are reusable as-is.

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
   - [`aws_networks`](#72-aws_networks)
   - [`aws_infras`](#73-aws_infras)
   - [`aws_clusters`](#74-aws_clusters)
   - [`aws_peerings`](#75-aws_peerings)
8. [How resources are wired](#8-how-resources-are-wired)
   - [Using an existing network or infrastructure](#81-using-an-existing-network-or-infrastructure)
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
| 1 | ODB Network | `aws_odb_network` | `modules/odb-network` |
| 2 | Exadata Infrastructure | `aws_odb_cloud_exadata_infrastructure` | `modules/exadata-infra` |
| 3 | VM Cluster | `aws_odb_cloud_vm_cluster` | `modules/vm-cluster` |
| — *(optional)* | Network peering | `aws_odb_network_peering_connection` | `modules/peering` |

A data source (`aws_odb_db_servers`) sits between steps 2 and 3 to **auto-discover** the DB server
IDs from the infrastructure and hand them to the cluster — you never copy IDs by hand.

**Provider:** `hashicorp/aws >= 6.15.0` · **Terraform:** `>= 1.5.0` (or OpenTofu `>= 1.6.0`).

---

## 2. Architecture

```
                          ┌─────────────────────────────────────────────┐
                          │             Your AWS account                 │
                          │                                              │
  terraform.tfvars        │   ┌────────────────────────────────────┐    │
  ┌───────────────┐       │   │  ODB Network  (modules/odb-network) │    │
  │ aws_networks   │──────┼──▶│   ├─ client subnet CIDR             │    │
  │                │      │   │   └─ backup subnet CIDR             │    │
  ├───────────────┤       │   └────────────────────────────────────┘    │
  │ aws_infras     │──────┼──▶┌────────────────────────────────────┐     │
  │                │      │   │  Exadata Infrastructure             │    │
  ├───────────────┤       │   └──────────────┬─────────────────────┘    │
  │ aws_clusters   │       │   ┌──────────────▼─────────────────────┐    │
  │                │──────┼──▶│  data.aws_odb_db_servers            │    │
  ├───────────────┤       │   │       (auto-discovery)              │    │
  │ aws_peerings   │       │   └──────────────┬─────────────────────┘    │
  │  (optional)    │──┐    │   ┌──────────────▼─────────────────────┐    │
  └───────────────┘  │    │   │  VM Cluster (modules/vm-cluster)    │    │
        map keys     │    │   └─────────────────────────────────────┘    │
   wire everything   │    │   ┌─────────────────────────────────────┐    │
                     └────┼──▶│  Peering → your existing VPC        │    │
                          │   └─────────────────────────────────────┘    │
                          └─────────────────────────────────────────────┘
```

The maps in `terraform.tfvars` are joined by **keys**, not by IDs:

```
aws_clusters["vmc1"].network_ref = "net1"   ─▶ aws_networks["net1"]
aws_clusters["vmc1"].infra_ref   = "infra1"  ─▶ aws_infras["infra1"]
aws_peerings["peer1"].network_ref = "net1"   ─▶ aws_networks["net1"]
```

---

## 3. Prerequisites

Before `terraform apply`:

1. **Oracle Database@AWS enabled** for your account. Subscribe through AWS Marketplace
   (“Oracle Database@AWS”) and complete the Oracle/AWS account linking. This is a one-time,
   account-level step done outside Terraform.
2. **A region and AZ where ODB@AWS is offered.** You need the **availability zone ID** (e.g.
   `use1-az6`), not just the AZ name — find it with:
   ```bash
   aws ec2 describe-availability-zones --region us-east-1 \
     --query "AvailabilityZones[].{Name:ZoneName,Id:ZoneId}" --output table
   ```
3. **IAM permissions** for the `odb` service (ODB networks, Exadata infrastructure, VM clusters,
   peering) plus EC2 read access for AZ lookups, on the identity running Terraform.
4. **Service quotas / capacity** for the chosen shape in that AZ.
5. **A peer VPC** (only if you'll use `aws_peerings`) — you'll supply its `vpc-…` ID.
6. **Terraform `>= 1.5.0`** (the configuration uses optional object attributes).

---

## 4. Authentication

This blueprint uses the standard AWS credential chain — any of:

```bash
aws configure                      # writes ~/.aws/credentials
# or
export AWS_PROFILE=my-profile
# or
export AWS_ACCESS_KEY_ID=...  AWS_SECRET_ACCESS_KEY=...  AWS_SESSION_TOKEN=...
```

…or an EC2 instance role / SSO. The provider's region comes from `aws_region` in `terraform.tfvars`.
Each network/infra/cluster entry can override the region via its own `region` field.

---

## 5. Repository layout

```
db-at-aws/
├── main.tf              # provider + module wiring (do not need to edit)
├── variables.tf         # variable definitions (do not need to edit)
├── outputs.tf           # outputs (do not need to edit)
├── terraform.tfvars     # ◀── YOU EDIT THIS
└── modules/
    ├── odb-network/     # ODB network
    ├── exadata-infra/   # Exadata infrastructure
    ├── peering/         # ODB network peering (optional)
    └── vm-cluster/      # VM cluster
```

---

## 6. Quick start

```bash
cd blueprints/db-at-aws

# 1. authenticate
aws configure            # or export AWS_PROFILE

# 2. edit terraform.tfvars — set aws_region, availability_zone_id, subnet CIDRs,
#    gi_version, and your real SSH public key

# 3. run
terraform init
terraform plan           # review what will be created
terraform apply
```

> **Heads-up on timing:** the Exadata infrastructure plus VM cluster can take **several hours** to
> provision.

---

## 7. Variable reference

### 7.1 Top-level variables

| Variable | Type | Required | Description |
|----------|------|----------|-------------|
| `aws_region` | string | ✅ | Default AWS region for the deployment. Overridable per map entry via `region`. |
| `tags` | map(string) | — | Tags applied to all resources. Default `{}`. |
| `existing_odb_network_ids` | map(string) | — | IDs of ODB networks that already exist, keyed the way `network_ref` references them. Referenced only, never created. See [8.1](#81-using-an-existing-network-or-infrastructure). |
| `existing_infra_ids` | map(string) | — | IDs of Exadata infrastructures that already exist, keyed the way `infra_ref` references them. Referenced only, never created. See [8.1](#81-using-an-existing-network-or-infrastructure). |

### 7.2 `aws_networks`

Map of ODB networks. The map **key** is referenced by `aws_clusters[*].network_ref` and
`aws_peerings[*].network_ref`.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `display_name` | string | — (required) | Friendly name for the ODB network. |
| `availability_zone_id` | string | — (required) | AZ **ID** (e.g. `use1-az6`) where the network lives. |
| `client_subnet_cidr` | string | — (required) | CIDR for the client subnet. |
| `backup_subnet_cidr` | string | — (required) | CIDR for the backup subnet. |
| `s3_access` | string | `ENABLED` | `ENABLED` or `DISABLED`. |
| `zero_etl_access` | string | `DISABLED` | `ENABLED` or `DISABLED`. |
| `availability_zone` | string | `""` | AZ name override (usually leave blank; use the ID above). |
| `region` | string | `""` | Region override. |
| `custom_domain_name` | string | `""` | Custom DNS domain — mutually exclusive with `default_dns_prefix`. |
| `default_dns_prefix` | string | `""` | DNS prefix — used only when `custom_domain_name` is blank. |
| `delete_associated_resources` | bool | `false` | Delete associated resources on network deletion. |

### 7.3 `aws_infras`

Map of Exadata infrastructures. The map **key** is referenced by `aws_clusters[*].infra_ref`.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `display_name` | string | — (required) | Friendly name. |
| `availability_zone_id` | string | — (required) | AZ ID — should match the network's AZ. |
| `shape` | string | `Exadata.X11M` | Exadata shape. |
| `compute_count` | number | `2` | Compute nodes. |
| `storage_count` | number | `3` | Storage servers. |
| `availability_zone` / `region` | string | `""` | Overrides. |
| `database_server_type` / `storage_server_type` | string | `""` | Optional server-type pins. |
| `customer_contacts` | list(string) | `[]` | Emails sent to OCI for notifications. |
| `mw_preference` | string | `NO_PREFERENCE` | Maintenance-window preference. |
| `mw_patching_mode` | string | `ROLLING` | `ROLLING` or `NON_ROLLING`. |
| `mw_is_custom_action_timeout_enabled` | bool | `false` | Enable custom action timeout. |
| `mw_custom_action_timeout_in_mins` | number | `15` | Custom action timeout. |
| `mw_lead_time_in_weeks` | number | `0` | Lead time in weeks (0 → unset). |
| `mw_days_of_week` / `mw_months` | list(string) | `[]` | Custom-window days/months. |
| `mw_hours_of_day` / `mw_weeks_of_month` | list(number) | `[]` | Custom-window hours/weeks. |

### 7.4 `aws_clusters`

Map of VM clusters. `infra_ref` and `network_ref` must match keys in `aws_infras` / `aws_networks`.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `display_name` | string | — (required) | Friendly name. |
| `gi_version` | string | — (required) | Grid Infrastructure version (e.g. `23.0.0.0`). |
| `hostname_prefix` | string | — (required) | Hostname prefix for cluster nodes. |
| `infra_ref` | string | — (required) | Key into `aws_infras`. |
| `network_ref` | string | — (required) | Key into `aws_networks`. |
| `cpu_core_count` | number | `16` | Enabled CPU cores. |
| `license_model` | string | `LICENSE_INCLUDED` | or `BRING_YOUR_OWN_LICENSE`. |
| `ssh_public_keys` | list(string) | `[]` | SSH keys for node access (set this!). |
| `db_servers` | list(string) | `[]` | Explicit DB server IDs (manual mode only). |
| `db_servers_mode` | string | `auto` | `auto` = discover from infra; `manual` = use `db_servers`. |
| `dco_is_diagnostics_events_enabled` | bool | `true` | Diagnostics events. |
| `dco_is_health_monitoring_enabled` | bool | `true` | Health monitoring. |
| `dco_is_incident_logs_enabled` | bool | `true` | Incident logs. |
| `cluster_name` | string | `""` | Optional cluster name. |
| `timezone` | string | `""` | e.g. `UTC`. |
| `data_storage_size_in_tbs` | number | `null` | Data storage (TB). |
| `db_node_storage_size_in_gbs` | number | `null` | Local node storage (GB). |
| `memory_size_in_gbs` | number | `null` | Memory (GB). |
| `scan_listener_port_tcp` | number | `null` | SCAN listener port. |
| `is_local_backup_enabled` | bool | `false` | Enable local backups. |
| `is_sparse_diskgroup_enabled` | bool | `false` | Enable sparse disk group. |

### 7.5 `aws_peerings`

Optional. Map of ODB network peering connections. `network_ref` must match a key in `aws_networks`.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `display_name` | string | — (required) | Friendly name. |
| `network_ref` | string | — (required) | Key into `aws_networks` (the source ODB network). |
| `peer_network_id` | string | — (required) | The **peer VPC** ID (`vpc-…`). |
| `region` | string | `""` | Region override. |

---

## 8. How resources are wired

You never paste a network ID, infra ID, or DB-server ID. The root `main.tf` resolves them:

```hcl
# one keyspace for what this blueprint creates and what already exists
locals {
  odb_network_ids = merge({ for k, m in module.odb_network : k => m.network_id }, var.existing_odb_network_ids)
  infra_ids       = merge({ for k, m in module.exadata_infra : k => m.infra_id }, var.existing_infra_ids)
}

# cluster → infra ID and network ID
cloud_exadata_infrastructure_id = local.infra_ids[each.value.infra_ref]
odb_network_id                  = local.odb_network_ids[each.value.network_ref]

# cluster → DB server IDs (auto-discovered when db_servers_mode = "auto")
db_servers = each.value.db_servers_mode == "auto" ? data.aws_odb_db_servers.this[each.key].db_servers[*].id : each.value.db_servers

# peering → source ODB network ID
odb_network_id = local.odb_network_ids[each.value.network_ref]
```

That's why the only thing you set in tfvars is the **key** (`infra_ref = "infra1"`).

### 8.1 Using an existing network or infrastructure

If the ODB network or Exadata infrastructure was provisioned outside this blueprint — by hand, by
another stack, or by another team — give its **ID** under the same key your clusters already
reference, and leave the matching `aws_networks` / `aws_infras` entry out:

```hcl
existing_infra_ids = {
  infra1 = "odb-exa-0a1b2c3d4e5f67890"
}

aws_infras = {}                 # infra1 already exists — nothing to create

aws_clusters = {
  vmc1 = {
    display_name    = "vmc-prod-use1"
    gi_version      = "23.0.0.0"
    hostname_prefix = "exadb"
    infra_ref       = "infra1"  # unchanged — now resolves to the existing infra
    network_ref     = "net1"
    ssh_public_keys = ["ssh-rsa AAAA... your-key"]
  }
}
```

`existing_odb_network_ids` works the same way for `network_ref`, and peerings pick it up too.

Managed and existing resources share one keyspace, so you can mix them freely — create the network
here and reuse an existing infrastructure, or the reverse. Terraform never creates, changes or
destroys anything listed in an `existing_*` map; it only reads the ID.

Two things to know:

- Pass the **ID** (`odb-exa-…`, `odb-net-…`), not the ARN.
- Keep each resource in **one** map. Listing the same key in `aws_infras` *and*
  `existing_infra_ids` would create a new infrastructure and still wire the clusters to the
  existing one; a `check` block flags that at plan time.
- `db_servers_mode = "auto"` still works against an existing infrastructure — the
  `aws_odb_db_servers` data source queries it by ID like any other.

If you would rather Terraform *adopt* the resource and manage it from now on, use an `import` block
against the module address instead, fill in the matching `aws_infras` entry to match reality, and
confirm `terraform plan` reports no changes before applying.

---

## 9. Scaling: adding more resources

**Add a second VM cluster on the same infra/network** — just add a map entry:

```hcl
aws_clusters = {
  vmc1 = { display_name = "vmc-prod", gi_version = "23.0.0.0", hostname_prefix = "exadb", infra_ref = "infra1", network_ref = "net1", ... }
  vmc2 = {                                   # ← new
    display_name    = "vmc-reporting"
    gi_version      = "23.0.0.0"
    hostname_prefix = "rpt"
    infra_ref       = "infra1"
    network_ref     = "net1"
    cpu_core_count  = 8
    ssh_public_keys = ["ssh-rsa AAAA... your-key"]
  }
}
```

**Add a whole second stack** in another AZ/region: add a `net2` to `aws_networks`, an `infra2` to
`aws_infras`, and a `vmc3` pointing at them. No `.tf` changes — `terraform plan` shows only additions.

---

## 10. Outputs

| Output | Shape | Notes |
|--------|-------|-------|
| `odb_networks` | map keyed by network key | `network_id`, `network_arn` |
| `exadata_infras` | map keyed by infra key | `infra_id`, `infra_arn` |
| `peerings` | map keyed by peering key | `peering_connection_id` |
| `vm_clusters` | map keyed by cluster key | `vm_cluster_id`, **`ocid`** |
| `db_servers` | map keyed by cluster key | list of discovered DB server IDs |

```bash
terraform output vm_clusters
terraform output -json | jq '.vm_clusters.value.vmc1.ocid'
```

The cluster **`ocid`** is the handle you feed to the `oracle/oci` provider if you go on to create
DB Homes / CDBs / PDBs on the cluster.

---

## 11. Day-2 operations

- **DB server discovery:** with `db_servers_mode = "auto"`, the `data.aws_odb_db_servers` lookup runs
  on every plan and pins the current DB servers from the infra. Switch to `"manual"` and set
  `db_servers = [...]` if you need to control exactly which servers a cluster uses.
- **Peering CIDRs are update-only:** `peer_network_cidrs` is rejected by the AWS API on create. Create
  the peering first, then uncomment the `peer_network_cidrs` line in `modules/peering/main.tf` and the
  `peer_network_cidrs` variable, wire it through, and re-apply to manage allowed CIDRs.
- **State:** local by default. For team use, add an `backend "s3"` block to `main.tf` and re-init.

---

## 12. Destroying

```bash
terraform destroy
```

Destroy order is handled automatically (peering + clusters → infra → network). If a network has
`delete_associated_resources = false` and still has dependents, remove the dependents first.

---

## 13. Troubleshooting

| Symptom | Likely cause / fix |
|---------|--------------------|
| `UnauthorizedOperation` / `AccessDenied` on `odb:*` | Missing IAM permissions for the ODB service. |
| Invalid / unsupported `availability_zone_id` | Use the AZ **ID** (`use1-az6`), not the name; confirm ODB@AWS is offered there. |
| Cluster create fails to find DB servers | Infra not finished, or `infra_ref` points at the wrong key. Check `data.aws_odb_db_servers`. |
| Peering apply rejects `peer_network_cidrs` | It's update-only — add it after the peering exists (see §11). |
| `Invalid index` on `module.exadata_infra[...]` | A cluster's `infra_ref`/`network_ref` doesn't match an existing map key. |
| Apply seems to hang for a long time | Expected — infra/cluster provisioning is measured in hours. |

Validate before applying:

```bash
terraform fmt -recursive
terraform validate
```

---

## 14. FAQ

**Do I ever edit the `.tf` files?**
Only for things the maps don't expose (custom backends, enabling peering CIDRs). Routine work — more
clusters, different sizes, new AZs — is all in `terraform.tfvars`.

**Can I run this with OpenTofu?**
Yes. Replace `terraform` with `tofu`; OpenTofu resolves `hashicorp/aws` from its own registry.

**Auto vs manual DB servers — which should I use?**
`auto` is right for almost everyone: it lets the infra decide which DB servers back the cluster. Use
`manual` only when you must place a cluster on specific DB servers.

**How do I create databases (CDB/PDB) on the cluster?**
Use the cluster `ocid` output with the `oracle/oci` provider. The main Terraflow Studio app can
generate that layer; this blueprint stops at the VM cluster.

**Is the state safe to commit?**
No — `terraform.tfstate` can contain sensitive values. Use a remote backend and keep state out of git.
