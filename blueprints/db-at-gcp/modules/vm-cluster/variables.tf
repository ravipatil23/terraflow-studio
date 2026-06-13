variable "cloud_vm_cluster_id" {
  description = "Immutable unique ID for the VM cluster."
  type        = string
}

variable "display_name" {
  type    = string
  default = null
}

variable "location" {
  description = "GCP region (e.g. us-east4)."
  type        = string
}

variable "project" {
  description = "GCP project ID. Defaults to provider project if null."
  type        = string
  default     = null
}

variable "exadata_infrastructure" {
  description = "Full resource path of the Exadata Infrastructure (module.exadata_infra[key].infra_self_link)."
  type        = string
}

variable "odb_network" {
  description = "ODB Network name (module.odb_network[key].odb_network_name)."
  type        = string
}

variable "odb_subnet" {
  description = "Client ODB Subnet name (module.odb_network[key].client_subnet_name)."
  type        = string
}

variable "backup_odb_subnet" {
  description = "Backup ODB Subnet name (module.odb_network[key].backup_subnet_name)."
  type        = string
}

variable "db_server_ocids" {
  description = "DB server OCIDs from data.google_oracle_database_db_servers.this[key]."
  type        = list(string)
}

variable "deletion_protection" {
  type    = bool
  default = true
}

variable "gi_version" {
  description = "Grid Infrastructure version, e.g. '23.0.0.0'."
  type        = string
  default     = null
}

variable "hostname_prefix" {
  description = "Hostname prefix — max 12 chars, letters/numbers/hyphens, must start with a letter."
  type        = string
}

variable "cpu_core_count" {
  type = number
}

variable "memory_size_gb" {
  type = number
}

variable "db_node_storage_size_gb" {
  type = number
}

variable "data_storage_size_tb" {
  type = number
}

variable "local_backup_enabled" {
  type    = bool
  default = false
}

variable "sparse_diskgroup_enabled" {
  type    = bool
  default = false
}

variable "license_type" {
  description = "LICENSE_INCLUDED or BRING_YOUR_OWN_LICENSE."
  type        = string
  default     = "LICENSE_INCLUDED"
  validation {
    condition     = contains(["LICENSE_INCLUDED", "BRING_YOUR_OWN_LICENSE"], var.license_type)
    error_message = "Must be LICENSE_INCLUDED or BRING_YOUR_OWN_LICENSE."
  }
}

variable "ssh_public_keys" {
  description = "SSH public keys for cluster node access."
  type        = list(string)
}

variable "cluster_name" {
  description = "Optional cluster name — max 11 chars."
  type        = string
  default     = null
}

variable "node_count" {
  type    = number
  default = null
}

variable "ocpu_count" {
  type    = number
  default = null
}

variable "disk_redundancy" {
  description = "HIGH or NORMAL."
  type        = string
  default     = null
}

variable "time_zone" {
  description = "Time zone ID, e.g. 'UTC' or 'America/New_York'."
  type        = string
  default     = "UTC"
}

variable "scan_listener_port_tcp" {
  description = "TCP port for SCAN listener. Default 1521, range 1024–8999."
  type        = number
  default     = null
}

variable "dco_diagnostics" {
  type    = bool
  default = true
}

variable "dco_health" {
  type    = bool
  default = true
}

variable "dco_incident_logs" {
  type    = bool
  default = true
}

variable "labels" {
  type    = map(string)
  default = {}
}
