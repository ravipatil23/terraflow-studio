# ─────────────────────────────────────────────────────────────────────────────
# Oracle Database@GCP — fill in your values here. This is the ONLY file you
# normally need to edit. Add more entries to any map to create more resources.
#
# Commented lines show OPTIONAL parameters with their default/sample values —
# uncomment and edit any you need. Uncommented lines are required (or recommended).
# ─────────────────────────────────────────────────────────────────────────────

gcp_project = "my-gcp-project"
gcp_region  = "us-east4"

# ── ODB Networks (creates the network + client & backup subnets) ──────────────
# Key ("net1") is referenced by gcp_vm_clusters.network_key below.
gcp_odb_networks = {
  net1 = {
    odb_network_id    = "odbnet-prod"
    network           = "projects/my-gcp-project/global/networks/default"
    client_subnet_id  = "odb-client-prod"
    client_cidr_range = "10.30.0.0/24"
    backup_subnet_id  = "odb-backup-prod"
    backup_cidr_range = "10.30.1.0/24"

    # ── optional (defaults shown) ──
    # location            = ""                # region override (defaults to gcp_region)
    # project             = ""                # project override (defaults to gcp_project)
    # gcp_oracle_zone     = "us-east4-b-r1"   # Oracle zone within the region
    # deletion_protection = true
    # labels              = { env = "prod" }
  }
}

# ── Exadata Infrastructures ───────────────────────────────────────────────────
gcp_exadata_infras = {
  infra1 = {
    cloud_exadata_infrastructure_id = "exa-prod"
    shape                           = "Exadata.X11M"
    compute_count                   = 2
    storage_count                   = 3

    # ── optional (defaults shown) ──
    # display_name                        = "Exadata Prod"
    # gcp_oracle_zone                     = "us-east4-b-r1"
    # location                            = ""               # region override
    # project                             = ""               # project override
    # total_storage_size_gb               = 0                # 0 = shape default
    # customer_contacts                   = ["dba@example.com"]
    # mw_preference                       = "NO_PREFERENCE"  # NO_PREFERENCE | CUSTOM_PREFERENCE
    # mw_patching_mode                    = "ROLLING"        # ROLLING | NONROLLING
    # mw_is_custom_action_timeout_enabled = false
    # mw_custom_action_timeout_mins       = 15
    # mw_lead_time_week                   = 1
    # mw_days_of_week                     = ["MONDAY"]
    # mw_months                           = ["JANUARY"]
    # mw_hours_of_day                     = [4]              # 0,4,8,12,16,20 UTC
    # mw_weeks_of_month                   = [1]              # 1-4
    # deletion_protection                 = true
    # labels                              = { env = "prod" }
  }
}

# ── ExaDB VM Clusters ─────────────────────────────────────────────────────────
# infra_key / network_key must match keys above.
gcp_vm_clusters = {
  vmc1 = {
    infra_key               = "infra1"
    network_key             = "net1"
    cloud_vm_cluster_id     = "vmc-prod"
    hostname_prefix         = "exadb"
    cpu_core_count          = 4
    memory_size_gb          = 60
    db_node_storage_size_gb = 120
    data_storage_size_tb    = 2
    ssh_public_keys = [
      "ssh-rsa AAAAB3Nza... replace-with-your-key",
    ]

    # ── optional (defaults shown) ──
    # display_name             = "VM Cluster Prod"
    # location                 = ""               # region override
    # project                  = ""               # project override
    # gi_version               = "23.0.0.0"
    # license_type             = "LICENSE_INCLUDED"  # or BRING_YOUR_OWN_LICENSE
    # local_backup_enabled     = false
    # sparse_diskgroup_enabled = false
    # cluster_name             = "prodclu"        # max 11 chars
    # node_count               = 2
    # ocpu_count               = 4                # fractional OCPU allocation
    # disk_redundancy          = "HIGH"           # HIGH | NORMAL
    # time_zone                = "UTC"
    # scan_listener_port_tcp   = 1521
    # dco_diagnostics          = true
    # dco_health               = true
    # dco_incident_logs        = true
    # deletion_protection      = true
    # labels                   = { env = "prod" }
  }
}
