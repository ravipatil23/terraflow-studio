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

# ── Cluster VCN default route tables — managed only when manage_route_table=true ─
#
# The cluster VCNs already exist, so their DEFAULT route tables already exist. To add
# the Data Guard route, Terraform adopts them via `manage_default_resource_id`, which
# REQUIRES importing before the first apply or apply will overwrite existing routes:
#
#   terraform import 'oci_core_default_route_table.primary_rt[0]' <primary-default-rt-ocid>
#   terraform import 'oci_core_default_route_table.standby_rt[0]' <standby-default-rt-ocid>
#
# Prefer to add the route by hand? Set manage_route_table=false (see README) and these
# resources are skipped; add one LPG route per VCN after apply.
resource "oci_core_default_route_table" "primary_rt" {
  count                      = var.manage_route_table ? 1 : 0
  manage_default_resource_id = var.primary_route_table_id

  route_rules {
    network_entity_id = oci_core_local_peering_gateway.primary_lpg.id
    destination       = var.standby_client_cidr
    destination_type  = "CIDR_BLOCK"
    description       = "Data Guard: route to standby subnet via LPG"
  }

  # After importing, copy each PRE-EXISTING rule here (terraform state show ...) so it isn't dropped.
}

resource "oci_core_default_route_table" "standby_rt" {
  count                      = var.manage_route_table ? 1 : 0
  manage_default_resource_id = var.standby_route_table_id

  route_rules {
    network_entity_id = oci_core_local_peering_gateway.standby_lpg.id
    destination       = var.primary_client_cidr
    destination_type  = "CIDR_BLOCK"
    description       = "Data Guard: route to primary subnet via LPG"
  }

  # After importing, copy each PRE-EXISTING rule here (terraform state show ...) so it isn't dropped.
}
