# ─────────────────────────────────────────────────────────────────────────────
# Oracle Database@AWS — fill in your values here. This is the ONLY file you
# normally need to edit. Add more entries to any map to create more resources.
# ─────────────────────────────────────────────────────────────────────────────

aws_region = "us-east-1"

tags = {
  Environment = "dev"
  ManagedBy   = "Terraform"
  Owner       = "platform-team"
}

# ── ODB Networks ──────────────────────────────────────────────────────────────
# Key ("net1") is an internal reference used by clusters/peerings below.
aws_networks = {
  net1 = {
    display_name         = "odbnet-prod-use1"
    availability_zone_id = "use1-az6"
    client_subnet_cidr   = "10.10.0.0/24"
    backup_subnet_cidr   = "10.10.1.0/24"
    # s3_access          = "ENABLED"
    # zero_etl_access    = "DISABLED"
  }
}

# ── Exadata Infrastructures ───────────────────────────────────────────────────
aws_infras = {
  infra1 = {
    display_name         = "exa-prod-use1"
    availability_zone_id = "use1-az6"
    shape                = "Exadata.X11M"
    compute_count        = 2
    storage_count        = 3
    # customer_contacts  = ["dba@example.com"]
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
    cpu_core_count  = 16
    license_model   = "LICENSE_INCLUDED"
    ssh_public_keys = [
      "ssh-rsa AAAAB3Nza... replace-with-your-key",
    ]
    # db_servers_mode = "auto"  # auto-discovers DB servers from infra1
  }
}

# ── Network Peerings (optional) ───────────────────────────────────────────────
# Uncomment to peer an ODB network with one of your existing VPCs.
# aws_peerings = {
#   peer1 = {
#     display_name    = "peer-to-app-vpc"
#     network_ref     = "net1"
#     peer_network_id = "vpc-0123456789abcdef0"
#   }
# }
