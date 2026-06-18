variable "db_home_id" {
  description = "OCID of the Database Home (wired from the db-home module in root)."
  type        = string
}

variable "db_name" {
  description = "CDB name — max 8 alphanumeric chars."
  type        = string
  default     = "ORCL"
}

variable "admin_password" {
  description = "CDB admin (SYS) password. Set via TF_VAR_admin_password — do not hardcode."
  type        = string
  sensitive   = true
}

variable "character_set" {
  description = "Database character set."
  type        = string
  default     = "AL32UTF8"
}

variable "ncharacter_set" {
  description = "National character set."
  type        = string
  default     = "AL16UTF16"
}

variable "initial_pdb_name" {
  description = "Optional initial PDB created with the CDB. Leave blank to create the CDB only."
  type        = string
  default     = ""
}

variable "db_unique_name" {
  description = "Optional DB unique name. Defaults to db_name if blank."
  type        = string
  default     = ""
}

variable "sid_prefix" {
  description = "Optional SID prefix."
  type        = string
  default     = ""
}

variable "auto_backup_enabled" {
  description = "Enable managed automatic backups."
  type        = bool
  default     = false
}

variable "auto_backup_window" {
  description = "Backup window slot (e.g. SLOT_TWO). Used only when auto_backup_enabled = true."
  type        = string
  default     = "SLOT_TWO"
}

variable "recovery_window_in_days" {
  description = "Backup retention in days. Used only when auto_backup_enabled = true."
  type        = number
  default     = 30
}
