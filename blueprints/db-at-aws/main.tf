# Oracle Database@AWS — reusable root module
#
# Fill in terraform.tfvars and run. You do NOT need to edit this file to add
# more networks / infras / clusters — just add entries to the maps in tfvars.
#
# Flow: ODB Network -> Exadata Infrastructure -> VM Cluster (+ optional peering)

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.15.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# ── ODB Networks ────────────────────────────────────────────────────────────
module "odb_network" {
  source   = "./modules/odb-network"
  for_each = var.aws_networks

  display_name                = each.value.display_name
  availability_zone_id        = each.value.availability_zone_id
  client_subnet_cidr          = each.value.client_subnet_cidr
  backup_subnet_cidr          = each.value.backup_subnet_cidr
  s3_access                   = each.value.s3_access
  zero_etl_access             = each.value.zero_etl_access
  availability_zone           = each.value.availability_zone
  region                      = each.value.region
  custom_domain_name          = each.value.custom_domain_name
  default_dns_prefix          = each.value.default_dns_prefix
  delete_associated_resources = each.value.delete_associated_resources
  tags                        = var.tags
}

# ── Exadata Infrastructures ───────────────────────────────────────────────────
module "exadata_infra" {
  source   = "./modules/exadata-infra"
  for_each = var.aws_infras

  display_name                        = each.value.display_name
  shape                               = each.value.shape
  compute_count                       = each.value.compute_count
  storage_count                       = each.value.storage_count
  availability_zone_id                = each.value.availability_zone_id
  availability_zone                   = each.value.availability_zone
  region                              = each.value.region
  database_server_type                = each.value.database_server_type
  storage_server_type                 = each.value.storage_server_type
  customer_contacts                   = each.value.customer_contacts
  mw_preference                       = each.value.mw_preference
  mw_patching_mode                    = each.value.mw_patching_mode
  mw_is_custom_action_timeout_enabled = each.value.mw_is_custom_action_timeout_enabled
  mw_custom_action_timeout_in_mins    = each.value.mw_custom_action_timeout_in_mins
  mw_lead_time_in_weeks               = each.value.mw_lead_time_in_weeks
  mw_days_of_week                     = each.value.mw_days_of_week
  mw_months                           = each.value.mw_months
  mw_hours_of_day                     = each.value.mw_hours_of_day
  mw_weeks_of_month                   = each.value.mw_weeks_of_month
  tags                                = var.tags
}

# ── DB Server IDs ─────────────────────────────────────────────────────────────
# Auto-discovered per cluster from the Exadata Infrastructure when
# db_servers_mode = "auto" (the default). Set "manual" to supply your own.
data "aws_odb_db_servers" "this" {
  depends_on                      = [module.exadata_infra]
  for_each                        = { for k, v in var.aws_clusters : k => v if v.db_servers_mode == "auto" }
  cloud_exadata_infrastructure_id = module.exadata_infra[each.value.infra_ref].infra_id
}

# ── Network Peerings (optional) ───────────────────────────────────────────────
module "peering" {
  source   = "./modules/peering"
  for_each = var.aws_peerings

  display_name    = each.value.display_name
  odb_network_id  = module.odb_network[each.value.network_ref].network_id
  peer_network_id = each.value.peer_network_id
  region          = each.value.region
  tags            = var.tags

  depends_on = [module.odb_network]
}

# ── VM Clusters ───────────────────────────────────────────────────────────────
module "vm_cluster" {
  source   = "./modules/vm-cluster"
  for_each = var.aws_clusters

  display_name                      = each.value.display_name
  cpu_core_count                    = each.value.cpu_core_count
  gi_version                        = each.value.gi_version
  hostname_prefix                   = each.value.hostname_prefix
  license_model                     = each.value.license_model
  ssh_public_keys                   = each.value.ssh_public_keys
  cloud_exadata_infrastructure_id   = module.exadata_infra[each.value.infra_ref].infra_id
  odb_network_id                    = module.odb_network[each.value.network_ref].network_id
  db_servers                        = each.value.db_servers_mode == "auto" ? data.aws_odb_db_servers.this[each.key].db_servers[*].id : each.value.db_servers
  dco_is_diagnostics_events_enabled = each.value.dco_is_diagnostics_events_enabled
  dco_is_health_monitoring_enabled  = each.value.dco_is_health_monitoring_enabled
  dco_is_incident_logs_enabled      = each.value.dco_is_incident_logs_enabled
  cluster_name                      = each.value.cluster_name
  timezone                          = each.value.timezone
  data_storage_size_in_tbs          = each.value.data_storage_size_in_tbs
  db_node_storage_size_in_gbs       = each.value.db_node_storage_size_in_gbs
  memory_size_in_gbs                = each.value.memory_size_in_gbs
  scan_listener_port_tcp            = each.value.scan_listener_port_tcp
  is_local_backup_enabled           = each.value.is_local_backup_enabled
  is_sparse_diskgroup_enabled       = each.value.is_sparse_diskgroup_enabled
  tags                              = var.tags

  depends_on = [module.odb_network, module.exadata_infra]
}
