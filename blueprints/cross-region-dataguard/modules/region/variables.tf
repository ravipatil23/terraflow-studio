variable "prefix" {
  description = "Name prefix for all resources in this region (e.g. dg-primary)."
  type        = string
}

variable "compartment_id" {
  description = "OCI compartment OCID."
  type        = string
  sensitive   = true
}

variable "hub_cidr" {
  description = "CIDR for this region's Hub (transit) VCN, e.g. 10.15.0.0/24. Must not overlap the cluster or remote CIDRs."
  type        = string
}

variable "cluster_vcn_id" {
  description = "OCID of the existing VM Cluster VCN in this region."
  type        = string
}

variable "cluster_nsg_id" {
  description = "OCID of the VM Cluster Network Security Group in this region."
  type        = string
}

variable "local_client_cidr" {
  description = "CIDR of this region's client subnet, e.g. 10.10.1.0/24."
  type        = string
}

variable "remote_client_cidr" {
  description = "CIDR of the remote (peer) region's client subnet, e.g. 10.30.1.0/24."
  type        = string
}

variable "add_ssh" {
  description = "Also open TCP 22 (SSH) from the remote region in the cluster NSG."
  type        = bool
  default     = false
}
