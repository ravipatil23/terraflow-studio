"""AWS (ODB@AWS) and CloudFormation generators."""
import re
from .helpers import render_tf, is_ref, parse_list, tf_bool
from .oci_gen import (
    _avmc_filled, _ocidb_filled, _oci_db_defaults,
    _mn_dbhome, _mn_cdb, _mn_pdb,
    oci_dbhome_main, oci_dbhome_vars, oci_dbhome_outputs, oci_dbhome_tfvars,
    oci_cdb_main, oci_cdb_vars, oci_cdb_outputs, oci_cdb_tfvars,
    oci_pdb_main, oci_pdb_vars, oci_pdb_outputs, oci_pdb_tfvars,
)

_AWS_TO_OCI_REGION = {
    'us-east-1':      'us-ashburn-1',
    'us-east-2':      'us-ashburn-1',
    'us-west-1':      'us-sanjose-1',
    'us-west-2':      'us-portland-1',
    'eu-west-1':      'eu-frankfurt-1',
    'eu-central-1':   'eu-frankfurt-1',
    'ap-southeast-1': 'ap-singapore-1',
    'ap-northeast-1': 'ap-tokyo-1',
}


# ── AWS MODULE 0 — aws_odb_network ────────────────────────────────────────────

def mod0_main(mn, d):
    return render_tf('aws_odb_network/main.tf.j2',
        module_name=mn,
        custom_domain_name=d.get('custom_domain_name', ''),
        default_dns_prefix=d.get('default_dns_prefix', ''),
    )


def _s3_val(v):
    if isinstance(v, str):
        return v if v in ('ENABLED', 'DISABLED') else ('ENABLED' if v else 'DISABLED')
    return 'ENABLED' if v else 'DISABLED'


def mod0_vars(mn, d):
    return render_tf('aws_odb_network/variables.tf.j2',
        module_name=mn,
        display_name=d.get('display_name', ''),
        availability_zone_id=d.get('availability_zone_id', ''),
        client_subnet_cidr=d.get('client_subnet_cidr', ''),
        backup_subnet_cidr=d.get('backup_subnet_cidr', ''),
        s3_access=_s3_val(d.get('s3_access')),
        zero_etl_access=_s3_val(d.get('zero_etl_access')),
        availability_zone=d.get('availability_zone', ''),
        region=d.get('region', ''),
        default_dns_prefix=d.get('default_dns_prefix', ''),
        custom_domain_name=d.get('custom_domain_name', ''),
        delete_associated_resources=tf_bool(d.get('delete_associated_resources', False)),
        tags=d.get('tags', {}),
    )


def mod0_outputs(mn):
    return render_tf('aws_odb_network/outputs.tf.j2', module_name=mn)


def mod0_tfvars(mn, d):
    return render_tf('aws_odb_network/terraform.tfvars.j2',
        module_name=mn,
        display_name=d.get('display_name', '') or 'odb-my-net',
        availability_zone_id=d.get('availability_zone_id', '') or 'use1-az6',
        client_subnet_cidr=d.get('client_subnet_cidr', '') or '10.2.0.0/24',
        backup_subnet_cidr=d.get('backup_subnet_cidr', '') or '10.2.1.0/24',
        s3_access=_s3_val(d.get('s3_access')),
        zero_etl_access=_s3_val(d.get('zero_etl_access')),
        availability_zone=d.get('availability_zone', ''),
        region=d.get('region', ''),
        default_dns_prefix=d.get('default_dns_prefix', ''),
        custom_domain_name=d.get('custom_domain_name', ''),
        delete_associated_resources=tf_bool(d.get('delete_associated_resources', False)),
        tags=d.get('tags', {}),
    )


# ── AWS MODULE 1 — aws_odb_cloud_exadata_infrastructure ──────────────────────

