# Oracle Database@GCP — reusable root module
#
# Fill in terraform.tfvars and run. Add entries to the maps to scale — no need
# to edit this file.
#
# Flow: ODB Network (+ client/backup subnets) -> Exadata Infrastructure -> VM Cluster

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 6.0.0"
    }
  }
}

provider "google" {
  project = var.gcp_project
  region  = var.gcp_region
}

# ── ODB Networks ────────────────────────────────────────────────────────────
module "odb_network" {
  source   = "./modules/odb-network"
  for_each = var.gcp_odb_networks

  odb_network_id      = each.value.odb_network_id
  location            = each.value.location != "" ? each.value.location : var.gcp_region
  network             = each.value.network
  project             = each.value.project != "" ? each.value.project : var.gcp_project
  gcp_oracle_zone     = each.value.gcp_oracle_zone
  client_subnet_id    = each.value.client_subnet_id
  client_cidr_range   = each.value.client_cidr_range
  backup_subnet_id    = each.value.backup_subnet_id
  backup_cidr_range   = each.value.backup_cidr_range
  deletion_protection = each.value.deletion_protection
  labels              = each.value.labels
}

# ── Exadata Infrastructures ───────────────────────────────────────────────────
module "exadata_infra" {
  source   = "./modules/exadata-infra"
  for_each = var.gcp_exadata_infras

  cloud_exadata_infrastructure_id     = each.value.cloud_exadata_infrastructure_id
  location                            = each.value.location != "" ? each.value.location : var.gcp_region
  display_name                        = each.value.display_name
  gcp_oracle_zone                     = each.value.gcp_oracle_zone
  project                             = each.value.project != "" ? each.value.project : var.gcp_project
  shape                               = each.value.shape
  compute_count                       = each.value.compute_count
  storage_count                       = each.value.storage_count
  total_storage_size_gb               = each.value.total_storage_size_gb
  customer_contacts                   = each.value.customer_contacts
  mw_preference                       = each.value.mw_preference
  mw_patching_mode                    = each.value.mw_patching_mode
  mw_is_custom_action_timeout_enabled = each.value.mw_is_custom_action_timeout_enabled
  mw_custom_action_timeout_mins       = each.value.mw_custom_action_timeout_mins
  mw_lead_time_week                   = each.value.mw_lead_time_week
  mw_days_of_week                     = each.value.mw_days_of_week
  mw_months                           = each.value.mw_months
  mw_hours_of_day                     = each.value.mw_hours_of_day
  mw_weeks_of_month                   = each.value.mw_weeks_of_month
  deletion_protection                 = each.value.deletion_protection
  labels                              = each.value.labels
}

# ── DB Server OCIDs ───────────────────────────────────────────────────────────
# Auto-discovered per cluster from the Exadata Infrastructure.
data "google_oracle_database_db_servers" "this" {
  depends_on                   = [module.exadata_infra]
  for_each                     = var.gcp_vm_clusters
  location                     = each.value.location != "" ? each.value.location : var.gcp_region
  project                      = each.value.project != "" ? each.value.project : var.gcp_project
  cloud_exadata_infrastructure = module.exadata_infra[each.value.infra_key].infra_self_link
}

# ── VM Clusters ───────────────────────────────────────────────────────────────
# infra_key / network_key must match keys in gcp_exadata_infras / gcp_odb_networks.
module "vm_cluster" {
  source   = "./modules/vm-cluster"
  for_each = var.gcp_vm_clusters

  cloud_vm_cluster_id      = each.value.cloud_vm_cluster_id
  display_name             = each.value.display_name
  location                 = each.value.location != "" ? each.value.location : var.gcp_region
  project                  = each.value.project != "" ? each.value.project : var.gcp_project
  exadata_infrastructure   = module.exadata_infra[each.value.infra_key].infra_self_link
  odb_network              = module.odb_network[each.value.network_key].odb_network_name
  odb_subnet               = module.odb_network[each.value.network_key].client_subnet_name
  backup_odb_subnet        = module.odb_network[each.value.network_key].backup_subnet_name
  db_server_ocids          = data.google_oracle_database_db_servers.this[each.key].db_servers[*].properties[0].ocid
  hostname_prefix          = each.value.hostname_prefix
  cpu_core_count           = each.value.cpu_core_count
  memory_size_gb           = each.value.memory_size_gb
  db_node_storage_size_gb  = each.value.db_node_storage_size_gb
  data_storage_size_tb     = each.value.data_storage_size_tb
  gi_version               = each.value.gi_version
  license_type             = each.value.license_type
  ssh_public_keys          = each.value.ssh_public_keys
  local_backup_enabled     = each.value.local_backup_enabled
  sparse_diskgroup_enabled = each.value.sparse_diskgroup_enabled
  cluster_name             = each.value.cluster_name
  node_count               = each.value.node_count
  ocpu_count               = each.value.ocpu_count
  disk_redundancy          = each.value.disk_redundancy
  time_zone                = each.value.time_zone
  scan_listener_port_tcp   = each.value.scan_listener_port_tcp
  dco_diagnostics          = each.value.dco_diagnostics
  dco_health               = each.value.dco_health
  dco_incident_logs        = each.value.dco_incident_logs
  deletion_protection      = each.value.deletion_protection
  labels                   = each.value.labels

  depends_on = [module.odb_network, module.exadata_infra]
}
