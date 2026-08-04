# Oracle Database@Azure — reusable root module
#
# Fill in terraform.tfvars and run. Add entries to the maps to scale — no need
# to edit this file.
#
# Flow: VNet (+ delegated subnet) -> Exadata Infrastructure -> VM Cluster

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 4.9.0"
    }
  }
}

provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
}

# ── VNets + delegated subnets ─────────────────────────────────────────────────
module "vnet" {
  source   = "./modules/vnet"
  for_each = var.azure_vnets

  resource_group_name   = var.resource_group_name
  location              = var.location
  vnet_name             = each.value.vnet_name
  address_space         = each.value.address_space
  subnet_name           = each.value.subnet_name
  subnet_address_prefix = each.value.subnet_address_prefix
  tags                  = var.tags
}

# ── Exadata Infrastructures ───────────────────────────────────────────────────
module "exadata_infra" {
  source   = "./modules/exadata-infra"
  for_each = var.azure_infras

  resource_group_name = var.resource_group_name
  location            = var.location
  name                = each.value.name
  display_name        = each.value.display_name
  shape               = each.value.shape
  compute_count       = each.value.compute_count
  storage_count       = each.value.storage_count
  zone                = each.value.zone
  tags                = var.tags
}

# ── VM Clusters ───────────────────────────────────────────────────────────────
# infra_ref / vnet_ref must match keys in azure_infras / azure_vnets.
module "vm_cluster" {
  source   = "./modules/vm-cluster"
  for_each = var.azure_clusters

  resource_group_name             = var.resource_group_name
  location                        = var.location
  name                            = each.value.name
  display_name                    = each.value.display_name
  hostname                        = each.value.hostname
  cpu_core_count                  = each.value.cpu_core_count
  data_storage_size_in_tbs        = each.value.data_storage_size_in_tbs
  memory_size_in_gbs              = each.value.memory_size_in_gbs
  db_node_storage_size_in_gbs     = each.value.db_node_storage_size_in_gbs
  gi_version                      = each.value.gi_version
  license_model                   = each.value.license_model
  ssh_public_keys                 = each.value.ssh_public_keys
  local_backup_enabled            = each.value.local_backup_enabled
  sparse_diskgroup_enabled        = each.value.sparse_diskgroup_enabled
  cluster_name                    = each.value.cluster_name
  time_zone                       = each.value.time_zone
  scan_listener_port_tcp          = each.value.scan_listener_port_tcp
  backup_subnet_cidr              = each.value.backup_subnet_cidr
  cloud_exadata_infrastructure_id = module.exadata_infra[each.value.infra_ref].infra_id
  subnet_id                       = module.vnet[each.value.vnet_ref].subnet_id
  virtual_network_id              = module.vnet[each.value.vnet_ref].vnet_id
  tags                            = var.tags

  depends_on = [module.exadata_infra, module.vnet]
}
