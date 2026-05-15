"""GCP (DB@GCP) generators."""
from .helpers import render_tf, is_ref, parse_list, tf_bool
from .oci_gen import (
    _ocidb_filled, _oci_db_defaults,
    _mn_dbhome, _mn_cdb, _mn_pdb,
    oci_dbhome_main, oci_dbhome_vars, oci_dbhome_outputs, oci_dbhome_tfvars,
    oci_cdb_main, oci_cdb_vars, oci_cdb_outputs, oci_cdb_tfvars,
    oci_pdb_main, oci_pdb_vars, oci_pdb_outputs, oci_pdb_tfvars,
)

_GCP_TO_OCI_REGION = {
    'us-east4':                'us-ashburn-1',
    'us-central1':             'us-desmoines-1',
    'us-west3':                'us-saltlake-2',
    'northamerica-northeast1': 'ca-montreal-1',
    'northamerica-northeast2': 'ca-toronto-1',
    'europe-west3':            'eu-frankfurt-1',
    'europe-west2':            'uk-london-1',
    'europe-west8':            'eu-milan-1',
    'asia-south2':             'ap-delhi-1',
    'australia-southeast2':    'ap-melbourne-1',
    'asia-south1':             'ap-mumbai-1',
    'asia-northeast2':         'ap-osaka-1',
    'australia-southeast1':    'ap-sydney-1',
    'asia-northeast1':         'ap-tokyo-1',
    'southamerica-east1':      'sa-saopaulo-1',
}


# ── GCP MODULE 0 — google_oracle_database_odb_network ────────────────────────

def gcp0_main(mn):
    return render_tf('gcp_odb_network/main.tf.j2', module_name=mn)


def gcp0_vars(mn, d):
    return render_tf('gcp_odb_network/variables.tf.j2',
        module_name=mn,
        odb_network_id=d.get('odb_network_id', ''),
        location=d.get('location', ''),
        network=d.get('network', ''),
        project=d.get('project', ''),
        gcp_oracle_zone=d.get('gcp_oracle_zone', ''),
        deletion_protection=tf_bool(d.get('deletion_protection', True)),
        labels=d.get('labels', {}),
    )


def gcp0_outputs(mn):
    return render_tf('gcp_odb_network/outputs.tf.j2', module_name=mn)


def gcp0_tfvars(mn, d):
    return render_tf('gcp_odb_network/terraform.tfvars.j2',
        module_name=mn,
        odb_network_id=d.get('odb_network_id', '') or 'my-odb-network',
        location=d.get('location', '') or 'us-east4',
        network=d.get('network', '') or 'projects/my-project/global/networks/default',
        project=d.get('project', ''),
        gcp_oracle_zone=d.get('gcp_oracle_zone', ''),
        deletion_protection=tf_bool(d.get('deletion_protection', True)),
        labels=d.get('labels', {}),
    )


# ── GCP MODULE — google_oracle_database_odb_subnet ───────────────────────────

def _gcp_subnet_ctx(d, mn0='', defaults=False):
    odb_net = d.get('odb_network', '')
    return dict(
        odb_subnet_id=d.get('odb_subnet_id', '') or ('my-odb-subnet' if defaults else ''),
        location=d.get('location', '') or ('us-east4' if defaults else ''),
        odb_network=odb_net,
        odb_network_is_literal=bool(odb_net) and not is_ref(odb_net),
        cidr_range=d.get('cidr_range', '') or ('10.0.1.0/24' if defaults else ''),
        purpose=d.get('purpose', 'CLIENT_SUBNET'),
        project=d.get('project', ''),
        deletion_protection=tf_bool(d.get('deletion_protection', True)),
        mn0=mn0,
    )


def gcp_subnet_main(mn):
    return render_tf('gcp_odb_subnet/main.tf.j2', module_name=mn)


def gcp_subnet_vars(mn, d, mn0=''):
    return render_tf('gcp_odb_subnet/variables.tf.j2', module_name=mn, **_gcp_subnet_ctx(d, mn0))


def gcp_subnet_outputs(mn):
    return render_tf('gcp_odb_subnet/outputs.tf.j2', module_name=mn)


def gcp_subnet_tfvars(mn, d, mn0=''):
    return render_tf('gcp_odb_subnet/terraform.tfvars.j2', module_name=mn, **_gcp_subnet_ctx(d, mn0, defaults=True))


# ── GCP MODULE 2 — google_oracle_database_cloud_exadata_infrastructure ────────

