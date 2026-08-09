"""Oracle Database@Azure payload validation.

Rules for the form payload the browser POSTs to /api/validate - required fields,
value ranges, CIDR sanity. Distinct from schema.py, which describes the Terraform
provider's own resource schema and is used by tf_validator.

Owned entirely by this cloud: nothing here is imported by another cloud package,
so a rule change cannot affect AWS or GCP.
"""
import ipaddress
import re


def validate(data, errors):
    """Populate `errors` as {{module_name: {{field: message}}}}. Returns nothing."""
    return _validate_azure(data, errors)


def _validate_azure(data, errors):
    def _err(mn, f, m): errors.setdefault(mn, {})[f] = m
    tab = data.get('tab', 0)

    if tab == 20:  # Azure VNet + Subnet
        for vnet in data.get('azure_vnets', []):
            mn = vnet.get('module_name', 'azure_vnet')
            if not vnet.get('resource_group_name'): _err(mn, 'resource_group_name', 'Required')
            if not vnet.get('location'):             _err(mn, 'location',            'Required')
            if not vnet.get('vnet_name'):            _err(mn, 'vnet_name',           'Required')
            if not re.match(r'^\d+\.\d+\.\d+\.\d+/\d+$', vnet.get('address_space', '')):
                _err(mn, 'address_space', 'Valid CIDR required')
            if not re.match(r'^\d+\.\d+\.\d+\.\d+/\d+$', vnet.get('subnet_address_prefix', '')):
                _err(mn, 'subnet_address_prefix', 'Valid CIDR required')

    elif tab == 21:  # Azure Exadata Infrastructure
        for inf in data.get('azure_infras', []):
            mn = inf.get('module_name', 'azure_exainfra')
            if not inf.get('resource_group_name'): _err(mn, 'resource_group_name', 'Required')
            if not inf.get('location'):             _err(mn, 'location',            'Required')
            if not inf.get('name'):                 _err(mn, 'name',                'Required')
            if not inf.get('display_name'):         _err(mn, 'display_name',        'Required')
            if not inf.get('shape'):                _err(mn, 'shape',               'Required')
            if int(inf.get('compute_count', 0) or 0) < 2: _err(mn, 'compute_count', 'Minimum 2')
            if int(inf.get('storage_count', 0) or 0) < 3: _err(mn, 'storage_count', 'Minimum 3')

    elif tab == 22:  # Azure VM Cluster
        clusters = data.get('azure_clusters', [])
        # Delegated subnet is shared by design — several VM clusters attach to the
        # same one. The backup range is not: Oracle carves it inside the VNet per
        # cluster, so two clusters on one delegated subnet must not collide.
        vnets_by_name = {v.get('module_name'): v for v in data.get('azure_vnets', [])}
        sharing = {}
        for cl in clusters:
            sharing.setdefault(cl.get('vnet_ref'), []).append(cl)
        # Backup ranges are carved inside the VNet, so they can only collide
        # with other clusters on that same VNet.
        claimed = {}   # vnet_ref -> [(module_name, ip_network)] accepted so far

        for cl in clusters:
            mn = cl.get('module_name', 'azure_vmcluster')
            if not cl.get('resource_group_name'): _err(mn, 'resource_group_name', 'Required')
            if not cl.get('location'):             _err(mn, 'location',            'Required')
            if not cl.get('name'):                 _err(mn, 'name',                'Required')
            if not cl.get('display_name'):         _err(mn, 'display_name',        'Required')
            if not cl.get('hostname'):             _err(mn, 'hostname',            'Required')
            if not cl.get('gi_version'):           _err(mn, 'gi_version',          'Required')
            if int(cl.get('cpu_core_count', 0) or 0) < 2:
                _err(mn, 'cpu_core_count', 'Minimum 2')
            if float(cl.get('data_storage_size_in_tbs', 0) or 0) < 2:
                _err(mn, 'data_storage_size_in_tbs', 'Minimum 2 TiB')
            if not cl.get('ssh_public_keys'):
                _err(mn, 'ssh_public_keys', 'At least one SSH key required')

            vnet_ref = cl.get('vnet_ref')
            backup   = (cl.get('backup_subnet_cidr') or '').strip()
            if not backup:
                # Only enforced when the delegated subnet is shared — a lone
                # cluster can let Oracle pick the default backup range.
                if len(sharing.get(vnet_ref, [])) > 1:
                    _err(mn, 'backup_subnet_cidr',
                         'Required when clusters share a delegated subnet - each needs its own range')
                continue
            if not re.match(r'^\d+\.\d+\.\d+\.\d+/\d+$', backup):
                _err(mn, 'backup_subnet_cidr', 'Valid CIDR required')
                continue
            try:
                backup_net = ipaddress.ip_network(backup, strict=False)
            except ValueError:
                _err(mn, 'backup_subnet_cidr', 'Valid CIDR required')
                continue
            delegated = (vnets_by_name.get(vnet_ref) or {}).get('subnet_address_prefix', '')
            if delegated:
                try:
                    if backup_net.overlaps(ipaddress.ip_network(delegated, strict=False)):
                        _err(mn, 'backup_subnet_cidr',
                             f'Overlaps the delegated subnet {delegated}')
                        continue
                except ValueError:
                    pass
            peers = claimed.setdefault(vnet_ref, [])
            clash = next((other for other, net in peers if net.overlaps(backup_net)), None)
            if clash:
                _err(mn, 'backup_subnet_cidr', f'Overlaps the backup subnet of {clash}')
                continue
            peers.append((mn, backup_net))
