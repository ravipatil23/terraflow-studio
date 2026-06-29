output "hub_listening_endpoint_ip" {
  description = "Private IP of the DNS Hub LISTENING endpoint. Point Azure's DNS forwarding ruleset at this address."
  value       = oci_dns_resolver_endpoint.hub_listening.listening_address
}

output "hub_forwarding_endpoint_ip" {
  description = "Private IP of the DNS Hub FORWARDING endpoint."
  value       = oci_dns_resolver_endpoint.hub_forwarding.forwarding_address
}

output "private_zones" {
  description = "Per-environment OCI private DNS zones served by the hub."
  value       = { for k, z in oci_dns_zone.env : k => z.name }
}

output "links" {
  description = "Per-environment wiring details (LPGs + forwarding endpoint)."
  value = {
    for k, m in module.link : k => {
      exadata_lpg_id           = m.exadata_lpg_id
      hub_lpg_id               = m.hub_lpg_id
      forwarding_endpoint_ip   = m.forwarding_endpoint_ip
      forwarding_endpoint_name = m.forwarding_endpoint_name
      peering_status           = m.peering_status
    }
  }
}