def _gcp2_ctx(d, defaults=False):
    raw_hours  = parse_list(d.get('mw_hours_of_day', ''))
    raw_weeks  = parse_list(d.get('mw_weeks_of_month', ''))
    hours_ints = [int(x) for x in raw_hours  if x.strip().lstrip('-').isdigit()]
    weeks_ints = [int(x) for x in raw_weeks  if x.strip().lstrip('-').isdigit()]
    return dict(
        cloud_exadata_infrastructure_id=d.get('cloud_exadata_infrastructure_id', '') or ('my-exadb-infra' if defaults else ''),
        location=d.get('location', '') or ('us-east4' if defaults else ''),
        display_name=d.get('display_name', ''),
        gcp_oracle_zone=d.get('gcp_oracle_zone', ''),
        project=d.get('project', ''),
        deletion_protection=tf_bool(d.get('deletion_protection', True)),
        shape=d.get('shape', 'Exadata.X9M') or 'Exadata.X9M',
        compute_count=int(d.get('compute_count', 2) or 2),
        storage_count=int(d.get('storage_count', 3) or 3),
        total_storage_size_gb=int(d.get('total_storage_size_gb', 0) or 0),
        customer_contacts=d.get('customer_contacts', []),
        mw_preference=d.get('mw_preference', 'NO_PREFERENCE'),
        mw_patching_mode=d.get('mw_patching_mode', 'ROLLING'),
        mw_is_custom_action_timeout_enabled=tf_bool(d.get('mw_is_custom_action_timeout_enabled', False)),
        mw_custom_action_timeout_mins=int(d.get('mw_custom_action_timeout_mins', 15) or 15),
        is_custom_mw=(d.get('mw_preference', '') == 'CUSTOM_PREFERENCE'),
        mw_lead_time_week=d.get('mw_lead_time_week', ''),
        mw_months=parse_list(d.get('mw_months', '')),
        mw_weeks_of_month=weeks_ints,
        mw_days_of_week=parse_list(d.get('mw_days_of_week', '')),
        mw_hours_of_day=hours_ints,
        labels=d.get('labels', {}),
    )


def gcp2_main(mn):
    return render_tf('gcp_exadb_infra/main.tf.j2', module_name=mn)


def gcp2_vars(mn, d):
    return render_tf('gcp_exadb_infra/variables.tf.j2', module_name=mn, **_gcp2_ctx(d))


def gcp2_outputs(mn):
    return render_tf('gcp_exadb_infra/outputs.tf.j2', module_name=mn)


def gcp2_tfvars(mn, d):
    return render_tf('gcp_exadb_infra/terraform.tfvars.j2', module_name=mn, **_gcp2_ctx(d, defaults=True))


# ── GCP MODULE 1 — google_oracle_database_exadb_vm_cluster ───────────────────

