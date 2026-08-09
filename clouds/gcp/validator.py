"""Oracle Database@GCP payload validation.

Rules for the form payload the browser POSTs to /api/validate - required fields,
value ranges, CIDR sanity. Distinct from schema.py, which describes the Terraform
provider's own resource schema and is used by tf_validator.

Owned entirely by this cloud: nothing here is imported by another cloud package,
so a rule change cannot affect AWS or Azure.
"""


def validate(data, errors):
    """Populate `errors` as {{module_name: {{field: message}}}}. Returns nothing."""
    return _validate_gcp(data, errors)


def _validate_gcp(data, errors):
    def _err(mn, f, m): errors.setdefault(mn, {})[f] = m
    tab = data.get('tab', 0)

    if tab == 10:  # GCP Networks
        for net in data.get('gcp_networks', [data.get('gcp_module_0', {})]):
            mn = net.get('module_name', 'gcp_network')
            if not net.get('odb_network_id'): _err(mn, 'odb_network_id', 'Required')
            if not net.get('location'):        _err(mn, 'location',       'Required')
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
            if not cl.get('cloud_vm_cluster_id'):  _err(mn, 'cloud_vm_cluster_id', 'Required')
            if not cl.get('location'):             _err(mn, 'location',            'Required')
            if not cl.get('hostname_prefix'):      _err(mn, 'hostname_prefix',     'Required')
            if int(cl.get('cpu_core_count', 0) or 0) < 2:
                _err(mn, 'cpu_core_count', 'Minimum 2')
            if not cl.get('ssh_public_keys'):
                _err(mn, 'ssh_public_keys', 'At least one SSH key required')

    elif tab == 14:  # GCP OCI DB Home / CDB / PDB
        for db in data.get('gcp_oci_databases', []):
            mn = db.get('module_name', 'oci_database')
            if not db.get('vmcluster_ref'): _err(mn, 'vmcluster_ref', 'VM Cluster reference required')
            if not db.get('db_version'):    _err(mn, 'db_version',    'Required')
            if not db.get('db_name'):       _err(mn, 'db_name',       'Required')
