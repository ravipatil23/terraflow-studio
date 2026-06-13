# ─────────────────────────────────────────────────────────────────────────────
# Oracle Database@GCP — fill in your values here. This is the ONLY file you
# normally need to edit. Add more entries to any map to create more resources.
# ─────────────────────────────────────────────────────────────────────────────

gcp_project = "my-gcp-project"
gcp_region  = "us-east4"

# ── ODB Networks (creates the network + client & backup subnets) ──────────────
# Key ("net1") is referenced by gcp_vm_clusters.network_key below.
gcp_odb_networks = {
  net1 = {
    odb_network_id    = "odbnet-prod"
    network           = "projects/my-gcp-project/global/networks/default"
    gcp_oracle_zone   = "us-east4-b-r1"
    client_subnet_id  = "odb-client-prod"
    client_cidr_range = "10.30.0.0/24"
    backup_subnet_id  = "odb-backup-prod"
    backup_cidr_range = "10.30.1.0/24"
    # deletion_protection = true
  }
}

# ── Exadata Infrastructures ───────────────────────────────────────────────────
gcp_exadata_infras = {
  infra1 = {
    cloud_exadata_infrastructure_id = "exa-prod"
    display_name                    = "Exadata Prod"
    gcp_oracle_zone                 = "us-east4-b-r1"
    shape                           = "Exadata.X11M"
    compute_count                   = 2
    storage_count                   = 3
    # customer_contacts             = ["dba@example.com"]
  }
}

# ── ExaDB VM Clusters ─────────────────────────────────────────────────────────
# infra_key / network_key must match keys above.
gcp_vm_clusters = {
  vmc1 = {
    infra_key               = "infra1"
    network_key             = "net1"
    cloud_vm_cluster_id     = "vmc-prod"
    display_name            = "VM Cluster Prod"
    hostname_prefix         = "exadb"
    cpu_core_count          = 4
    memory_size_gb          = 60
    db_node_storage_size_gb = 120
    data_storage_size_tb    = 2
    gi_version              = "23.0.0.0"
    license_type            = "LICENSE_INCLUDED"
    ssh_public_keys = [
      "ssh-rsa AAAAB3Nza... replace-with-your-key",
    ]
  }
}
