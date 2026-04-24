"""
Terraflow Studio — Flask Application
Generates modular Terraform code for Oracle Database@AWS and DB@GCP.
All HCL output is rendered from Jinja2 templates in templates/tf/.
"""

# Load .env FIRST — before any module reads os.environ at import time
try:
    from dotenv import load_dotenv
    import pathlib as _pl
    _env_path = _pl.Path(__file__).parent / '.env'
    load_dotenv(dotenv_path=_env_path, override=True)
except ImportError:
    import pathlib as _pl, os as _os
    _env_path = _pl.Path(__file__).parent / '.env'
    if _env_path.exists():
        for _line in _env_path.read_text(encoding='utf-8').splitlines():
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _k, _v = _line.split('=', 1)
                _k = _k.strip(); _v = _v.strip().strip('"').strip("'")
                if _k: _os.environ[_k] = _v

import io
import json
import re
import zipfile
from flask import Flask, render_template, request, jsonify, send_file, make_response
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from store import storage
import llm as llm_module
import github as github_module

app = Flask(__name__)

# ─────────────────────────────────────────────
#  JINJA2 ENVIRONMENT FOR TF TEMPLATES
# ─────────────────────────────────────────────

_tf_env = Environment(
    loader=FileSystemLoader('templates/tf'),
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=True,
)

def render_tf(template_path: str, **ctx) -> str:
    """Render a Terraform Jinja2 template with the given context."""
    return _tf_env.get_template(template_path).render(**ctx).rstrip('\n')


# ─────────────────────────────────────────────
#  SHARED HELPERS
# ─────────────────────────────────────────────

def is_ref(s: str) -> bool:
    """Return True if s looks like a Terraform reference (e.g. module.x.y)."""
    if not s:
        return False
    return bool(re.match(r'^[a-z_][a-z0-9_.]*(\.[a-z_][a-z0-9_.\[\]*]*)+$', s))

def parse_list(s: str) -> list:
    """Split a comma-separated string into a list, stripping whitespace."""
    if not s:
        return []
    return [x.strip() for x in s.split(',') if x.strip()]

def tf_bool(v) -> str:
    return 'true' if v else 'false'


# ─────────────────────────────────────────────
#  AWS MODULE 0 — aws_odb_network
# ─────────────────────────────────────────────

def mod0_main(mn):
    return render_tf('aws_odb_network/main.tf.j2', module_name=mn)

def _s3_val(v):
    """Normalise s3_access / zero_etl_access to ENABLED or DISABLED string."""
    if isinstance(v, str): return v if v in ('ENABLED','DISABLED') else ('ENABLED' if v else 'DISABLED')
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
        delete_associated_resources=tf_bool(d.get('delete_associated_resources', False)),
        tags=d.get('tags', {}),
    )


# ─────────────────────────────────────────────
#  AWS MODULE 1 — aws_odb_cloud_exadata_infrastructure
# ─────────────────────────────────────────────

def _mod1_ctx(d, defaults=False):
    # hours_of_day and weeks_of_month are number lists
    raw_hours  = parse_list(d.get('mw_hours_of_day', ''))
    raw_weeks  = parse_list(d.get('mw_weeks_of_month', ''))
    hours_ints = [int(x) for x in raw_hours  if x.strip().lstrip('-').isdigit()]
    weeks_ints = [int(x) for x in raw_weeks  if x.strip().lstrip('-').isdigit()]
    # days_of_week and months stay as plain strings; template renders { name = "..." }
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


# ─────────────────────────────────────────────
#  AWS MODULE 2 — aws_odb_network_peering_connection
# ─────────────────────────────────────────────

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
        cidrs=d.get('additional_peer_network_cidrs', []),
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


# ─────────────────────────────────────────────
#  AWS MODULE 3 — aws_odb_cloud_vm_cluster
# ─────────────────────────────────────────────

def _mod3_ctx(d, mn0='', mn1='', defaults=False):
    infraid  = d.get('cloud_exadata_infrastructure_id', '')
    netid    = d.get('odb_network_id', '')
    ds  = d.get('data_storage_size_in_tbs', '')
    dng = d.get('db_node_storage_size_in_gbs', '')
    mem = d.get('memory_size_in_gbs', '')
    sc  = d.get('scan_listener_port_tcp', '')
    # Auto-resolve to module refs when user left fields empty
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
        cloud_exadata_infrastructure_arn=d.get('cloud_exadata_infrastructure_arn', ''),
        odb_network_arn=d.get('odb_network_arn', ''),
        infra_id=infra_val,
        net_id=net_val,
        mn0=mn0, mn1=mn1,
        ssh_public_keys=d.get('ssh_public_keys', []),
        db_servers=d.get('db_servers', []),
        db_servers_mode=d.get('db_servers_mode', 'auto'),
        vm_mode=d.get('vm_mode', 'arn'),
        dco_is_diagnostics_events_enabled=tf_bool(d.get('dco_is_diagnostics_events_enabled', True)),
        dco_is_health_monitoring_enabled=tf_bool(d.get('dco_is_health_monitoring_enabled', True)),
        dco_is_incident_logs_enabled=tf_bool(d.get('dco_is_incident_logs_enabled', True)),
        cluster_name=d.get('cluster_name', ''),
        timezone=d.get('timezone', ''),
        data_storage_size_in_tbs=ds,
        db_node_storage_size_in_gbs=dng,
        memory_size_in_gbs=mem,
        scan_listener_port_tcp=sc,
        system_version=d.get('system_version', ''),
        is_local_backup_enabled=tf_bool(d.get('is_local_backup_enabled', False)),
        is_sparse_diskgroup_enabled=tf_bool(d.get('is_sparse_diskgroup_enabled', False)),
        region=d.get('region', ''),
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


# ─────────────────────────────────────────────
#  AWS AUTONOMOUS VM CLUSTER (mod4)
# ─────────────────────────────────────────────

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


# ─────────────────────────────────────────────
#  OCI DATABASE MODULE (DB Home / CDB / PDB)
# ─────────────────────────────────────────────

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

