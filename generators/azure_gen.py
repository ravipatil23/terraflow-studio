"""Azure (DB@Azure) generators."""
from core.helpers import render_tf, tf_bool
from oci import generate_oci_dg_tf


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
        'mw_days_of_week':       d.get('mw_days_of_week') or '',
        'mw_hours_of_day':       d.get('mw_hours_of_day') or '',
        'mw_weeks_of_month':     d.get('mw_weeks_of_month') or '',
        'mw_months':             d.get('mw_months') or '',
        'customer_contacts':     d.get('customer_contacts') or [],
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
        'virtual_network_id':    d.get('virtual_network_id') or d.get('vnet_id') or '',
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
        # Never leave this blank: the service assigns 192.168.252.0/22 when it is
        # omitted, and the attribute is ForceNew, so an empty config would make
        # every subsequent plan replace the VM cluster.
        'backup_subnet_cidr':    d.get('backup_subnet_cidr') or '192.168.252.0/22',
        'time_zone':             d.get('time_zone') or 'UTC',
        'db_servers':            d.get('db_servers') or [],
        'scan_listener_port_tcp':     int(d.get('scan_listener_port_tcp') or 1521),
        'scan_listener_port_tcp_ssl': d.get('scan_listener_port_tcp_ssl') or None,
        'system_version':             d.get('system_version') or '',
        'zone_id':                    d.get('zone_id') or '',
        'file_system_configuration':  d.get('file_system_configuration') or (
            [{'mount_point': d.get('fsc_mount_point') or '', 'size_in_gb': int(d['fsc_size_in_gb'])}]
            if d.get('fsc_size_in_gb') else []
        ),
        'dco_diagnostics_events_enabled': bool(d.get('dco_diagnostics_events_enabled', True)),
        'dco_health_monitoring_enabled':  bool(d.get('dco_health_monitoring_enabled', True)),
        'dco_incident_logs_enabled':      bool(d.get('dco_incident_logs_enabled', True)),
        'local_backup_enabled':        bool(d.get('local_backup_enabled', d.get('is_local_backup_enabled', False))),
        'sparse_diskgroup_enabled':    bool(d.get('sparse_diskgroup_enabled', d.get('is_sparse_diskgroup_enabled', False))),
        'data_storage_percentage':     int(d.get('data_storage_percentage') or 80),
        'infra_ref':             d.get('infra_ref') or first_infra_name,
        'vnet_ref':              d.get('vnet_ref') or first_vnet_name,
        'tags':                  d.get('tags') or {},
    }


def _azure_anchor_defaults(d):
    return {
        'module_name':         d.get('module_name') or 'azure_resource_anchor',
        'name':                d.get('name') or '',
        'resource_group_name': d.get('resource_group_name') or '',
        'tags':                d.get('tags') or {},
    }


def _azure_anchor_ctx(d):
    return dict(
        resource_group_name=d['resource_group_name'],
        name=d['name'],
        tags=d['tags'],
    )


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


def _parse_str_list(s):
    return [v.strip() for v in s.split(',') if v.strip()] if s else []


def _azure_infra_ctx(d):
    days   = _parse_str_list(d.get('mw_days_of_week') or '')
    hours  = _parse_str_list(d.get('mw_hours_of_day') or '')
    weeks  = _parse_str_list(d.get('mw_weeks_of_month') or '')
    months = _parse_str_list(d.get('mw_months') or '')
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
        mw_days_of_week=days,
        mw_hours_of_day=[int(x) for x in hours if x.isdigit()],
        mw_weeks_of_month=[int(x) for x in weeks if x.isdigit()],
        mw_months=months,
        tags=d['tags'],
    )


def _fsc_tf(fsc_list):
    if not fsc_list:
        return '[]'
    items = []
    for item in fsc_list:
        mp = f'"{item["mount_point"]}"' if item.get('mount_point') else 'null'
        sg = str(item['size_in_gb']) if item.get('size_in_gb') is not None else 'null'
        items.append('{ mount_point = ' + mp + ', size_in_gb = ' + sg + ' }')
    return '[' + ', '.join(items) + ']'


def _lifecycle_ignore(d):
    """ForceNew attributes whose value can differ from what was submitted.

    Only the three optional arguments that are ForceNew *without* being Computed
    can diff against an empty config; the Computed ones adopt the state value
    when config omits them, so they are safe and stay out of this list.
    Attributes that drift because of operator action (scaling, key rotation) are
    emitted commented-out in the template for the user to enable as needed.
    """
    names = ['backup_subnet_cidr', 'gi_version']
    # Emitted as null when blank, so it would diff against any port the service
    # assigns. An explicit port round-trips and needs no guard.
    if not d.get('scan_listener_port_tcp_ssl'):
        names.append('scan_listener_port_tcp_ssl')
    return names


def _azure_cluster_ctx(d):
    keys = d.get('ssh_public_keys') or []
    ssh_tf = '[' + ', '.join(f'"{k}"' for k in keys) + ']'
    dbs = d.get('db_servers') or []
    db_servers_tf = '[' + ', '.join(f'"{s}"' for s in dbs) + ']'
    return dict(
        resource_group_name=d['resource_group_name'],
        location=d['location'],
        name=d['name'],
        display_name=d['display_name'],
        cloud_exadata_infrastructure_id=d['cloud_exadata_infrastructure_id'],
        subnet_id=d['subnet_id'],
        virtual_network_id=d['virtual_network_id'],
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
        lifecycle_ignore=_lifecycle_ignore(d),
        data_storage_percentage=d['data_storage_percentage'],
        time_zone=d['time_zone'],
        scan_listener_port_tcp=d['scan_listener_port_tcp'],
        scan_listener_port_tcp_ssl=d.get('scan_listener_port_tcp_ssl') or '',
        system_version=d.get('system_version') or '',
        zone_id=d.get('zone_id') or '',
        dco_diagnostics_events_enabled=tf_bool(d['dco_diagnostics_events_enabled']),
        dco_health_monitoring_enabled=tf_bool(d['dco_health_monitoring_enabled']),
        dco_incident_logs_enabled=tf_bool(d['dco_incident_logs_enabled']),
        local_backup_enabled=tf_bool(d['local_backup_enabled']),
        sparse_diskgroup_enabled=tf_bool(d['sparse_diskgroup_enabled']),
        file_system_configuration=d.get('file_system_configuration') or [],
        file_system_configuration_tf=_fsc_tf(d.get('file_system_configuration') or []),
        db_servers_tf=db_servers_tf,
        tags=d['tags'],
    )


