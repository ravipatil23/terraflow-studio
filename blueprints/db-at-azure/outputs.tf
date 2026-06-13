output "vnets" {
  description = "VNet details keyed by instance name."
  value = { for k, v in module.vnet : k => {
    vnet_id   = v.vnet_id
    subnet_id = v.subnet_id
  } }
}

output "exadata_infras" {
  description = "Exadata Infrastructure details keyed by instance name."
  value = { for k, v in module.exadata_infra : k => {
    infra_id   = v.infra_id
    infra_name = v.infra_name
  } }
}

output "vm_clusters" {
  description = "VM Cluster details keyed by instance name."
  value = { for k, v in module.vm_cluster : k => {
    cluster_id = v.cluster_id
    ocid       = v.ocid
  } }
}
