# Variable definitions. Real values go in terraform.tfvars; passwords via env vars.

variable "oci_region" {
  description = "OCI region of the VM cluster(s), e.g. us-ashburn-1."
  type        = string
}

variable "vm_cluster_ocid" {
  description = "Default VM cluster OCID for homes that don't set their own. Override per-home via db_homes[*].vm_cluster_ocid."
  type        = string
}

# ── DB Homes -> CDBs -> PDBs ──────────────────────────────────────────────────
# Add a home / CDB / PDB by adding a map entry at the matching level.
variable "db_homes" {
  description = "Map of Database Homes keyed by a short name. Each home has its own db_version and a nested map of CDBs; each CDB has a nested map of PDBs."
  type = map(object({
    db_version      = string
    display_name    = optional(string, "") # defaults to the home's map key
    vm_cluster_ocid = optional(string, "") # defaults to the top-level vm_cluster_ocid
    cdbs = optional(map(object({
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
    })), {})
  }))
  default = {}
}

# ── Passwords (keep out of tfvars — supply as JSON via environment variables) ──
# Key = "<homeKey>.<cdbKey>"
# export TF_VAR_cdb_admin_passwords='{"home19.sales":"...","home19.hr":"..."}'
variable "cdb_admin_passwords" {
  description = "CDB admin (SYS) passwords keyed by \"<homeKey>.<cdbKey>\"."
  type        = map(string)
  default     = {}
  sensitive   = true
}

# Key = "<homeKey>.<cdbKey>.<pdbKey>"
# export TF_VAR_pdb_admin_passwords='{"home19.sales.app":"...","home19.hr.emp":"..."}'
variable "pdb_admin_passwords" {
  description = "PDB admin passwords keyed by \"<homeKey>.<cdbKey>.<pdbKey>\" (also the TDE wallet password)."
  type        = map(string)
  default     = {}
  sensitive   = true
}
