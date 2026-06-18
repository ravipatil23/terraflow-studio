variable "vm_cluster_ocid" {
  description = "OCID of the existing Exadata VM cluster to create the DB Home on."
  type        = string
}

variable "display_name" {
  description = "Display name for the Database Home."
  type        = string
  default     = "dbhome"
}

variable "db_version" {
  description = "Oracle Database version, e.g. 19.28.0.0.0 or 23.0.0.0."
  type        = string
  default     = "19.0.0.0"
}
