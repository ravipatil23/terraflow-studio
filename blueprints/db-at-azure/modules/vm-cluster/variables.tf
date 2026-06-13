variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "name" {
  type = string
}

variable "display_name" {
  type = string
}

variable "cloud_exadata_infrastructure_id" {
  description = "Wired from module.exadata_infra in root."
  type        = string
}

variable "subnet_id" {
  description = "Delegated subnet ID — wired from module.vnet in root."
  type        = string
}

variable "virtual_network_id" {
  description = "VNet ID — wired from module.vnet in root."
  type        = string
}

variable "hostname" {
  type = string
}

variable "cpu_core_count" {
  type    = number
  default = 4
}

variable "data_storage_size_in_tbs" {
  type    = number
  default = 2
}

variable "db_node_storage_size_in_gbs" {
  type    = number
  default = 120
}

variable "memory_size_in_gbs" {
  type    = number
  default = 60
}

variable "ssh_public_keys" {
  type    = list(string)
  default = []
}

variable "gi_version" {
  type    = string
  default = "23.0.0.0"
}

variable "license_model" {
  type    = string
  default = "LicenseIncluded"
}

variable "cluster_name" {
  type    = string
  default = ""
}

variable "domain" {
  type    = string
  default = ""
}

variable "backup_subnet_cidr" {
  type    = string
  default = ""
}

variable "data_storage_percentage" {
  type    = number
  default = 80
}

variable "time_zone" {
  type    = string
  default = "UTC"
}

variable "scan_listener_port_tcp" {
  type    = number
  default = 1521
}

variable "scan_listener_port_tcp_ssl" {
  type    = number
  default = null
}

variable "system_version" {
  type    = string
  default = ""
}

variable "zone_id" {
  type    = string
  default = ""
}

variable "db_servers" {
  type    = list(string)
  default = []
}

variable "local_backup_enabled" {
  type    = bool
  default = false
}

variable "sparse_diskgroup_enabled" {
  type    = bool
  default = false
}

variable "file_system_configuration" {
  type = list(object({
    mount_point = optional(string)
    size_in_gb  = optional(number)
  }))
  default = []
}

variable "dco_diagnostics_events_enabled" {
  type    = bool
  default = true
}

variable "dco_health_monitoring_enabled" {
  type    = bool
  default = true
}

variable "dco_incident_logs_enabled" {
  type    = bool
  default = true
}

variable "tags" {
  type    = map(string)
  default = {}
}
