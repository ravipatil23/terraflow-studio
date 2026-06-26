# Oracle Database@Azure — Network Anchor(s)
#
# Provisions the Oracle.Database/networkAnchors ARM resource via the AzAPI provider
# (azurerm has no native resource for it). A Network Anchor bridges an Azure delegated
# subnet to OCI and is a prerequisite for an Oracle Base Database. It requires an
# EXISTING Resource Anchor and a subnet delegated to Oracle.Database/networkAttachment.
#
# Fill in terraform.tfvars and run. Add a map entry to create more anchors.

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    azapi = {
      source  = "Azure/azapi"
      version = ">= 2.0.0"
    }
  }
}

# Auth uses the standard Azure chain (az login / ARM_* env vars), same as azurerm.
provider "azapi" {
  subscription_id = var.subscription_id
}

resource "azapi_resource" "network_anchor" {
  for_each = var.network_anchors

  type      = "Oracle.Database/networkAnchors@2025-09-01"
  name      = each.value.name
  parent_id = "/subscriptions/${var.subscription_id}/resourceGroups/${each.value.resource_group_name}"
  location  = each.value.location
  tags      = each.value.tags

  body = {
    # zones lives at the body level (the AZ where the Base Database will reside)
    zones = each.value.zones

    properties = merge(
      {
        resourceAnchorId                     = each.value.resource_anchor_id
        subnetId                             = each.value.subnet_id
        isOracleDnsListeningEndpointEnabled  = each.value.dns_listening_endpoint_enabled
        isOracleDnsForwardingEndpointEnabled = each.value.dns_forwarding_endpoint_enabled
        isOracleToAzureDnsZoneSyncEnabled    = each.value.dns_zone_sync_enabled
      },
      # Optional fields — only sent when set, so the API applies its own defaults.
      each.value.oci_vcn_dns_label != "" ? { ociVcnDnsLabel = each.value.oci_vcn_dns_label } : {},
      each.value.oci_backup_cidr_block != "" ? { ociBackupCidrBlock = each.value.oci_backup_cidr_block } : {},
      each.value.dns_listening_allowed_cidrs != "" ? { dnsListeningEndpointAllowedCidrs = each.value.dns_listening_allowed_cidrs } : {},
      length(each.value.dns_forwarding_rules) > 0 ? {
        dnsForwardingRules = [for r in each.value.dns_forwarding_rules : {
          domainNames         = r.domain_names
          forwardingIpAddress = r.forwarding_ip_address
        }]
      } : {},
    )
  }
}