def _mod1_ctx(d, defaults=False):
    raw_hours  = parse_list(d.get('mw_hours_of_day', ''))
    raw_weeks  = parse_list(d.get('mw_weeks_of_month', ''))
    hours_ints = [int(x) for x in raw_hours  if x.strip().lstrip('-').isdigit()]
    weeks_ints = [int(x) for x in raw_weeks  if x.strip().lstrip('-').isdigit()]
    days  = parse_list(d.get('mw_days_of_week', ''))
    months = parse_list(d.get('mw_months', ''))
    return dict(
        display_name=d.get('display_name', '') or ('exadb-inf-demo' if defaults else ''),
        shape=d.get('shape', 'Exadata.X11M') or 'Exadata.X11M',
        compute_count=int(d.get('compute_count', 2) or 2),
        storage_count=int(d.get('storage_count', 3) or 3),
        availability_zone_id=d.get('availability_zone_id', '') or ('usw2-az3' if defaults else ''),
        availability_zone=d.get('availability_zone', ''),
        region=d.get('region', ''),
        database_server_type=d.get('database_server_type', ''),
        storage_server_type=d.get('storage_server_type', ''),
        customer_contacts=d.get('customer_contacts', []),
        mw_preference=d.get('mw_preference', 'NO_PREFERENCE'),
        mw_patching_mode=d.get('mw_patching_mode', 'ROLLING'),
        mw_is_custom_action_timeout_enabled=tf_bool(d.get('mw_is_custom_action_timeout_enabled', False)),
        mw_custom_action_timeout_in_mins=int(d.get('mw_custom_action_timeout_in_mins', 15) or 15),
        is_custom_mw=(d.get('mw_preference', '') == 'CUSTOM_PREFERENCE'),
        mw_lead_time_in_weeks=d.get('mw_lead_time_in_weeks', ''),
        mw_hours_of_day=hours_ints,
        mw_weeks_of_month=weeks_ints,
        mw_days_of_week=days,
        mw_months=months,
        tags=d.get('tags', {}),
    )


def mod1_main(mn):
    return render_tf('aws_exadata_infra/main.tf.j2', module_name=mn)


def mod1_vars(mn, d):
    return render_tf('aws_exadata_infra/variables.tf.j2', module_name=mn, **_mod1_ctx(d))


def mod1_outputs(mn):
    return render_tf('aws_exadata_infra/outputs.tf.j2', module_name=mn)


def mod1_tfvars(mn, d):
    return render_tf('aws_exadata_infra/terraform.tfvars.j2', module_name=mn, **_mod1_ctx(d, defaults=True))


# ── AWS MODULE 2 — aws_odb_network_peering_connection ────────────────────────

def _mod2_ctx(d, mn0, defaults=False):
    odb  = d.get('odb_network_id', '') or (f'module.{mn0}.network_id' if mn0 else '')
    peer = d.get('peer_network_id', '')
    return dict(
        display_name=d.get('display_name', '') or ('odb-peering-conn' if defaults else ''),
        odb_network_id=odb,
        odb_network_id_is_ref=is_ref(odb),
        peer_network_id=peer,
        peer_network_id_is_ref=is_ref(peer),
        mn0=mn0,
        region=d.get('region', ''),
        cidrs=d.get('peer_network_cidrs', []),
        tags=d.get('tags', {}),
    )


def mod2_main(mn):
    return render_tf('aws_peering/main.tf.j2', module_name=mn)


def mod2_vars(mn, d, mn0):
    return render_tf('aws_peering/variables.tf.j2', module_name=mn, **_mod2_ctx(d, mn0))


def mod2_outputs(mn):
    return render_tf('aws_peering/outputs.tf.j2', module_name=mn)


def mod2_tfvars(mn, d, mn0):
    return render_tf('aws_peering/terraform.tfvars.j2', module_name=mn, **_mod2_ctx(d, mn0, defaults=True))


# ── AWS MODULE 3 — aws_odb_cloud_vm_cluster ───────────────────────────────────

def _mod3_ctx(d, mn0='', mn1='', defaults=False):
    infraid = d.get('cloud_exadata_infrastructure_id', '')
    netid   = d.get('odb_network_id', '')
    ds      = d.get('data_storage_size_in_tbs', '')  or 'null'
    dng     = d.get('db_node_storage_size_in_gbs', '') or 'null'
    mem     = d.get('memory_size_in_gbs', '')          or 'null'
    sc      = d.get('scan_listener_port_tcp', '')      or 'null'
    sc_ssl  = d.get('scan_listener_port_tcp_ssl', '') or 'null'
    infraid = infraid or (f'module.{mn1}.infra_id' if mn1 else '')
    netid   = netid   or (f'module.{mn0}.network_id' if mn0 else '')
    infra_val = infraid if not is_ref(infraid) else infraid
    net_val   = netid   if not is_ref(netid)   else netid
    return dict(
        display_name=d.get('display_name', '') or ('tf-vmc-demo' if defaults else ''),
        cpu_core_count=int(d.get('cpu_core_count', 16) or 16),
        gi_version=d.get('gi_version', ''),
        hostname_prefix=d.get('hostname_prefix', ''),
        license_model=d.get('license_model', 'LICENSE_INCLUDED'),
        cloud_exadata_infrastructure_id=infraid,
        odb_network_id=netid,
        infra_id=infra_val,
        net_id=net_val,
        mn0=mn0, mn1=mn1,
        ssh_public_keys=d.get('ssh_public_keys', []),
        db_servers=d.get('db_servers', []),
        db_servers_mode=d.get('db_servers_mode', 'auto'),
        dco_is_diagnostics_events_enabled=tf_bool(d.get('dco_is_diagnostics_events_enabled', True)),
        dco_is_health_monitoring_enabled=tf_bool(d.get('dco_is_health_monitoring_enabled', True)),
        dco_is_incident_logs_enabled=tf_bool(d.get('dco_is_incident_logs_enabled', True)),
        cluster_name=d.get('cluster_name', ''),
        timezone=d.get('timezone', ''),
        data_storage_size_in_tbs=ds,
        db_node_storage_size_in_gbs=dng,
        memory_size_in_gbs=mem,
        scan_listener_port_tcp=sc,
        scan_listener_port_tcp_ssl=sc_ssl,
        is_local_backup_enabled=tf_bool(d.get('is_local_backup_enabled', False)),
        is_sparse_diskgroup_enabled=tf_bool(d.get('is_sparse_diskgroup_enabled', False)),
        tags=d.get('tags', {}),
    )


