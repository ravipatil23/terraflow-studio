"""Azure DB@Azure provider schemas — hashicorp/azurerm (4.74.0)."""

AZURE_SCHEMAS = {
    'azurerm_virtual_network': {
        'required': ['name', 'address_space', 'location', 'resource_group_name'],
        'optional': ['tags'],
    },
    'azurerm_subnet': {
        'required': ['name', 'resource_group_name', 'virtual_network_name', 'address_prefixes'],
        'optional': ['delegation'],
    },
    'azurerm_oracle_exadata_infrastructure': {
        'required': ['name', 'resource_group_name', 'location', 'shape',
                     'compute_count', 'storage_count', 'zones'],
        'optional': ['display_name', 'maintenance_window', 'tags'],
    },
    'azurerm_oracle_cloud_vm_cluster': {
        'required': ['name', 'resource_group_name', 'location',
                     'cloud_exadata_infrastructure_id', 'subnet_id',
                     'virtual_network_id', 'hostname', 'cpu_core_count',
                     'data_storage_size_in_tbs', 'gi_version',
                     'license_model', 'ssh_public_keys'],
        'optional': ['display_name', 'cluster_name', 'domain', 'backup_subnet_cidr',
                     'data_storage_percentage', 'time_zone',
                     'scan_listener_port_tcp', 'db_servers',
                     'data_collection_options', 'tags'],
    },
}

AZURE_RESOURCE_OUTPUTS = {
    'azurerm_virtual_network': ['id', 'name', 'location', 'resource_group_name'],
    'azurerm_subnet': ['id', 'name'],
    'azurerm_oracle_exadata_infrastructure': ['id', 'name'],
    'azurerm_oracle_cloud_vm_cluster': ['id', 'name', 'ocid'],
}
