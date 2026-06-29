# ─────────────────────────────────────────────────────────────────────────────
# exadata-dns-link — wire one Exadata VCN to the central DNS Hub VCN
#
# Implements the per-spoke wiring from:
#   "Custom DNS for Oracle AI Database@Azure" — Scenario #2:
#   Multiple Database@Azure Environments With Custom DNS Using the
#   Network Anchor as a DNS Hub.
#
# For ONE Exadata environment (e.g. prod or nonprod) this creates:
#   1. A 1:1 Local Peering Gateway (LPG) pair between the Exadata VCN and
#      the DNS Hub VCN  (LPG peering is strictly 1:1, so each environment
#      gets its own pair).
#   2. A FORWARDING DNS resolver endpoint on the Exadata VCN resolver.
#   3. A resolver FORWARD rule that sends the configured Azure domains to
#      the DNS Hub's LISTENING endpoint, so databases can resolve Azure
#      FQDNs (egress: Exadata → Azure).
#   4. NSG ingress rules opening DNS (UDP/TCP 53) across the peering.
#   5. Optional route rules (default route table) on both VCNs so the
#      resolver subnets can reach each other over the LPG pair.
#
# Ingress resolution (Azure → OCI private zones) is handled by the Hub's
# LISTENING endpoint and the private views/zones, created in the root module.
# ─────────────────────────────────────────────────────────────────────────────

terraform {
  required_providers {
    oci = {
      source  = "oracle/oci"
      version = ">= 6.0.0"
    }
  }
}

locals {
  prefix = "${var.env_name}-dnshub"

  # The VCN's default (system) resolver. Supply it explicitly, or let the
  # module discover it from the VCN via the association data source.
  exadata_resolver_id = coalesce(
    var.exadata_resolver_id,
    data.oci_core_vcn_dns_resolver_association.exadata.dns_resolver_id,
  )
}

# Discover the Exadata VCN's system resolver when not supplied explicitly.
data "oci_core_vcn_dns_resolver_association" "exadata" {
  vcn_id = var.exadata_vcn_id
}

# ── 1:1 Local Peering Gateway pair  (Exadata VCN ⇄ DNS Hub VCN) ──────────────

# Hub side — acceptor, created first (no peer_id).
resource "oci_core_local_peering_gateway" "hub" {
  compartment_id = var.compartment_id
  vcn_id         = var.hub_vcn_id
  display_name   = "${local.prefix}-hub-lpg"
}

# Exadata side — requester, establishes the peering toward the hub LPG.
resource "oci_core_local_peering_gateway" "exadata" {
  compartment_id = var.compartment_id
  vcn_id         = var.exadata_vcn_id
  display_name   = "${local.prefix}-exadata-lpg"
  peer_id        = oci_core_local_peering_gateway.hub.id
}

# ── FORWARDING endpoint on the Exadata VCN resolver ──────────────────────────
# Source of egress queries from the databases toward the Hub listener.

resource "oci_dns_resolver_endpoint" "exadata_forward" {
  resolver_id   = local.exadata_resolver_id
  name          = "${var.env_name}ExadataFwd"
  scope         = "PRIVATE"
  subnet_id     = var.exadata_resolver_subnet_id
  is_forwarding = true
  is_listening  = false

  # forwarding_address is auto-assigned from the subnet when omitted.
  nsg_ids = var.exadata_resolver_nsg_id != null ? [var.exadata_resolver_nsg_id] : null
}

# ── FORWARD rule: Azure domains → Hub LISTENING endpoint ─────────────────────
# Manages the Exadata VCN's existing system resolver to add the rule.
# qname_cover_conditions lists the Azure domains that must resolve via the hub.

resource "oci_dns_resolver" "exadata" {
  resolver_id  = local.exadata_resolver_id
  scope        = "PRIVATE"
  display_name = "${var.env_name}-exadata-resolver"

  rules {
    action                 = "FORWARD"
    source_endpoint_name   = oci_dns_resolver_endpoint.exadata_forward.name
    destination_addresses  = [var.hub_listening_endpoint_ip]
    qname_cover_conditions = var.azure_forward_domains
  }
}

