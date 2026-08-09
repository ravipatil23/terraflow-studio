"""Oracle Database@AWS payload validation.

Rules for the form payload the browser POSTs to /api/validate - required fields,
value ranges, CIDR sanity. Distinct from schema.py, which describes the Terraform
provider's own resource schema and is used by tf_validator.

Owned entirely by this cloud: nothing here is imported by another cloud package,
so a rule change cannot affect GCP or Azure.
"""
import re


def validate(data, errors):
    """Populate `errors` as {{module_name: {{field: message}}}}. Returns nothing."""
    return _validate_aws(data, errors)


def _validate_aws(data, errors):
    def _err(mn, f, m): errors.setdefault(mn, {})[f] = m
    tab = data.get('tab', 0)

    if tab == 0:   # ODB Networks
        for net in data.get('aws_networks', [data.get('module_0', {})]):
            mn = net.get('module_name', 'odb_network')
            # Externally provisioned: nothing is created, so only the ID matters.
            if net.get('is_existing'):
                if not net.get('existing_id'):
                    _err(mn, 'existing_id', 'Required when already provisioned')
                continue
            if not net.get('display_name'):            _err(mn, 'display_name',        'Required')
            if not net.get('availability_zone_id'):    _err(mn, 'availability_zone_id', 'Required')
            if not re.match(r'^\d+\.\d+\.\d+\.\d+/\d+$', net.get('client_subnet_cidr', '')):
                _err(mn, 'client_subnet_cidr', 'Valid CIDR required')
            if not re.match(r'^\d+\.\d+\.\d+\.\d+/\d+$', net.get('backup_subnet_cidr', '')):
                _err(mn, 'backup_subnet_cidr', 'Valid CIDR required')

    elif tab == 1:  # Exadata Infras
        for inf in data.get('aws_infras', [data.get('module_1', {})]):
            mn = inf.get('module_name', 'odb_exaInfra')
            # Externally provisioned: nothing is created, so only the ID matters.
            if inf.get('is_existing'):
                if not inf.get('existing_id'):
                    _err(mn, 'existing_id', 'Required when already provisioned')
                continue
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
