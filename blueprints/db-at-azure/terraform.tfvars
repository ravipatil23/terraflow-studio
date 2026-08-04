# ─────────────────────────────────────────────────────────────────────────────
# Oracle Database@Azure — fill in your values here. This is the ONLY file you
# normally need to edit. Add more entries to any map to create more resources.
# The resource group must already exist.
#
# Commented lines show OPTIONAL parameters with their default/sample values —
# uncomment and edit any you need. Uncommented lines are required (or recommended).
# ─────────────────────────────────────────────────────────────────────────────

subscription_id     = "00000000-0000-0000-0000-000000000000"
resource_group_name = "rg-oracle-prod"
location            = "eastus"

tags = {
  Environment = "dev"
  ManagedBy   = "Terraform"
}

# ── VNets (+ Oracle-delegated subnet) ─────────────────────────────────────────
azure_vnets = {
  vnet1 = {
    vnet_name             = "vnet-oracle-eastus"
    address_space         = "10.20.0.0/16"
    subnet_name           = "snet-oracle-delegated"
    subnet_address_prefix = "10.20.1.0/24"
    # (no optional fields — all four are required)
  }
}

# ── Exadata Infrastructures ───────────────────────────────────────────────────
azure_infras = {
  infra1 = {
    name         = "exa-prod-eastus"
    display_name = "Exadata Prod EastUS"
    zone         = "2"

    # ── optional (defaults shown) ──
    # shape         = "Exadata.X11M"
    # compute_count = 2
    # storage_count = 3
  }
}

# ── VM Clusters ───────────────────────────────────────────────────────────────
# infra_ref / vnet_ref must match keys above.
azure_clusters = {
  vmc1 = {
    name         = "vmc-prod-eastus"
    display_name = "VM Cluster Prod"
    hostname     = "exadb"
    infra_ref    = "infra1"
    vnet_ref     = "vnet1"
    ssh_public_keys = [
      "ssh-rsa AAAAB3Nza... replace-with-your-key",
    ]

    # ── optional (defaults shown) ──
    # cpu_core_count              = 4
    # data_storage_size_in_tbs    = 2
    # memory_size_in_gbs          = 60
    # db_node_storage_size_in_gbs = 120
    # gi_version                  = "23.0.0.0"
    # license_model               = "LicenseIncluded"  # or BringYourOwnLicense
    # local_backup_enabled        = false
    # sparse_diskgroup_enabled    = false
    # cluster_name                = ""        # optional cluster name
    # time_zone                   = "UTC"
    # scan_listener_port_tcp      = 1521
    # backup_subnet_cidr          = "192.168.252.0/22"  # see the note below
  }

  # ── Adding a second cluster on the SAME delegated subnet ──────────────────
  # Reuse the subnet by pointing at the same vnet_ref. The delegated subnet is
  # shared by design; the backup range is not — Oracle carves it inside the VNet
  # per cluster, so give each cluster its own non-overlapping range once more
  # than one cluster shares a vnet_ref. Both clusters default to the same
  # 192.168.252.0/22, so the second one MUST be given a different range or the
  # apply fails on a collision. Never set it to "" — an empty value makes every
  # later plan propose replacing the cluster.
  #
  # vmc2 = {
  #   name               = "vmc-reporting-eastus"
  #   display_name       = "VM Cluster Reporting"
  #   hostname           = "rpt"
  #   infra_ref          = "infra1"
  #   vnet_ref           = "vnet1"          # same delegated subnet as vmc1
  #   backup_subnet_cidr = "10.0.11.0/24"   # vmc1's must differ, e.g. 10.0.10.0/24
  #   ssh_public_keys    = ["ssh-rsa AAAAB3Nza... replace-with-your-key"]
  # }
}
