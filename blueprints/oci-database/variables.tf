# Variable definitions. Real values go in terraform.tfvars; passwords via env vars.

variable "oci_region" {
  description = "OCI region of the VM cluster, e.g. us-ashburn-1."
  type        = string
}

variable "vm_cluster_ocid" {
  description = "OCID of the existing Exadata VM cluster to host the database."
  type        = string
}

# ── The single DB Home (all CDBs below live in this one home) ─────────────────
variable "db_home_display_name" {
  description = "Display name for the Database Home."
  type        = string
  default     = "dbhome"
}

variable "db_version" {
  description = "Oracle Database version, e.g. 19.28.0.0.0 or 23.0.0.0."
  type        = string
  default     = "19.0.0.0"
}

# ── CDBs (and their PDBs) ─────────────────────────────────────────────────────
# Add a CDB by adding a map entry; add a PDB by adding to that CDB's nested pdbs map.
variable "cdbs" {
  description = "Map of Container Databases keyed by a short name. Each CDB hosts the PDBs in its nested `pdbs` map."
  type = map(object({
    db_name                 = string
    character_set           = optional(string, "AL32UTF8")
    ncharacter_set          = optional(string, "AL16UTF16")
    db_unique_name          = optional(string, "")
    sid_prefix              = optional(string, "")
    auto_backup_enabled     = optional(bool, false)
    auto_backup_window      = optional(string, "SLOT_TWO")
    recovery_window_in_days = optional(number, 30)
    pdbs = optional(map(object({
      pdb_name = string
    })), {})
  }))
  default = {}
}

# ── Passwords (keep out of tfvars — supply as JSON via environment variables) ──
# export TF_VAR_cdb_admin_passwords='{"sales":"...","hr":"..."}'
variable "cdb_admin_passwords" {
  description = "CDB admin (SYS) passwords keyed by the cdbs map key."
  type        = map(string)
  default     = {}
  sensitive   = true
}

# export TF_VAR_pdb_admin_passwords='{"sales.app":"...","hr.emp":"..."}'  (key = "<cdbKey>.<pdbKey>")
variable "pdb_admin_passwords" {
  description = "PDB admin passwords keyed by \"<cdbKey>.<pdbKey>\" (also used as the TDE wallet password)."
  type        = map(string)
  default     = {}
  sensitive   = true
}
