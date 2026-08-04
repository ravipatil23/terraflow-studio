# ─────────────────────────────────────────────────────────────────────────────
# Oracle Database@AWS — fill in your values here. This is the ONLY file you
# normally need to edit. Add more entries to any map to create more resources.
#
# Commented lines show OPTIONAL parameters with their default/sample values —
# uncomment and edit any you need. Uncommented lines are required (or recommended).
# ─────────────────────────────────────────────────────────────────────────────

aws_region = "us-east-1"

tags = {
  Environment = "dev"
  ManagedBy   = "Terraform"
  Owner       = "platform-team"
}

# ── Existing resources (brownfield) ───────────────────────────────────────────
# Already have an ODB Network or Exadata Infrastructure — provisioned by hand,
# by another stack, or by another team? List its ID here instead of describing
# it in the aws_networks / aws_infras maps below. Entries here are referenced
# only: Terraform never creates, changes or destroys them.
#
# Use the same key your clusters and peerings already reference, and leave the
# matching aws_networks / aws_infras entry out. Mixing is fine — create one
# network here and reuse an existing infra, or any other combination.
#
#   existing_odb_network_ids = {
#     net1 = "odb-net-0a1b2c3d4e5f67890"
#   }
#
#   existing_infra_ids = {
#     infra1 = "odb-exa-0a1b2c3d4e5f67890"
#   }
#
#   aws_networks = {}          # net1 is not created — it already exists
#   aws_infras   = {}          # infra1 is not created — it already exists
#
#   aws_clusters = {
#     vmc1 = { network_ref = "net1", infra_ref = "infra1", ... }   # unchanged
#   }

# ── ODB Networks ──────────────────────────────────────────────────────────────
# Key ("net1") is an internal reference used by clusters/peerings below.
# Omit an entry here if you listed it in existing_odb_network_ids above.
aws_networks = {
  net1 = {
    display_name         = "odbnet-prod-use1"
    availability_zone_id = "use1-az6"
    client_subnet_cidr   = "10.10.0.0/24"
    backup_subnet_cidr   = "10.10.1.0/24"

    # ── optional (defaults shown) ──
    # s3_access                   = "ENABLED"   # ENABLED | DISABLED
    # zero_etl_access             = "DISABLED"  # ENABLED | DISABLED
    # availability_zone           = ""          # AZ name override (prefer availability_zone_id)
    # region                      = ""          # region override (defaults to aws_region)
    # custom_domain_name          = ""          # custom DNS domain (mutually exclusive with default_dns_prefix)
    # default_dns_prefix          = ""          # DNS prefix (used only when custom_domain_name is blank)
    # delete_associated_resources = false       # delete associated resources on network deletion
  }
}

# ── Exadata Infrastructures ───────────────────────────────────────────────────
aws_infras = {
  infra1 = {
    display_name         = "exa-prod-use1"
    availability_zone_id = "use1-az6"

    # ── optional (defaults shown) ──
    # shape                               = "Exadata.X11M"
    # compute_count                       = 2
    # storage_count                       = 3
    # availability_zone                   = ""               # AZ name override
    # region                              = ""               # region override
    # database_server_type                = ""               # e.g. "X11M"
    # storage_server_type                 = ""               # e.g. "X11M-HC"
    # customer_contacts                   = ["dba@example.com"]
    # mw_preference                       = "NO_PREFERENCE"  # NO_PREFERENCE | CUSTOM_PREFERENCE
    # mw_patching_mode                    = "ROLLING"        # ROLLING | NON_ROLLING
    # mw_is_custom_action_timeout_enabled = false
    # mw_custom_action_timeout_in_mins    = 15
    # mw_lead_time_in_weeks               = 0
    # mw_days_of_week                     = ["MONDAY"]       # custom-window days
    # mw_months                           = ["JANUARY"]      # custom-window months
    # mw_hours_of_day                     = [4]              # 0,4,8,12,16,20 (UTC)
    # mw_weeks_of_month                   = [1]              # 1-4
  }
}

# ── VM Clusters ───────────────────────────────────────────────────────────────
# infra_ref / network_ref must match keys above.
aws_clusters = {
  vmc1 = {
    display_name    = "vmc-prod-use1"
    gi_version      = "23.0.0.0"
    hostname_prefix = "exadb"
    infra_ref       = "infra1"
    network_ref     = "net1"
    ssh_public_keys = [
      "ssh-rsa AAAAB3Nza... replace-with-your-key",
    ]

    # ── optional (defaults shown) ──
    # cpu_core_count                    = 16
    # license_model                     = "LICENSE_INCLUDED"  # or BRING_YOUR_OWN_LICENSE
    # db_servers_mode                   = "auto"               # "auto" discovers from infra; "manual" uses db_servers
    # db_servers                        = ["dbserver-ocid-1"]  # only when db_servers_mode = "manual"
    # dco_is_diagnostics_events_enabled = true
    # dco_is_health_monitoring_enabled  = true
    # dco_is_incident_logs_enabled      = true
    # cluster_name                      = ""        # optional cluster name
    # timezone                          = "UTC"
    # data_storage_size_in_tbs          = 2
    # db_node_storage_size_in_gbs       = 120
    # memory_size_in_gbs                = 60
    # scan_listener_port_tcp            = 1521
    # is_local_backup_enabled           = false
    # is_sparse_diskgroup_enabled       = false
  }
}

# ── Network Peerings (optional) ───────────────────────────────────────────────
# Uncomment to peer an ODB network with one of your existing VPCs.
# aws_peerings = {
#   peer1 = {
#     display_name    = "peer-to-app-vpc"
#     network_ref     = "net1"
#     peer_network_id = "vpc-0123456789abcdef0"
#     # region        = ""   # optional region override
#   }
# }
