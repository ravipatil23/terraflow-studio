output "odb_networks" {
  description = "ODB Network details keyed by instance name."
  value = { for k, v in module.odb_network : k => {
    network_id  = v.network_id
    network_arn = v.network_arn
  } }
}

output "exadata_infras" {
  description = "Exadata Infrastructure details keyed by instance name."
  value = { for k, v in module.exadata_infra : k => {
    infra_id  = v.infra_id
    infra_arn = v.infra_arn
  } }
}

output "peerings" {
  description = "Network Peering details keyed by instance name."
  value = { for k, v in module.peering : k => {
    peering_connection_id = v.peering_connection_id
  } }
}

output "vm_clusters" {
  description = "VM Cluster details keyed by instance name."
  value = { for k, v in module.vm_cluster : k => {
    vm_cluster_id = v.vm_cluster_id
    ocid          = v.ocid
  } }
}

output "db_servers" {
  description = "DB Server IDs per cluster, keyed by cluster instance name."
  value       = { for k, v in data.aws_odb_db_servers.this : k => v.db_servers[*].id }
}
