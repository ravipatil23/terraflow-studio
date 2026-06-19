# Oracle Database — many DB Homes, each with many CDBs, each with many PDBs
#
# Hierarchy: VM cluster -> DB Homes -> CDBs -> PDBs.
#   • a DB Home is created on a VM cluster
#   • each DB Home hosts one or more CDBs
#   • each CDB hosts one or more PDBs
#   • a CDB belongs to exactly one Home; a PDB belongs to exactly one CDB
#
# Scale by editing terraform.tfvars only: add a home / CDB / PDB by adding a map
# entry at the matching level. No .tf edits. Layers on EXISTING Exadata VM
# cluster(s) (created by db-at-aws / db-at-gcp / db-at-azure, or native OCI).

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

# ── DB Homes — one entry per home in var.db_homes ─────────────────────────────
module "db_home" {
  source   = "./modules/db-home"
  for_each = var.db_homes

  vm_cluster_ocid = each.value.vm_cluster_ocid != "" ? each.value.vm_cluster_ocid : var.vm_cluster_ocid
  display_name    = each.value.display_name != "" ? each.value.display_name : each.key
  db_version      = each.value.db_version
}

# ── Flatten homes -> cdbs (key "<homeKey>.<cdbKey>") and homes -> cdbs -> pdbs ─
locals {
  cdb_list = flatten([
    for hk, hv in var.db_homes : [
      for ck, cv in hv.cdbs : {
        key                     = "${hk}.${ck}"
        home_key                = hk
        db_name                 = cv.db_name
        character_set           = cv.character_set
        ncharacter_set          = cv.ncharacter_set
        db_unique_name          = cv.db_unique_name
        sid_prefix              = cv.sid_prefix
        auto_backup_enabled     = cv.auto_backup_enabled
        auto_backup_window      = cv.auto_backup_window
        recovery_window_in_days = cv.recovery_window_in_days
      }
    ]
  ])
  cdb_instances = { for c in local.cdb_list : c.key => c }

  pdb_list = flatten([
    for hk, hv in var.db_homes : [
      for ck, cv in hv.cdbs : [
        for pk, pv in cv.pdbs : {
          key      = "${hk}.${ck}.${pk}"
          cdb_key  = "${hk}.${ck}"
          pdb_name = pv.pdb_name
        }
      ]
    ]
  ])
  pdb_instances = { for p in local.pdb_list : p.key => p }
}

# ── Container Databases — one per "<homeKey>.<cdbKey>" ─────────────────────────
module "cdb" {
  source   = "./modules/cdb"
  for_each = local.cdb_instances

  db_home_id              = module.db_home[each.value.home_key].db_home_id
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

# ── Pluggable Databases — one per "<homeKey>.<cdbKey>.<pdbKey>" ────────────────
module "pdb" {
  source   = "./modules/pdb"
  for_each = local.pdb_instances

  container_database_id = module.cdb[each.value.cdb_key].cdb_id
  pdb_name              = each.value.pdb_name
  pdb_admin_password    = var.pdb_admin_passwords[each.key]

  depends_on = [module.cdb]
}
