output "odb_networks" {
  description = "ODB Network details keyed by instance name."
  value = { for k, v in module.odb_network : k => {
    odb_network_name   = v.odb_network_name
    client_subnet_name = v.client_subnet_name
    backup_subnet_name = v.backup_subnet_name
  } }
}

output "exadata_infras" {
  description = "Exadata Infrastructure details keyed by instance name."
  value = { for k, v in module.exadata_infra : k => {
    infra_name = v.infra_name
    ocid       = v.ocid
  } }
}

output "vm_clusters" {
  description = "VM Cluster details keyed by instance name."
  value = { for k, v in module.vm_cluster : k => {
    vm_cluster_name = v.vm_cluster_name
    ocid            = v.ocid
  } }
}

output "db_servers" {
  description = "DB Server OCIDs per cluster, keyed by cluster instance name."
  value       = { for k, v in data.google_oracle_database_db_servers.this : k => v.db_servers[*].properties[0].ocid }
}