def _gcp1_ctx(d, mn0='', mn1='', mn2='', mn3='', defaults=False):
    odb_net   = d.get('odb_network', '')    or (f'module.{mn0}.odb_network_name'    if mn0 else '')
    odb_sub   = d.get('odb_subnet', '')     or (f'module.{mn1}.odb_subnet_name'     if mn1 else '')
    bak_sub   = d.get('backup_odb_subnet', '') or (f'module.{mn2}.odb_subnet_name'  if mn2 else '')
    exa_infra = d.get('exadata_infrastructure', '') or (f'module.{mn3}.infra_name'  if mn3 else '')
    return dict(
        exadb_vm_cluster_id=d.get('exadb_vm_cluster_id', '') or ('my-exadb-cluster' if defaults else ''),
        display_name=d.get('display_name', '') or ('my-exadb-vm-cluster' if defaults else ''),
        location=d.get('location', '') or ('us-east4' if defaults else ''),
        gcp_oracle_zone=d.get('gcp_oracle_zone', ''),
        odb_network=odb_net,
        odb_network_is_literal=bool(odb_net) and not is_ref(odb_net),
        odb_subnet=odb_sub,
        odb_subnet_is_literal=bool(odb_sub) and not is_ref(odb_sub),
        backup_odb_subnet=bak_sub,
        backup_subnet_is_literal=bool(bak_sub) and not is_ref(bak_sub),
        exadata_infrastructure=exa_infra,
        exainfra_is_literal=bool(exa_infra) and not is_ref(exa_infra),
        project=d.get('project', ''),
        deletion_protection=tf_bool(d.get('deletion_protection', True)),
        grid_image_id=d.get('grid_image_id', ''),
        exascale_db_storage_vault=d.get('exascale_db_storage_vault', ''),
        shape_attribute=d.get('shape_attribute', 'SMART_STORAGE'),
        hostname_prefix=d.get('hostname_prefix', ''),
        license_type=d.get('license_type', 'LICENSE_INCLUDED'),
        cluster_name=d.get('cluster_name', ''),
        node_count=int(d.get('node_count', 2) or 2),
        enabled_ecpu_count_per_node=int(d.get('enabled_ecpu_count_per_node', 8) or 8),
        additional_ecpu_count_per_node=int(d.get('additional_ecpu_count_per_node', 0) or 0),
        vm_file_system_storage_size_gbs=int(d.get('vm_file_system_storage_size_gbs', 60) or 60),
        ssh_public_keys=d.get('ssh_public_keys', []),
        dco_diagnostics=tf_bool(d.get('dco_diagnostics', True)),
        dco_health=tf_bool(d.get('dco_health', True)),
        dco_incident_logs=tf_bool(d.get('dco_incident_logs', True)),
        time_zone=d.get('time_zone', ''),
        memory_per_node_in_gbs=int(d.get('memory_per_node_in_gbs', 0) or 0),
        db_node_storage_size_per_vm_in_gbs=int(d.get('db_node_storage_size_per_vm_in_gbs', 0) or 0),
        data_storage_size_in_tbs=int(d.get('data_storage_size_in_tbs', 0) or 0),
        spare_snapshot_space_in_gbs=int(d.get('spare_snapshot_space_in_gbs', 0) or 0),
        disk_redundancy=d.get('disk_redundancy', ''),
        db_servers=d.get('db_servers', []),
        mn0=mn0, mn1=mn1, mn2=mn2, mn3=mn3,
        labels=d.get('labels', {}),
    )


def gcp1_main(mn, d=None, mn0='', mn1='', mn2='', mn3=''):
    ctx = _gcp1_ctx(d, mn0, mn1, mn2, mn3) if d else {'db_servers': []}
    return render_tf('gcp_exadb_vm_cluster/main.tf.j2', module_name=mn, **ctx)


def gcp1_vars(mn, d, mn0='', mn1='', mn2='', mn3=''):
    return render_tf('gcp_exadb_vm_cluster/variables.tf.j2', module_name=mn, **_gcp1_ctx(d, mn0, mn1, mn2, mn3))


def gcp1_outputs(mn):
    return render_tf('gcp_exadb_vm_cluster/outputs.tf.j2', module_name=mn)


def gcp1_tfvars(mn, d, mn0='', mn1='', mn2='', mn3=''):
    return render_tf('gcp_exadb_vm_cluster/terraform.tfvars.j2', module_name=mn,
                     **_gcp1_ctx(d, mn0, mn1, mn2, mn3, defaults=True))


# ── GCP ROOT ──────────────────────────────────────────────────────────────────

def gcp_build_root_vars(networks, infras, clusters, oci_databases=None, oci_region='us-ashburn-1'):
    gcp_project = 'my-gcp-project'
    gcp_region  = 'us-east4'
    for n in (networks or []):
        if n.get('project'): gcp_project = n['project']; break
    for items in [networks, infras, clusters]:
        for item in items:
            if item.get('location'): gcp_region = item['location']; break
    return render_tf('gcp_root/variables.tf.j2',
        gcp_project=gcp_project, gcp_region=gcp_region,
        oci_databases=oci_databases or [], oci_region=oci_region)


def gcp_build_root_main(networks, infras, clusters, oci_databases=None, oci_region='us-ashburn-1', iac_tool='terraform'):
    return render_tf('gcp_root/main.tf.j2', networks=networks, infras=infras, clusters=clusters,
                     oci_databases=oci_databases or [], oci_region=oci_region, iac_tool=iac_tool)


def gcp_build_root_tfvars(networks, infras, clusters):
    proj = 'my-gcp-project'
    loc  = 'us-east4'
    all_labels = {}
    for items in [networks, infras, clusters]:
        for item in items:
            all_labels.update(item.get('labels', {}))
            if item.get('project'): proj = item['project']
            if item.get('location'): loc = item['location']
    return render_tf('gcp_root/terraform.tfvars.j2',
        gcp_project=proj, gcp_region=loc,
        networks=networks, infras=infras, clusters=clusters,
        labels=all_labels if all_labels else {'managed-by': 'terraform'},
    )


