# ─────────────────────────────────────────────────────────────────────────────
# Oracle Database@Azure — Network Anchor — fill in your values here.
#
# Prerequisites (must already exist): a Resource Anchor, and a subnet delegated to
# Oracle.Database/networkAttachment. Get their Azure resource IDs (e.g. via
# `az resource show ... --query id`) and paste them below.
#
# Commented lines show OPTIONAL parameters with default/sample values.
# ─────────────────────────────────────────────────────────────────────────────

subscription_id = "00000000-0000-0000-0000-000000000000"

network_anchors = {
  anchor1 = {
    name                = "odb-anchor-eastus" # 3-24 chars, letters/numbers/hyphens
    resource_group_name = "rg-oracle-prod"
    location            = "eastus"
    resource_anchor_id  = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-oracle-prod/providers/Oracle.Database/resourceAnchors/ra-eastus"
    subnet_id           = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-oracle-prod/providers/Microsoft.Network/virtualNetworks/vnet-oracle-eastus/subnets/snet-oracle-delegated"

    # ── optional (defaults shown) ──
    # zones                 = ["2"]            # AZ where the Base Database resides
    # tags                  = { env = "prod" }
    # oci_vcn_dns_label     = "odbprod"        # optional if DNS config provided
    # oci_backup_cidr_block = "10.20.2.0/24"   # not needed for Base Database

    # ── DNS options (all default false / empty) ──
    # dns_listening_endpoint_enabled  = true
    # dns_listening_allowed_cidrs     = "10.0.0.0/16,10.1.0.0/16"   # comma-separated
    # dns_forwarding_endpoint_enabled = true
    # dns_forwarding_rules = [
    #   { domain_names = "corp.example.com,db.example.com", forwarding_ip_address = "10.0.0.10" },
    # ]
    # dns_zone_sync_enabled = true             # overlaps with the listening endpoint — pick one
  }
}