def mod3_main(mn, d=None, mn0='', mn1=''):
    ctx = _mod3_ctx(d, mn0, mn1) if d else {'db_servers_mode': 'auto', 'db_servers': [], 'vm_mode': 'arn'}
    return render_tf('aws_vm_cluster/main.tf.j2', module_name=mn, **ctx)


def mod3_vars(mn, d, mn0='', mn1=''):
    return render_tf('aws_vm_cluster/variables.tf.j2', module_name=mn, **_mod3_ctx(d, mn0, mn1))


def mod3_outputs(mn):
    return render_tf('aws_vm_cluster/outputs.tf.j2', module_name=mn)


def mod3_tfvars(mn, d, mn0, mn1):
    return render_tf('aws_vm_cluster/terraform.tfvars.j2', module_name=mn, **_mod3_ctx(d, mn0, mn1, defaults=True))


# ── AWS MODULE 4 — aws_odb_cloud_autonomous_vm_cluster ───────────────────────

def _mod4_ctx(d, mn0='', mn1='', defaults=False):
    infra_arn = d.get('cloud_exadata_infrastructure_arn', '') or (f'module.{mn1}.infra_arn' if mn1 else '')
    net_arn   = d.get('odb_network_arn', '') or (f'module.{mn0}.network_arn' if mn0 else '')
    infra_id  = d.get('cloud_exadata_infrastructure_id', '') or (f'module.{mn1}.infra_id' if mn1 else '')
    net_id    = d.get('odb_network_id', '') or (f'module.{mn0}.network_id' if mn0 else '')
    has_sched = any([d.get('mw_days_of_week'), d.get('mw_hours_of_day'),
                     d.get('mw_months'), d.get('mw_weeks_of_month'), d.get('mw_lead_time_week')])
    return dict(
        display_name=d.get('display_name', '') or ('tf-avmc-demo' if defaults else ''),
        autonomous_data_storage_size_in_tbs=float(d.get('autonomous_data_storage_size_in_tbs', 5) or 5),
        cpu_core_count_per_node=int(d.get('cpu_core_count_per_node', 40) or 40),
        memory_per_oracle_compute_unit_in_gbs=int(d.get('memory_per_oracle_compute_unit_in_gbs', 2) or 2),
        total_container_databases=int(d.get('total_container_databases', 2) or 2),
        scan_listener_port_non_tls=int(d.get('scan_listener_port_non_tls', 1521) or 1521),
        scan_listener_port_tls=int(d.get('scan_listener_port_tls', 2484) or 2484),
        license_model=d.get('license_model', 'LICENSE_INCLUDED'),
        is_mtls_enabled_vm_cluster=tf_bool(d.get('is_mtls_enabled_vm_cluster', False)),
        description=d.get('description', ''),
        time_zone=d.get('time_zone', ''),
        cloud_exadata_infrastructure_id=infra_id,
        odb_network_id=net_id,
        cloud_exadata_infrastructure_arn=infra_arn,
        odb_network_arn=net_arn,
        db_servers=d.get('db_servers', []),
        db_servers_mode=d.get('db_servers_mode', 'auto'),
        mw_preference=d.get('mw_preference', 'NO_PREFERENCE'),
        mw_patching_mode=d.get('mw_patching_mode', 'ROLLING'),
        mw_is_custom_action_timeout_enabled=tf_bool(d.get('mw_is_custom_action_timeout_enabled', False)),
        mw_custom_action_timeout_mins=int(d.get('mw_custom_action_timeout_mins', 15) or 15),
        maintenance_window_has_schedule=has_sched,
        mn0=mn0, mn1=mn1,
        tags=d.get('tags', {}),
    )


