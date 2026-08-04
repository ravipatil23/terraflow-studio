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

# ── Resource lookup ───────────────────────────────────────────────────────────
# One keyspace covering resources this blueprint creates and resources that
# already exist (see the existing_* maps in terraform.tfvars), so network_ref /
# infra_ref resolve the same way whichever side a resource lives on.
#
# Merged rather than a conditional on purpose: both branches of a ?: get
# evaluated, so indexing a module for a key that was never created fails even on
# the branch that is not taken.
locals {
  odb_network_ids = merge(
    { for k, m in module.odb_network : k => m.network_id },
    var.existing_odb_network_ids,
  )
  infra_ids = merge(
    { for k, m in module.exadata_infra : k => m.infra_id },
    var.existing_infra_ids,
  )
}

# A key defined in both maps would create the resource *and* wire everything to
# the pre-existing one, leaving the new resource orphaned. Catch it up front.
check "no_duplicate_network_keys" {
  assert {
    condition = length(setintersection(keys(var.aws_networks), keys(var.existing_odb_network_ids))) == 0
    error_message = format(
      "These keys appear in both aws_networks and existing_odb_network_ids: %s. Keep each network in one map only — describe it in aws_networks to create it, or give its ID in existing_odb_network_ids to reuse it.",
      join(", ", setintersection(keys(var.aws_networks), keys(var.existing_odb_network_ids))),
    )
  }
}

check "no_duplicate_infra_keys" {
  assert {
    condition = length(setintersection(keys(var.aws_infras), keys(var.existing_infra_ids))) == 0
    error_message = format(
      "These keys appear in both aws_infras and existing_infra_ids: %s. Keep each infrastructure in one map only — describe it in aws_infras to create it, or give its ID in existing_infra_ids to reuse it.",
      join(", ", setintersection(keys(var.aws_infras), keys(var.existing_infra_ids))),
    )
  }
}

# ── DB Server IDs ─────────────────────────────────────────────────────────────
# Auto-discovered per cluster from the Exadata Infrastructure when
# db_servers_mode = "auto" (the default). Set "manual" to supply your own.
data "aws_odb_db_servers" "this" {
  depends_on                      = [module.exadata_infra]
  for_each                        = { for k, v in var.aws_clusters : k => v if v.db_servers_mode == "auto" }
  cloud_exadata_infrastructure_id = local.infra_ids[each.value.infra_ref]
}

# ── Network Peerings (optional) ───────────────────────────────────────────────
module "peering" {
  source   = "./modules/peering"
  for_each = var.aws_peerings

  display_name    = each.value.display_name
  odb_network_id  = local.odb_network_ids[each.value.network_ref]
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
  cloud_exadata_infrastructure_id   = local.infra_ids[each.value.infra_ref]
  odb_network_id                    = local.odb_network_ids[each.value.network_ref]
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