def azure_anchor_main(mn, d):
    return render_tf('azure_resource_anchor/main.tf.j2', module_name=mn, **_azure_anchor_ctx(d))


def azure_anchor_vars(mn, d):
    return render_tf('azure_resource_anchor/variables.tf.j2', module_name=mn, **_azure_anchor_ctx(d))


def azure_anchor_outputs(mn):
    return render_tf('azure_resource_anchor/outputs.tf.j2', module_name=mn)


def azure_anchor_tfvars(mn, d):
    return render_tf('azure_resource_anchor/terraform.tfvars.j2', module_name=mn, **_azure_anchor_ctx(d))


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


def azure_build_root_main(vnets, infras, clusters, anchors=None, iac_tool='terraform'):
    return render_tf('azure_root/main.tf.j2', vnets=vnets, infras=infras, clusters=clusters,
                     anchors=anchors or [], iac_tool=iac_tool)


def azure_build_root_vars(vnets, infras, clusters, subscription_id='', resource_group_name='', location='eastus', tags=None, anchors=None):
    return render_tf('azure_root/variables.tf.j2',
        vnets=vnets, infras=infras, clusters=clusters, anchors=anchors or [],
        subscription_id=subscription_id,
        resource_group_name=resource_group_name,
        location=location,
        tags=tags or {},
    )


def azure_build_root_tfvars(vnets, infras, clusters, subscription_id='', resource_group_name='', location='eastus', tags=None, iac_tool='terraform', anchors=None):
    return render_tf('azure_root/terraform.tfvars.j2',
        vnets=vnets, infras=infras, clusters=clusters, anchors=anchors or [],
        subscription_id=subscription_id,
        resource_group_name=resource_group_name,
        location=location,
        tags=tags or {},
    )


def generate_azure_tf(data: dict) -> dict:
    raw_anchors  = data.get('azure_resource_anchors', [])
    raw_vnets    = data.get('azure_vnets', [])
    raw_infras   = data.get('azure_infras', [])
    raw_clusters = data.get('azure_clusters', [])

    first_vnet_name  = raw_vnets[0].get('module_name', 'azure_vnet') if raw_vnets else 'azure_vnet'
    first_infra_name = raw_infras[0].get('module_name', 'azure_exainfra') if raw_infras else 'azure_exainfra'

    anchors  = [_azure_anchor_defaults(a) for a in raw_anchors]
    vnets    = [_azure_vnet_defaults(n) for n in raw_vnets]
    infras   = [_azure_infra_defaults(i) for i in raw_infras]
    clusters = [_azure_cluster_defaults(c, first_vnet_name, first_infra_name) for c in raw_clusters]

    subscription_id     = data.get('subscription_id', '')
    resource_group_name = data.get('resource_group_name', '')
    location            = data.get('location', 'eastus')
    tags                = data.get('tags', {})
    iac_tool            = data.get('iac_tool', 'terraform')

    files = {
        'main.tf':          azure_build_root_main(vnets, infras, clusters, anchors, iac_tool),
        'variables.tf':     azure_build_root_vars(vnets, infras, clusters, subscription_id, resource_group_name, location, tags, anchors),
        'terraform.auto.tfvars': azure_build_root_tfvars(vnets, infras, clusters, subscription_id, resource_group_name, location, tags, iac_tool, anchors),
    }
    for anc in anchors:
        mn = anc['module_name']
        files[f'modules/{mn}/main.tf']      = azure_anchor_main(mn, anc)
        files[f'modules/{mn}/variables.tf'] = azure_anchor_vars(mn, anc)
        files[f'modules/{mn}/outputs.tf']   = azure_anchor_outputs(mn)
    for net in vnets:
        mn = net['module_name']
        files[f'modules/{mn}/main.tf']          = azure_vnet_main(mn, net)
        files[f'modules/{mn}/variables.tf']     = azure_vnet_vars(mn, net)
        files[f'modules/{mn}/outputs.tf']       = azure_vnet_outputs(mn)
    for inf in infras:
        mn = inf['module_name']
        files[f'modules/{mn}/main.tf']          = azure_infra_main(mn, inf)
        files[f'modules/{mn}/variables.tf']     = azure_infra_vars(mn, inf)
        files[f'modules/{mn}/outputs.tf']       = azure_infra_outputs(mn)
    for cl in clusters:
        mn = cl['module_name']
        files[f'modules/{mn}/main.tf']          = azure_cluster_main(mn, cl)
        files[f'modules/{mn}/variables.tf']     = azure_cluster_vars(mn, cl)
        files[f'modules/{mn}/outputs.tf']       = azure_cluster_outputs(mn)

    files.update(generate_oci_dg_tf({
        'dg_multi_az':     data.get('azure_dg_multi_az', []),
        'dg_cross_region': data.get('azure_dg_cross_region', []),
    }))

    return files
