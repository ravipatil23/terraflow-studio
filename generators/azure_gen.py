"""Azure (DB@Azure) generators."""
from .helpers import render_tf, tf_bool


def _azure_vnet_defaults(d):
    return {
        'module_name':           d.get('module_name') or 'azure_vnet',
        'resource_group_name':   d.get('resource_group_name') or '',
        'location':              d.get('location') or 'eastus',
        'vnet_name':             d.get('vnet_name') or '',
        'address_space':         d.get('address_space') or '10.0.0.0/16',
        'subnet_name':           d.get('subnet_name') or '',
        'subnet_address_prefix': d.get('subnet_address_prefix') or '10.0.1.0/24',
        'tags':                  d.get('tags') or {},
    }


def _azure_infra_defaults(d):
    return {
        'module_name':           d.get('module_name') or 'azure_exainfra',
        'resource_group_name':   d.get('resource_group_name') or '',
        'location':              d.get('location') or 'eastus',
        'name':                  d.get('name') or '',
        'display_name':          d.get('display_name') or '',
        'shape':                 d.get('shape') or 'Exadata.X11M',
        'compute_count':         int(d.get('compute_count') or 2),
        'storage_count':         int(d.get('storage_count') or 3),
        'zone':                  d.get('zone') or '1',
        'mw_preference':         d.get('mw_preference') or 'NoPreference',
        'mw_patching_mode':      d.get('mw_patching_mode') or 'Rolling',
        'mw_lead_time_in_weeks': int(d.get('mw_lead_time_in_weeks') or 0),
        'tags':                  d.get('tags') or {},
    }


def _azure_cluster_defaults(d, first_vnet_name='', first_infra_name=''):
    return {
        'module_name':           d.get('module_name') or 'azure_vmcluster',
        'resource_group_name':   d.get('resource_group_name') or '',
        'location':              d.get('location') or 'eastus',
        'name':                  d.get('name') or '',
        'display_name':          d.get('display_name') or '',
        'cloud_exadata_infrastructure_id': d.get('cloud_exadata_infrastructure_id') or '',
        'subnet_id':             d.get('subnet_id') or '',
        'vnet_id':               d.get('vnet_id') or '',
        'hostname':              d.get('hostname') or '',
        'cpu_core_count':        int(d.get('cpu_core_count') or 4),
        'data_storage_size_in_tbs':    float(d.get('data_storage_size_in_tbs') or 2),
        'db_node_storage_size_in_gbs': int(d.get('db_node_storage_size_in_gbs') or 120),
        'memory_size_in_gbs':    int(d.get('memory_size_in_gbs') or 60),
        'ssh_public_keys':       d.get('ssh_public_keys') or [],
        'gi_version':            d.get('gi_version') or '19.0.0.0',
        'license_model':         d.get('license_model') or 'LicenseIncluded',
        'cluster_name':          d.get('cluster_name') or '',
        'domain':                d.get('domain') or '',
        'backup_subnet_cidr':    d.get('backup_subnet_cidr') or '',
        'data_storage_percentage':        int(d.get('data_storage_percentage') or 100),
        'is_local_backup_enabled':        bool(d.get('is_local_backup_enabled', False)),
        'is_sparse_diskgroup_enabled':    bool(d.get('is_sparse_diskgroup_enabled', False)),
        'time_zone':             d.get('time_zone') or '',
        'scan_listener_port_tcp':     int(d.get('scan_listener_port_tcp') or 1521),
        'scan_listener_port_tcp_ssl': int(d.get('scan_listener_port_tcp_ssl') or 2484),
        'dco_diagnostics_events_enabled': bool(d.get('dco_diagnostics_events_enabled', True)),
        'dco_health_monitoring_enabled':  bool(d.get('dco_health_monitoring_enabled', True)),
        'dco_incident_logs_enabled':      bool(d.get('dco_incident_logs_enabled', True)),
        'infra_ref':             d.get('infra_ref') or first_infra_name,
        'vnet_ref':              d.get('vnet_ref') or first_vnet_name,
        'tags':                  d.get('tags') or {},
    }


