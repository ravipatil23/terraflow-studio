# Oracle Database (many DB Homes → many CDBs → many PDBs) — Terraform Blueprint

Standalone Terraform that creates the **database stack on existing Exadata VM cluster(s)**,
built on the natural Oracle hierarchy: **a VM cluster hosts one or more Database Homes, each
Home hosts one or more Container Databases (CDBs), and each CDB hosts one or more Pluggable
Databases (PDBs)** — and a CDB belongs to exactly one Home, a PDB to exactly one CDB. You scale
by editing **only `terraform.tfvars`** (passwords go in env vars).

> **Scope:** the VM cluster(s) must already exist. Create them first with the
> [`db-at-aws`](../db-at-aws), [`db-at-gcp`](../db-at-gcp), or [`db-at-azure`](../db-at-azure)
> blueprint (each outputs the cluster `ocid`), or use native OCI Exadata clusters.

---

## Table of contents

1. [What this deploys](#1-what-this-deploys)
2. [The model & how to scale](#2-the-model--how-to-scale)
3. [Prerequisites](#3-prerequisites)
4. [Authentication & passwords](#4-authentication--passwords)
5. [Quick start](#5-quick-start)
6. [Variable reference](#6-variable-reference)
7. [Outputs](#7-outputs)
8. [Notes & gotchas](#8-notes--gotchas)
9. [Destroying](#9-destroying)

---

## 1. What this deploys

| Resource | Terraform resource | Module | Count |
|----------|--------------------|--------|-------|
| Database Home | `oci_database_db_home` | `modules/db-home` | one per `db_homes` entry |
| Container Database | `oci_database_database` | `modules/cdb` | one per nested `cdbs` entry |
| Pluggable Database | `oci_database_pluggable_database` | `modules/pdb` | one per nested `pdbs` entry |

**Provider:** `oracle/oci >= 6.0.0` · **Terraform:** `>= 1.5.0` (or OpenTofu `>= 1.6.0`).

---

## 2. The model & how to scale

```
            VM cluster(s)  (var.vm_cluster_ocid, overridable per home)
                  │
        ┌─────────┴──────────┐
   Home "home19"        Home "home23"             ← db_homes map (for_each)
   (19.28.0.0.0)        (23.0.0.0)
      │                     │
  ┌───┴────┐                │
 CDB sales  CDB hr        CDB dw                  ← each home's nested cdbs map
   │          │             │
 app rpt     emp          mart                    ← each CDB's nested pdbs map
```

Everything is driven by the nested maps — **no `.tf` edits**:

```hcl
db_homes = {
  home19 = {                        # ← add a Home: new top-level key (its own db_version)
    db_version = "19.28.0.0.0"
    cdbs = {
      sales = {                     # ← add a CDB: new key under the home's cdbs
        db_name = "SALES"
        pdbs = {
          app = { pdb_name = "SALESAPP" }   # ← add a PDB: new key under the CDB's pdbs
          rpt = { pdb_name = "SALESRPT" }
        }
      }
    }
  }
  home23 = { db_version = "23.0.0.0", cdbs = { dw = { db_name = "DW", pdbs = { mart = { pdb_name = "DWMART" } } } } }
}
```

Under the hood the root flattens the tree into keyed maps — CDBs keyed `"<homeKey>.<cdbKey>"`
(e.g. `home19.sales`) and PDBs keyed `"<homeKey>.<cdbKey>.<pdbKey>"` (e.g. `home19.sales.app`) —
so each CDB is wired to its Home's `db_home_id` and each PDB to its CDB's `cdb_id` automatically.

**Multiple Homes / clusters:** each home sets its own `db_version` (e.g. a 19c home and a 23ai
home side by side). By default all homes land on the top-level `vm_cluster_ocid`; a home can set
its own `vm_cluster_ocid` to live on a different cluster.

---

## 3. Prerequisites

1. **Existing Exadata VM cluster(s)** and their **OCID(s)** (`ocid1.cloudvmcluster...`) — the
   `db-at-*` blueprints expose this as `vm_clusters[*].ocid`.
2. **IAM** to manage `database-family` in the compartment / region.
3. **Supported DB versions** for each cluster's Grid Infrastructure (e.g. `19.28.0.0.0`, `23.0.0.0`).
4. **Terraform `>= 1.5.0`** and the `oracle/oci` provider (pulled automatically).

---

## 4. Authentication & passwords

**Provider auth** comes from your OCI config — no secrets in this code:

```bash
oci setup config        # ~/.oci/config
# or export OCI_CLI_USER / OCI_CLI_TENANCY / OCI_CLI_FINGERPRINT / OCI_CLI_KEY_FILE / OCI_CLI_REGION
```

**Database passwords are NOT in tfvars.** Supply them as JSON maps via environment variables,
keyed to match the map keys (`"<home>.<cdb>"` for CDBs, `"<home>.<cdb>.<pdb>"` for PDBs):

```bash
export TF_VAR_cdb_admin_passwords='{"home19.sales":"YourStr0ng#1","home19.hr":"YourStr0ng#2","home23.dw":"YourStr0ng#3"}'
export TF_VAR_pdb_admin_passwords='{"home19.sales.app":"YourStr0ng#4","home19.sales.rpt":"YourStr0ng#5","home19.hr.emp":"YourStr0ng#6","home23.dw.mart":"YourStr0ng#7"}'
```

Oracle password rules: 9–30 chars, ≥ 2 uppercase, 2 lowercase, 2 digits, 2 special chars, and
not the DB name. A missing key surfaces as an apply-time error for that CDB/PDB.

---

## 5. Quick start

```bash
cd blueprints/oci-database

# 1. auth + passwords (keys must match the maps in terraform.tfvars)
oci setup config
export TF_VAR_cdb_admin_passwords='{"home19.sales":"...","home19.hr":"...","home23.dw":"..."}'
export TF_VAR_pdb_admin_passwords='{"home19.sales.app":"...","home19.sales.rpt":"...","home19.hr.emp":"...","home23.dw.mart":"..."}'

# 2. edit terraform.tfvars — oci_region, vm_cluster_ocid, and the db_homes tree

# 3. run
terraform init
terraform plan
terraform apply
```

> **Timing:** each DB Home + its first CDB typically takes 30–60+ minutes; extra CDBs/PDBs add more.

---

## 6. Variable reference

| Variable | Type | Required | Description |
|----------|------|----------|-------------|
| `oci_region` | string | ✅ | OCI region of the VM cluster(s). |
| `vm_cluster_ocid` | string | ✅ | Default VM cluster OCID for homes that don't override it. |
| `db_homes` | map(object) | — | Map of DB Homes (see below). Default `{}`. |
| `cdb_admin_passwords` | map(string), sensitive (**env**) | ✅ per CDB | CDB SYS passwords keyed `"<home>.<cdb>"`. |
| `pdb_admin_passwords` | map(string), sensitive (**env**) | ✅ per PDB | PDB passwords keyed `"<home>.<cdb>.<pdb>"`. |

**`db_homes` entry fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `db_version` | string | — (required) | Oracle version for this home, e.g. `19.28.0.0.0`. |
| `display_name` | string | home key | DB Home display name. |
| `vm_cluster_ocid` | string | top-level `vm_cluster_ocid` | Put this home on a different cluster. |
| `cdbs` | map(object) | `{}` | Nested map of CDBs in this home. |

**`cdbs` entry fields:** `db_name` (required, ≤ 8 alphanumeric); `character_set` / `ncharacter_set`
(`AL32UTF8` / `AL16UTF16`); `db_unique_name` / `sid_prefix` (`""`); `auto_backup_enabled` (`false`);
`auto_backup_window` / `recovery_window_in_days` (`SLOT_TWO` / `30`); `pdbs` (nested map, default `{}`).

**`pdbs` entry fields:** `pdb_name` (required, ≤ 30 chars, ≠ the CDB name).

---

## 7. Outputs

| Output | Shape |
|--------|-------|
| `db_homes` | Map keyed by home key → `{ db_home_id }`. |
| `cdbs` | Map keyed by `"<home>.<cdb>"` → `{ cdb_id, db_name }`. |
| `pdbs` | Map keyed by `"<home>.<cdb>.<pdb>"` → `{ pdb_id, pdb_name }`. |

```bash
terraform output db_homes
terraform output -json pdbs | jq
```

---

## 8. Notes & gotchas

- **Hierarchy is enforced by structure:** CDBs live under a home, PDBs under a CDB — a CDB/PDB
  can't span homes. Multiple homes (e.g. different DB versions) coexist on the same cluster, or
  spread across clusters via each home's `vm_cluster_ocid`.
- **Passwords are per-entry and keyed.** CDB key = `"<home>.<cdb>"`; PDB key = `"<home>.<cdb>.<pdb>"`.
  Mismatched/missing keys fail at apply for that DB.
- **`admin_password` is under `ignore_changes`** in the CDB module — rotate it through the
  database tooling, not Terraform.
- **Renaming any map key** destroys and recreates that home/CDB/PDB (Terraform identity is the key).
- **OpenTofu** works — replace `terraform` with `tofu`.

---

## 9. Destroying

```bash
terraform destroy
```

Tears down PDBs → CDBs → DB Homes (reverse dependency order). The VM cluster(s) are **not**
touched — they're inputs, owned by whatever created them.
