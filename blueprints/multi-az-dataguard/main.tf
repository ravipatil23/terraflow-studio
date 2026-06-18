# Multi-AZ (same-region) Data Guard networking for Oracle Exadata (OCI side)
#
# Connects two EXISTING Exadata VM cluster VCNs in two Availability Domains of the
# SAME OCI region so Data Guard redo can flow between them. Because it's same-region,
# it uses a pair of immediately-peered Local Peering Gateways (no DRG / remote peering).
# For cross-region DR, use the ../cross-region-dataguard blueprint instead.
#
# Fill in terraform.tfvars and run. You only edit that file.

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    oci = {
      source  = "oracle/oci"
      version = ">= 6.0.0"
    }
  }
}

# Auth comes from ~/.oci/config or OCI_* / TF_VAR_* env vars — no secrets here.
provider "oci" {
  region = var.oci_region
}

# ── Primary: Local Peering Gateway (initiates the peering) ───────────────────
resource "oci_core_local_peering_gateway" "primary_lpg" {
  compartment_id = var.compartment_id
  vcn_id         = var.primary_vcn_id
  display_name   = "${var.prefix}-primary-lpg"
  peer_id        = oci_core_local_peering_gateway.standby_lpg.id
}

# ── Standby: Local Peering Gateway ───────────────────────────────────────────
resource "oci_core_local_peering_gateway" "standby_lpg" {
  compartment_id = var.compartment_id
  vcn_id         = var.standby_vcn_id
  display_name   = "${var.prefix}-standby-lpg"
}

# ── Primary NSG: allow Data Guard redo (TCP 1521) from the standby subnet ────
resource "oci_core_network_security_group_security_rule" "primary_dg_ingress" {
  network_security_group_id = var.primary_nsg_id
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = var.standby_client_cidr
  source_type               = "CIDR_BLOCK"
  description               = "Data Guard ingress from standby (${var.standby_client_cidr})"

  tcp_options {
    destination_port_range {
      min = 1521
      max = 1521
    }
  }
}

# ── Standby NSG: allow Data Guard redo (TCP 1521) from the primary subnet ────
resource "oci_core_network_security_group_security_rule" "standby_dg_ingress" {
  network_security_group_id = var.standby_nsg_id
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = var.primary_client_cidr
  source_type               = "CIDR_BLOCK"
  description               = "Data Guard ingress from primary (${var.primary_client_cidr})"

  tcp_options {
    destination_port_range {
      min = 1521
      max = 1521
    }
  }
}

# ── Optional SSH (TCP 22) between the two subnets ────────────────────────────
resource "oci_core_network_security_group_security_rule" "primary_ssh_ingress" {
  count                     = var.add_ssh ? 1 : 0
  network_security_group_id = var.primary_nsg_id
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = var.standby_client_cidr
  source_type               = "CIDR_BLOCK"
  description               = "SSH from standby"

  tcp_options {
    destination_port_range {
      min = 22
      max = 22
    }
  }
}

resource "oci_core_network_security_group_security_rule" "standby_ssh_ingress" {
  count                     = var.add_ssh ? 1 : 0
  network_security_group_id = var.standby_nsg_id
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = var.primary_client_cidr
  source_type               = "CIDR_BLOCK"
  description               = "SSH from primary"

  tcp_options {
    destination_port_range {
      min = 22
      max = 22
    }
  }
}

# ── Cluster VCN routes — NOT managed by Terraform (add manually after apply) ─────
#
# Like the cross-region Data Guard blueprint's manual mode, this configuration does
# NOT touch the existing VM cluster VCN route tables — adopting a pre-existing default
# route table risks wiping its current routes. After `terraform apply`, add one Data
# Guard route to EACH cluster VCN's default route table:
#
#   Primary VCN  -> destination = standby client CIDR, target = primary LPG
#                   (terraform output primary_lpg_id)
#   Standby VCN  -> destination = primary client CIDR, target = standby LPG
#                   (terraform output standby_lpg_id)
#
# OCI Console: Networking -> VCN -> Route Tables -> Default Route Table -> Add Route
#   Rule -> Target Type: Local Peering Gateway. See the README for OCI CLI commands.
