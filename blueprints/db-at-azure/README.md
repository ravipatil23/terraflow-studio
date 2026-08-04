# Oracle Database@Azure — Terraform Blueprint

A complete, standalone Terraform configuration for deploying **Oracle Database@Azure**
(Oracle Exadata Database Service on Azure). You only edit [`terraform.tfvars`](terraform.tfvars) —
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
   - [`azure_vnets`](#72-azure_vnets)
   - [`azure_infras`](#73-azure_infras)
   - [`azure_clusters`](#74-azure_clusters)
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
| 1 | VNet + Oracle-delegated subnet | `azurerm_virtual_network`, `azurerm_subnet` | `modules/vnet` |
| 2 | Exadata Infrastructure | `azurerm_oracle_exadata_infrastructure` | `modules/exadata-infra` |
| 3 | VM Cluster | `azurerm_oracle_cloud_vm_cluster` | `modules/vm-cluster` |

The subnet is automatically **delegated to `Oracle.Database/networkAttachments`**, which Azure
requires before a VM cluster can attach to it.

**Provider:** `hashicorp/azurerm >= 4.9.0` · **Terraform:** `>= 1.5.0` (or OpenTofu `>= 1.6.0`).

---

## 2. Architecture

```
                          ┌─────────────────────────────────────────────┐
                          │   Azure subscription / resource group        │
                          │                                              │
  terraform.tfvars        │   ┌────────────────────────────────────┐    │
  ┌───────────────┐       │   │  VNet  (modules/vnet)               │    │
  │ azure_vnets    │──────┼──▶│   └─ subnet delegated to            │    │
  │                │      │   │      Oracle.Database/networkAttach… │    │
  ├───────────────┤       │   └────────────────────────────────────┘    │
  │ azure_infras   │──────┼──▶┌────────────────────────────────────┐     │
  │                │      │   │  Exadata Infrastructure             │    │
  ├───────────────┤       │   └──────────────┬─────────────────────┘    │
  │ azure_clusters │       │   ┌──────────────▼─────────────────────┐    │
  │                │──────┼──▶│  VM Cluster (modules/vm-cluster)    │    │
  └───────────────┘       │   │  (attaches to delegated subnet)     │    │
        map keys          │   └─────────────────────────────────────┘    │
   wire everything        │                                              │
                          └─────────────────────────────────────────────┘
```

The three maps in `terraform.tfvars` are joined by **keys**, not by IDs:

```
azure_clusters["vmc1"].vnet_ref  = "vnet1"   ─▶ azure_vnets["vnet1"]
azure_clusters["vmc1"].infra_ref = "infra1"  ─▶ azure_infras["infra1"]
```

---

## 3. Prerequisites

Before `terraform apply`:

1. **Oracle Database@Azure enabled** for your subscription. Set it up through the Azure Marketplace
   (“Oracle Database@Azure”) and complete the Oracle/Azure account linking. This is a one-time,
   subscription-level step done outside Terraform.
2. **An existing resource group.** This blueprint does **not** create it — set `resource_group_name`
   to one that already exists:
   ```bash
   az group create --name rg-oracle-prod --location eastus    # if you need to create one
   ```
3. **The `Oracle.Database` resource provider registered** in the subscription:
   ```bash
   az provider register --namespace Oracle.Database
   ```
4. **A region where Oracle Database@Azure is offered**, and the availability **zone** number for it
   (e.g. `"2"`).
5. **RBAC permissions** to create networking + Oracle.Database resources in the resource group.
6. **Capacity / quota** for the chosen shape in that region/zone.
7. **Terraform `>= 1.5.0`** (the configuration uses optional object attributes).

---

## 4. Authentication

Sign in with the Azure CLI and select the subscription:

```bash
az login
az account set --subscription "00000000-0000-0000-0000-000000000000"
```

Set the same `subscription_id` in `terraform.tfvars` (the provider has
`subscription_id = var.subscription_id`). For automation, a service principal works too:

```bash
export ARM_CLIENT_ID=...  ARM_CLIENT_SECRET=...  ARM_TENANT_ID=...  ARM_SUBSCRIPTION_ID=...
```

---

## 5. Repository layout

```
db-at-azure/
├── main.tf              # provider + module wiring (do not need to edit)
├── variables.tf         # variable definitions (do not need to edit)
├── outputs.tf           # outputs (do not need to edit)
├── terraform.tfvars     # ◀── YOU EDIT THIS
└── modules/
    ├── vnet/            # VNet + Oracle-delegated subnet
    ├── exadata-infra/   # Exadata infrastructure
    └── vm-cluster/      # VM cluster
```

---

## 6. Quick start

```bash
cd blueprints/db-at-azure

# 1. authenticate
az login

# 2. edit terraform.tfvars — set subscription_id, resource_group_name (must exist),
#    location, VNet/subnet CIDRs, zone, and your real SSH public key

# 3. run
terraform init
terraform plan           # review what will be created
terraform apply
```

> **Heads-up on timing:** the Exadata infrastructure plus VM cluster can take **several hours** to
> provision. The modules set generous `timeouts` (infra create = 6h, cluster create = 3h) so apply
> does not abort early.

---

## 7. Variable reference

### 7.1 Top-level variables

| Variable | Type | Required | Description |
|----------|------|----------|-------------|
| `subscription_id` | string | ✅ | Azure subscription ID. |
| `resource_group_name` | string | ✅ | Existing resource group (not created by this config). |
| `location` | string | ✅ | Azure region, e.g. `eastus`. |
| `tags` | map(string) | — | Tags applied to all resources. Default `{}`. |

### 7.2 `azure_vnets`

Map of VNets, each with one Oracle-delegated subnet. The map **key** is referenced by
`azure_clusters[*].vnet_ref`.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `vnet_name` | string | — (required) | Name of the virtual network. |
| `address_space` | string | — (required) | VNet CIDR, e.g. `10.20.0.0/16`. |
| `subnet_name` | string | — (required) | Name of the delegated subnet. |
| `subnet_address_prefix` | string | — (required) | Subnet CIDR, e.g. `10.20.1.0/24`. |

> The subnet is created with a `delegation` block for `Oracle.Database/networkAttachments` — you do
> not configure this yourself.

### 7.3 `azure_infras`

Map of Exadata infrastructures. The map **key** is referenced by `azure_clusters[*].infra_ref`.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | string | — (required) | Azure resource name. |
| `display_name` | string | — (required) | Friendly display name. |
| `zone` | string | — (required) | Availability zone **number** as a string, e.g. `"2"`. |
| `shape` | string | `Exadata.X11M` | Exadata shape. |
| `compute_count` | number | `2` | Compute nodes. |
| `storage_count` | number | `3` | Storage servers. |

> The module also exposes maintenance-window inputs (`mw_preference`, `mw_patching_mode`,
> `mw_lead_time_in_weeks`, `mw_days_of_week`, etc.) with sensible defaults. To use a custom window,
> pass them through `main.tf` or extend the `azure_infras` object type.

### 7.4 `azure_clusters`

Map of VM clusters. `infra_ref` and `vnet_ref` must match keys in `azure_infras` / `azure_vnets`.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | string | — (required) | Azure resource name. |
| `display_name` | string | — (required) | Friendly display name. |
| `hostname` | string | — (required) | Hostname for cluster nodes. |
| `infra_ref` | string | — (required) | Key into `azure_infras`. |
| `vnet_ref` | string | — (required) | Key into `azure_vnets`. |
| `cpu_core_count` | number | `4` | Enabled CPU cores. |
| `data_storage_size_in_tbs` | number | `2` | Data storage (TB). |
| `memory_size_in_gbs` | number | `60` | Memory (GB). |
| `db_node_storage_size_in_gbs` | number | `120` | Local node storage (GB). |
| `gi_version` | string | `23.0.0.0` | Grid Infrastructure **major-version selector**. Oracle resolves it to the running release (`19.0.0.0` → `19.32.0.0.0`) and stores that in state, so config and state never match — see [9](#9-scaling-adding-more-resources). Covered by the module's `ignore_changes` guard. |
| `license_model` | string | `LicenseIncluded` | or `BringYourOwnLicense` (Azure-style casing). |
| `ssh_public_keys` | list(string) | `[]` | SSH keys for node access (set this!). |
| `local_backup_enabled` | bool | `false` | Enable local backups. |
| `sparse_diskgroup_enabled` | bool | `false` | Enable sparse disk group. |
| `cluster_name` | string | `""` | Optional cluster name. |
| `time_zone` | string | `UTC` | e.g. `America/New_York`. |
| `scan_listener_port_tcp` | number | `1521` | SCAN listener port. |
| `backup_subnet_cidr` | string | `192.168.252.0/22` | Backup range Oracle carves inside the VNet, e.g. `10.0.11.0/24`. Must differ per cluster when several share a `vnet_ref` — see [9](#9-scaling-adding-more-resources). **Never set it to `""`**: the attribute is `ForceNew` and not `Computed`, so an empty config makes every later plan propose replacing the cluster. |

> The underlying module supports further fields that this root does not expose yet (`domain`,
> `data_storage_percentage`, `scan_listener_port_tcp_ssl`, `system_version`, `zone_id`, `db_servers`,
> `file_system_configuration`, and the `dco_*` toggles). Add them to the `azure_clusters` object type
> in `variables.tf` and wire them in `main.tf` if you need them.

---

## 8. How resources are wired

You never paste a subnet ID, VNet ID, or infra ID. The root `main.tf` resolves them:

```hcl
# cluster → infra ID (from the infra module output)
cloud_exadata_infrastructure_id = module.exadata_infra[each.value.infra_ref].infra_id

# cluster → delegated subnet ID + VNet ID (from the vnet module outputs)
subnet_id          = module.vnet[each.value.vnet_ref].subnet_id
virtual_network_id = module.vnet[each.value.vnet_ref].vnet_id
```

That's why the only thing you set in tfvars is the **key** (`infra_ref = "infra1"`).

---

## 9. Scaling: adding more resources

**Add a second VM cluster on the same infra/VNet** — just add a map entry. Pointing at the same
`vnet_ref` reuses the existing delegated subnet; no second subnet is created.

The one field you must not reuse is `backup_subnet_cidr`. The delegated subnet is shared by design,
but Oracle carves the backup range inside the VNet **per cluster** — so once more than one cluster
shares a `vnet_ref`, give each its own non-overlapping range:

```hcl
azure_clusters = {
  vmc1 = {
    name = "vmc-prod", display_name = "VM Cluster Prod", hostname = "exadb"
    infra_ref = "infra1", vnet_ref = "vnet1"
    backup_subnet_cidr = "10.0.10.0/24"      # ← add one to the existing cluster too
    ...
  }
  vmc2 = {                                   # ← new
    name               = "vmc-reporting"
    display_name       = "VM Cluster Reporting"
    hostname           = "rpt"
    infra_ref          = "infra1"
    vnet_ref           = "vnet1"             # same delegated subnet as vmc1
    backup_subnet_cidr = "10.0.11.0/24"      # must not overlap vmc1's
    cpu_core_count     = 8
    ssh_public_keys    = ["ssh-rsa AAAA... your-key"]
  }
}
```

Pick ranges inside the VNet `address_space` that do not overlap each other or the delegated
`subnet_address_prefix`. Terraform does not check this for you — a collision surfaces as an Azure
error during apply. Both clusters default to the same `192.168.252.0/22`, so the second one must be
given its own range.

**Never set `backup_subnet_cidr` to `""`.** The attribute is `ForceNew` and not `Computed`, and the
provider reads the API's value back into state. An empty config therefore compares `null` against
the range the service assigned, and every later `terraform plan` proposes **destroying and
recreating the cluster** — a multi-hour rebuild. Always state the range explicitly; the default
`192.168.252.0/22` is the range the service would have picked anyway.

### Why the module has an `ignore_changes` guard

On `azurerm_oracle_cloud_vm_cluster` almost every argument is `ForceNew`, and the provider's
`Update()` handles only `tags` and `file_system_configuration`. **Anything else that changes outside
Terraform proposes destroying the cluster rather than correcting it** — a multi-hour rebuild.

Three optional arguments are `ForceNew` *without* being `Computed`, which makes them the ones that
diff against an empty config. They are guarded by default:

| Guarded | Why |
|---|---|
| `backup_subnet_cidr` | Not `Computed`, so a blank config diffs against the range the service assigns. |
| `gi_version` | A **major-version selector** — Oracle resolves `19.0.0.0` to the running release (`19.32.0.0.0`) and stores that. It moves again with every quarterly GI patch, so pinning the resolved release only delays the diff. |
| `scan_listener_port_tcp_ssl` | Passed as `null` unless you set a port, so it diffs against any port the service assigns. |

The other optional arguments — `cluster_name`, `domain`, `time_zone`, `system_version`, `zone_id`,
`data_storage_percentage`, `local_backup_enabled`, `sparse_diskgroup_enabled` — **are** `Computed`.
Terraform adopts the state value when config omits them, so they need no guard while left blank and
guarding them would cost you real drift detection.

### Attributes changed outside Terraform

If your operations team patches or scales the cluster through the OCI console or Azure portal,
Terraform sees that as drift on a `ForceNew` attribute and proposes a rebuild. The module ships
these commented out in `modules/vm-cluster/main.tf` — uncomment the ones that apply to you:

```hcl
# system_version,              # Exadata image patching
# cpu_core_count,              # online OCPU scaling from the console
# ssh_public_keys,             # key rotation on the nodes
# data_storage_size_in_tbs,    # storage scaling
# memory_size_in_gbs,          # memory scaling
# db_node_storage_size_in_gbs, # local storage scaling
```

`cpu_core_count` deserves particular attention: Oracle supports **online** OCPU scaling, so an
operator resizing the cluster from the console leaves Terraform proposing to destroy it.

Each entry you add is drift Terraform will no longer report, so add them deliberately rather than
pre-emptively.

To change a guarded value deliberately, edit it and force the replacement yourself:

```bash
terraform apply -replace='module.vm_cluster["vmc1"].azurerm_oracle_cloud_vm_cluster.this'
```

One consequence worth knowing: with that guard in place Terraform will no longer report drift on
this field, so the cluster silently keeps whatever range Azure actually assigned. Confirm it once
after the first apply:

```bash
terraform state show 'module.vm_cluster["vmc1"].azurerm_oracle_cloud_vm_cluster.this' | grep backup_subnet_cidr
```

**Add a whole second stack** in another region: add a `vnet2` to `azure_vnets`, an `infra2` to
`azure_infras` (with its own `zone`), and a `vmc3` pointing at them. No `.tf` changes — `terraform
plan` shows only the additions. (All resources land in the single `resource_group_name`/`location`;
for multiple regions, run separate root configurations or extend the modules to take per-entry
location.)

---

## 10. Outputs

| Output | Shape | Notes |
|--------|-------|-------|
| `vnets` | map keyed by VNet key | `vnet_id`, `subnet_id` |
| `exadata_infras` | map keyed by infra key | `infra_id`, `infra_name` |
| `vm_clusters` | map keyed by cluster key | `cluster_id`, **`ocid`** |

```bash
terraform output vm_clusters
terraform output -json | jq '.vm_clusters.value.vmc1.ocid'
```

The cluster **`ocid`** is the handle you feed to the `oracle/oci` provider if you go on to create
DB Homes / CDBs / PDBs on the cluster.

---

## 11. Day-2 operations

- **Resource group is assumed to exist** — this config never creates or deletes it, so `destroy`
  leaves the RG intact.
- **Subnet delegation** is fixed to `Oracle.Database/networkAttachments`; don't repurpose the
  delegated subnet for other workloads.
- **Long-running creates** are covered by module `timeouts`. If you raise shapes/counts substantially,
  you may want to increase them further.
- **State:** local by default. For team use, add a `backend "azurerm"` block to `main.tf` and re-init.

---

## 12. Destroying

```bash
terraform destroy
```

Destroy order is handled automatically (cluster → infra → VNet/subnet). The pre-existing resource
group is not touched.

---

## 13. Troubleshooting

| Symptom | Likely cause / fix |
|---------|--------------------|
| `MissingSubscriptionRegistration` for `Oracle.Database` | Run `az provider register --namespace Oracle.Database`. |
| `ResourceGroupNotFound` | `resource_group_name` doesn't exist — create it or fix the name. |
| Subnet delegation / attachment errors | The subnet must be delegated to `Oracle.Database/networkAttachments` (the module does this) and not used by other resources. |
| Invalid `zone` | Use the zone **number** as a string (`"2"`), and one offered for Oracle in your region. |
| `license_model` rejected | Use Azure casing: `LicenseIncluded` or `BringYourOwnLicense`. |
| `Invalid index` on `module.exadata_infra[...]` | A cluster's `infra_ref`/`vnet_ref` doesn't match an existing map key. |
| Apply seems to hang for a long time | Expected — infra/cluster provisioning is measured in hours (timeouts up to 6h). |

Validate before applying:

```bash
terraform fmt -recursive
terraform validate
```

---

## 14. FAQ

**Do I ever edit the `.tf` files?**
Only for things the maps don't expose (custom backends, advanced VM-cluster fields, custom maintenance
windows). Routine work — more clusters, different sizes — is all in `terraform.tfvars`.

**Can I run this with OpenTofu?**
Yes. Replace `terraform` with `tofu`; OpenTofu resolves `hashicorp/azurerm` from its own registry.

**Why doesn't it create the resource group?**
Resource groups are usually governed centrally (policy, naming, RBAC). The blueprint takes an existing
one so it slots into your environment cleanly. Add an `azurerm_resource_group` resource to `main.tf`
if you'd rather Terraform own it.

**How do I create databases (CDB/PDB) on the cluster?**
Use the cluster `ocid` output with the `oracle/oci` provider. The main Terraflow Studio app can
generate that layer; this blueprint stops at the VM cluster.

**Is the state safe to commit?**
No — `terraform.tfstate` can contain sensitive values. Use a remote backend and keep state out of git.
