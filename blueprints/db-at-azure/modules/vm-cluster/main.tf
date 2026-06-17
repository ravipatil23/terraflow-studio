terraform {
  required_providers {
    azurerm = { source = "hashicorp/azurerm", version = ">= 4.9.0" }
  }
}

resource "azurerm_oracle_cloud_vm_cluster" "this" {
  name                            = var.name
  display_name                    = var.display_name
  resource_group_name             = var.resource_group_name
  location                        = var.location
  cloud_exadata_infrastructure_id = var.cloud_exadata_infrastructure_id
  subnet_id                       = var.subnet_id
  virtual_network_id              = var.virtual_network_id
  hostname                        = var.hostname
  cpu_core_count                  = var.cpu_core_count
  data_storage_size_in_tbs        = var.data_storage_size_in_tbs
  db_node_storage_size_in_gbs     = var.db_node_storage_size_in_gbs
  memory_size_in_gbs              = var.memory_size_in_gbs
  ssh_public_keys                 = var.ssh_public_keys
  gi_version                      = var.gi_version
  license_model                   = var.license_model

  cluster_name               = var.cluster_name != "" ? var.cluster_name : null
  domain                     = var.domain != "" ? var.domain : null
  backup_subnet_cidr         = var.backup_subnet_cidr != "" ? var.backup_subnet_cidr : null
  data_storage_percentage    = var.data_storage_percentage
  time_zone                  = var.time_zone != "" ? var.time_zone : null
  scan_listener_port_tcp     = var.scan_listener_port_tcp
  scan_listener_port_tcp_ssl = var.scan_listener_port_tcp_ssl
  system_version             = var.system_version != "" ? var.system_version : null
  zone_id                    = var.zone_id != "" ? var.zone_id : null

  local_backup_enabled     = var.local_backup_enabled
  sparse_diskgroup_enabled = var.sparse_diskgroup_enabled

  db_servers = length(var.db_servers) > 0 ? var.db_servers : null

  dynamic "file_system_configuration" {
    for_each = var.file_system_configuration
    content {
      mount_point = lookup(file_system_configuration.value, "mount_point", null)
      size_in_gb  = lookup(file_system_configuration.value, "size_in_gb", null)
    }
  }

  data_collection_options {
    diagnostics_events_enabled = var.dco_diagnostics_events_enabled
    health_monitoring_enabled  = var.dco_health_monitoring_enabled
    incident_logs_enabled      = var.dco_incident_logs_enabled
  }

  tags = var.tags

  timeouts {
    create = "12h"
    update = "2h"
    delete = "8h"
  }
}
