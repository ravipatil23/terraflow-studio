# Cross-region DRG remote peering.
# The DR RPC is the acceptor (created first, no peer_id); the primary RPC is the
# requester and initiates the peering. Both DRG OCIDs come from the region modules.

terraform {
  required_providers {
    oci = {
      source                = "oracle/oci"
      version               = ">= 6.0.0"
      configuration_aliases = [oci.primary, oci.dr]
    }
  }
}

# ── DR side: acceptor — no peer_id, created first ────────────────────────────
resource "oci_core_remote_peering_connection" "dr" {
  provider       = oci.dr
  compartment_id = var.compartment_id
  drg_id         = var.dr_drg_id
  display_name   = "${var.prefix}-dr-rpc"
}

# ── Primary side: requester — initiates peering toward DR ─────────────────────
resource "oci_core_remote_peering_connection" "primary" {
  provider         = oci.primary
  compartment_id   = var.compartment_id
  drg_id           = var.primary_drg_id
  display_name     = "${var.prefix}-primary-rpc"
  peer_id          = oci_core_remote_peering_connection.dr.id
  peer_region_name = var.dr_region
}