def mod4_main(mn, d=None, mn0='', mn1=''):
    ctx = _mod4_ctx(d, mn0, mn1) if d else {'db_servers_mode': 'auto', 'db_servers': [], 'vm_mode': 'arn'}
    return render_tf('aws_avmcluster/main.tf.j2', module_name=mn, **ctx)


def mod4_vars(mn, d, mn0='', mn1=''):
    return render_tf('aws_avmcluster/variables.tf.j2', module_name=mn, **_mod4_ctx(d, mn0, mn1))


def mod4_outputs(mn):
    return render_tf('aws_avmcluster/outputs.tf.j2', module_name=mn)


def mod4_tfvars(mn, d, mn0, mn1):
    return render_tf('aws_avmcluster/terraform.tfvars.j2', module_name=mn, **_mod4_ctx(d, mn0, mn1, defaults=True))


# ── AWS ROOT ──────────────────────────────────────────────────────────────────

def build_root_main(networks, infras, peerings, clusters, avmclusters=None, oci_databases=None, iac_tool='terraform'):
    aws_region = 'us-east-1'
    for n in (networks or []):
        if n.get('region'): aws_region = n['region']; break
    oci_region = _AWS_TO_OCI_REGION.get(aws_region, 'us-ashburn-1')
    return render_tf('aws_root/main.tf.j2',
        networks=networks, infras=infras, peerings=peerings,
        clusters=clusters, avmclusters=avmclusters or [],
        oci_databases=oci_databases or [],
        oci_region=oci_region,
        iac_tool=iac_tool)


def build_root_vars(networks, infras, peerings, clusters, avmclusters=None, oci_databases=None):
    aws_region = 'us-east-1'
    for n in (networks or []):
        if n.get('region'): aws_region = n['region']; break
    oci_region = _AWS_TO_OCI_REGION.get(aws_region, 'us-ashburn-1')
    return render_tf('aws_root/variables.tf.j2',
        aws_region=aws_region, oci_region=oci_region,
        oci_databases=oci_databases or [])


def build_root_tfvars(networks, infras, peerings, clusters, avmclusters=None, iac_tool='terraform'):
    avmclusters = avmclusters or []
    all_tags = {}
    for items in [networks, infras, peerings, clusters, avmclusters]:
        for item in items:
            all_tags.update(item.get('tags', {}))
    region = 'us-east-1'
    for items in [networks, infras]:
        for item in items:
            if item.get('region'): region = item['region']; break
    return render_tf('aws_root/terraform.tfvars.j2',
        aws_region=region,
        networks=networks, infras=infras, peerings=peerings,
        clusters=clusters, avmclusters=avmclusters,
        tags=all_tags if all_tags else {'ManagedBy': 'Terraform'},
    )


# ── Default normalizers ───────────────────────────────────────────────────────

def _aws_net_defaults(d):
    cdn = d.get('custom_domain_name', '')
    return {**d,
        'display_name': d.get('display_name') or 'odb-network',
        'availability_zone_id': d.get('availability_zone_id') or 'use1-az6',
        'client_subnet_cidr': d.get('client_subnet_cidr') or '10.2.0.0/24',
        'backup_subnet_cidr': d.get('backup_subnet_cidr') or '10.2.1.0/24',
        's3_access': 'ENABLED' if d.get('s3_access') else 'DISABLED',
        'zero_etl_access': 'ENABLED' if d.get('zero_etl_access') else 'DISABLED',
        'region': d.get('region', ''),
        'custom_domain_name': cdn,
        'default_dns_prefix': '' if cdn else d.get('default_dns_prefix', ''),
    }


def _aws_infra_defaults(d):
    return {**d,
        'display_name': d.get('display_name') or 'odb-exadata-infra',
        'shape': d.get('shape') or 'Exadata.X11M',
        'compute_count': int(d.get('compute_count') or 2),
        'storage_count': int(d.get('storage_count') or 3),
        'availability_zone_id': d.get('availability_zone_id') or 'use1-az6',
    }


def _aws_peer_defaults(d, first_network_name=''):
    return {**d,
        'display_name': d.get('display_name') or 'odb-peering',
        'peer_network_id': d.get('peer_network_id') or 'vpc-CHANGEME',
        'network_ref': d.get('network_ref') or first_network_name,
    }


