# Variable definitions. Real values go in terraform.tfvars.

variable "prefix" {
  description = "Name prefix for all resources (e.g. acme-dg)."
  type        = string
}

variable "compartment_id" {
  description = "OCI compartment OCID where all resources are created."
  type        = string
  sensitive   = true
}

variable "primary_region" {
  description = "OCI region identifier for the primary site, e.g. us-ashburn-1."
  type        = string
}

variable "dr_region" {
  description = "OCI region identifier for the DR/standby site, e.g. us-phoenix-1."
  type        = string
}

# ── Primary region inputs ─────────────────────────────────────────────────────
variable "primary_vcn_id" {
  description = "OCID of the existing primary VM Cluster VCN."
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

variable "primary_hub_cidr" {
  description = "CIDR for the primary Hub (transit) VCN, e.g. 10.15.0.0/24."
  type        = string
}

# ── DR region inputs ──────────────────────────────────────────────────────────
variable "dr_vcn_id" {
  description = "OCID of the existing DR VM Cluster VCN."
  type        = string
}

variable "dr_nsg_id" {
  description = "OCID of the DR VM Cluster Network Security Group."
  type        = string
}

variable "dr_client_cidr" {
  description = "CIDR of the DR client subnet, e.g. 10.30.1.0/24."
  type        = string
}

variable "dr_hub_cidr" {
  description = "CIDR for the DR Hub (transit) VCN, e.g. 10.16.0.0/24."
  type        = string
}

# ── Behavior toggles (apply to both regions) ──────────────────────────────────
variable "add_ssh" {
  description = "Also open TCP 22 (SSH) between regions in the cluster NSGs."
  type        = bool
  default     = false
}
