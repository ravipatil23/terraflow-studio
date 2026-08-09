"""GCP contribution to the /api/test self-check run."""
from clouds.gcp.generator import (
    _gcp_net_defaults, _gcp_infra_defaults, _gcp_cluster_defaults,
    _GCP_MOD_NET, _GCP_MOD_INFRA, _GCP_MOD_CLUSTER,
)

#: Keys are the names derive() returns; see clouds/aws/selftest.py.
PAYLOAD_KEYS = {
    'nets': 'gcp_networks', 'infras': 'gcp_infras',
    'clusters': 'gcp_clusters',
}

#: Shared for_each module directories, one set regardless of instance count.
MODULE_DIRS = (_GCP_MOD_NET, _GCP_MOD_INFRA, _GCP_MOD_CLUSTER)


def derive(payload):
    raw_nets     = payload.get('gcp_networks') or []
    raw_infras   = payload.get('gcp_infras') or []
    raw_clusters = payload.get('gcp_clusters') or []

    # Pre-multi-instance configs stored one resource per gcp_module_N key, with
    # the two subnets flattened into the network entry.
    if not raw_nets and payload.get('gcp_module_0'):
        mn = payload.get('gcp_module_names', {})
        d0, d1, d2, d3, d4 = (payload.get(f'gcp_module_{k}', {}) for k in range(5))
        raw_nets = [{**d0,
                     'module_name': mn.get('0', 'gcp_network'),
                     'client_subnet_module': mn.get('1', 'gcp_client_subnet'),
                     'backup_subnet_module': mn.get('2', 'gcp_backup_subnet'),
                     'client_subnet_id': d1.get('odb_subnet_id', ''),
                     'client_cidr': d1.get('cidr_range', ''),
                     'backup_subnet_id': d2.get('odb_subnet_id', ''),
                     'backup_cidr': d2.get('cidr_range', '')}]
        raw_infras   = [{**d3, 'module_name': mn.get('3', 'gcp_infra')}]
        raw_clusters = [{**d4, 'module_name': mn.get('4', 'gcp_cluster')}]

    nets   = [_gcp_net_defaults(n) for n in raw_nets]
    infras = [_gcp_infra_defaults(i) for i in raw_infras]
    return {
        'raw_nets': raw_nets, 'raw_infras': raw_infras,
        'raw_peerings': [], 'raw_clusters': raw_clusters,
        'nets': nets, 'infras': infras, 'peerings': [],
        'clusters': [_gcp_cluster_defaults(c, nets[0] if nets else None,
                                           infras[0] if infras else None)
                     for c in raw_clusters],
    }


def check_inputs(d, t):
    for net in d['raw_nets']:
        mn = net.get('module_name', '?')
        t.check(f'Network "{mn}": odb_network_id present',
                lambda n=net: bool(n.get('odb_network_id')), 'odb_network_id missing')
        t.check(f'Network "{mn}": location present',
                lambda n=net: bool(n.get('location')), 'location missing')
    for inf in d['raw_infras']:
        mn = inf.get('module_name', '?')
        t.check(f'Infra "{mn}": cloud_exadata_infrastructure_id present',
                lambda i=inf: bool(i.get('cloud_exadata_infrastructure_id')),
                'infra id missing')
    for cl in d['raw_clusters']:
        mn = cl.get('module_name', '?')
        t.check(f'Cluster "{mn}": ssh_public_keys not empty',
                lambda c=cl: bool(c.get('ssh_public_keys')), 'No SSH keys')


def module_keys(d):
    return [f'modules/{mod}/{f}'
            for mod in MODULE_DIRS
            for f in ('main.tf', 'variables.tf', 'outputs.tf')]


def check_content(d, files, t):
    root = files.get('main.tf', '')
    tfvars = files.get('terraform.auto.tfvars', '')

    t.check('root main.tf contains GCP provider',
            lambda: 'hashicorp/google' in root, 'hashicorp/google missing')
    t.check('root main.tf uses for_each on GCP networks',
            lambda: 'for_each = var.gcp_odb_networks' in root,
            'for_each on gcp_odb_networks missing')
    t.check('root main.tf uses for_each on GCP clusters',
            lambda: 'for_each = var.gcp_vm_clusters' in root,
            'for_each on gcp_vm_clusters missing')
    t.check('root main.tf exposes client_subnet_name',
            lambda: 'client_subnet_name' in root, 'client_subnet_name missing in root')

    for n in d['nets']:
        mn = n['module_name']
        t.check(f'network "{mn}" entry in tfvars',
                lambda m=mn: f'"{m}"' in tfvars, f'"{mn}" not in tfvars')
    for cl in d['clusters']:
        mn = cl['module_name']
        t.check(f'cluster "{mn}" entry in tfvars',
                lambda m=mn: f'"{m}"' in tfvars, f'"{mn}" not in tfvars')