def _azure_vnet_ctx(d):
    return dict(
        resource_group_name=d['resource_group_name'],
        location=d['location'],
        vnet_name=d['vnet_name'],
        address_space=d['address_space'],
        subnet_name=d['subnet_name'],
        subnet_address_prefix=d['subnet_address_prefix'],
        tags=d['tags'],
    )


def _azure_infra_ctx(d):
    return dict(
        resource_group_name=d['resource_group_name'],
        location=d['location'],
        name=d['name'],
        display_name=d['display_name'],
        shape=d['shape'],
        compute_count=d['compute_count'],
        storage_count=d['storage_count'],
        zone=d['zone'],
        mw_preference=d['mw_preference'],
        mw_patching_mode=d['mw_patching_mode'],
        mw_lead_time_in_weeks=d['mw_lead_time_in_weeks'],
        tags=d['tags'],
    )


def _azure_cluster_ctx(d):
    keys = d.get('ssh_public_keys') or []
    ssh_tf = '[' + ', '.join(f'"{k}"' for k in keys) + ']'
    return dict(
        resource_group_name=d['resource_group_name'],
        location=d['location'],
        name=d['name'],
        display_name=d['display_name'],
        cloud_exadata_infrastructure_id=d['cloud_exadata_infrastructure_id'],
        subnet_id=d['subnet_id'],
        vnet_id=d['vnet_id'],
        hostname=d['hostname'],
        cpu_core_count=d['cpu_core_count'],
        data_storage_size_in_tbs=d['data_storage_size_in_tbs'],
        db_node_storage_size_in_gbs=d['db_node_storage_size_in_gbs'],
        memory_size_in_gbs=d['memory_size_in_gbs'],
        ssh_public_keys_tf=ssh_tf,
        gi_version=d['gi_version'],
        license_model=d['license_model'],
        cluster_name=d['cluster_name'],
        domain=d['domain'],
        backup_subnet_cidr=d['backup_subnet_cidr'],
        data_storage_percentage=d['data_storage_percentage'],
        is_local_backup_enabled=tf_bool(d['is_local_backup_enabled']),
        is_sparse_diskgroup_enabled=tf_bool(d['is_sparse_diskgroup_enabled']),
        time_zone=d['time_zone'],
        scan_listener_port_tcp=d['scan_listener_port_tcp'],
        scan_listener_port_tcp_ssl=d['scan_listener_port_tcp_ssl'],
        dco_diagnostics_events_enabled=tf_bool(d['dco_diagnostics_events_enabled']),
        dco_health_monitoring_enabled=tf_bool(d['dco_health_monitoring_enabled']),
        dco_incident_logs_enabled=tf_bool(d['dco_incident_logs_enabled']),
        tags=d['tags'],
    )


def azure_vnet_main(mn, d):
    return render_tf('azure_vnet/main.tf.j2', module_name=mn, **_azure_vnet_ctx(d))


def azure_vnet_vars(mn, d):
    return render_tf('azure_vnet/variables.tf.j2', module_name=mn, **_azure_vnet_ctx(d))


def azure_vnet_outputs(mn):
    return render_tf('azure_vnet/outputs.tf.j2', module_name=mn)


def azure_vnet_tfvars(mn, d):
    return render_tf('azure_vnet/terraform.tfvars.j2', module_name=mn, **_azure_vnet_ctx(d))


def azure_infra_main(mn, d):
    return render_tf('azure_exadata_infra/main.tf.j2', module_name=mn, **_azure_infra_ctx(d))


def azure_infra_vars(mn, d):
    return render_tf('azure_exadata_infra/variables.tf.j2', module_name=mn, **_azure_infra_ctx(d))


def azure_infra_outputs(mn):
    return render_tf('azure_exadata_infra/outputs.tf.j2', module_name=mn)


def azure_infra_tfvars(mn, d):
    return render_tf('azure_exadata_infra/terraform.tfvars.j2', module_name=mn, **_azure_infra_ctx(d))


def azure_cluster_main(mn, d):
    return render_tf('azure_vm_cluster/main.tf.j2', module_name=mn, **_azure_cluster_ctx(d))


