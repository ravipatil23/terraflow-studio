# Per-region Data Guard transit networking.
# Instantiated twice from the root (primary + DR), each with its own OCI provider.
# Builds: Hub (transit) VCN, LPGs (hub <-> cluster), DRG + attachment, transit
# route tables, the Data Guard route on the cluster VCN, and NSG ingress rules.

terraform {
  required_providers {
    oci = {
      source  = "oracle/oci"
      version = ">= 6.0.0"
    }
  }
}

# ── Hub (transit) VCN ─────────────────────────────────────────────────────────
resource "oci_core_vcn" "hub" {
  compartment_id = var.compartment_id
  cidr_blocks    = [var.hub_cidr]
  display_name   = "${var.prefix}-hub-vcn"
}

# ── LPG: Hub VCN side (peers with the cluster LPG) ───────────────────────────
resource "oci_core_local_peering_gateway" "hub_lpg" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.hub.id
  display_name   = "${var.prefix}-hub-lpg"
  peer_id        = oci_core_local_peering_gateway.cluster_lpg.id
  route_table_id = oci_core_route_table.hub_transit_lpg.id
}

# ── LPG: existing Cluster VCN side ───────────────────────────────────────────
resource "oci_core_local_peering_gateway" "cluster_lpg" {
  compartment_id = var.compartment_id
  vcn_id         = var.cluster_vcn_id
  display_name   = "${var.prefix}-cluster-lpg"
}

# ── DRG (for cross-region remote peering) ────────────────────────────────────
resource "oci_core_drg" "hub" {
  compartment_id = var.compartment_id
  display_name   = "${var.prefix}-hub-drg"
}

# ── Transit route table: DRG attachment -> cluster VCN via hub LPG ───────────
resource "oci_core_route_table" "hub_transit_drg" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.hub.id
  display_name   = "${var.prefix}-hub-transit-drg"

  route_rules {
    network_entity_id = oci_core_local_peering_gateway.hub_lpg.id
    destination       = var.local_client_cidr
    destination_type  = "CIDR_BLOCK"
    description       = "DRG to cluster VCN via hub LPG"
  }
}

# ── Transit route table: hub LPG -> remote region via DRG ────────────────────
resource "oci_core_route_table" "hub_transit_lpg" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.hub.id
  display_name   = "${var.prefix}-hub-transit-lpg"

  route_rules {
    network_entity_id = oci_core_drg.hub.id
    destination       = var.remote_client_cidr
    destination_type  = "CIDR_BLOCK"
    description       = "Cluster VCN to remote region via DRG"
  }
}

# ── DRG attachment to the Hub VCN ─────────────────────────────────────────────
resource "oci_core_drg_attachment" "hub" {
  drg_id       = oci_core_drg.hub.id
  display_name = "${var.prefix}-hub-drg-attachment"

  network_details {
    id             = oci_core_vcn.hub.id
    type           = "VCN"
    route_table_id = oci_core_route_table.hub_transit_drg.id
  }
}

# ── Cluster VCN default route table — managed only when manage_route_table=true ─
#
# The cluster VCN already exists, so its DEFAULT route table already exists too.
# Terraform can only manage it via `manage_default_resource_id`, which REQUIRES an
# import before the first apply — otherwise apply will overwrite existing routes.
#
#   terraform import 'module.primary.oci_core_default_route_table.cluster_rt[0]' <primary-default-rt-ocid>
#   terraform import 'module.dr.oci_core_default_route_table.cluster_rt[0]'      <dr-default-rt-ocid>
#
# If you'd rather add the Data Guard route by hand, set manage_route_table=false
# (see the README) and this resource is skipped entirely.
resource "oci_core_default_route_table" "cluster_rt" {
  count                      = var.manage_route_table ? 1 : 0
  manage_default_resource_id = var.cluster_route_table_id

  # Data Guard route added by this blueprint:
  route_rules {
    network_entity_id = oci_core_local_peering_gateway.cluster_lpg.id
    destination       = var.remote_client_cidr
    destination_type  = "CIDR_BLOCK"
    description       = "Data Guard: to remote region via Hub LPG"
  }

  # After importing, copy each PRE-EXISTING rule here so it isn't dropped. Read them
  # with: terraform state show 'module.<side>.oci_core_default_route_table.cluster_rt[0]'
  #
  # route_rules {
  #   destination       = "0.0.0.0/0"
  #   destination_type  = "CIDR_BLOCK"
  #   network_entity_id = "<internet-or-nat-gateway-ocid>"
  #   description       = "existing default route"
  # }
}

# ── NSG: allow Data Guard redo transport (TCP 1521) from the remote region ───
resource "oci_core_network_security_group_security_rule" "dg_ingress" {
  network_security_group_id = var.cluster_nsg_id
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = var.remote_client_cidr
  source_type               = "CIDR_BLOCK"
  description               = "Data Guard ingress from remote region"

  tcp_options {
    destination_port_range {
      min = 1521
      max = 1521
    }
  }
}

# ── NSG: optional SSH from the remote region ─────────────────────────────────
resource "oci_core_network_security_group_security_rule" "ssh_ingress" {
  count                     = var.add_ssh ? 1 : 0
  network_security_group_id = var.cluster_nsg_id
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = var.remote_client_cidr
  source_type               = "CIDR_BLOCK"
  description               = "SSH from remote region"

  tcp_options {
    destination_port_range {
      min = 22
      max = 22
    }
  }
}
