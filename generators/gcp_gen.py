"""GCP (DB@GCP) generators."""
import datetime
from .helpers import render_tf, parse_list, tf_bool
from .oci_dg_gen import generate_oci_dg_tf
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

# Shared module directory names (fixed, not per-instance)
_GCP_MOD_NET     = 'gcp-odb-network'
_GCP_MOD_INFRA   = 'gcp-exadata-infra'
_GCP_MOD_CLUSTER = 'gcp-vm-cluster'


# ── Shared module file renderers ──────────────────────────────────────────────

def _gcp_shared_module_files() -> dict:
    """Render the 3 shared, reusable GCP module directories."""
    return {
        f'modules/{_GCP_MOD_NET}/main.tf':       render_tf('gcp_odb_network/main.tf.j2'),
        f'modules/{_GCP_MOD_NET}/variables.tf':  render_tf('gcp_odb_network/variables.tf.j2'),
        f'modules/{_GCP_MOD_NET}/outputs.tf':    render_tf('gcp_odb_network/outputs.tf.j2'),
        f'modules/{_GCP_MOD_INFRA}/main.tf':     render_tf('gcp_exadb_infra/main.tf.j2'),
        f'modules/{_GCP_MOD_INFRA}/variables.tf': render_tf('gcp_exadb_infra/variables.tf.j2'),
        f'modules/{_GCP_MOD_INFRA}/outputs.tf':  render_tf('gcp_exadb_infra/outputs.tf.j2'),
        f'modules/{_GCP_MOD_CLUSTER}/main.tf':      render_tf('gcp_exadb_vm_cluster/main.tf.j2'),
        f'modules/{_GCP_MOD_CLUSTER}/variables.tf': render_tf('gcp_exadb_vm_cluster/variables.tf.j2'),
        f'modules/{_GCP_MOD_CLUSTER}/outputs.tf':   render_tf('gcp_exadb_vm_cluster/outputs.tf.j2'),
    }


# ── Root builders ─────────────────────────────────────────────────────────────

def gcp_build_root_main(networks, infras, clusters, oci_databases=None, oci_region='us-ashburn-1', iac_tool='terraform'):
    return render_tf('gcp_root/main.tf.j2',
        networks=networks, infras=infras, clusters=clusters,
        oci_databases=oci_databases or [], oci_region=oci_region, iac_tool=iac_tool)


def gcp_build_root_vars(networks, infras, clusters, oci_databases=None, oci_region='us-ashburn-1'):
    gcp_project = 'my-gcp-project'
    gcp_region  = 'us-east4'
    for n in (networks or []):
        if n.get('project'): gcp_project = n['project']; break
    for items in [networks, infras, clusters]:
        for item in (items or []):
            if item.get('location'): gcp_region = item['location']; break
    return render_tf('gcp_root/variables.tf.j2',
        gcp_project=gcp_project, gcp_region=gcp_region,
        oci_databases=oci_databases or [], oci_region=oci_region)


def gcp_build_readme(networks, infras, clusters, iac_tool='terraform', customer_name=''):
    proj = 'my-gcp-project'
    loc  = 'us-east4'
    for items in [networks, infras, clusters]:
        for item in (items or []):
            if item.get('project'): proj = item['project']
            if item.get('location'): loc = item['location']
    # Ensure display-friendly CIDR aliases are present
    nets_doc = [{**n, 'client_cidr_range': n.get('client_cidr_range') or n.get('client_cidr', ''),
                      'backup_cidr_range': n.get('backup_cidr_range') or n.get('backup_cidr', '')}
                for n in networks]
    return render_tf('gcp_root/README.md.j2',
        gcp_project=proj, gcp_region=loc,
        networks=nets_doc, infras=infras, clusters=clusters,
        iac_tool=iac_tool,
        customer_name=customer_name,
        generated_date=datetime.date.today().isoformat())


