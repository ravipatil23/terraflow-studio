# Cross-Region Data Guard networking for Oracle Exadata (OCI side)
#
# Connects two EXISTING Oracle Exadata VM cluster VCNs across two OCI regions so
# Data Guard redo can flow between them. Builds, in each region: a Hub transit VCN,
# Local Peering Gateways, a DRG + attachment, transit route tables, the DG route on
# the cluster VCN, and NSG ingress rules — then peers the two DRGs across regions.
#
# Fill in terraform.tfvars and run. You only edit that file.
#
# Apply order is automatic: module.primary + module.dr run in parallel, then
# module.drg_peering (depends_on) wires the cross-region remote peering.

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    oci = {
      source  = "oracle/oci"
      version = ">= 6.0.0"
    }
  }
}

# One provider alias per OCI region. Auth comes from ~/.oci/config or TF_VAR_* /
# OCI_* environment variables — no credentials are stored in this code.
provider "oci" {
  alias  = "primary"
  region = var.primary_region
}

provider "oci" {
  alias  = "dr"
  region = var.dr_region
}

# ── Primary region ────────────────────────────────────────────────────────────
module "primary" {
  source = "./modules/region"
  providers = {
    oci = oci.primary
  }

  prefix                 = "${var.prefix}-primary"
  compartment_id         = var.compartment_id
  hub_cidr               = var.primary_hub_cidr
  cluster_vcn_id         = var.primary_vcn_id
  cluster_nsg_id         = var.primary_nsg_id
  cluster_route_table_id = var.primary_route_table_id
  local_client_cidr      = var.primary_client_cidr
  remote_client_cidr     = var.dr_client_cidr
  manage_route_table     = var.manage_route_table
  add_ssh                = var.add_ssh
}

# ── DR region ─────────────────────────────────────────────────────────────────
module "dr" {
  source = "./modules/region"
  providers = {
    oci = oci.dr
  }

  prefix                 = "${var.prefix}-dr"
  compartment_id         = var.compartment_id
  hub_cidr               = var.dr_hub_cidr
  cluster_vcn_id         = var.dr_vcn_id
  cluster_nsg_id         = var.dr_nsg_id
  cluster_route_table_id = var.dr_route_table_id
  local_client_cidr      = var.dr_client_cidr
  remote_client_cidr     = var.primary_client_cidr
  manage_route_table     = var.manage_route_table
  add_ssh                = var.add_ssh
}

# ── Cross-region DRG peering ───────────────────────────────────────────────────
module "drg_peering" {
  source = "./modules/peering"
  providers = {
    oci.primary = oci.primary
    oci.dr      = oci.dr
  }

  prefix         = var.prefix
  compartment_id = var.compartment_id
  primary_drg_id = module.primary.drg_id
  dr_drg_id      = module.dr.drg_id
  dr_region      = var.dr_region

  depends_on = [module.primary, module.dr]
}
