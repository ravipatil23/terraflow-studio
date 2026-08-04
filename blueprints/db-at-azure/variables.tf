# Variable definitions. Real values go in terraform.tfvars.

variable "subscription_id" {
  description = "Azure subscription ID."
  type        = string
}

variable "resource_group_name" {
  description = "Azure resource group (must already exist)."
  type        = string
}

variable "location" {
  description = "Azure region, e.g. eastus."
  type        = string
}

variable "tags" {
  type    = map(string)
  default = {}
}

# ── VNets ─────────────────────────────────────────────────────────────────────
variable "azure_vnets" {
  description = "Map of VNets with an Oracle-delegated subnet. Key is referenced by azure_clusters.vnet_ref."
  type = map(object({
    vnet_name             = string
    address_space         = string
    subnet_name           = string
    subnet_address_prefix = string
  }))
  default = {}
}

# ── Exadata Infrastructures ───────────────────────────────────────────────────
variable "azure_infras" {
  description = "Map of Exadata Infrastructures. Key is referenced by azure_clusters.infra_ref."
  type = map(object({
    name          = string
    display_name  = string
    shape         = optional(string, "Exadata.X11M")
    compute_count = optional(number, 2)
    storage_count = optional(number, 3)
    zone          = string
  }))
  default = {}
}

# ── VM Clusters ───────────────────────────────────────────────────────────────
variable "azure_clusters" {
  description = "Map of VM Clusters. infra_ref and vnet_ref must match keys in azure_infras and azure_vnets."
  type = map(object({
    name                        = string
    display_name                = string
    hostname                    = string
    infra_ref                   = string
    vnet_ref                    = string
    cpu_core_count              = optional(number, 4)
    data_storage_size_in_tbs    = optional(number, 2)
    memory_size_in_gbs          = optional(number, 60)
    db_node_storage_size_in_gbs = optional(number, 120)
    gi_version                  = optional(string, "23.0.0.0")
    license_model               = optional(string, "LicenseIncluded")
    ssh_public_keys             = optional(list(string), [])
    local_backup_enabled        = optional(bool, false)
    sparse_diskgroup_enabled    = optional(bool, false)
    cluster_name                = optional(string, "")
    time_zone                   = optional(string, "UTC")
    scan_listener_port_tcp      = optional(number, 1521)
    # Oracle carves the backup range inside the VNet, per cluster. Several
    # clusters share one delegated subnet by design, but they cannot share a
    # backup range — give each its own when more than one uses a vnet_ref.
    # Do NOT leave this empty. The attribute is ForceNew and not Computed, so an
    # empty config lets the service write its own default into state and every
    # later plan proposes replacing the cluster. The default below is the range
    # the service would have picked anyway, stated explicitly.
    backup_subnet_cidr = optional(string, "192.168.252.0/22")
  }))
  default = {}
}