def gcp_build_root_tfvars(networks, infras, clusters):
    proj = 'my-gcp-project'
    loc  = 'us-east4'
    for items in [networks, infras, clusters]:
        for item in (items or []):
            if item.get('project'): proj = item['project']
            if item.get('location'): loc = item['location']
    return render_tf('gcp_root/terraform.tfvars.j2',
        gcp_project=proj, gcp_region=loc,
        networks=networks, infras=infras, clusters=clusters)


# ── Default normalizers ───────────────────────────────────────────────────────

def _gcp_net_defaults(d):
    return {**d,
        'odb_network_id':     d.get('odb_network_id') or 'my-odb-network',
        'network':            d.get('network') or 'projects/PROJECT/global/networks/default',
        'client_subnet_id':   d.get('client_subnet_id') or 'client-subnet',
        'client_cidr':        d.get('client_cidr') or d.get('client_subnet_cidr') or '10.0.1.0/24',
        'backup_subnet_id':   d.get('backup_subnet_id') or 'backup-subnet',
        'backup_cidr':        d.get('backup_cidr') or d.get('backup_subnet_cidr') or '10.0.2.0/24',
        'deletion_protection': d.get('deletion_protection', True),
        'gcp_oracle_zone':    d.get('gcp_oracle_zone') or '',
        'labels':             d.get('labels', {}),
    }


def _gcp_infra_defaults(d):
    raw_hours  = parse_list(d.get('mw_hours_of_day', ''))
    raw_weeks  = parse_list(d.get('mw_weeks_of_month', ''))
    return {**d,
        'cloud_exadata_infrastructure_id': d.get('cloud_exadata_infrastructure_id') or 'my-exadb-infra',
        'display_name':       d.get('display_name') or 'my-exadb-infra',
        'gcp_oracle_zone':    d.get('gcp_oracle_zone') or '',
        'shape':              d.get('shape') or 'Exadata.X9M',
        'compute_count':      int(d.get('compute_count') or 2),
        'storage_count':      int(d.get('storage_count') or 3),
        'total_storage_size_gb': int(d.get('total_storage_size_gb') or 0),
        'customer_contacts':  d.get('customer_contacts', []),
        'mw_preference':      d.get('mw_preference', 'NO_PREFERENCE'),
        'mw_patching_mode':   d.get('mw_patching_mode', 'ROLLING'),
        'mw_is_custom_action_timeout_enabled': tf_bool(d.get('mw_is_custom_action_timeout_enabled', False)),
        'mw_custom_action_timeout_mins': int(d.get('mw_custom_action_timeout_mins', 15) or 15),
        'mw_lead_time_week':  d.get('mw_lead_time_week', ''),
        'mw_months':          parse_list(d.get('mw_months', '')),
        'mw_weeks_of_month':  [int(x) for x in raw_weeks if x.strip().lstrip('-').isdigit()],
        'mw_days_of_week':    parse_list(d.get('mw_days_of_week', '')),
        'mw_hours_of_day':    [int(x) for x in raw_hours if x.strip().lstrip('-').isdigit()],
        'deletion_protection': d.get('deletion_protection', True),
        'labels':             d.get('labels', {}),
    }


def _gcp_cluster_defaults(d, first_net=None, first_infra=None):
    first_net   = first_net or {}
    first_infra = first_infra or {}
    return {**d,
        'cloud_vm_cluster_id':    d.get('cloud_vm_cluster_id') or d.get('exadb_vm_cluster_id') or 'my-vm-cluster',
        'display_name':           d.get('display_name') or 'my-vm-cluster',
        'gi_version':             d.get('gi_version') or '23.0.0.0',
        'hostname_prefix':        d.get('hostname_prefix') or 'vm',
        'cpu_core_count':         int(d.get('cpu_core_count') or 16),
        'memory_size_gb':         int(d.get('memory_size_gb') or 60),
        'db_node_storage_size_gb': int(d.get('db_node_storage_size_gb') or 120),
        'data_storage_size_tb':   float(d.get('data_storage_size_tb') or 4.0),
        'local_backup_enabled':   d.get('local_backup_enabled', False),
        'sparse_diskgroup_enabled': d.get('sparse_diskgroup_enabled', False),
        'license_type':           d.get('license_type') or 'LICENSE_INCLUDED',
        'ssh_public_keys':        d.get('ssh_public_keys') or [],
        'deletion_protection':    d.get('deletion_protection', True),
        'network_ref':  d.get('network_ref') or first_net.get('module_name') or 'gcp-odb-network',
        'infra_ref':    d.get('infra_ref')   or first_infra.get('module_name') or 'gcp-exadata-infra',
        'labels':       d.get('labels', {}),
    }


