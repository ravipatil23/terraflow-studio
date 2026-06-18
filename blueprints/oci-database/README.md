# Oracle Database (one DB Home → many CDBs → many PDBs) — Terraform Blueprint

Standalone Terraform that creates the **database stack on an existing Exadata VM cluster**,
built on one rule: **a single Database Home hosts multiple Container Databases (CDBs), and
each CDB hosts multiple Pluggable Databases (PDBs)** — and a CDB/PDB belongs to exactly one
DB Home. You scale by editing **only `terraform.tfvars`** (passwords go in env vars).

> **Scope:** the VM cluster must already exist. Create it first with the
> [`db-at-aws`](../db-at-aws), [`db-at-gcp`](../db-at-gcp), or [`db-at-azure`](../db-at-azure)
> blueprint (each outputs the cluster `ocid`), or use a native OCI Exadata cluster.

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
| Database Home | `oci_database_db_home` | `modules/db-home` | exactly **1** |
| Container Database | `oci_database_database` | `modules/cdb` | one per `cdbs` entry |
| Pluggable Database | `oci_database_pluggable_database` | `modules/pdb` | one per nested `pdbs` entry |

**Provider:** `oracle/oci >= 6.0.0` · **Terraform:** `>= 1.5.0` (or OpenTofu `>= 1.6.0`).

---

## 2. The model & how to scale

```
                  one DB Home (var.db_home_display_name)
                            │
            ┌───────────────┼───────────────┐
         CDB "sales"     CDB "hr"        CDB "..."        ← cdbs map (for_each)
          ┌────┴────┐        │
       PDB "app" PDB "rpt"  PDB "emp"                     ← each CDB's nested pdbs map
```

Everything is driven by the `cdbs` map and each CDB's nested `pdbs` map — **no `.tf` edits**:

```hcl
cdbs = {
  sales = {                     # ← add a CDB: new top-level key
    db_name = "SALES"
    pdbs = {
      app = { pdb_name = "SALESAPP" }   # ← add a PDB: new nested key
      rpt = { pdb_name = "SALESRPT" }
    }
  }
  hr = {
    db_name = "HR"
    pdbs = { emp = { pdb_name = "HREMP" } }
  }
}
```

Under the hood the root flattens `cdbs → pdbs` into one map keyed `"<cdbKey>.<pdbKey>"`
(e.g. `sales.app`), so each PDB is wired to its parent CDB's OCID automatically. There is
only ever **one** `db_home` resource — CDBs reference its `db_home_id`, PDBs reference their
CDB's `cdb_id`.

---

## 3. Prerequisites

1. **An existing Exadata VM cluster** and its **OCID** (`ocid1.cloudvmcluster...`) — the
   `db-at-*` blueprints expose this as `vm_clusters[*].ocid`.
2. **IAM** to manage `database-family` in the compartment / region.
3. **A supported DB version** for the cluster's Grid Infrastructure (e.g. `19.28.0.0.0`, `23.0.0.0`).
4. **Terraform `>= 1.5.0`** and the `oracle/oci` provider (pulled automatically).

---

## 4. Authentication & passwords

**Provider auth** comes from your OCI config — no secrets in this code:

```bash
oci setup config        # ~/.oci/config
# or export OCI_CLI_USER / OCI_CLI_TENANCY / OCI_CLI_FINGERPRINT / OCI_CLI_KEY_FILE / OCI_CLI_REGION
```

**Database passwords are NOT in tfvars.** Supply them as JSON maps via environment variables,
keyed to match the map keys (CDB key for CDBs; `"<cdbKey>.<pdbKey>"` for PDBs):

```bash
export TF_VAR_cdb_admin_passwords='{"sales":"YourStr0ng#1","hr":"YourStr0ng#2"}'
export TF_VAR_pdb_admin_passwords='{"sales.app":"YourStr0ng#3","sales.rpt":"YourStr0ng#4","hr.emp":"YourStr0ng#5"}'
```

Oracle password rules: 9–30 chars, ≥ 2 uppercase, 2 lowercase, 2 digits, 2 special chars, and
not the DB name. A missing key surfaces as an apply-time error for that CDB/PDB.

---

## 5. Quick start

```bash
cd blueprints/oci-database

# 1. auth + passwords (keys must match the maps in terraform.tfvars)
oci setup config
export TF_VAR_cdb_admin_passwords='{"sales":"...","hr":"..."}'
export TF_VAR_pdb_admin_passwords='{"sales.app":"...","sales.rpt":"...","hr.emp":"..."}'

# 2. edit terraform.tfvars — oci_region, vm_cluster_ocid, db_version, and the cdbs map

# 3. run
terraform init
terraform plan
terraform apply
```

> **Timing:** the DB Home + first CDB typically takes 30–60+ minutes; each extra CDB/PDB adds more.

---

## 6. Variable reference

| Variable | Type | Required | Description |
|----------|------|----------|-------------|
| `oci_region` | string | ✅ | OCI region of the VM cluster. |
| `vm_cluster_ocid` | string | ✅ | OCID of the existing Exadata VM cluster. |
| `db_home_display_name` | string | — | Name of the single DB Home. Default `dbhome`. |
| `db_version` | string | — | Oracle version. Default `19.0.0.0`. |
| `cdbs` | map(object) | — | Map of CDBs (see below). Default `{}`. |
| `cdb_admin_passwords` | map(string), sensitive (**env**) | ✅ per CDB | CDB SYS passwords keyed by CDB key. |
| `pdb_admin_passwords` | map(string), sensitive (**env**) | ✅ per PDB | PDB passwords keyed by `"<cdbKey>.<pdbKey>"`. |

**`cdbs` entry fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `db_name` | string | — (required) | CDB name, ≤ 8 alphanumeric. |
| `character_set` / `ncharacter_set` | string | `AL32UTF8` / `AL16UTF16` | Character sets. |
| `db_unique_name` / `sid_prefix` | string | `""` | Optional. |
| `auto_backup_enabled` | bool | `false` | Managed backups for this CDB. |
| `auto_backup_window` / `recovery_window_in_days` | string / number | `SLOT_TWO` / `30` | Used only when backups enabled. |
| `pdbs` | map(object) | `{}` | Nested map of PDBs; each entry has `pdb_name` (≤ 30 chars, ≠ CDB name). |

---

## 7. Outputs

| Output | Shape |
|--------|-------|
| `db_home_id` | OCID of the single DB Home. |
| `cdbs` | Map keyed by CDB key → `{ cdb_id, db_name }`. |
| `pdbs` | Map keyed by `"<cdbKey>.<pdbKey>"` → `{ pdb_id, pdb_name }`. |

```bash
terraform output cdbs
terraform output -json pdbs | jq
```

---

## 8. Notes & gotchas

- **One DB Home only.** By design every CDB lives in the single `db_home`; there is no map of
  homes. To use multiple DB Homes (e.g. different DB versions), run multiple copies of this
  blueprint in separate state/dirs.
- **Passwords are per-entry and keyed.** The CDB password map key = the `cdbs` key; the PDB
  password map key = `"<cdbKey>.<pdbKey>"`. Mismatched/missing keys fail at apply for that DB.
- **`admin_password` is under `ignore_changes`** in the CDB module — rotate it through the
  database tooling, not Terraform.
- **Renaming a map key** destroys and recreates that CDB/PDB (Terraform identity is the key).
- **OpenTofu** works — replace `terraform` with `tofu`.

---

## 9. Destroying

```bash
terraform destroy
```

Tears down PDBs → CDBs → DB Home (reverse dependency order). The VM cluster is **not** touched —
it's an input, owned by whatever created it.
