terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = ">= 6.15.0" }
  }
}

resource "aws_odb_cloud_vm_cluster" "this" {
  display_name    = var.display_name
  cpu_core_count  = var.cpu_core_count
  gi_version      = var.gi_version
  hostname_prefix = var.hostname_prefix
  license_model   = var.license_model

  cloud_exadata_infrastructure_id = var.cloud_exadata_infrastructure_id != "" ? var.cloud_exadata_infrastructure_id : null
  odb_network_id                  = var.odb_network_id != "" ? var.odb_network_id : null

  ssh_public_keys = var.ssh_public_keys

  # db_servers wired from root: data.aws_odb_db_servers (auto) or supplied list (manual)
  db_servers = length(var.db_servers) > 0 ? var.db_servers : null

  data_collection_options {
    is_diagnostics_events_enabled = var.dco_is_diagnostics_events_enabled
    is_health_monitoring_enabled  = var.dco_is_health_monitoring_enabled
    is_incident_logs_enabled      = var.dco_is_incident_logs_enabled
  }

  cluster_name                = var.cluster_name != "" ? var.cluster_name : null
  timezone                    = var.timezone != "" ? var.timezone : null
  data_storage_size_in_tbs    = var.data_storage_size_in_tbs
  db_node_storage_size_in_gbs = var.db_node_storage_size_in_gbs
  memory_size_in_gbs          = var.memory_size_in_gbs
  scan_listener_port_tcp      = var.scan_listener_port_tcp
  is_local_backup_enabled     = var.is_local_backup_enabled
  is_sparse_diskgroup_enabled = var.is_sparse_diskgroup_enabled

  tags = var.tags

  timeouts {
    create = "12h"
    update = "2h"
    delete = "8h"
  }
}