# ── Default normalizers ───────────────────────────────────────────────────────

def _gcp_net_defaults(d):
    csm = d.get('client_subnet_module') or (d.get('module_name', 'gcp-net') + '-client-subnet')
    bsm = d.get('backup_subnet_module') or (d.get('module_name', 'gcp-net') + '-backup-subnet')
    return {**d,
        'odb_network_id': d.get('odb_network_id') or 'my-odb-network',
        'network': d.get('network') or 'projects/PROJECT/global/networks/default',
        'client_subnet_module': csm,
        'backup_subnet_module': bsm,
        'client_subnet_id': d.get('client_subnet_id') or csm,
        'client_cidr': d.get('client_cidr') or d.get('client_subnet_cidr') or '10.0.1.0/24',
        'backup_subnet_id': d.get('backup_subnet_id') or bsm,
        'backup_cidr': d.get('backup_cidr') or d.get('backup_subnet_cidr') or '10.0.2.0/24',
    }


def _gcp_infra_defaults(d):
    return {**d,
        'cloud_exadata_infrastructure_id': d.get('cloud_exadata_infrastructure_id') or 'my-exadb-infra',
        'display_name': d.get('display_name') or 'my-exadb-infra',
        'gcp_oracle_zone': d.get('gcp_oracle_zone') or '',
        'shape': d.get('shape') or 'Exadata.X9M',
        'compute_count': int(d.get('compute_count') or 2),
        'storage_count': int(d.get('storage_count') or 3),
    }


def _gcp_cluster_defaults(d, first_net=None, first_infra=None):
    first_net = first_net or {}
    net_mn = first_net.get('module_name', 'gcp_odb_network')
    return {**d,
        'exadb_vm_cluster_id': d.get('exadb_vm_cluster_id') or 'my-exadb-cluster',
        'display_name': d.get('display_name') or 'my-exadb-vm-cluster',
        'gcp_oracle_zone': d.get('gcp_oracle_zone') or '',
        'grid_image_id': d.get('grid_image_id') or '',
        'exascale_db_storage_vault': d.get('exascale_db_storage_vault') or '',
        'shape_attribute': d.get('shape_attribute') or 'SMART_STORAGE',
        'hostname_prefix': d.get('hostname_prefix') or 'vm',
        'license_type': d.get('license_type') or 'LICENSE_INCLUDED',
        'node_count': int(d.get('node_count') or 2),
        'enabled_ecpu_count_per_node': int(d.get('enabled_ecpu_count_per_node') or 8),
        'ssh_public_keys': d.get('ssh_public_keys') or [],
        'network_ref': d.get('network_ref') or net_mn,
        'client_subnet_ref': d.get('client_subnet_ref') or first_net.get('client_subnet_module') or (net_mn + '-client-subnet'),
        'backup_subnet_ref': d.get('backup_subnet_ref') or first_net.get('backup_subnet_module') or (net_mn + '-backup-subnet'),
        'infra_ref': d.get('infra_ref') or (first_infra or {}).get('module_name') or 'gcp_exadb_infra',
    }


# ── GCP Terraform generator ───────────────────────────────────────────────────