# ── GCP Terraform generator ───────────────────────────────────────────────────

def generate_gcp_tf(data: dict) -> dict:
    raw_nets     = data.get('gcp_networks', [])
    raw_infras   = data.get('gcp_infras', [])
    raw_clusters = data.get('gcp_clusters', [])
    raw_oci_dbs  = data.get('gcp_oci_databases', [])

    # Legacy single-resource payload support
    if not raw_nets:
        raw_nets = [{
            **data.get('gcp_module_0', {}),
            'module_name': data.get('gcp_module_names', {}).get('0', 'gcp-odb-network'),
            'client_subnet_id':  data.get('gcp_module_1', {}).get('odb_subnet_id', 'client-subnet'),
            'client_cidr':       data.get('gcp_module_1', {}).get('cidr_range', '10.0.1.0/24'),
            'backup_subnet_id':  data.get('gcp_module_2', {}).get('odb_subnet_id', 'backup-subnet'),
            'backup_cidr':       data.get('gcp_module_2', {}).get('cidr_range', '10.0.2.0/24'),
        }]
    if not raw_infras:
        raw_infras = [{**data.get('gcp_module_3', {}), 'module_name': data.get('gcp_module_names', {}).get('3', 'gcp-exadata-infra')}]
    if not raw_clusters:
        raw_clusters = [{**data.get('gcp_module_4', {}), 'module_name': data.get('gcp_module_names', {}).get('4', 'gcp-vm-cluster')}]

    networks  = [_gcp_net_defaults(n) for n in raw_nets]
    infras    = [_gcp_infra_defaults(i) for i in raw_infras]
    clusters  = [_gcp_cluster_defaults(c, networks[0] if networks else None, infras[0] if infras else None)
                 for c in raw_clusters]

    first_cl_name = clusters[0]['module_name'] if clusters else ''
    oci_dbs = [_oci_db_defaults(db, first_cl_name) for db in raw_oci_dbs if _ocidb_filled(db)]

    gcp_region = 'us-east4'
    for n in networks:
        if n.get('location'): gcp_region = n['location']; break
    oci_region = _GCP_TO_OCI_REGION.get(gcp_region, 'us-ashburn-1')

    iac_tool = data.get('iac_tool', 'terraform')

    customer_name = data.get('customer_name', '')
    files = {
        'main.tf':               gcp_build_root_main(networks, infras, clusters, oci_dbs, oci_region, iac_tool),
        'variables.tf':          gcp_build_root_vars(networks, infras, clusters, oci_dbs, oci_region),
        'terraform.auto.tfvars': gcp_build_root_tfvars(networks, infras, clusters),
        'README.md':             gcp_build_readme(networks, infras, clusters, iac_tool, customer_name),
    }

    # 3 shared, reusable module directories (Aeris-style — independent of instance count)
    files.update(_gcp_shared_module_files())

    # OCI DB Home / CDB / PDB modules — still per-instance (named)
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

    files.update(generate_oci_dg_tf({
        'aws_dg_multi_az':    data.get('gcp_dg_multi_az', []),
        'aws_dg_cross_region': data.get('gcp_dg_cross_region', []),
    }))

    return files