# ── DNS security (UDP/TCP 53) across the peering ─────────────────────────────
# Hub listener must accept queries originating from the Exadata resolver subnet.

resource "oci_core_network_security_group_security_rule" "hub_dns_ingress_udp" {
  network_security_group_id = var.hub_resolver_nsg_id
  direction                 = "INGRESS"
  protocol                  = "17" # UDP
  source                    = var.exadata_resolver_subnet_cidr
  source_type               = "CIDR_BLOCK"
  description               = "DNS (UDP) from ${var.env_name} Exadata resolver subnet"

  udp_options {
    destination_port_range {
      min = 53
      max = 53
    }
  }
}

resource "oci_core_network_security_group_security_rule" "hub_dns_ingress_tcp" {
  network_security_group_id = var.hub_resolver_nsg_id
  direction                 = "INGRESS"
  protocol                  = "6" # TCP
  source                    = var.exadata_resolver_subnet_cidr
  source_type               = "CIDR_BLOCK"
  description               = "DNS (TCP) from ${var.env_name} Exadata resolver subnet"

  tcp_options {
    destination_port_range {
      min = 53
      max = 53
    }
  }
}

# Exadata forwarding endpoint must accept replies / queries from the hub subnet.
resource "oci_core_network_security_group_security_rule" "exadata_dns_ingress_udp" {
  count                     = var.exadata_resolver_nsg_id != null ? 1 : 0
  network_security_group_id = var.exadata_resolver_nsg_id
  direction                 = "INGRESS"
  protocol                  = "17" # UDP
  source                    = var.hub_resolver_subnet_cidr
  source_type               = "CIDR_BLOCK"
  description               = "DNS (UDP) from DNS Hub resolver subnet"

  udp_options {
    destination_port_range {
      min = 53
      max = 53
    }
  }
}

resource "oci_core_network_security_group_security_rule" "exadata_dns_ingress_tcp" {
  count                     = var.exadata_resolver_nsg_id != null ? 1 : 0
  network_security_group_id = var.exadata_resolver_nsg_id
  direction                 = "INGRESS"
  protocol                  = "6" # TCP
  source                    = var.hub_resolver_subnet_cidr
  source_type               = "CIDR_BLOCK"
  description               = "DNS (TCP) from DNS Hub resolver subnet"

  tcp_options {
    destination_port_range {
      min = 53
      max = 53
    }
  }
}

# ── Routing over the LPG pair ────────────────────────────────────────────────
# DNS packets must route between the two resolver subnets via the LPGs.
# When the resolver subnets use their VCN's DEFAULT route table, let the
# module manage it. Import the existing default route tables first:
#
#   terraform import \
#     'module.<env>.oci_core_default_route_table.exadata[0]' <exadata-default-rt-ocid>
#   terraform import \
#     'module.<env>.oci_core_default_route_table.hub[0]'     <hub-default-rt-ocid>
#
# then copy any pre-existing route_rules from `terraform state show` into the
# blocks below. Set manage_route_tables = false to add the routes by hand.

resource "oci_core_default_route_table" "exadata" {
  count                      = var.manage_route_tables ? 1 : 0
  manage_default_resource_id = var.exadata_route_table_id

  route_rules {
    network_entity_id = oci_core_local_peering_gateway.exadata.id
    destination       = var.hub_resolver_subnet_cidr
    destination_type  = "CIDR_BLOCK"
    description       = "To DNS Hub resolver subnet via LPG"
  }

  # ── Pre-existing Exadata VCN routes — paste from `terraform state show` ────
  # route_rules { destination = "0.0.0.0/0" destination_type = "CIDR_BLOCK" network_entity_id = "<nat/igw-ocid>" }
}

resource "oci_core_default_route_table" "hub" {
  count                      = var.manage_route_tables ? 1 : 0
  manage_default_resource_id = var.hub_route_table_id

  route_rules {
    network_entity_id = oci_core_local_peering_gateway.hub.id
    destination       = var.exadata_resolver_subnet_cidr
    destination_type  = "CIDR_BLOCK"
    description       = "To ${var.env_name} Exadata resolver subnet via LPG"
  }

  # ── Pre-existing Hub VCN routes — paste from `terraform state show` ────────
}