def _oci_db_defaults(d, first_cluster_name=''):
    return {**d,
        'module_name':          d.get('module_name') or 'oci_database',
        'vmcluster_ref':        d.get('vmcluster_ref') or first_cluster_name,
        'db_home_display_name': d.get('db_home_display_name') or 'dbhome',
        'db_version':           d.get('db_version') or '19.0.0.0',
        'db_name':              d.get('db_name') or 'MYDB',
        'character_set':        d.get('character_set') or 'AL32UTF8',
        'ncharacter_set':       d.get('ncharacter_set') or 'AL16UTF16',
        'pdb_name':             d.get('pdb_name') or '',
        'db_unique_name':       d.get('db_unique_name') or '',
        'sid_prefix':           d.get('sid_prefix') or '',
        'create_pdb':           bool(d.get('create_pdb', True)),
        'auto_backup_enabled':  bool(d.get('auto_backup_enabled', False)),
        'auto_backup_window':   d.get('auto_backup_window') or 'SLOT_TWO',
        'recovery_window_in_days': int(d.get('recovery_window_in_days') or 7),
    }

def _mn_dbhome(base): return f'{base}_dbhome'
def _mn_cdb(base):    return f'{base}_cdb'
def _mn_pdb(base):    return f'{base}_pdb'

def oci_dbhome_main(mn, d, vmcluster_ref=''):
    return render_tf('oci_db_home/main.tf.j2', module_name=mn, vmcluster_ref=vmcluster_ref,
        display_name=d.get('db_home_display_name','dbhome'), db_version=d.get('db_version','19.0.0.0'))

def oci_dbhome_vars(mn, d, vmcluster_ref=''):
    return render_tf('oci_db_home/variables.tf.j2', module_name=mn, vmcluster_ref=vmcluster_ref,
        display_name=d.get('db_home_display_name','dbhome'), db_version=d.get('db_version','19.0.0.0'))

def oci_dbhome_outputs(mn):
    return render_tf('oci_db_home/outputs.tf.j2', module_name=mn)

def oci_dbhome_tfvars(mn, d, vmcluster_ref=''):
    return render_tf('oci_db_home/terraform.tfvars.j2', module_name=mn, vmcluster_ref=vmcluster_ref,
        display_name=d.get('db_home_display_name','dbhome'), db_version=d.get('db_version','19.0.0.0'))

def _cdb_ctx(mn, d, dbhome_ref=''):
    ab = bool(d.get('auto_backup_enabled', False))
    return dict(module_name=mn, dbhome_ref=dbhome_ref,
        db_name=d.get('db_name','MYDB'), character_set=d.get('character_set','AL32UTF8'),
        ncharacter_set=d.get('ncharacter_set','AL16UTF16'), pdb_name=d.get('pdb_name',''),
        db_unique_name=d.get('db_unique_name',''), sid_prefix=d.get('sid_prefix',''),
        auto_backup_enabled=tf_bool(ab), auto_backup_window=d.get('auto_backup_window','SLOT_TWO'),
        recovery_window_in_days=int(d.get('recovery_window_in_days') or 7))

def oci_cdb_main(mn, d, dbhome_ref=''):    return render_tf('oci_cdb/main.tf.j2', **_cdb_ctx(mn, d, dbhome_ref))
def oci_cdb_vars(mn, d, dbhome_ref=''):    return render_tf('oci_cdb/variables.tf.j2', **_cdb_ctx(mn, d, dbhome_ref))
def oci_cdb_outputs(mn):                   return render_tf('oci_cdb/outputs.tf.j2', module_name=mn)
def oci_cdb_tfvars(mn, d, dbhome_ref=''):  return render_tf('oci_cdb/terraform.tfvars.j2', **_cdb_ctx(mn, d, dbhome_ref))

def oci_pdb_main(mn, d, cdb_ref=''):
    return render_tf('oci_pdb/main.tf.j2', module_name=mn, cdb_ref=cdb_ref, pdb_name=d.get('pdb_name','MYPDB'))
def oci_pdb_vars(mn, d, cdb_ref=''):
    return render_tf('oci_pdb/variables.tf.j2', module_name=mn, cdb_ref=cdb_ref, pdb_name=d.get('pdb_name','MYPDB'))
def oci_pdb_outputs(mn):
    return render_tf('oci_pdb/outputs.tf.j2', module_name=mn)
def oci_pdb_tfvars(mn, d, cdb_ref=''):
    return render_tf('oci_pdb/terraform.tfvars.j2', module_name=mn, cdb_ref=cdb_ref, pdb_name=d.get('pdb_name','MYPDB'))


# ─────────────────────────────────────────────
#  AWS ROOT
# ─────────────────────────────────────────────

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


# ═════════════════════════════════════════════
#  GCP MODULE 0 — google_oracle_database_odb_network
# ═════════════════════════════════════════════

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


# ═════════════════════════════════════════════
#  GCP MODULE 1 — google_oracle_database_odb_subnet
# ═════════════════════════════════════════════

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


# ═════════════════════════════════════════════
#  GCP MODULE 2 — google_oracle_database_cloud_exadata_infrastructure
# ═════════════════════════════════════════════

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


# ═════════════════════════════════════════════
#  GCP MODULE 2 — google_oracle_database_exadb_vm_cluster
# ═════════════════════════════════════════════

def _gcp1_ctx(d, mn0='', mn1='', mn2='', mn3='', defaults=False):
    # If user left these blank, default to the canonical module output references
    odb_net   = d.get('odb_network', '')    or (f'module.{mn0}.odb_network_name'    if mn0 else '')
    odb_sub   = d.get('odb_subnet', '')     or (f'module.{mn1}.odb_subnet_name'     if mn1 else '')
    bak_sub   = d.get('backup_odb_subnet','') or (f'module.{mn2}.odb_subnet_name'   if mn2 else '')
    exa_infra = d.get('exadata_infrastructure','') or (f'module.{mn3}.infra_name'   if mn3 else '')
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
        gi_version=d.get('gi_version', ''),
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
        system_version=d.get('system_version', ''),
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
    return render_tf('gcp_exadb_vm_cluster/terraform.tfvars.j2', module_name=mn, **_gcp1_ctx(d, mn0, mn1, mn2, mn3, defaults=True))


