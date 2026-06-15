output "primary_hub_vcn_id" {
  description = "OCID of the primary Hub VCN."
  value       = module.primary.hub_vcn_id
}

output "dr_hub_vcn_id" {
  description = "OCID of the DR Hub VCN."
  value       = module.dr.hub_vcn_id
}

output "primary_drg_id" {
  description = "OCID of the primary DRG."
  value       = module.primary.drg_id
}

output "dr_drg_id" {
  description = "OCID of the DR DRG."
  value       = module.dr.drg_id
}

output "primary_cluster_lpg_id" {
  description = "OCID of the primary cluster-side LPG (use it if adding the DG route manually)."
  value       = module.primary.cluster_lpg_id
}

output "dr_cluster_lpg_id" {
  description = "OCID of the DR cluster-side LPG (use it if adding the DG route manually)."
  value       = module.dr.cluster_lpg_id
}

output "primary_rpc_id" {
  description = "OCID of the primary Remote Peering Connection."
  value       = module.drg_peering.primary_rpc_id
}

output "dr_rpc_id" {
  description = "OCID of the DR Remote Peering Connection."
  value       = module.drg_peering.dr_rpc_id
}

output "peering_status" {
  description = "Cross-region peering status — should become PEERED after apply."
  value       = module.drg_peering.peering_status
}
