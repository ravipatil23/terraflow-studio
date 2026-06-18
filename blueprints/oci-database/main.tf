# Oracle Database on an Exadata VM cluster — DB Home -> CDB -> PDB
#
# Layers the database stack on top of an EXISTING Exadata VM cluster (created by
# the db-at-aws / db-at-gcp / db-at-azure blueprints, or native OCI). You supply
# the VM cluster OCID; this creates a DB Home, a Container Database, and an
# optional Pluggable Database. Fill in terraform.tfvars and run.
#
# Apply order is automatic: db_home -> cdb -> pdb (via depends_on).

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

# ── Step 1: Database Home ─────────────────────────────────────────────────────
module "db_home" {
  source = "./modules/db-home"

  vm_cluster_ocid = var.vm_cluster_ocid
  display_name    = var.db_home_display_name
  db_version      = var.db_version
}

# ── Step 2: Container Database ────────────────────────────────────────────────
module "cdb" {
  source = "./modules/cdb"

  db_home_id              = module.db_home.db_home_id
  db_name                 = var.db_name
  admin_password          = var.admin_password
  character_set           = var.character_set
  ncharacter_set          = var.ncharacter_set
  initial_pdb_name        = var.initial_pdb_name
  db_unique_name          = var.db_unique_name
  sid_prefix              = var.sid_prefix
  auto_backup_enabled     = var.auto_backup_enabled
  auto_backup_window      = var.auto_backup_window
  recovery_window_in_days = var.recovery_window_in_days

  depends_on = [module.db_home]
}

# ── Step 3: Pluggable Database (optional) ─────────────────────────────────────
module "pdb" {
  source = "./modules/pdb"
  count  = var.create_pdb ? 1 : 0

  container_database_id = module.cdb.cdb_id
  pdb_name              = var.pdb_name
  pdb_admin_password    = var.pdb_admin_password

  depends_on = [module.cdb]
}
