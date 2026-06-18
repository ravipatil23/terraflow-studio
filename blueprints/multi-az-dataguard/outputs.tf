output "primary_lpg_id" {
  description = "OCID of the primary Local Peering Gateway (route target if adding the DG route manually)."
  value       = oci_core_local_peering_gateway.primary_lpg.id
}

output "standby_lpg_id" {
  description = "OCID of the standby Local Peering Gateway (route target if adding the DG route manually)."
  value       = oci_core_local_peering_gateway.standby_lpg.id
}

output "primary_lpg_peering_status" {
  description = "Peering status of the primary LPG — should become PEERED after apply."
  value       = oci_core_local_peering_gateway.primary_lpg.peering_status
}

output "standby_lpg_peering_status" {
  description = "Peering status of the standby LPG — should become PEERED after apply."
  value       = oci_core_local_peering_gateway.standby_lpg.peering_status
}
