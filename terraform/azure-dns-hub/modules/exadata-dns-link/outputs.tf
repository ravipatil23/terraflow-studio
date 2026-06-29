output "exadata_lpg_id" {
  description = "OCID of the Exadata-side Local Peering Gateway."
  value       = oci_core_local_peering_gateway.exadata.id
}

output "hub_lpg_id" {
  description = "OCID of the Hub-side Local Peering Gateway."
  value       = oci_core_local_peering_gateway.hub.id
}

output "forwarding_endpoint_name" {
  description = "Name of the Exadata VCN forwarding resolver endpoint."
  value       = oci_dns_resolver_endpoint.exadata_forward.name
}

output "forwarding_endpoint_ip" {
  description = "Private IP assigned to the Exadata forwarding resolver endpoint."
  value       = oci_dns_resolver_endpoint.exadata_forward.forwarding_address
}

output "peering_status" {
  description = "Status of the Exadata-side LPG peering toward the hub."
  value       = oci_core_local_peering_gateway.exadata.peering_status
}
