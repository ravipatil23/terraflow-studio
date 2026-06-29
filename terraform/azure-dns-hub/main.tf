# ─────────────────────────────────────────────────────────────────────────────
# Database@Azure — Custom DNS, Scenario #2
# Network Anchor as a centralized DNS Hub for multiple Exadata environments.
#
# Source: "Custom DNS for Oracle AI Database@Azure" (A-Team) / Oracle docs
#         "DNS for Oracle AI Database@Azure".
#
# Topology
# ────────
#                       ┌────────────────────────────┐
#   Azure private  ───▶ │  DNS Hub VCN (Network       │
#   resolver / VNets    │  Anchor)                    │
#                       │   • LISTENING endpoint  ◀───┼─── Azure queries OCI zones
#                       │   • FORWARDING endpoint ───▶┼─── (optional) → Azure
#                       │   • Private views + zones   │
#                       └───────┬─────────────┬───────┘
#                       LPG 1:1 │             │ LPG 1:1
#                  ┌────────────▼──┐      ┌───▼────────────┐
#                  │ Exadata VCN   │      │ Exadata VCN    │
#                  │  (prod)       │      │  (nonprod)     │
#                  │  FORWARD ep ──┼──────┼─▶ hub listener │  egress: DB → Azure FQDN
#                  └───────────────┘      └────────────────┘
#
# This root module owns the HUB-side shared objects (listening/forwarding
# endpoints + private views/zones). The reusable `exadata-dns-link` module
# wires each Exadata VCN to the hub (LPG pair + forwarding rule + routes + NSG).
# ─────────────────────────────────────────────────────────────────────────────

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    oci = {
      source  = "oracle/oci"
      version = ">= 6.0.0"
    }
  }
}

provider "oci" {
  # Configure auth via env vars, config file, or instance principals.
  region = var.region
}

# Discover the Hub VCN's system resolver (where hub endpoints/views attach).
data "oci_core_vcn_dns_resolver_association" "hub" {
  vcn_id = var.hub_vcn_id
}

locals {
  hub_resolver_id = coalesce(var.hub_resolver_id, data.oci_core_vcn_dns_resolver_association.hub.dns_resolver_id)
}

# ── Hub LISTENING endpoint — Azure points its DNS forwarding here ────────────
resource "oci_dns_resolver_endpoint" "hub_listening" {
  resolver_id   = local.hub_resolver_id
  name          = "dnsHubListening"
  scope         = "PRIVATE"
  subnet_id     = var.hub_resolver_subnet_id
  is_listening  = true
  is_forwarding = false
  nsg_ids       = [var.hub_resolver_nsg_id]
}

# ── Hub FORWARDING endpoint — hub forwards out to Azure when needed ──────────
resource "oci_dns_resolver_endpoint" "hub_forwarding" {
  resolver_id   = local.hub_resolver_id
  name          = "dnsHubForwarding"
  scope         = "PRIVATE"
  subnet_id     = var.hub_resolver_subnet_id
  is_forwarding = true
  is_listening  = false
  nsg_ids       = [var.hub_resolver_nsg_id]
}

# ── Per-environment private view + zone (Azure resolves OCI hostnames here) ──
resource "oci_dns_view" "env" {
  for_each       = var.environments
  compartment_id = var.compartment_id
  scope          = "PRIVATE"
  display_name   = "${each.key}-odaa-view"
}

resource "oci_dns_zone" "env" {
  for_each       = var.environments
  compartment_id = var.compartment_id
  name           = each.value.private_zone
  zone_type      = "PRIMARY"
  scope          = "PRIVATE"
  view_id        = oci_dns_view.env[each.key].id
}

# Attach the per-environment views to the hub resolver so the LISTENING
# endpoint can answer Azure queries for every environment's private zone.
resource "oci_dns_resolver" "hub" {
  resolver_id  = local.hub_resolver_id
  scope        = "PRIVATE"
  display_name = "dns-hub-resolver"

  dynamic "attached_views" {
    for_each = var.environments
    content {
      view_id = oci_dns_view.env[attached_views.key].id
    }
  }
}

# ── Wire each Exadata VCN to the hub ─────────────────────────────────────────
module "link" {
  for_each = var.environments
  source   = "./modules/exadata-dns-link"

  compartment_id = var.compartment_id
  env_name       = each.key

  hub_vcn_id                = var.hub_vcn_id
  hub_listening_endpoint_ip = oci_dns_resolver_endpoint.hub_listening.listening_address
  hub_resolver_subnet_cidr  = var.hub_resolver_subnet_cidr
  hub_resolver_nsg_id       = var.hub_resolver_nsg_id
  hub_route_table_id        = var.hub_route_table_id

  exadata_vcn_id               = each.value.vcn_id
  exadata_resolver_subnet_id   = each.value.resolver_subnet_id
  exadata_resolver_subnet_cidr = each.value.resolver_subnet_cidr
  exadata_resolver_nsg_id      = each.value.resolver_nsg_id
  exadata_route_table_id       = each.value.route_table_id

  azure_forward_domains = var.azure_forward_domains
  manage_route_tables   = var.manage_route_tables
}