# ═════════════════════════════════════════════
#  GCP ROOT
# ═════════════════════════════════════════════

def gcp_build_root_main(networks, infras, clusters, iac_tool='terraform'):
    return render_tf('gcp_root/main.tf.j2', networks=networks, infras=infras, clusters=clusters, iac_tool=iac_tool)

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


# ─────────────────────────────────────────────
#  GENERATE ALL FILES
# ─────────────────────────────────────────────

def _aws_net_defaults(d):
    """Ensure required fields have defaults for tfvars rendering."""
    return {**d,
        'display_name': d.get('display_name') or 'odb-network',
        'availability_zone_id': d.get('availability_zone_id') or 'use1-az6',
        'client_subnet_cidr': d.get('client_subnet_cidr') or '10.2.0.0/24',
        'backup_subnet_cidr': d.get('backup_subnet_cidr') or '10.2.1.0/24',
        's3_access': 'ENABLED' if d.get('s3_access') else 'DISABLED',
        'zero_etl_access': 'ENABLED' if d.get('zero_etl_access') else 'DISABLED',
        'region': d.get('region', ''),
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

def _gcp_net_defaults(d):
    csm = d.get('client_subnet_module') or (d.get('module_name', 'gcp-net') + '-client-subnet')
    bsm = d.get('backup_subnet_module') or (d.get('module_name', 'gcp-net') + '-backup-subnet')
    return {**d,
        'odb_network_id': d.get('odb_network_id') or 'my-odb-network',
        'network': d.get('network') or 'projects/PROJECT/global/networks/default',
        'client_subnet_module': csm,
        'backup_subnet_module': bsm,
        'client_subnet_id': d.get('client_subnet_id') or (csm),
        'client_cidr': d.get('client_cidr') or d.get('client_subnet_cidr') or '10.0.1.0/24',
        'backup_subnet_id': d.get('backup_subnet_id') or (bsm),
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
        'gi_version': d.get('gi_version') or '23.0.0.0',
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


def generate_all(data: dict) -> dict:
    """Generate all Terraform files. Returns a dict of path -> content."""
    cloud = data.get('cloud', 'aws')

    if cloud == 'gcp':
        # ── Multi-instance GCP ──────────────────────────────────────────────
        raw_nets    = data.get('gcp_networks', [])
        raw_infras  = data.get('gcp_infras', [])
        raw_clusters = data.get('gcp_clusters', [])

        # Default module names when not provided
        if not raw_nets:
            raw_nets = [{**data.get('gcp_module_0', {}), 'module_name': data.get('gcp_module_names',{}).get('0','gcp_odb_network'),
                         'client_subnet_module': data.get('gcp_module_names',{}).get('1','gcp_odb_client_subnet'),
                         'backup_subnet_module': data.get('gcp_module_names',{}).get('2','gcp_odb_backup_subnet'),
                         'client_subnet_id': data.get('gcp_module_1',{}).get('odb_subnet_id','gcp-odb-client-subnet'),
                         'client_cidr': data.get('gcp_module_1',{}).get('cidr_range','10.0.1.0/24'),
                         'backup_subnet_id': data.get('gcp_module_2',{}).get('odb_subnet_id','gcp-odb-backup-subnet'),
                         'backup_cidr': data.get('gcp_module_2',{}).get('cidr_range','10.0.2.0/24')}]
        if not raw_infras:
            raw_infras = [{**data.get('gcp_module_3', {}), 'module_name': data.get('gcp_module_names',{}).get('3','gcp_exadb_infra')}]
        if not raw_clusters:
            raw_clusters = [{**data.get('gcp_module_4', {}), 'module_name': data.get('gcp_module_names',{}).get('4','gcp_exadb_vm_cluster')}]

        networks  = [_gcp_net_defaults(n) for n in raw_nets]
        infras    = [_gcp_infra_defaults(i) for i in raw_infras]
        clusters  = [_gcp_cluster_defaults(c, networks[0] if networks else None, infras[0] if infras else None) for c in raw_clusters]

        files = {
            'main.tf':          gcp_build_root_main(networks, infras, clusters, iac_tool=data.get('iac_tool','terraform')),
            'terraform.tfvars': gcp_build_root_tfvars(networks, infras, clusters),
        }
        # ODB Networks + subnets
        for net in networks:
            mn = net['module_name']
            net_data = {**net, 'odb_network_id': net.get('odb_network_id',''), 'location': net.get('location',''), 'network': net.get('network',''), 'project': net.get('project',''), 'gcp_oracle_zone': net.get('gcp_oracle_zone',''), 'deletion_protection': net.get('deletion_protection', True), 'labels': net.get('labels',{})}
            files[f'modules/{mn}/main.tf']         = gcp0_main(mn)
            files[f'modules/{mn}/variables.tf']    = gcp0_vars(mn, net_data)
            files[f'modules/{mn}/outputs.tf']      = gcp0_outputs(mn)
            files[f'modules/{mn}/terraform.tfvars']= gcp0_tfvars(mn, net_data)
            for smn, purpose, sid, scidr in [
                (net['client_subnet_module'], 'CLIENT_SUBNET', net.get('client_subnet_id',''), net.get('client_cidr','')),
                (net['backup_subnet_module'], 'BACKUP_SUBNET', net.get('backup_subnet_id',''), net.get('backup_cidr','')),
            ]:
                sd = {'odb_subnet_id': sid, 'location': net.get('location',''), 'cidr_range': scidr, 'purpose': purpose, 'project': net.get('project',''), 'deletion_protection': net.get('deletion_protection', True)}
                files[f'modules/{smn}/main.tf']         = gcp_subnet_main(smn)
                files[f'modules/{smn}/variables.tf']    = gcp_subnet_vars(smn, sd, mn)
                files[f'modules/{smn}/outputs.tf']      = gcp_subnet_outputs(smn)
                files[f'modules/{smn}/terraform.tfvars']= gcp_subnet_tfvars(smn, sd, mn)
        # Exadata Infras
        for inf in infras:
            mn = inf['module_name']
            files[f'modules/{mn}/main.tf']         = gcp2_main(mn)
            files[f'modules/{mn}/variables.tf']    = gcp2_vars(mn, inf)
            files[f'modules/{mn}/outputs.tf']      = gcp2_outputs(mn)
            files[f'modules/{mn}/terraform.tfvars']= gcp2_tfvars(mn, inf)
        # VM Clusters
        for cl in clusters:
            mn   = cl['module_name']
            net_mn  = cl['network_ref']
            clsn_mn = cl['client_subnet_ref']
            bksn_mn = cl['backup_subnet_ref']
            inf_mn  = cl['infra_ref']
            files[f'modules/{mn}/main.tf']         = gcp1_main(mn, cl, net_mn, clsn_mn, bksn_mn, inf_mn)
            files[f'modules/{mn}/variables.tf']    = gcp1_vars(mn, cl, net_mn, clsn_mn, bksn_mn, inf_mn)
            files[f'modules/{mn}/outputs.tf']      = gcp1_outputs(mn)
            files[f'modules/{mn}/terraform.tfvars']= gcp1_tfvars(mn, cl, net_mn, clsn_mn, bksn_mn, inf_mn)
        return files

    # ── Multi-instance AWS ──────────────────────────────────────────────────
    raw_nets     = data.get('aws_networks', [])
    raw_infras   = data.get('aws_infras', [])
    raw_peerings = data.get('aws_peerings', [])
    raw_clusters = data.get('aws_clusters', [])
    raw_avmc     = data.get('aws_avmclusters', [])

    # Backward compatibility: fall back to single-instance module_0/1/2/3
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
    avmclusters = [_aws_avmc_defaults(a, first_net_name, first_inf_name) for a in raw_avmc]

    raw_oci_dbs   = data.get('aws_oci_databases', [])
    first_cl_name = clusters[0]['module_name'] if clusters else (avmclusters[0]['module_name'] if avmclusters else '')
    oci_dbs = [_oci_db_defaults(db, first_cl_name) for db in raw_oci_dbs]

    iac_tool = data.get('iac_tool', 'terraform')

    files = {
        'main.tf':          build_root_main(networks, infras, peerings, clusters, avmclusters, oci_dbs, iac_tool),
        'terraform.tfvars': build_root_tfvars(networks, infras, peerings, clusters, avmclusters),
    }
    for net in networks:
        mn = net['module_name']
        files[f'modules/{mn}/main.tf']          = mod0_main(mn)
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


# ─────────────────────────────────────────────
#  ROUTES
# ─────────────────────────────────────────────
#  LLM ROUTES
# ─────────────────────────────────────────────

@app.route('/api/llm/info', methods=['GET'])
def api_llm_info():
    return jsonify(llm_module.provider_info())

@app.route('/api/llm/debug', methods=['GET'])
def api_llm_debug():
    import os as _os, pathlib as _pl
    key = _os.environ.get('LLM_API_KEY', '')
    env_path = _pl.Path(__file__).parent / '.env'
    try:
        import dotenv; dotenv_installed = True
    except ImportError:
        dotenv_installed = False
    return jsonify({
        'env_file_path':    str(env_path),
        'env_file_exists':  env_path.exists(),
        'dotenv_installed': dotenv_installed,
        'LLM_PROVIDER':     _os.environ.get('LLM_PROVIDER', '(not set)'),
        'LLM_API_KEY':      f'{key[:8]}...{key[-4:]}' if len(key) > 12 else ('(set, short)' if key else '(not set)'),
        'LLM_MODEL':        _os.environ.get('LLM_MODEL', '(not set)'),
        'LLM_BASE_URL':     _os.environ.get('LLM_BASE_URL', '(not set)'),
        'LLM_MAX_TOKENS':   _os.environ.get('LLM_MAX_TOKENS', '(not set)'),
    })

@app.route('/api/llm/chat', methods=['POST'])
def api_llm_chat():
    body = request.get_json(force=True)
    messages = body.get('messages', [])
    if not messages:
        return jsonify({'error': 'messages array is required'}), 400
    try:
        return jsonify({'content': llm_module.chat(messages)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/llm/fill', methods=['POST'])
def api_llm_fill():
    body    = request.get_json(force=True)
    prompt  = body.get('prompt', '').strip()
    cloud   = body.get('cloud', 'aws')
    current = body.get('current', {})
    if not prompt:
        return jsonify({'error': 'prompt is required'}), 400
    system_msg = """You are a Terraform infrastructure assistant for Oracle Database@AWS and DB@GCP.
Interpret a natural-language infrastructure request and return a valid Terraflow Studio payload JSON.
The payload schema includes: cloud, aws_networks, aws_infras, aws_peerings, aws_clusters, aws_avmclusters, aws_oci_databases, gcp_networks, gcp_infras, gcp_clusters.
Key rules: module_name is a unique slug, db_name max 8 chars, aws shapes: Exadata.X9M/X10M/X11M, license_model: LICENSE_INCLUDED or BRING_YOUR_OWN_LICENSE.
Return ONLY a valid JSON object with exactly two keys: {"payload": {...}, "explanation": "..."}
No markdown, no preamble."""
    user_msg = f"Cloud: {cloud}\nCurrent: {json.dumps(current)[:3000]}\nRequest: {prompt}\nReturn JSON object."
    try:
        reply = llm_module.chat([{'role':'system','content':system_msg},{'role':'user','content':user_msg}])
        clean = reply.strip()
        if clean.startswith('```'): clean = '\n'.join(clean.split('\n')[1:])
        if clean.endswith('```'):   clean = '\n'.join(clean.split('\n')[:-1])
        result = json.loads(clean.strip())
        return jsonify({'payload': result.get('payload',{}), 'explanation': result.get('explanation','')})
    except json.JSONDecodeError as e:
        return jsonify({'error': f'LLM returned invalid JSON: {e}', 'raw': reply[:500]}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────
#  GITHUB ROUTES
# ─────────────────────────────────────────────

@app.route('/api/github/info', methods=['GET'])
def api_github_info():
    return jsonify(github_module.github_info())

@app.route('/api/github/push', methods=['POST'])
def api_github_push():
    data           = request.get_json(force=True)
    commit_message = data.pop('commit_message', '')
    customer       = data.get('customer', '')
    try:
        files = generate_all(data)
    except Exception as e:
        return jsonify({'error': f'Generation failed: {e}'}), 500
    try:
        pusher = github_module.GitHubPusher()
    except RuntimeError as e:
        return jsonify({'error': str(e)}), 400
    try:
        return jsonify(pusher.push_files(files, customer=customer, commit_message=commit_message))
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────

@app.route('/')
def index():
    resp = make_response(render_template('index.html'))
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    return resp


@app.route('/api/generate', methods=['POST'])
def api_generate():
    data = request.get_json(force=True)
    file_key = data.get('file_key', 'main.tf')
    try:
        files = generate_all(data)
        content = files.get(file_key)
        if content is None:
            return jsonify({'error': f'Unknown file key: {file_key}'})
        return jsonify({'content': content})
    except Exception as e:
        return jsonify({'error': str(e)})


@app.route('/api/download', methods=['POST'])
def api_download():
    data = request.get_json(force=True)
    cloud = data.get('cloud', 'aws')
    zip_name = 'terraflow-studio-gcp' if cloud == 'gcp' else 'terraflow-studio-aws'
    files = generate_all(data)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for path, content in files.items():
            zf.writestr(f'{zip_name}/{path}', content)
    buf.seek(0)
    return send_file(buf, mimetype='application/zip',
                     as_attachment=True, download_name=f'{zip_name}.zip')


@app.route('/api/validate', methods=['POST'])
def api_validate():
    data   = request.get_json(force=True)
    tab    = data.get('tab', 0)
    errors = {}   # {module_name: {field: message}}

    def _err(module_name, field, msg):
        errors.setdefault(module_name, {})[field] = msg

    # ── AWS tabs ──────────────────────────────────────────────────────────────
    if tab == 0:   # ODB Networks
        for net in data.get('aws_networks', [data.get('module_0', {})]):
            mn = net.get('module_name', 'odb_network')
            if not net.get('display_name'):            _err(mn, 'display_name',        'Required')
            if not net.get('availability_zone_id'):    _err(mn, 'availability_zone_id', 'Required')
            if not re.match(r'^\d+\.\d+\.\d+\.\d+/\d+$', net.get('client_subnet_cidr', '')):
                _err(mn, 'client_subnet_cidr', 'Valid CIDR required')
            if not re.match(r'^\d+\.\d+\.\d+\.\d+/\d+$', net.get('backup_subnet_cidr', '')):
                _err(mn, 'backup_subnet_cidr', 'Valid CIDR required')

    elif tab == 1:  # Exadata Infras
        for inf in data.get('aws_infras', [data.get('module_1', {})]):
            mn = inf.get('module_name', 'odb_exaInfra')
            if not inf.get('display_name'):             _err(mn, 'display_name',        'Required')
            if not inf.get('shape'):                    _err(mn, 'shape',               'Required')
            if not inf.get('availability_zone_id'):     _err(mn, 'availability_zone_id', 'Required')
            if int(inf.get('compute_count', 0) or 0) < 2: _err(mn, 'compute_count', 'Minimum 2')
            if int(inf.get('storage_count', 0) or 0) < 3: _err(mn, 'storage_count', 'Minimum 3')

    elif tab == 2:  # Peerings
        for peer in data.get('aws_peerings', [data.get('module_2', {})]):
            mn = peer.get('module_name', 'odb_peering')
            if not peer.get('display_name'):    _err(mn, 'display_name',    'Required')
            if not peer.get('peer_network_id'): _err(mn, 'peer_network_id', 'Required')

    elif tab == 3:  # VM Clusters
        for cl in data.get('aws_clusters', [data.get('module_3', {})]):
            mn = cl.get('module_name', 'odb_vmcluster')
            if not cl.get('display_name'):                  _err(mn, 'display_name',    'Required')
            if int(cl.get('cpu_core_count', 0) or 0) < 2:  _err(mn, 'cpu_core_count',  'Minimum 2')
            if not cl.get('gi_version'):                    _err(mn, 'gi_version',       'Required')
            if not cl.get('hostname_prefix'):               _err(mn, 'hostname_prefix',  'Required')
            if not cl.get('ssh_public_keys'):               _err(mn, 'ssh_public_keys',  'At least one SSH key required')

    elif tab == 4:  # Autonomous VM Clusters
        for av in data.get('aws_avmclusters', []):
            mn = av.get('module_name', 'odb_avmcluster')
            if not av.get('display_name'):                                       _err(mn, 'display_name', 'Required')
            if float(av.get('autonomous_data_storage_size_in_tbs', 0) or 0) <= 0: _err(mn, 'autonomous_data_storage_size_in_tbs', 'Required, must be > 0')
            if int(av.get('cpu_core_count_per_node', 0) or 0) < 1:              _err(mn, 'cpu_core_count_per_node', 'Required, minimum 1')
            if int(av.get('memory_per_oracle_compute_unit_in_gbs', 0) or 0) < 1: _err(mn, 'memory_per_oracle_compute_unit_in_gbs', 'Required, minimum 1')
            if int(av.get('total_container_databases', 0) or 0) < 1:            _err(mn, 'total_container_databases', 'Required, minimum 1')

    # ── GCP tabs ──────────────────────────────────────────────────────────────
    elif tab == 10:  # GCP Networks
        for net in data.get('gcp_networks', [data.get('gcp_module_0', {})]):
            mn = net.get('module_name', 'gcp_network')
            if not net.get('odb_network_id'): _err(mn, 'odb_network_id', 'Required')
            if not net.get('location'):        _err(mn, 'location',       'Required')
            if not net.get('network'):         _err(mn, 'network',        'Required')
            if not net.get('client_cidr') and not net.get('client_subnet_cidr'):
                _err(mn, 'client_cidr', 'Required')
            if not net.get('backup_cidr') and not net.get('backup_subnet_cidr'):
                _err(mn, 'backup_cidr', 'Required')

    elif tab == 12:  # GCP Infras
        for inf in data.get('gcp_infras', [data.get('gcp_module_3', {})]):
            mn = inf.get('module_name', 'gcp_infra')
            if not inf.get('cloud_exadata_infrastructure_id'): _err(mn, 'cloud_exadata_infrastructure_id', 'Required')
            if not inf.get('location'):  _err(mn, 'location', 'Required')
            if not inf.get('shape'):     _err(mn, 'shape',    'Required')
            if int(inf.get('compute_count', 0) or 0) < 2: _err(mn, 'compute_count', 'Minimum 2')
            if int(inf.get('storage_count', 0) or 0) < 3: _err(mn, 'storage_count', 'Minimum 3')

    elif tab == 13:  # GCP VM Clusters
        for cl in data.get('gcp_clusters', [data.get('gcp_module_4', {})]):
            mn = cl.get('module_name', 'gcp_cluster')
            if not cl.get('exadb_vm_cluster_id'): _err(mn, 'exadb_vm_cluster_id', 'Required')
            if not cl.get('display_name'):         _err(mn, 'display_name',        'Required')
            if not cl.get('location'):             _err(mn, 'location',            'Required')
            if not cl.get('gi_version'):           _err(mn, 'gi_version',          'Required')
            if not cl.get('hostname_prefix'):      _err(mn, 'hostname_prefix',     'Required')
            if int(cl.get('node_count', 0) or 0) < 2:
                _err(mn, 'node_count', 'Minimum 2')
            if int(cl.get('enabled_ecpu_count_per_node', 0) or 0) < 8:
                _err(mn, 'enabled_ecpu_count_per_node', 'Minimum 8 (multiples of 4)')
            if not cl.get('ssh_public_keys'):
                _err(mn, 'ssh_public_keys', 'At least one SSH key required')

    flat_errors = {}
    for mn_errors in errors.values():
        flat_errors.update(mn_errors)
    return jsonify({'valid': len(errors) == 0, 'errors': flat_errors, 'errors_by_module': errors})


# ─────────────────────────────────────────────
#  CONFIG PERSISTENCE ROUTES
# ─────────────────────────────────────────────

@app.route('/api/config/save', methods=['POST'])
def api_config_save():
    """Save full form payload for a customer + cloud."""
    data = request.get_json(force=True)
    customer = (data.get('customer') or '').strip()
    if not customer:
        return jsonify({'error': 'customer name is required'}), 400
    cloud = data.get('cloud', 'aws')
    try:
        result = storage.save(customer, cloud, data)
        return jsonify({'ok': True, 'backend': storage.backend_name, **result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/config/load/<customer>/<cloud>', methods=['GET'])
def api_config_load(customer, cloud):
    """Load saved config for a customer + cloud."""
    try:
        doc = storage.load(customer, cloud)
        if doc is None:
            return jsonify({'error': 'not found'}), 404
        return jsonify(doc)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/config/list', methods=['GET'])
def api_config_list():
    """List all saved customers."""
    try:
        return jsonify(storage.list_customers())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/config/delete/<customer>/<cloud>', methods=['DELETE'])
def api_config_delete(customer, cloud):
    """Delete a saved config."""
    try:
        ok = storage.delete(customer, cloud)
        return jsonify({'ok': ok})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/config/backend', methods=['GET'])
def api_config_backend():
    """Return which storage backend is active."""
    return jsonify({'backend': storage.backend_name})


@app.route('/api/test', methods=['POST'])
def api_test():
    """
    Run Terraform generation tests for a specific customer config.
    Loads the saved config (or uses the posted payload directly),
    then runs all generation tests and returns structured results.
    """
    data     = request.get_json(force=True)
    customer = (data.get('customer') or '').strip()
    cloud    = data.get('cloud', 'aws')

    # Load saved config if customer name given, otherwise use posted payload
    payload = data
    if customer:
        saved = storage.load(customer, cloud)
        if saved:
            payload = saved

    results = []

    def run_test(group, name, fn):
        try:
            fn()
            results.append({'group': group, 'name': name, 'status': 'pass'})
        except Exception as e:
            results.append({'group': group, 'name': name, 'status': 'fail', 'error': str(e)})

    # ── Derive inputs ───────────────────────────────────────────────────────
    if cloud == 'aws':
        raw_nets     = payload.get('aws_networks') or []
        raw_infras   = payload.get('aws_infras') or []
        raw_peerings = payload.get('aws_peerings') or []
        raw_clusters = payload.get('aws_clusters') or []
        # backward-compat single-instance
        if not raw_nets and payload.get('module_0'):
            mn = payload.get('module_names', {})
            raw_nets     = [{**payload['module_0'],     'module_name': mn.get('0','odb_network')}]
            raw_infras   = [{**payload.get('module_1',{}), 'module_name': mn.get('1','odb_exaInfra')}]
            raw_peerings = [{**payload.get('module_2',{}), 'module_name': mn.get('2','odb_peering')}]
            raw_clusters = [{**payload.get('module_3',{}), 'module_name': mn.get('3','odb_vmcluster')}]
        nets     = [_aws_net_defaults(n) for n in raw_nets]
        infras   = [_aws_infra_defaults(i) for i in raw_infras]
        first_net  = nets[0]['module_name']  if nets    else 'odb_network'
        first_inf  = infras[0]['module_name'] if infras else 'odb_exaInfra'
        peerings = [_aws_peer_defaults(p, first_net)         for p in raw_peerings]
        clusters = [_aws_cluster_defaults(c, first_net, first_inf) for c in raw_clusters]
    else:
        raw_nets     = payload.get('gcp_networks') or []
        raw_infras   = payload.get('gcp_infras') or []
        raw_clusters = payload.get('gcp_clusters') or []
        if not raw_nets and payload.get('gcp_module_0'):
            mn = payload.get('gcp_module_names', {})
            d0, d1, d2, d3, d4 = (payload.get(f'gcp_module_{k}',{}) for k in range(5))
            net_mn = mn.get('0','gcp_network')
            cs_mn  = mn.get('1','gcp_client_subnet')
            bs_mn  = mn.get('2','gcp_backup_subnet')
            raw_nets     = [{**d0, 'module_name': net_mn, 'client_subnet_module': cs_mn,
                             'backup_subnet_module': bs_mn,
                             'client_subnet_id': d1.get('odb_subnet_id',''), 'client_cidr': d1.get('cidr_range',''),
                             'backup_subnet_id': d2.get('odb_subnet_id',''), 'backup_cidr': d2.get('cidr_range','')}]
            raw_infras   = [{**d3, 'module_name': mn.get('3','gcp_infra')}]
            raw_clusters = [{**d4, 'module_name': mn.get('4','gcp_cluster')}]
        nets     = [_gcp_net_defaults(n) for n in raw_nets]
        infras   = [_gcp_infra_defaults(i) for i in raw_infras]
        clusters = [_gcp_cluster_defaults(c, nets[0] if nets else None, infras[0] if infras else None)
                    for c in raw_clusters]
        peerings = []

    # ── TEST GROUP 1: Input validation ──────────────────────────────────────
    grp = 'Input Validation'
    if cloud == 'aws':
        for net in raw_nets:
            mn = net.get('module_name','?')
            run_test(grp, f'Network "{mn}": display_name present',
                     lambda n=net: (_ for _ in ()).throw(AssertionError('display_name missing')) if not n.get('display_name') else None)
            run_test(grp, f'Network "{mn}": availability_zone_id present',
                     lambda n=net: (_ for _ in ()).throw(AssertionError('availability_zone_id missing')) if not n.get('availability_zone_id') else None)
            run_test(grp, f'Network "{mn}": client_subnet_cidr valid CIDR',
                     lambda n=net: (_ for _ in ()).throw(AssertionError(f'Invalid CIDR: {n.get("client_subnet_cidr")}'))
                     if not re.match(r'^\d+\.\d+\.\d+\.\d+/\d+$', n.get('client_subnet_cidr','')) else None)
            run_test(grp, f'Network "{mn}": backup_subnet_cidr valid CIDR',
                     lambda n=net: (_ for _ in ()).throw(AssertionError(f'Invalid CIDR: {n.get("backup_subnet_cidr")}'))
                     if not re.match(r'^\d+\.\d+\.\d+\.\d+/\d+$', n.get('backup_subnet_cidr','')) else None)
        for inf in raw_infras:
            mn = inf.get('module_name','?')
            run_test(grp, f'Infra "{mn}": compute_count >= 2',
                     lambda i=inf: (_ for _ in ()).throw(AssertionError(f'compute_count={i.get("compute_count")} < 2'))
                     if int(i.get('compute_count',0) or 0) < 2 else None)
            run_test(grp, f'Infra "{mn}": storage_count >= 3',
                     lambda i=inf: (_ for _ in ()).throw(AssertionError(f'storage_count={i.get("storage_count")} < 3'))
                     if int(i.get('storage_count',0) or 0) < 3 else None)
        for cl in raw_clusters:
            mn = cl.get('module_name','?')
            run_test(grp, f'Cluster "{mn}": ssh_public_keys not empty',
                     lambda c=cl: (_ for _ in ()).throw(AssertionError('No SSH keys'))
                     if not c.get('ssh_public_keys') else None)
            run_test(grp, f'Cluster "{mn}": gi_version present',
                     lambda c=cl: (_ for _ in ()).throw(AssertionError('gi_version missing'))
                     if not c.get('gi_version') else None)
            run_test(grp, f'Cluster "{mn}": hostname_prefix present',
                     lambda c=cl: (_ for _ in ()).throw(AssertionError('hostname_prefix missing'))
                     if not c.get('hostname_prefix') else None)
    else:
        for net in raw_nets:
            mn = net.get('module_name','?')
            run_test(grp, f'Network "{mn}": odb_network_id present',
                     lambda n=net: (_ for _ in ()).throw(AssertionError('odb_network_id missing')) if not n.get('odb_network_id') else None)
            run_test(grp, f'Network "{mn}": location present',
                     lambda n=net: (_ for _ in ()).throw(AssertionError('location missing')) if not n.get('location') else None)
        for inf in raw_infras:
            mn = inf.get('module_name','?')
            run_test(grp, f'Infra "{mn}": cloud_exadata_infrastructure_id present',
                     lambda i=inf: (_ for _ in ()).throw(AssertionError('infra id missing'))
                     if not i.get('cloud_exadata_infrastructure_id') else None)
        for cl in raw_clusters:
            mn = cl.get('module_name','?')
            run_test(grp, f'Cluster "{mn}": ssh_public_keys not empty',
                     lambda c=cl: (_ for _ in ()).throw(AssertionError('No SSH keys'))
                     if not c.get('ssh_public_keys') else None)
            run_test(grp, f'Cluster "{mn}": gi_version present',
                     lambda c=cl: (_ for _ in ()).throw(AssertionError('gi_version missing'))
                     if not c.get('gi_version') else None)

    # ── TEST GROUP 2: Module file generation ───────────────────────────────
    grp = 'Module Generation'
    try:
        all_files = generate_all({**payload, 'cloud': cloud,
                                  'aws_networks': nets if cloud=='aws' else [],
                                  'aws_infras': infras if cloud=='aws' else [],
                                  'aws_peerings': peerings if cloud=='aws' else [],
                                  'aws_clusters': clusters if cloud=='aws' else [],
                                  'gcp_networks': nets if cloud=='gcp' else [],
                                  'gcp_infras': infras if cloud=='gcp' else [],
                                  'gcp_clusters': clusters if cloud=='gcp' else []})
        run_test(grp, 'generate_all() succeeds without error', lambda: None)
    except Exception as e:
        results.append({'group': grp, 'name': 'generate_all() succeeds without error',
                        'status': 'fail', 'error': str(e)})
        all_files = {}

    run_test(grp, 'root main.tf generated',
             lambda: (_ for _ in ()).throw(AssertionError('main.tf missing')) if 'main.tf' not in all_files else None)
    run_test(grp, 'root terraform.tfvars generated',
             lambda: (_ for _ in ()).throw(AssertionError('terraform.tfvars missing')) if 'terraform.tfvars' not in all_files else None)
    run_test(grp, 'All generated files are non-empty',
             lambda: [(_ for _ in ()).throw(AssertionError(f'{p} is empty')) for p, c in all_files.items() if not c.strip()])

    # Per-module file checks
    if cloud == 'aws':
        for mn in ([n['module_name'] for n in nets] + [i['module_name'] for i in infras] +
                   [p['module_name'] for p in peerings] + [c['module_name'] for c in clusters]):
            for ftype in ['main.tf','variables.tf','outputs.tf','terraform.tfvars']:
                key = f'modules/{mn}/{ftype}'
                run_test(grp, f'{key} generated',
                         lambda k=key: (_ for _ in ()).throw(AssertionError(f'{k} missing')) if k not in all_files else None)
    else:
        module_names = []
        for n in nets:
            module_names += [n['module_name'], n.get('client_subnet_module',''), n.get('backup_subnet_module','')]
        module_names += [i['module_name'] for i in infras] + [c['module_name'] for c in clusters]
        for mn in filter(None, module_names):
            for ftype in ['main.tf','variables.tf','outputs.tf','terraform.tfvars']:
                key = f'modules/{mn}/{ftype}'
                run_test(grp, f'{key} generated',
                         lambda k=key: (_ for _ in ()).throw(AssertionError(f'{k} missing')) if k not in all_files else None)

    # ── TEST GROUP 3: Content checks ────────────────────────────────────────
    grp = 'Content Checks'
    root = all_files.get('main.tf','')
    if cloud == 'aws':
        run_test(grp, 'root main.tf contains AWS provider',
                 lambda: (_ for _ in ()).throw(AssertionError('hashicorp/aws missing')) if 'hashicorp/aws' not in root else None)
        for n in nets:
            mn = n['module_name']
            run_test(grp, f'root main.tf references module "{mn}"',
                     lambda m=mn: (_ for _ in ()).throw(AssertionError(f'module "{m}" not in root')) if f'module "{m}"' not in root else None)
        for cl in clusters:
            mn, ir, nr = cl['module_name'], cl.get('infra_ref',''), cl.get('network_ref','')
            if ir:
                run_test(grp, f'Cluster "{mn}" wired to infra "{ir}"',
                         lambda m=mn, i=ir: (_ for _ in ()).throw(AssertionError(f'infra ref missing'))
                         if f'module.{i}.infra_id' not in root else None)
            if nr:
                run_test(grp, f'Cluster "{mn}" wired to network "{nr}"',
                         lambda m=mn, n2=nr: (_ for _ in ()).throw(AssertionError(f'network ref missing'))
                         if f'module.{n2}.network_id' not in root else None)
        for p in peerings:
            mn, nr = p['module_name'], p.get('network_ref','')
            if nr:
                run_test(grp, f'Peering "{mn}" wired to network "{nr}"',
                         lambda m=mn, n2=nr: (_ for _ in ()).throw(AssertionError(f'network ref missing'))
                         if f'module.{n2}.network_id' not in root else None)
    else:
        run_test(grp, 'root main.tf contains GCP provider',
                 lambda: (_ for _ in ()).throw(AssertionError('hashicorp/google missing')) if 'hashicorp/google' not in root else None)
        for n in nets:
            mn = n['module_name']
            run_test(grp, f'root main.tf references network "{mn}"',
                     lambda m=mn: (_ for _ in ()).throw(AssertionError(f'module "{m}" not in root')) if f'module "{m}"' not in root else None)
            csm = n.get('client_subnet_module','')
            if csm:
                run_test(grp, f'root main.tf references client subnet "{csm}"',
                         lambda m=csm: (_ for _ in ()).throw(AssertionError(f'subnet "{m}" not in root')) if f'module "{m}"' not in root else None)
        for cl in clusters:
            mn, ir, nr = cl['module_name'], cl.get('infra_ref',''), cl.get('network_ref','')
            if ir:
                run_test(grp, f'Cluster "{mn}" wired to infra "{ir}"',
                         lambda m=mn, i=ir: (_ for _ in ()).throw(AssertionError('infra ref missing'))
                         if f'module.{i}.infra_name' not in root else None)

    # ── TEST GROUP 4: Uniqueness ─────────────────────────────────────────────
    grp = 'Uniqueness'
    all_mns = ([n['module_name'] for n in nets] + [i['module_name'] for i in infras] +
               [p['module_name'] for p in peerings] + [c['module_name'] for c in clusters])
    run_test(grp, 'No duplicate module names',
             lambda: (_ for _ in ()).throw(AssertionError(f'Duplicate names: {[m for m in all_mns if all_mns.count(m)>1]}'))
             if len(all_mns) != len(set(all_mns)) else None)

    passed = sum(1 for r in results if r['status']=='pass')
    failed = sum(1 for r in results if r['status']=='fail')
    return jsonify({'customer': customer or '(current)', 'cloud': cloud,
                    'passed': passed, 'failed': failed, 'total': len(results),
                    'results': results})


from tf_validator import validate_terraform, summarise


@app.route('/api/tf-validate', methods=['POST'])
def api_tf_validate():
    """
    Run the mock Terraform provider validator against a customer's generated files.
    Loads saved config (or uses posted payload), generates all files, then
    runs structural/schema validation simulating `terraform validate`.
    """
    data     = request.get_json(force=True)
    customer = (data.get('customer') or '').strip()
    cloud    = data.get('cloud', 'aws')

    payload = data
    if customer:
        saved = storage.load(customer, cloud)
        if saved:
            payload = saved

    try:
        files = generate_all({**payload, 'cloud': cloud})
    except Exception as e:
        return jsonify({'error': f'File generation failed: {e}',
                        'passed': 0, 'failed': 1, 'warned': 0, 'total': 1,
                        'results': [{'group': 'File Generation', 'name': 'generate_all()',
                                     'status': 'fail', 'error': str(e), 'file': None}]})

    results = validate_terraform(files, cloud)
    summary = summarise(results)
    summary['customer'] = customer or '(current)'
    summary['cloud']    = cloud
    summary['files_generated'] = len(files)
    return jsonify(summary)


if __name__ == '__main__':
    app.run(debug=True, port=5000)