def azure_cluster_vars(mn, d):
    return render_tf('azure_vm_cluster/variables.tf.j2', module_name=mn, **_azure_cluster_ctx(d))


def azure_cluster_outputs(mn):
    return render_tf('azure_vm_cluster/outputs.tf.j2', module_name=mn)


def azure_cluster_tfvars(mn, d):
    return render_tf('azure_vm_cluster/terraform.tfvars.j2', module_name=mn, **_azure_cluster_ctx(d))


def azure_build_root_main(vnets, infras, clusters, iac_tool='terraform'):
    return render_tf('azure_root/main.tf.j2', vnets=vnets, infras=infras, clusters=clusters, iac_tool=iac_tool)


def azure_build_root_vars(vnets, infras, clusters, subscription_id='', resource_group_name='', location='eastus', tags=None):
    return render_tf('azure_root/variables.tf.j2',
        vnets=vnets, infras=infras, clusters=clusters,
        subscription_id=subscription_id,
        resource_group_name=resource_group_name,
        location=location,
        tags=tags or {},
    )


def azure_build_root_tfvars(vnets, infras, clusters, subscription_id='', resource_group_name='', location='eastus', tags=None, iac_tool='terraform'):
    return render_tf('azure_root/terraform.tfvars.j2',
        vnets=vnets, infras=infras, clusters=clusters,
        subscription_id=subscription_id,
        resource_group_name=resource_group_name,
        location=location,
        tags=tags or {},
    )


def generate_azure_tf(data: dict) -> dict:
    raw_vnets    = data.get('azure_vnets', [])
    raw_infras   = data.get('azure_infras', [])
    raw_clusters = data.get('azure_clusters', [])

    first_vnet_name  = raw_vnets[0].get('module_name', 'azure_vnet') if raw_vnets else 'azure_vnet'
    first_infra_name = raw_infras[0].get('module_name', 'azure_exainfra') if raw_infras else 'azure_exainfra'

    vnets    = [_azure_vnet_defaults(n) for n in raw_vnets]
    infras   = [_azure_infra_defaults(i) for i in raw_infras]
    clusters = [_azure_cluster_defaults(c, first_vnet_name, first_infra_name) for c in raw_clusters]

    subscription_id     = data.get('subscription_id', '')
    resource_group_name = data.get('resource_group_name', '')
    location            = data.get('location', 'eastus')
    tags                = data.get('tags', {})
    iac_tool            = data.get('iac_tool', 'terraform')

    files = {
        'main.tf':          azure_build_root_main(vnets, infras, clusters, iac_tool),
        'variables.tf':     azure_build_root_vars(vnets, infras, clusters, subscription_id, resource_group_name, location, tags),
        'terraform.tfvars': azure_build_root_tfvars(vnets, infras, clusters, subscription_id, resource_group_name, location, tags, iac_tool),
    }
    for net in vnets:
        mn = net['module_name']
        files[f'modules/{mn}/main.tf']          = azure_vnet_main(mn, net)
        files[f'modules/{mn}/variables.tf']     = azure_vnet_vars(mn, net)
        files[f'modules/{mn}/outputs.tf']       = azure_vnet_outputs(mn)
        files[f'modules/{mn}/terraform.tfvars'] = azure_vnet_tfvars(mn, net)
    for inf in infras:
        mn = inf['module_name']
        files[f'modules/{mn}/main.tf']          = azure_infra_main(mn, inf)
        files[f'modules/{mn}/variables.tf']     = azure_infra_vars(mn, inf)
        files[f'modules/{mn}/outputs.tf']       = azure_infra_outputs(mn)
        files[f'modules/{mn}/terraform.tfvars'] = azure_infra_tfvars(mn, inf)
    for cl in clusters:
        mn = cl['module_name']
        files[f'modules/{mn}/main.tf']          = azure_cluster_main(mn, cl)
        files[f'modules/{mn}/variables.tf']     = azure_cluster_vars(mn, cl)
        files[f'modules/{mn}/outputs.tf']       = azure_cluster_outputs(mn)
        files[f'modules/{mn}/terraform.tfvars'] = azure_cluster_tfvars(mn, cl)

    return files
