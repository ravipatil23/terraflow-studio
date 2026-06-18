# Variable definitions. Real values go in terraform.tfvars (passwords via env).

variable "oci_region" {
  description = "OCI region of the VM cluster, e.g. us-ashburn-1."
  type        = string
}

variable "vm_cluster_ocid" {
  description = "OCID of the existing Exadata VM cluster to host the database."
  type        = string
}

# ── DB Home ───────────────────────────────────────────────────────────────────
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

# ── CDB ─────────────────────────────────────────────────────────────────────--
variable "db_name" {
  description = "CDB name — max 8 alphanumeric chars."
  type        = string
  default     = "ORCL"
}

variable "admin_password" {
  description = "CDB admin (SYS) password. Set via: export TF_VAR_admin_password=..."
  type        = string
  sensitive   = true
}

variable "character_set" {
  type    = string
  default = "AL32UTF8"
}

variable "ncharacter_set" {
  type    = string
  default = "AL16UTF16"
}

variable "initial_pdb_name" {
  description = "Optional initial PDB created with the CDB. Leave blank for a CDB-only create."
  type        = string
  default     = ""
}

variable "db_unique_name" {
  type    = string
  default = ""
}

variable "sid_prefix" {
  type    = string
  default = ""
}

variable "auto_backup_enabled" {
  type    = bool
  default = false
}

variable "auto_backup_window" {
  type    = string
  default = "SLOT_TWO"
}

variable "recovery_window_in_days" {
  type    = number
  default = 30
}

# ── PDB ─────────────────────────────────────────────────────────────────────--
variable "create_pdb" {
  description = "Create a Pluggable Database after the CDB."
  type        = bool
  default     = true
}

variable "pdb_name" {
  description = "PDB name — max 30 chars, must differ from db_name."
  type        = string
  default     = "PDB1"
}

variable "pdb_admin_password" {
  description = "PDB admin password (also TDE wallet password). Set via: export TF_VAR_pdb_admin_password=..."
  type        = string
  sensitive   = true
  default     = ""
}