def _aws_cluster_defaults(d, first_network_name='', first_infra_name=''):
    return {**d,
        'display_name': d.get('display_name') or 'odb-vm-cluster',
        'cpu_core_count': int(d.get('cpu_core_count') or 16),
        'gi_version': d.get('gi_version') or '23.0.0.0',
        'hostname_prefix': d.get('hostname_prefix') or 'vm',
        'license_model': d.get('license_model') or 'LICENSE_INCLUDED',
        'ssh_public_keys': d.get('ssh_public_keys') or [],
        'db_servers': d.get('db_servers') or [],
        'db_servers_mode': d.get('db_servers_mode') or 'auto',
        'vm_mode': d.get('vm_mode') or 'arn',
        'network_ref': d.get('network_ref') or first_network_name,
        'infra_ref': d.get('infra_ref') or first_infra_name,
    }


def _aws_avmc_defaults(d, first_network_name='', first_infra_name=''):
    return {**d,
        'display_name': d.get('display_name') or 'odb-avmc',
        'autonomous_data_storage_size_in_tbs': float(d.get('autonomous_data_storage_size_in_tbs') or 5),
        'cpu_core_count_per_node': int(d.get('cpu_core_count_per_node') or 40),
        'memory_per_oracle_compute_unit_in_gbs': int(d.get('memory_per_oracle_compute_unit_in_gbs') or 2),
        'total_container_databases': int(d.get('total_container_databases') or 2),
        'scan_listener_port_non_tls': int(d.get('scan_listener_port_non_tls') or 1521),
        'scan_listener_port_tls': int(d.get('scan_listener_port_tls') or 2484),
        'license_model': d.get('license_model') or 'LICENSE_INCLUDED',
        'is_mtls_enabled_vm_cluster': bool(d.get('is_mtls_enabled_vm_cluster', False)),
        'db_servers': d.get('db_servers') or [],
        'db_servers_mode': d.get('db_servers_mode') or 'auto',
        'network_ref': d.get('network_ref') or first_network_name,
        'infra_ref': d.get('infra_ref') or first_infra_name,
        'description': d.get('description') or '',
        'time_zone': d.get('time_zone') or '',
        'mw_preference': d.get('mw_preference') or 'NO_PREFERENCE',
        'mw_patching_mode': d.get('mw_patching_mode') or 'ROLLING',
        'mw_is_custom_action_timeout_enabled': bool(d.get('mw_is_custom_action_timeout_enabled', False)),
        'mw_custom_action_timeout_mins': int(d.get('mw_custom_action_timeout_mins') or 15),
    }


# ── CloudFormation generator ──────────────────────────────────────────────────

def _pascal(s: str) -> str:
    return ''.join(p.capitalize() for p in re.split(r'[_\-\s]+', s) if p)


def _cfn_str(v) -> str:
    s = str(v)
    if any(c in s for c in ':{}[]|>&*!,#?@`"\'\n') or s in ('true', 'false', 'null', '~') or s == '':
        return "'" + s.replace("'", "''") + "'"
    return s


