# Oracle Database (DB Home → CDB → PDB) — Terraform Blueprint

Standalone Terraform that creates the **database stack on top of an existing Exadata
VM cluster**: a Database Home, a Container Database (CDB), and an optional Pluggable
Database (PDB). You only edit [`terraform.tfvars`](terraform.tfvars) (passwords go in env vars).

> **Scope:** this assumes the VM cluster already exists. Create it first with the
> [`db-at-aws`](../db-at-aws), [`db-at-gcp`](../db-at-gcp), or [`db-at-azure`](../db-at-azure)
> blueprint (each outputs the cluster `ocid`), or use a native OCI Exadata cluster.

---

## Table of contents

1. [What this deploys](#1-what-this-deploys)
2. [Architecture](#2-architecture)
3. [Prerequisites](#3-prerequisites)
4. [Authentication & passwords](#4-authentication--passwords)
5. [Quick start](#5-quick-start)
6. [Variable reference](#6-variable-reference)
7. [Outputs](#7-outputs)
8. [Notes & gotchas](#8-notes--gotchas)
9. [Destroying](#9-destroying)

---

## 1. What this deploys

| Order | Resource | Terraform resource | Module |
|-------|----------|--------------------|--------|
| 1 | Database Home | `oci_database_db_home` | `modules/db-home` |
| 2 | Container Database | `oci_database_database` | `modules/cdb` |
| 3 | Pluggable Database *(optional)* | `oci_database_pluggable_database` | `modules/pdb` |

**Provider:** `oracle/oci >= 6.0.0` · **Terraform:** `>= 1.5.0` (or OpenTofu `>= 1.6.0`).

---

## 2. Architecture

```
  existing Exadata VM cluster (var.vm_cluster_ocid)
            │
            ▼
  ┌───────────────────┐   db_home_id    ┌───────────────────┐   cdb_id   ┌───────────────────┐
  │ DB Home           │ ──────────────▶ │ Container DB (CDB) │ ─────────▶ │ Pluggable DB (PDB)│
  │ (db-home module)  │                 │ (cdb module)      │            │ (pdb module)      │
  └───────────────────┘                 └───────────────────┘            └───────────────────┘
                                                                          created only if create_pdb=true
```

Each step's output OCID is wired into the next, so the chain provisions in order.

---

## 3. Prerequisites

1. **An existing Exadata VM cluster** and its **OCID** (`ocid1.cloudvmcluster...`). The
   `db-at-*` blueprints expose this as the `vm_clusters[*].ocid` output.
2. **IAM** permission to manage `database-family` in the compartment / region.
3. **A supported DB version** for the cluster's Grid Infrastructure (e.g. `19.28.0.0.0`, `23.0.0.0`).
4. **Terraform `>= 1.5.0`** and the `oracle/oci` provider (pulled automatically).

---

## 4. Authentication & passwords

**Provider auth** comes from your OCI config — no secrets in this code:

```bash
oci setup config           # creates ~/.oci/config
# or export OCI_CLI_USER / OCI_CLI_TENANCY / OCI_CLI_FINGERPRINT / OCI_CLI_KEY_FILE / OCI_CLI_REGION
```

**Database passwords are NOT in tfvars.** Export them as environment variables so they
never land in a file or state diff input:

```bash
export TF_VAR_admin_password='YourStr0ng#Pass1'       # CDB SYS password
export TF_VAR_pdb_admin_password='YourStr0ng#Pass2'   # PDB admin + TDE wallet password
```

Oracle password rules: 9–30 chars, at least 2 uppercase, 2 lowercase, 2 numbers, 2 special
characters, and no reuse of the DB name.

---

## 5. Quick start

```bash
cd blueprints/oci-database

# 1. auth + passwords
oci setup config
export TF_VAR_admin_password='...'
export TF_VAR_pdb_admin_password='...'

# 2. edit terraform.tfvars — set oci_region, vm_cluster_ocid, names, db_version

# 3. run
terraform init
terraform plan
terraform apply
```

> **Timing:** DB Home + CDB creation typically takes 30–60+ minutes; a PDB adds several more.

---

## 6. Variable reference

| Variable | Type | Required | Description |
|----------|------|----------|-------------|
| `oci_region` | string | ✅ | OCI region of the VM cluster. |
| `vm_cluster_ocid` | string | ✅ | OCID of the existing Exadata VM cluster. |
| `db_home_display_name` | string | — | DB Home name. Default `dbhome`. |
| `db_version` | string | — | Oracle version. Default `19.0.0.0`. |
| `db_name` | string | — | CDB name, ≤ 8 alphanumeric. Default `ORCL`. |
| `admin_password` | string (sensitive, **env**) | ✅ | CDB SYS password — set via `TF_VAR_admin_password`. |
| `character_set` / `ncharacter_set` | string | — | Defaults `AL32UTF8` / `AL16UTF16`. |
| `initial_pdb_name` | string | — | Optional PDB created with the CDB. Blank = CDB only. |
| `db_unique_name` / `sid_prefix` | string | — | Optional; blank = provider default. |
| `auto_backup_enabled` | bool | — | Managed backups. Default `false`. |
| `auto_backup_window` / `recovery_window_in_days` | string / number | — | Used only when backups enabled. Defaults `SLOT_TWO` / `30`. |
| `create_pdb` | bool | — | Create the PDB step. Default `true`. |
| `pdb_name` | string | — | PDB name, ≤ 30 chars, ≠ `db_name`. Default `PDB1`. |
| `pdb_admin_password` | string (sensitive, **env**) | ✅ if `create_pdb` | Set via `TF_VAR_pdb_admin_password`. |

---

## 7. Outputs

| Output | Notes |
|--------|-------|
| `db_home_id` | OCID of the Database Home. |
| `cdb_id` | OCID of the Container Database. |
| `db_name` | CDB name. |
| `pdb_id` | OCID of the PDB (`null` when `create_pdb = false`). |
| `pdb_name` | PDB name (`null` when `create_pdb = false`). |

---

## 8. Notes & gotchas

- **`initial_pdb_name` vs the PDB module:** setting `initial_pdb_name` creates a PDB *as part of
  the CDB create*; the separate `pdb` module (`create_pdb = true`) creates an *additional*
  pluggable database. Use either or both.
- **`admin_password` is under `ignore_changes`** in the CDB module — changing it in Terraform
  won't trigger an update (rotate it through the database tooling instead).
- **CDB-only:** set `create_pdb = false` (and leave `pdb_admin_password` unset) to stop at the CDB.
- **OpenTofu:** works — replace `terraform` with `tofu`.

---

## 9. Destroying

```bash
terraform destroy
```

Tears down PDB → CDB → DB Home (reverse order). The VM cluster is **not** touched — it's an
input, owned by whatever created it.
