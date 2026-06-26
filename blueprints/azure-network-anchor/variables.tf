# Variable definitions. Real values go in terraform.tfvars.

variable "subscription_id" {
  description = "Azure subscription ID (used for provider auth and to build each anchor's parent resource-group ID)."
  type        = string
}

variable "network_anchors" {
  description = "Map of Network Anchors keyed by a short name. Add an entry to create another anchor."
  type = map(object({
    # ── required ──
    name                = string # 3-24 chars, letters/numbers/hyphens (^[a-zA-Z0-9-]{3,24}$)
    resource_group_name = string # existing resource group that holds the anchor
    location            = string # Azure region (must offer Oracle Base Database)
    resource_anchor_id  = string # Azure resource ID of the existing Resource Anchor
    subnet_id           = string # Azure resource ID of the delegated client subnet

    # ── optional ──
    zones                 = optional(list(string), []) # AZ(s) where the Base Database will reside, e.g. ["2"]
    tags                  = optional(map(string), {})
    oci_vcn_dns_label     = optional(string, "") # OCI VCN DNS label (optional if DNS config provided)
    oci_backup_cidr_block = optional(string, "") # OCI backup subnet CIDR (not needed for Base Database)

    # DNS options
    dns_listening_endpoint_enabled  = optional(bool, false) # Azure apps resolve DB FQDNs
    dns_listening_allowed_cidrs     = optional(string, "")  # comma-separated CIDRs allowed to query the listening endpoint
    dns_forwarding_endpoint_enabled = optional(bool, false) # DB instances resolve Azure private FQDNs
    dns_forwarding_rules = optional(list(object({
      domain_names          = string # comma-separated domain names
      forwarding_ip_address = string
    })), [])
    dns_zone_sync_enabled = optional(bool, false) # replicate DB private DNS zones from OCI to Azure
  }))
  default = {}
}
