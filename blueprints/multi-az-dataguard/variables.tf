# Variable definitions. Real values go in terraform.tfvars.

variable "prefix" {
  description = "Name prefix for all created resources."
  type        = string
  default     = "acme-dg"
}

variable "oci_region" {
  description = "OCI region (same region for both AZs in a multi-AZ setup)."
  type        = string
}

variable "compartment_id" {
  description = "OCI compartment OCID where the LPG resources are created."
  type        = string
  sensitive   = true
}

# ── Primary (one Availability Domain) ─────────────────────────────────────────
variable "primary_vcn_id" {
  description = "OCID of the primary VM Cluster VCN."
  type        = string
}

variable "primary_nsg_id" {
  description = "OCID of the primary VM Cluster Network Security Group."
  type        = string
}

variable "primary_client_cidr" {
  description = "CIDR of the primary client subnet, e.g. 10.10.1.0/24."
  type        = string
}

# ── Standby (the other Availability Domain) ───────────────────────────────────
variable "standby_vcn_id" {
  description = "OCID of the standby VM Cluster VCN."
  type        = string
}

variable "standby_nsg_id" {
  description = "OCID of the standby VM Cluster Network Security Group."
  type        = string
}

variable "standby_client_cidr" {
  description = "CIDR of the standby client subnet, e.g. 10.20.1.0/24. Must not overlap the primary CIDR."
  type        = string
}

# ── Toggles ───────────────────────────────────────────────────────────────────
variable "add_ssh" {
  description = "Also open TCP 22 (SSH) between the two subnets in the cluster NSGs."
  type        = bool
  default     = false
}
