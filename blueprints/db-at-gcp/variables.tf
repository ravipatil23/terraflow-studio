# Variable definitions. Real values go in terraform.tfvars.

variable "gcp_project" {
  description = "Default GCP project ID. Override per-resource via the project field in a map entry."
  type        = string
}

variable "gcp_region" {
  description = "Default GCP region. Override per-resource via the location field in a map entry."
  type        = string
}

# ── ODB Networks ──────────────────────────────────────────────────────────────
variable "gcp_odb_networks" {
  description = "Map of ODB Networks. Key is referenced by gcp_vm_clusters.network_key."
  type = map(object({
    odb_network_id      = string
    network             = string
    client_subnet_id    = string
    client_cidr_range   = string
    backup_subnet_id    = string
    backup_cidr_range   = string
    location            = optional(string, "")
    project             = optional(string, "")
    gcp_oracle_zone     = optional(string, "")
    deletion_protection = optional(bool, true)
    labels              = optional(map(string), {})
  }))
  default = {}
}

# ── Exadata Infrastructures ───────────────────────────────────────────────────
variable "gcp_exadata_infras" {
  description = "Map of Exadata Infrastructures. Key is referenced by gcp_vm_clusters.infra_key."
  type = map(object({
    cloud_exadata_infrastructure_id     = string
    shape                               = string
    compute_count                       = number
    storage_count                       = number
    location                            = optional(string, "")
    display_name                        = optional(string, "")
    gcp_oracle_zone                     = optional(string, "")
    project                             = optional(string, "")
    total_storage_size_gb               = optional(number, 0)
    customer_contacts                   = optional(list(string), [])
    mw_preference                       = optional(string, "NO_PREFERENCE")
    mw_patching_mode                    = optional(string, "ROLLING")
    mw_is_custom_action_timeout_enabled = optional(bool, false)
    mw_custom_action_timeout_mins       = optional(number, 15)
    mw_lead_time_week                   = optional(number, null)
    mw_days_of_week                     = optional(list(string), [])
    mw_months                           = optional(list(string), [])
    mw_hours_of_day                     = optional(list(number), [])
    mw_weeks_of_month                   = optional(list(number), [])
    deletion_protection                 = optional(bool, true)
    labels                              = optional(map(string), {})
  }))
  default = {}
}

# ── ExaDB VM Clusters ─────────────────────────────────────────────────────────
variable "gcp_vm_clusters" {
  description = "Map of ExaDB VM Clusters. infra_key and network_key must match keys in gcp_exadata_infras and gcp_odb_networks."
  type = map(object({
    infra_key                = string
    network_key              = string
    cloud_vm_cluster_id      = string
    hostname_prefix          = string
    cpu_core_count           = number
    memory_size_gb           = number
    db_node_storage_size_gb  = number
    data_storage_size_tb     = number
    ssh_public_keys          = list(string)
    display_name             = optional(string, "")
    location                 = optional(string, "")
    project                  = optional(string, "")
    gi_version               = optional(string, "23.0.0.0")
    license_type             = optional(string, "LICENSE_INCLUDED")
    local_backup_enabled     = optional(bool, false)
    sparse_diskgroup_enabled = optional(bool, false)
    cluster_name             = optional(string, null)
    node_count               = optional(number, null)
    ocpu_count               = optional(number, null)
    disk_redundancy          = optional(string, null)
    time_zone                = optional(string, "UTC")
    scan_listener_port_tcp   = optional(number, null)
    dco_diagnostics          = optional(bool, true)
    dco_health               = optional(bool, true)
    dco_incident_logs        = optional(bool, true)
    deletion_protection      = optional(bool, true)
    labels                   = optional(map(string), {})
  }))
  default = {}
}