def generate_cfn(data: dict) -> str:
    raw_nets     = data.get('aws_networks', [])
    raw_infras   = data.get('aws_infras', [])
    raw_peerings = data.get('aws_peerings', [])
    raw_clusters = data.get('aws_clusters', [])
    raw_avmc     = data.get('aws_avmclusters', [])

    if not raw_nets:
        mn0 = data.get('module_names', {}).get('0', 'odb_network')
        raw_nets = [{**data.get('module_0', {}), 'module_name': mn0}]
    if not raw_infras:
        mn1 = data.get('module_names', {}).get('1', 'odb_exadata_infra')
        raw_infras = [{**data.get('module_1', {}), 'module_name': mn1}]
    if not raw_peerings:
        mn2 = data.get('module_names', {}).get('2', 'odb_peering')
        raw_peerings = [{**data.get('module_2', {}), 'module_name': mn2}]
    if not raw_clusters:
        mn3 = data.get('module_names', {}).get('3', 'odb_vm_cluster')
        raw_clusters = [{**data.get('module_3', {}), 'module_name': mn3}]

    first_net_name = raw_nets[0].get('module_name', 'odb_network') if raw_nets else 'odb_network'
    first_inf_name = raw_infras[0].get('module_name', 'odb_exadata_infra') if raw_infras else 'odb_exadata_infra'

    networks    = [_aws_net_defaults(n) for n in raw_nets]
    infras      = [_aws_infra_defaults(i) for i in raw_infras]
    peerings    = [_aws_peer_defaults(p, first_net_name) for p in raw_peerings]
    clusters    = [_aws_cluster_defaults(c, first_net_name, first_inf_name) for c in raw_clusters]
    avmclusters = [_aws_avmc_defaults(a, first_net_name, first_inf_name) for a in raw_avmc if _avmc_filled(a)]

    L = []
    out = []

    def line(s=''):
        L.append(s)

    line("AWSTemplateFormatVersion: '2010-09-09'")
    line("Description: 'ODB@AWS stack generated by Terraflow Studio'")
    line()
    line("Resources:")

    for net in networks:
        lid = _pascal(net['module_name'])
        line()
        line(f"  # ODB Network: {net['module_name']}")
        line(f"  {lid}:")
        line(f"    Type: AWS::ODB::OdbNetwork")
        line(f"    Properties:")
        line(f"      DisplayName: {_cfn_str(net['display_name'])}")
        if net.get('availability_zone_id'):
            line(f"      AvailabilityZoneId: {_cfn_str(net['availability_zone_id'])}")
        line(f"      ClientSubnetCidr: {_cfn_str(net['client_subnet_cidr'])}")
        line(f"      BackupSubnetCidr: {_cfn_str(net['backup_subnet_cidr'])}")
        line(f"      S3Access: {net['s3_access']}")
        line(f"      ZeroEtlAccess: {net['zero_etl_access']}")
        if net.get('default_dns_prefix'):
            line(f"      DefaultDnsPrefix: {_cfn_str(net['default_dns_prefix'])}")
        if net.get('custom_domain_name'):
            line(f"      CustomDomainName: {_cfn_str(net['custom_domain_name'])}")
        line(f"      DeleteAssociatedResources: true")
        out.append((f"{lid}OdbNetworkId", lid, "OdbNetworkId"))

    for inf in infras:
        lid = _pascal(inf['module_name'])
        line()
        line(f"  # Exadata Infrastructure: {inf['module_name']}")
        line(f"  {lid}:")
        line(f"    Type: AWS::ODB::CloudExadataInfrastructure")
        line(f"    Properties:")
        line(f"      DisplayName: {_cfn_str(inf['display_name'])}")
        if inf.get('availability_zone_id'):
            line(f"      AvailabilityZoneId: {_cfn_str(inf['availability_zone_id'])}")
        line(f"      Shape: {_cfn_str(inf['shape'])}")
        line(f"      ComputeCount: {inf['compute_count']}")
        line(f"      StorageCount: {inf['storage_count']}")
        out.append((f"{lid}InfraId", lid, "CloudExadataInfrastructureId"))

    for peer in peerings:
        lid     = _pascal(peer['module_name'])
        net_lid = _pascal(peer.get('network_ref', first_net_name))
        line()
        line(f"  # ODB Peering Connection: {peer['module_name']}")
        line(f"  {lid}:")
        line(f"    Type: AWS::ODB::OdbPeeringConnection")
        line(f"    DependsOn: {net_lid}")
        line(f"    Properties:")
        line(f"      DisplayName: {_cfn_str(peer['display_name'])}")
        line(f"      OdbNetworkId: !GetAtt {net_lid}.OdbNetworkId")
        line(f"      PeerNetworkId: {_cfn_str(peer['peer_network_id'])}")
        out.append((f"{lid}PeeringId", lid, "OdbPeeringConnectionId"))

    for cl in clusters:
        lid     = _pascal(cl['module_name'])
        net_lid = _pascal(cl.get('network_ref', first_net_name))
        inf_lid = _pascal(cl.get('infra_ref', first_inf_name))
        line()
        line(f"  # VM Cluster: {cl['module_name']}")
        line(f"  {lid}:")
        line(f"    Type: AWS::ODB::CloudVmCluster")
        line(f"    DependsOn:")
        line(f"      - {net_lid}")
        line(f"      - {inf_lid}")
        line(f"    Properties:")
        line(f"      DisplayName: {_cfn_str(cl['display_name'])}")
        line(f"      OdbNetworkId: !GetAtt {net_lid}.OdbNetworkId")
        line(f"      CloudExadataInfrastructureId: !GetAtt {inf_lid}.CloudExadataInfrastructureId")
        if cl.get('hostname_prefix'):
            line(f"      Hostname: {_cfn_str(cl['hostname_prefix'])}")
        line(f"      GiVersion: {_cfn_str(cl.get('gi_version', '23.0.0.0'))}")
        line(f"      CpuCoreCount: {cl['cpu_core_count']}")
        mem = cl.get('memory_size_in_gbs') or ''
        if mem and str(mem) not in ('null', '0', ''):
            line(f"      MemorySizeInGBs: {mem}")
        ds = cl.get('data_storage_size_in_tbs') or ''
        if ds and str(ds) not in ('null', '0', ''):
            line(f"      DataStorageSizeInTBs: {ds}")
        dng = cl.get('db_node_storage_size_in_gbs') or ''
        if dng and str(dng) not in ('null', '0', ''):
            line(f"      DbNodeStorageSizeInGBs: {dng}")
        line(f"      LicenseModel: {cl['license_model']}")
        keys = cl.get('ssh_public_keys') or []
        if keys:
            line(f"      SshPublicKeys:")
            for k in keys:
                line(f"        - {_cfn_str(k)}")
        db_servers = cl.get('db_servers') or []
        if db_servers and cl.get('db_servers_mode') != 'auto':
            line(f"      DbServers:")
            for s in db_servers:
                line(f"        - {_cfn_str(s)}")
        out.append((f"{lid}VmClusterId", lid, "CloudVmClusterId"))

    for av in avmclusters:
        lid     = _pascal(av['module_name'])
        net_lid = _pascal(av.get('network_ref', first_net_name))
        inf_lid = _pascal(av.get('infra_ref', first_inf_name))
        line()
        line(f"  # Autonomous VM Cluster: {av['module_name']}")
        line(f"  {lid}:")
        line(f"    Type: AWS::ODB::CloudAutonomousVmCluster")
        line(f"    DependsOn:")
        line(f"      - {net_lid}")
        line(f"      - {inf_lid}")
        line(f"    Properties:")
        line(f"      DisplayName: {_cfn_str(av['display_name'])}")
        line(f"      OdbNetworkId: !GetAtt {net_lid}.OdbNetworkId")
        line(f"      CloudExadataInfrastructureId: !GetAtt {inf_lid}.CloudExadataInfrastructureId")
        line(f"      AutonomousDataStorageSizeInTBs: {av['autonomous_data_storage_size_in_tbs']}")
        line(f"      CpuCoreCountPerNode: {av['cpu_core_count_per_node']}")
        line(f"      MemoryPerOracleComputeUnitInGBs: {av['memory_per_oracle_compute_unit_in_gbs']}")
        line(f"      TotalContainerDatabases: {av['total_container_databases']}")
        line(f"      LicenseModel: {av['license_model']}")
        line(f"      IsMtlsEnabledVmCluster: {'true' if av['is_mtls_enabled_vm_cluster'] else 'false'}")
        if av.get('time_zone'):
            line(f"      TimeZone: {_cfn_str(av['time_zone'])}")
        if av.get('description'):
            line(f"      Description: {_cfn_str(av['description'])}")
        out.append((f"{lid}AvmClusterId", lid, "CloudAutonomousVmClusterId"))

    if out:
        line()
        line("Outputs:")
        for (out_key, lid, attr) in out:
            line()
            line(f"  {out_key}:")
            line(f"    Value: !GetAtt {lid}.{attr}")
            line(f"    Export:")
            line(f"      Name: !Sub '${{AWS::StackName}}-{out_key}'")

    return '\n'.join(L) + '\n'