def generate_gcp_tf(data: dict) -> dict:
    raw_nets    = data.get('gcp_networks', [])
    raw_infras  = data.get('gcp_infras', [])
    raw_clusters = data.get('gcp_clusters', [])
    raw_oci_dbs  = data.get('gcp_oci_databases', [])

    if not raw_nets:
        raw_nets = [{
            **data.get('gcp_module_0', {}),
            'module_name': data.get('gcp_module_names', {}).get('0', 'gcp_odb_network'),
            'client_subnet_module': data.get('gcp_module_names', {}).get('1', 'gcp_odb_client_subnet'),
            'backup_subnet_module': data.get('gcp_module_names', {}).get('2', 'gcp_odb_backup_subnet'),
            'client_subnet_id': data.get('gcp_module_1', {}).get('odb_subnet_id', 'gcp-odb-client-subnet'),
            'client_cidr': data.get('gcp_module_1', {}).get('cidr_range', '10.0.1.0/24'),
            'backup_subnet_id': data.get('gcp_module_2', {}).get('odb_subnet_id', 'gcp-odb-backup-subnet'),
            'backup_cidr': data.get('gcp_module_2', {}).get('cidr_range', '10.0.2.0/24'),
        }]
    if not raw_infras:
        raw_infras = [{**data.get('gcp_module_3', {}), 'module_name': data.get('gcp_module_names', {}).get('3', 'gcp_exadb_infra')}]
    if not raw_clusters:
        raw_clusters = [{**data.get('gcp_module_4', {}), 'module_name': data.get('gcp_module_names', {}).get('4', 'gcp_exadb_vm_cluster')}]

    networks  = [_gcp_net_defaults(n) for n in raw_nets]
    infras    = [_gcp_infra_defaults(i) for i in raw_infras]
    clusters  = [_gcp_cluster_defaults(c, networks[0] if networks else None, infras[0] if infras else None) for c in raw_clusters]

    first_cl_name = clusters[0]['module_name'] if clusters else ''
    oci_dbs = [_oci_db_defaults(db, first_cl_name) for db in raw_oci_dbs if _ocidb_filled(db)]

    gcp_region = 'us-east4'
    for n in networks:
        if n.get('location'): gcp_region = n['location']; break
    oci_region = _GCP_TO_OCI_REGION.get(gcp_region, 'us-ashburn-1')

    iac_tool = data.get('iac_tool', 'terraform')
    files = {
        'main.tf':          gcp_build_root_main(networks, infras, clusters, oci_dbs, oci_region, iac_tool),
        'variables.tf':     gcp_build_root_vars(networks, infras, clusters, oci_dbs, oci_region),
        'terraform.tfvars': gcp_build_root_tfvars(networks, infras, clusters),
    }
    for net in networks:
        mn = net['module_name']
        net_data = {
            **net,
            'odb_network_id': net.get('odb_network_id', ''),
            'location': net.get('location', ''),
            'network': net.get('network', ''),
            'project': net.get('project', ''),
            'gcp_oracle_zone': net.get('gcp_oracle_zone', ''),
            'deletion_protection': net.get('deletion_protection', True),
            'labels': net.get('labels', {}),
        }
        files[f'modules/{mn}/main.tf']         = gcp0_main(mn)
        files[f'modules/{mn}/variables.tf']    = gcp0_vars(mn, net_data)
        files[f'modules/{mn}/outputs.tf']      = gcp0_outputs(mn)
        files[f'modules/{mn}/terraform.tfvars']= gcp0_tfvars(mn, net_data)
        for smn, purpose, sid, scidr in [
            (net['client_subnet_module'], 'CLIENT_SUBNET', net.get('client_subnet_id', ''), net.get('client_cidr', '')),
            (net['backup_subnet_module'], 'BACKUP_SUBNET', net.get('backup_subnet_id', ''), net.get('backup_cidr', '')),
        ]:
            sd = {
                'odb_subnet_id': sid,
                'location': net.get('location', ''),
                'cidr_range': scidr,
                'purpose': purpose,
                'project': net.get('project', ''),
                'deletion_protection': net.get('deletion_protection', True),
            }
            files[f'modules/{smn}/main.tf']         = gcp_subnet_main(smn)
            files[f'modules/{smn}/variables.tf']    = gcp_subnet_vars(smn, sd, mn)
            files[f'modules/{smn}/outputs.tf']      = gcp_subnet_outputs(smn)
            files[f'modules/{smn}/terraform.tfvars']= gcp_subnet_tfvars(smn, sd, mn)
    for inf in infras:
        mn = inf['module_name']
        files[f'modules/{mn}/main.tf']         = gcp2_main(mn)
        files[f'modules/{mn}/variables.tf']    = gcp2_vars(mn, inf)
        files[f'modules/{mn}/outputs.tf']      = gcp2_outputs(mn)
        files[f'modules/{mn}/terraform.tfvars']= gcp2_tfvars(mn, inf)
    for cl in clusters:
        mn      = cl['module_name']
        net_mn  = cl['network_ref']
        clsn_mn = cl['client_subnet_ref']
        bksn_mn = cl['backup_subnet_ref']
        inf_mn  = cl['infra_ref']
        files[f'modules/{mn}/main.tf']         = gcp1_main(mn, cl, net_mn, clsn_mn, bksn_mn, inf_mn)
        files[f'modules/{mn}/variables.tf']    = gcp1_vars(mn, cl, net_mn, clsn_mn, bksn_mn, inf_mn)
        files[f'modules/{mn}/outputs.tf']      = gcp1_outputs(mn)
        files[f'modules/{mn}/terraform.tfvars']= gcp1_tfvars(mn, cl, net_mn, clsn_mn, bksn_mn, inf_mn)
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
