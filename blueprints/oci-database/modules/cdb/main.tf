terraform {
  required_providers {
    oci = {
      source  = "oracle/oci"
      version = ">= 6.0.0"
    }
  }
}

# Container Database (CDB) created in the DB Home.
resource "oci_database_database" "this" {
  db_home_id = var.db_home_id
  source     = "NONE"

  database {
    db_name        = var.db_name
    admin_password = var.admin_password
    character_set  = var.character_set
    ncharacter_set = var.ncharacter_set

    # Optional fields — omitted (null) unless you set them.
    pdb_name       = var.initial_pdb_name != "" ? var.initial_pdb_name : null
    db_unique_name = var.db_unique_name != "" ? var.db_unique_name : null
    sid_prefix     = var.sid_prefix != "" ? var.sid_prefix : null

    db_backup_config {
      auto_backup_enabled     = var.auto_backup_enabled
      auto_backup_window      = var.auto_backup_enabled ? var.auto_backup_window : null
      recovery_window_in_days = var.auto_backup_enabled ? var.recovery_window_in_days : null
    }
  }

  lifecycle {
    ignore_changes = [database[0].admin_password, source]
  }
}
