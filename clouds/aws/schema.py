"""AWS ODB provider schemas — hashicorp/aws."""

AWS_SCHEMAS = {
    'aws_odb_network': {
        'required': ['display_name', 'availability_zone_id', 'client_subnet_cidr',
                     'backup_subnet_cidr', 's3_access', 'zero_etl_access'],
        'optional': ['availability_zone', 'region', 'default_dns_prefix',
                     'delete_associated_resources', 'tags'],
    },
    'aws_odb_cloud_exadata_infrastructure': {
        'required': ['display_name', 'shape', 'compute_count', 'storage_count',
                     'availability_zone_id', 'maintenance_window'],
        'optional': ['availability_zone', 'region', 'database_server_type',
                     'storage_server_type', 'customer_contacts', 'tags'],
    },
    'aws_odb_network_peering_connection': {
        'required': ['display_name'],
        'optional': ['odb_network_id', 'odb_network_arn', 'peer_network_id',
                     'peer_network_cidrs', 'region', 'tags'],
    },
    'aws_odb_cloud_vm_cluster': {
        'required': ['display_name', 'cpu_core_count', 'gi_version',
                     'hostname_prefix', 'license_model', 'ssh_public_keys',
                     'data_collection_options'],
        'optional': ['cloud_exadata_infrastructure_id', 'cloud_exadata_infrastructure_arn',
                     'odb_network_id', 'odb_network_arn', 'db_servers',
                     'cluster_name', 'timezone', 'data_storage_size_in_tbs',
                     'db_node_storage_size_in_gbs', 'memory_size_in_gbs',
                     'scan_listener_port_tcp',
                     'is_local_backup_enabled', 'is_sparse_diskgroup_enabled',
                     'region', 'tags'],
    },
}

AWS_RESOURCE_OUTPUTS = {
    'aws_odb_network': [
        'id', 'arn', 'oci_network_anchor_id', 'oci_vcn_id', 'display_name',
        'status', 'status_reason', 'peering_connection_id',
    ],
    'aws_odb_cloud_exadata_infrastructure': [
        'id', 'arn', 'oci_exadata_infrastructure_id', 'display_name',
        'shape', 'compute_count', 'storage_count', 'status', 'status_reason',
        'activated_storage_count', 'additional_storage_count',
        'availability_zone', 'availability_zone_id',
    ],
    'aws_odb_network_peering_connection': [
        'id', 'arn', 'display_name', 'status', 'status_reason',
        'odb_network_id', 'peer_network_id',
    ],
    'aws_odb_cloud_vm_cluster': [
        'id', 'arn', 'display_name', 'gi_version', 'hostname_prefix',
        'hostname_prefix_computed', 'license_model', 'cpu_core_count',
        'cluster_name', 'scan_dns_name', 'scan_ip_ids', 'status', 'status_reason',
        'lifecycle_state', 'node_count', 'shape', 'storage_size_in_gbs',
        'data_storage_size_in_tbs', 'db_node_storage_size_in_gbs',
        'memory_size_in_gbs', 'scan_listener_port_tcp', 'system_version',
    ],
}
