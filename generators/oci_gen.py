"""OCI Database (DB Home / CDB / PDB) generators — shared by AWS and GCP."""
from .helpers import render_tf, tf_bool


def _mn_dbhome(base): return f'{base}_dbhome'
def _mn_cdb(base):    return f'{base}_cdb'
def _mn_pdb(base):    return f'{base}_pdb'


def _avmc_filled(d):
    return bool(d.get('display_name', '').strip())


def _ocidb_filled(d):
    dn  = d.get('db_home_display_name', '').strip()
    db  = d.get('db_name', '').strip()
    vcr = d.get('vmcluster_ref', '').strip()
    return vcr or dn not in ('', 'dbhome') or db not in ('', 'MYDB')


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


def oci_dbhome_main(mn, d, vmcluster_ref=''):
    return render_tf('oci_db_home/main.tf.j2', module_name=mn, vmcluster_ref=vmcluster_ref,
        display_name=d.get('db_home_display_name', 'dbhome'),
        db_version=d.get('db_version', '19.0.0.0'))


def oci_dbhome_vars(mn, d, vmcluster_ref=''):
    return render_tf('oci_db_home/variables.tf.j2', module_name=mn, vmcluster_ref=vmcluster_ref,
        display_name=d.get('db_home_display_name', 'dbhome'),
        db_version=d.get('db_version', '19.0.0.0'))


def oci_dbhome_outputs(mn):
    return render_tf('oci_db_home/outputs.tf.j2', module_name=mn)


def oci_dbhome_tfvars(mn, d, vmcluster_ref=''):
    return render_tf('oci_db_home/terraform.tfvars.j2', module_name=mn, vmcluster_ref=vmcluster_ref,
        display_name=d.get('db_home_display_name', 'dbhome'),
        db_version=d.get('db_version', '19.0.0.0'))


def _cdb_ctx(mn, d, dbhome_ref=''):
    ab = bool(d.get('auto_backup_enabled', False))
    return dict(module_name=mn, dbhome_ref=dbhome_ref,
        db_name=d.get('db_name', 'MYDB'),
        character_set=d.get('character_set', 'AL32UTF8'),
        ncharacter_set=d.get('ncharacter_set', 'AL16UTF16'),
        pdb_name=d.get('pdb_name', ''),
        db_unique_name=d.get('db_unique_name', ''),
        sid_prefix=d.get('sid_prefix', ''),
        auto_backup_enabled=tf_bool(ab),
        auto_backup_window=d.get('auto_backup_window', 'SLOT_TWO'),
        recovery_window_in_days=int(d.get('recovery_window_in_days') or 7))


def oci_cdb_main(mn, d, dbhome_ref=''):
    return render_tf('oci_cdb/main.tf.j2', **_cdb_ctx(mn, d, dbhome_ref))


def oci_cdb_vars(mn, d, dbhome_ref=''):
    return render_tf('oci_cdb/variables.tf.j2', **_cdb_ctx(mn, d, dbhome_ref))


def oci_cdb_outputs(mn):
    return render_tf('oci_cdb/outputs.tf.j2', module_name=mn)


def oci_cdb_tfvars(mn, d, dbhome_ref=''):
    return render_tf('oci_cdb/terraform.tfvars.j2', **_cdb_ctx(mn, d, dbhome_ref))


def oci_pdb_main(mn, d, cdb_ref=''):
    return render_tf('oci_pdb/main.tf.j2', module_name=mn, cdb_ref=cdb_ref,
        pdb_name=d.get('pdb_name', 'MYPDB'))


def oci_pdb_vars(mn, d, cdb_ref=''):
    return render_tf('oci_pdb/variables.tf.j2', module_name=mn, cdb_ref=cdb_ref,
        pdb_name=d.get('pdb_name', 'MYPDB'))


def oci_pdb_outputs(mn):
    return render_tf('oci_pdb/outputs.tf.j2', module_name=mn)


def oci_pdb_tfvars(mn, d, cdb_ref=''):
    return render_tf('oci_pdb/terraform.tfvars.j2', module_name=mn, cdb_ref=cdb_ref,
        pdb_name=d.get('pdb_name', 'MYPDB'))
