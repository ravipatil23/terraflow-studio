# Oracle Database — one DB Home, many CDBs, each with many PDBs
#
# Principle: a single Database Home hosts multiple Container Databases (CDBs), and
# each CDB hosts multiple Pluggable Databases (PDBs). A CDB/PDB belongs to exactly
# ONE DB Home. Scale by adding entries to the `cdbs` map — and each CDB's nested
# `pdbs` map — in terraform.tfvars. No .tf edits needed.
#
# Layers on an EXISTING Exadata VM cluster (created by db-at-aws / db-at-gcp /
# db-at-azure, or native OCI) — you supply its vm_cluster_ocid.

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    oci = {
      source  = "oracle/oci"
      version = ">= 6.0.0"
    }
  }
}

# Auth comes from ~/.oci/config or OCI_* / TF_VAR_* env vars — no secrets here.
provider "oci" {
  region = var.oci_region
}

# ── The single Database Home ──────────────────────────────────────────────────
module "db_home" {
  source = "./modules/db-home"

  vm_cluster_ocid = var.vm_cluster_ocid
  display_name    = var.db_home_display_name
  db_version      = var.db_version
}

# ── Container Databases — one entry per CDB in var.cdbs ────────────────────────
module "cdb" {
  source   = "./modules/cdb"
  for_each = var.cdbs

  db_home_id              = module.db_home.db_home_id
  db_name                 = each.value.db_name
  admin_password          = var.cdb_admin_passwords[each.key]
  character_set           = each.value.character_set
  ncharacter_set          = each.value.ncharacter_set
  db_unique_name          = each.value.db_unique_name
  sid_prefix              = each.value.sid_prefix
  auto_backup_enabled     = each.value.auto_backup_enabled
  auto_backup_window      = each.value.auto_backup_window
  recovery_window_in_days = each.value.recovery_window_in_days

  depends_on = [module.db_home]
}

# ── Flatten cdbs -> pdbs into one map keyed "<cdbKey>.<pdbKey>" ────────────────
locals {
  pdb_list = flatten([
    for ck, cv in var.cdbs : [
      for pk, pv in cv.pdbs : {
        key      = "${ck}.${pk}"
        cdb_key  = ck
        pdb_name = pv.pdb_name
      }
    ]
  ])
  pdb_instances = { for p in local.pdb_list : p.key => p }
}

# ── Pluggable Databases — one entry per PDB across all CDBs ────────────────────
module "pdb" {
  source   = "./modules/pdb"
  for_each = local.pdb_instances

  container_database_id = module.cdb[each.value.cdb_key].cdb_id
  pdb_name              = each.value.pdb_name
  pdb_admin_password    = var.pdb_admin_passwords[each.key]

  depends_on = [module.cdb]
}
