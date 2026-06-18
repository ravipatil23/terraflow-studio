variable "container_database_id" {
  description = "OCID of the parent CDB (wired from the cdb module in root)."
  type        = string
}

variable "pdb_name" {
  description = "PDB name — max 30 chars, must differ from the CDB name."
  type        = string
  default     = "PDB1"
}

variable "pdb_admin_password" {
  description = "PDB admin password (also used as the TDE wallet password). Set via TF_VAR_pdb_admin_password."
  type        = string
  sensitive   = true
}
