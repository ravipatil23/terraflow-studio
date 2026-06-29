variable "region" {
  type        = string
  description = "OCI region of the DNS Hub and Exadata VCNs, e.g. \"us-ashburn-1\"."
}

variable "compartment_id" {
  type        = string
  description = "OCID of the compartment holding the VCNs, LPGs and DNS objects."
}

# ── DNS Hub VCN (Network Anchor) ─────────────────────────────────────────────

variable "hub_vcn_id" {
  type        = string
  description = "OCID of the central DNS Hub VCN."
}

variable "hub_resolver_id" {
  type        = string
  default     = null
  description = "OCID of the Hub VCN system resolver. Discovered from the VCN when null."
}

variable "hub_resolver_subnet_id" {
  type        = string
  description = "OCID of the Hub VCN subnet that hosts the listening/forwarding endpoints."
}

variable "hub_resolver_subnet_cidr" {
  type        = string
  description = "CIDR of the Hub resolver subnet."
}

variable "hub_resolver_nsg_id" {
  type        = string
  description = "OCID of the NSG attached to the Hub resolver endpoints."
}

variable "hub_route_table_id" {
  type        = string
  default     = null
  description = "OCID of the Hub VCN default route table (required when manage_route_tables = true)."
}

# ── Exadata environments (one entry per spoke, e.g. prod / nonprod) ──────────

variable "environments" {
  description = "Map of Exadata environments to wire to the DNS hub (key = env label)."
  type = map(object({
    vcn_id               = string           # Exadata VCN OCID
    resolver_subnet_id   = string           # subnet hosting the forwarding endpoint
    resolver_subnet_cidr = string           # CIDR of that subnet
    resolver_nsg_id      = optional(string) # NSG for the forwarding endpoint
    route_table_id       = optional(string) # default RT OCID (if managing routes)
    private_zone         = string           # private DNS zone for this env, e.g. "prod.odaa.example.com"
  }))
}

# ── DNS forwarding behaviour ─────────────────────────────────────────────────

variable "azure_forward_domains" {
  type        = list(string)
  default     = ["azure.com", "windows.net"]
  description = "Azure domains every environment must resolve via the hub listener."
}

variable "manage_route_tables" {
  type        = bool
  default     = false
  description = "When true, Terraform manages each VCN's default route table (import required)."
}