# ── AWS Terraform generator ───────────────────────────────────────────────────

def generate_aws_tf(data: dict) -> dict:
    raw_nets     = data.get('aws_networks', [])
    raw_infras   = data.get('aws_infras', [])
    raw_peerings = data.get('aws_peerings', [])
    raw_clusters = data.get('aws_clusters', [])
    raw_avmc     = data.get('aws_avmclusters', [])

    if not raw_nets:
        d0 = data.get('module_0', {})
        mn0 = data.get('module_names', {}).get('0', 'odb_network')
        raw_nets = [{**d0, 'module_name': mn0}]
    if not raw_infras:
        d1 = data.get('module_1', {})
        mn1 = data.get('module_names', {}).get('1', 'odb_exadata_infra')
        raw_infras = [{**d1, 'module_name': mn1}]
    if not raw_peerings:
        d2 = data.get('module_2', {})
        mn2 = data.get('module_names', {}).get('2', 'odb_peering')
        raw_peerings = [{**d2, 'module_name': mn2}]
    if not raw_clusters:
        d3 = data.get('module_3', {})
        mn3 = data.get('module_names', {}).get('3', 'odb_vm_cluster')
        raw_clusters = [{**d3, 'module_name': mn3}]

    first_net_name  = raw_nets[0].get('module_name', 'odb_network')
    first_inf_name  = raw_infras[0].get('module_name', 'odb_exadata_infra')
    networks    = [_aws_net_defaults(n) for n in raw_nets]
    infras      = [_aws_infra_defaults(i) for i in raw_infras]
    peerings    = [_aws_peer_defaults(p, first_net_name) for p in raw_peerings]
    clusters    = [_aws_cluster_defaults(c, first_net_name, first_inf_name) for c in raw_clusters]
    avmclusters = [_aws_avmc_defaults(a, first_net_name, first_inf_name) for a in raw_avmc if _avmc_filled(a)]

    raw_oci_dbs   = [db for db in data.get('aws_oci_databases', []) if _ocidb_filled(db)]
    first_cl_name = clusters[0]['module_name'] if clusters else (avmclusters[0]['module_name'] if avmclusters else '')
    oci_dbs = [_oci_db_defaults(db, first_cl_name) for db in raw_oci_dbs]

    iac_tool = data.get('iac_tool', 'terraform')

    files = {
        'main.tf':          build_root_main(networks, infras, peerings, clusters, avmclusters, oci_dbs, iac_tool),
        'variables.tf':     build_root_vars(networks, infras, peerings, clusters, avmclusters, oci_dbs),
        'terraform.tfvars': build_root_tfvars(networks, infras, peerings, clusters, avmclusters),
    }
    for net in networks:
        mn = net['module_name']
        files[f'modules/{mn}/main.tf']          = mod0_main(mn, net)
        files[f'modules/{mn}/variables.tf']     = mod0_vars(mn, net)
        files[f'modules/{mn}/outputs.tf']       = mod0_outputs(mn)
        files[f'modules/{mn}/terraform.tfvars'] = mod0_tfvars(mn, net)
    for inf in infras:
        mn = inf['module_name']
        files[f'modules/{mn}/main.tf']          = mod1_main(mn)
        files[f'modules/{mn}/variables.tf']     = mod1_vars(mn, inf)
        files[f'modules/{mn}/outputs.tf']       = mod1_outputs(mn)
        files[f'modules/{mn}/terraform.tfvars'] = mod1_tfvars(mn, inf)
    for peer in peerings:
        mn  = peer['module_name']
        mn0 = peer.get('network_ref', first_net_name)
        files[f'modules/{mn}/main.tf']          = mod2_main(mn)
        files[f'modules/{mn}/variables.tf']     = mod2_vars(mn, peer, mn0)
        files[f'modules/{mn}/outputs.tf']       = mod2_outputs(mn)
        files[f'modules/{mn}/terraform.tfvars'] = mod2_tfvars(mn, peer, mn0)
    for cl in clusters:
        mn  = cl['module_name']
        mn0 = cl.get('network_ref', first_net_name)
        mn1 = cl.get('infra_ref', first_inf_name)
        files[f'modules/{mn}/main.tf']          = mod3_main(mn, cl, mn0, mn1)
        files[f'modules/{mn}/variables.tf']     = mod3_vars(mn, cl, mn0, mn1)
        files[f'modules/{mn}/outputs.tf']       = mod3_outputs(mn)
        files[f'modules/{mn}/terraform.tfvars'] = mod3_tfvars(mn, cl, mn0, mn1)
    for av in avmclusters:
        mn  = av['module_name']
        mn0 = av.get('network_ref', first_net_name)
        mn1 = av.get('infra_ref', first_inf_name)
        files[f'modules/{mn}/main.tf']          = mod4_main(mn, av, mn0, mn1)
        files[f'modules/{mn}/variables.tf']     = mod4_vars(mn, av, mn0, mn1)
        files[f'modules/{mn}/outputs.tf']       = mod4_outputs(mn)
        files[f'modules/{mn}/terraform.tfvars'] = mod4_tfvars(mn, av, mn0, mn1)
    for db in oci_dbs:
        base = db['module_name']
        vcr  = db.get('vmcluster_ref', first_cl_name)
        mn_h = _mn_dbhome(base); mn_c = _mn_cdb(base); mn_p = _mn_pdb(base)
        files[f'modules/{mn_h}/main.tf']          = oci_dbhome_main(mn_h, db, vcr)
        files[f'modules/{mn_h}/variables.tf']     = oci_dbhome_vars(mn_h, db, vcr)
        files[f'modules/{mn_h}/outputs.tf']       = oci_dbhome_outputs(mn_h)
        files[f'modules/{mn_h}/terraform.tfvars'] = oci_dbhome_tfvars(mn_h, db, vcr)
        files[f'modules/{mn_c}/main.tf']          = oci_cdb_main(mn_c, db, mn_h)
        files[f'modules/{mn_c}/variables.tf']     = oci_cdb_vars(mn_c, db, mn_h)
        files[f'modules/{mn_c}/outputs.tf']       = oci_cdb_outputs(mn_c)
        files[f'modules/{mn_c}/terraform.tfvars'] = oci_cdb_tfvars(mn_c, db, mn_h)
        if db.get('create_pdb') and db.get('pdb_name'):
            files[f'modules/{mn_p}/main.tf']          = oci_pdb_main(mn_p, db, mn_c)
            files[f'modules/{mn_p}/variables.tf']     = oci_pdb_vars(mn_p, db, mn_c)
            files[f'modules/{mn_p}/outputs.tf']       = oci_pdb_outputs(mn_p)
            files[f'modules/{mn_p}/terraform.tfvars'] = oci_pdb_tfvars(mn_p, db, mn_c)
    return files
