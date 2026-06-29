variable "compartment_id" {
  type        = string
  description = "OCID of the compartment that holds the VCNs, LPGs and DNS resolver objects."
}

variable "env_name" {
  type        = string
  description = "Short environment label used in names, e.g. \"prod\" or \"nonprod\"."
}

# ── DNS Hub VCN (the Network Anchor's VCN) ───────────────────────────────────

variable "hub_vcn_id" {
  type        = string
  description = "OCID of the central DNS Hub VCN."
}

variable "hub_listening_endpoint_ip" {
  type        = string
  description = "Private IP of the DNS Hub LISTENING resolver endpoint (the hub's listener)."
}

variable "hub_resolver_subnet_cidr" {
  type        = string
  description = "CIDR of the Hub VCN subnet that hosts the DNS resolver endpoints."
}

variable "hub_resolver_nsg_id" {
  type        = string
  description = "OCID of the NSG attached to the Hub resolver endpoints (DNS ingress is opened here)."
}

variable "hub_route_table_id" {
  type        = string
  default     = null
  description = "OCID of the Hub VCN default route table. Required when manage_route_tables = true."
}

# ── Exadata VCN (this environment's spoke) ───────────────────────────────────

variable "exadata_vcn_id" {
  type        = string
  description = "OCID of this environment's Exadata VCN."
}

variable "exadata_resolver_id" {
  type        = string
  default     = null
  description = "OCID of the Exadata VCN system resolver. Discovered from the VCN when null."
}

variable "exadata_resolver_subnet_id" {
  type        = string
  description = "OCID of the Exadata VCN subnet that will host the FORWARDING resolver endpoint."
}

variable "exadata_resolver_subnet_cidr" {
  type        = string
  description = "CIDR of the Exadata resolver subnet (used in routing and DNS ingress rules)."
}

variable "exadata_resolver_nsg_id" {
  type        = string
  default     = null
  description = "Optional NSG OCID for the Exadata forwarding endpoint. When set, DNS ingress from the hub is opened on it."
}

variable "exadata_route_table_id" {
  type        = string
  default     = null
  description = "OCID of the Exadata VCN default route table. Required when manage_route_tables = true."
}

# ── DNS forwarding behaviour ─────────────────────────────────────────────────

variable "azure_forward_domains" {
  type        = list(string)
  description = "Azure domains the databases must resolve via the hub, e.g. [\"azure.com\", \"windows.net\", \"database.azure.com\"]."
  default     = ["azure.com", "windows.net"]
}

variable "manage_route_tables" {
  type        = bool
  default     = false
  description = "When true, Terraform manages the VCN default route tables (import required). When false, add the LPG routes manually."
}
