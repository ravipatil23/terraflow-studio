"""AWS contribution to the /api/test self-check run.

Everything /api/test needs to know about AWS lives here: how to read the payload,
what makes the inputs valid, which module directories the generator produces, and
what the root module should contain. app.py drives the run and knows none of it.
"""
import re

from generators.aws_gen import (
    _aws_net_defaults, _aws_infra_defaults, _aws_peer_defaults, _aws_cluster_defaults,
)

CIDR_RE = re.compile(r'^\d+\.\d+\.\d+\.\d+/\d+$')

#: Payload keys the generator reads, used to rebuild a single-cloud payload.
#: Keys are the names derive() returns, values the payload keys the generator
#: reads. They must line up - a mismatch silently generates from empty input.
PAYLOAD_KEYS = {
    'nets': 'aws_networks', 'infras': 'aws_infras',
    'peerings': 'aws_peerings', 'clusters': 'aws_clusters',
}

#: Shared for_each module directories the root emits, one set regardless of how
#: many instances are configured.
MODULE_DIRS = ('aws-odb-network', 'aws-exadata-infra', 'aws-peering', 'aws-vm-cluster')


def derive(payload):
    """Raw and defaulted resource lists from the posted payload."""
    raw_nets     = payload.get('aws_networks') or []
    raw_infras   = payload.get('aws_infras') or []
    raw_peerings = payload.get('aws_peerings') or []
    raw_clusters = payload.get('aws_clusters') or []

    # Configs saved before the UI supported multiple instances stored one
    # resource per module_N key. Still loadable.
    if not raw_nets and payload.get('module_0'):
        mn = payload.get('module_names', {})
        raw_nets     = [{**payload['module_0'],       'module_name': mn.get('0', 'odb_network')}]
        raw_infras   = [{**payload.get('module_1', {}), 'module_name': mn.get('1', 'odb_exaInfra')}]
        raw_peerings = [{**payload.get('module_2', {}), 'module_name': mn.get('2', 'odb_peering')}]
        raw_clusters = [{**payload.get('module_3', {}), 'module_name': mn.get('3', 'odb_vmcluster')}]

    nets   = [_aws_net_defaults(n) for n in raw_nets]
    infras = [_aws_infra_defaults(i) for i in raw_infras]
    first_net = nets[0]['module_name'] if nets else 'odb_network'
    first_inf = infras[0]['module_name'] if infras else 'odb_exaInfra'
    return {
        'raw_nets': raw_nets, 'raw_infras': raw_infras,
        'raw_peerings': raw_peerings, 'raw_clusters': raw_clusters,
        'nets': nets, 'infras': infras,
        'peerings': [_aws_peer_defaults(p, first_net) for p in raw_peerings],
        'clusters': [_aws_cluster_defaults(c, first_net, first_inf) for c in raw_clusters],
    }


def check_inputs(d, t):
    """Group 1: the posted values are usable before anything is generated."""
    for net in d['raw_nets']:
        mn = net.get('module_name', '?')
        t.check(f'Network "{mn}": display_name present',
                lambda n=net: bool(n.get('display_name')), 'display_name missing')
        t.check(f'Network "{mn}": availability_zone_id present',
                lambda n=net: bool(n.get('availability_zone_id')),
                'availability_zone_id missing')
        for field in ('client_subnet_cidr', 'backup_subnet_cidr'):
            t.check(f'Network "{mn}": {field} valid CIDR',
                    lambda n=net, f=field: bool(CIDR_RE.match(n.get(f, ''))),
                    lambda n=net, f=field: f'Invalid CIDR: {n.get(f)}')
    for inf in d['raw_infras']:
        mn = inf.get('module_name', '?')
        t.check(f'Infra "{mn}": compute_count >= 2',
                lambda i=inf: int(i.get('compute_count', 0) or 0) >= 2,
                lambda i=inf: f'compute_count={i.get("compute_count")} < 2')
        t.check(f'Infra "{mn}": storage_count >= 3',
                lambda i=inf: int(i.get('storage_count', 0) or 0) >= 3,
                lambda i=inf: f'storage_count={i.get("storage_count")} < 3')
    for cl in d['raw_clusters']:
        mn = cl.get('module_name', '?')
        t.check(f'Cluster "{mn}": ssh_public_keys not empty',
                lambda c=cl: bool(c.get('ssh_public_keys')), 'No SSH keys')
        t.check(f'Cluster "{mn}": gi_version present',
                lambda c=cl: bool(c.get('gi_version')), 'gi_version missing')
        t.check(f'Cluster "{mn}": hostname_prefix present',
                lambda c=cl: bool(c.get('hostname_prefix')), 'hostname_prefix missing')


def module_keys(d):
    """Generated file paths that must exist, given these inputs."""
    return [f'modules/{mod}/{f}'
            for mod in MODULE_DIRS
            for f in ('main.tf', 'variables.tf', 'outputs.tf')]


def check_content(d, files, t):
    """Group 3: the generated root wires the modules together correctly."""
    root = files.get('main.tf', '')
    tfvars = files.get('terraform.auto.tfvars', '')

    t.check('root main.tf contains AWS provider',
            lambda: 'hashicorp/aws' in root, 'hashicorp/aws missing')
    t.check('root main.tf uses for_each on aws_networks',
            lambda: 'for_each = var.aws_networks' in root,
            'for_each on aws_networks missing')
    t.check('root main.tf uses for_each on aws_clusters',
            lambda: 'for_each = var.aws_clusters' in root,
            'for_each on aws_clusters missing')
    t.check('root main.tf wires infra_id to vm clusters',
            lambda: 'module.aws_exadata_infra' in root and 'infra_id' in root,
            'module.aws_exadata_infra infra_id missing')

    # Instances live in tfvars now, so that is where each one has to appear.
    for n in d['nets']:
        mn = n['module_name']
        t.check(f'network "{mn}" entry in tfvars',
                lambda m=mn: f'"{m}"' in tfvars, f'"{mn}" not in tfvars')
    for cl in d['clusters']:
        mn = cl['module_name']
        ir, nr = cl.get('infra_ref', ''), cl.get('network_ref', '')
        t.check(f'cluster "{mn}" entry in tfvars',
                lambda m=mn: f'"{m}"' in tfvars, f'"{mn}" not in tfvars')
        if ir:
            t.check(f'Cluster "{mn}" wired to infra "{ir}"',
                    lambda i=ir: f'"{i}"' in tfvars,
                    f'infra_ref "{ir}" missing in tfvars')
        if nr:
            t.check(f'Cluster "{mn}" wired to network "{nr}"',
                    lambda n2=nr: f'"{n2}"' in tfvars,
                    f'network_ref "{nr}" missing in tfvars')
