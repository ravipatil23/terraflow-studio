"""
AWS ODB tests — self-contained, no GCP or Azure dependencies.
Run with:  python -m unittest tests/test_aws.py
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import (
    app, generate_all,
    mod0_main, mod0_vars, mod0_outputs, mod0_tfvars,
    mod1_main, mod1_vars, mod1_outputs, mod1_tfvars,
    mod2_main, mod2_vars, mod2_outputs, mod2_tfvars,
    mod3_main, mod3_vars, mod3_outputs, mod3_tfvars,
    build_root_main, build_root_tfvars,
    _aws_net_defaults, _aws_infra_defaults, _aws_peer_defaults, _aws_cluster_defaults,
)


# ══════════════════════════════════════════════════════════════════════════════
#  FIXTURES
# ══════════════════════════════════════════════════════════════════════════════

def aws_net(module_name='odb_network', **kw):
    return {
        'module_name': module_name,
        'display_name': 'test-net',
        'availability_zone_id': 'use1-az6',
        'client_subnet_cidr': '10.2.0.0/24',
        'backup_subnet_cidr': '10.2.1.0/24',
        's3_access': True,
        'zero_etl_access': False,
        'tags': {'Env': 'test'},
        **kw,
    }

def aws_infra(module_name='odb_infra', **kw):
    return {
        'module_name': module_name,
        'display_name': 'test-infra',
        'shape': 'Exadata.X11M',
        'availability_zone_id': 'use1-az6',
        'compute_count': 2,
        'storage_count': 3,
        'mw_preference': 'NO_PREFERENCE',
        'mw_patching_mode': 'ROLLING',
        'tags': {},
        **kw,
    }

def aws_peer(module_name='odb_peering', **kw):
    return {
        'module_name': module_name,
        'display_name': 'test-peer',
        'peer_network_id': 'vpc-abc123',
        'network_ref': 'odb_network',
        'tags': {},
        **kw,
    }

def aws_cluster(module_name='odb_cluster', **kw):
    return {
        'module_name': module_name,
        'display_name': 'test-cluster',
        'cpu_core_count': 16,
        'gi_version': '23.0.0.0',
        'hostname_prefix': 'vm',
        'license_model': 'LICENSE_INCLUDED',
        'vm_mode': 'id',
        'infra_ref': 'odb_infra',
        'network_ref': 'odb_network',
        'ssh_public_keys': ['ssh-rsa AAAAB3Nz test@host'],
        'db_servers': [],
        'dco_is_diagnostics_events_enabled': True,
        'dco_is_health_monitoring_enabled': True,
        'dco_is_incident_logs_enabled': True,
        'tags': {},
        **kw,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  ODB Network
# ══════════════════════════════════════════════════════════════════════════════

class TestAwsOdbNetwork(unittest.TestCase):

    def setUp(self):
        self.mn = 'odb_network'
        self.d  = _aws_net_defaults(aws_net(self.mn))

    def test_main_contains_resource(self):
        out = mod0_main(self.mn, self.d)
        self.assertIn('aws_odb_network', out)
        self.assertIn(self.mn, out)

    def test_vars_contains_module_name(self):
        out = mod0_vars(self.mn, self.d)
        self.assertIn('variable', out)
        self.assertIn('display_name', out)

    def test_vars_contains_cidr_variables(self):
        out = mod0_vars(self.mn, self.d)
        self.assertIn('client_subnet_cidr', out)
        self.assertIn('backup_subnet_cidr', out)

    def test_outputs_contains_network_id(self):
        out = mod0_outputs(self.mn)
        self.assertIn('network_id', out)

    def test_tfvars_contains_display_name(self):
        out = mod0_tfvars(self.mn, self.d)
        self.assertIn('test-net', out)

    def test_tfvars_contains_cidr_values(self):
        out = mod0_tfvars(self.mn, self.d)
        self.assertIn('10.2.0.0/24', out)
        self.assertIn('10.2.1.0/24', out)

    def test_tfvars_s3_access_enabled(self):
        out = mod0_tfvars(self.mn, self.d)
        self.assertIn('ENABLED', out)

    def test_tfvars_zero_etl_disabled(self):
        out = mod0_tfvars(self.mn, self.d)
        self.assertIn('DISABLED', out)

    def test_custom_module_name(self):
        mn = 'prod_odb_network'
        d = _aws_net_defaults(aws_net(mn))
        out = mod0_main(mn, d)
        self.assertIn(mn, out)

    def test_tags_rendered_in_vars(self):
        out = mod0_vars(self.mn, self.d)
        self.assertIn('tags', out)


# ══════════════════════════════════════════════════════════════════════════════
#  Exadata Infrastructure
# ══════════════════════════════════════════════════════════════════════════════

class TestAwsExadataInfra(unittest.TestCase):

    def setUp(self):
        self.mn = 'odb_infra'
        self.d  = _aws_infra_defaults(aws_infra(self.mn))

    def test_main_contains_resource(self):
        out = mod1_main(self.mn)
        self.assertIn('aws_odb_cloud_exadata_infrastructure', out)

    def test_vars_contains_shape(self):
        out = mod1_vars(self.mn, self.d)
        self.assertIn('shape', out)

    def test_vars_contains_compute_storage(self):
        out = mod1_vars(self.mn, self.d)
        self.assertIn('compute_count', out)
        self.assertIn('storage_count', out)

    def test_vars_contains_maintenance_window(self):
        out = mod1_vars(self.mn, self.d)
        self.assertIn('maintenance_window', out)

    def test_outputs_contains_infra_id(self):
        out = mod1_outputs(self.mn)
        self.assertIn('infra_id', out)

    def test_tfvars_contains_shape_value(self):
        out = mod1_tfvars(self.mn, self.d)
        self.assertIn('Exadata.X11M', out)

    def test_tfvars_compute_count(self):
        out = mod1_tfvars(self.mn, self.d)
        self.assertIn('2', out)

    def test_custom_preference_no_preference(self):
        d = _aws_infra_defaults(aws_infra(self.mn, mw_preference='NO_PREFERENCE'))
        out = mod1_tfvars(self.mn, d)
        self.assertIn('NO_PREFERENCE', out)

    def test_custom_preference_custom(self):
        d = _aws_infra_defaults(aws_infra(self.mn,
            mw_preference='CUSTOM_PREFERENCE',
            mw_hours_of_day='4,8',
            mw_weeks_of_month='1,3',
        ))
        out = mod1_tfvars(self.mn, d)
        self.assertIn('CUSTOM_PREFERENCE', out)


# ══════════════════════════════════════════════════════════════════════════════
#  Network Peering
# ══════════════════════════════════════════════════════════════════════════════

class TestAwsPeering(unittest.TestCase):

    def setUp(self):
        self.mn  = 'odb_peering'
        self.mn0 = 'odb_network'
        self.d   = _aws_peer_defaults(aws_peer(self.mn), self.mn0)

    def test_main_contains_resource(self):
        out = mod2_main(self.mn)
        self.assertIn('aws_odb_network_peering_connection', out)

    def test_vars_contains_fields(self):
        out = mod2_vars(self.mn, self.d, self.mn0)
        self.assertIn('peer_network_id', out)

    def test_outputs_contains_peering_id(self):
        out = mod2_outputs(self.mn)
        self.assertIn('peering_connection_id', out)

    def test_tfvars_contains_peer_vpc(self):
        out = mod2_tfvars(self.mn, self.d, self.mn0)
        self.assertIn('vpc-abc123', out)

    def test_network_ref_in_root_main(self):
        nets     = [_aws_net_defaults(aws_net(self.mn0))]
        infras   = [_aws_infra_defaults(aws_infra())]
        peerings = [_aws_peer_defaults(aws_peer(self.mn, network_ref=self.mn0), self.mn0)]
        clusters = [_aws_cluster_defaults(aws_cluster())]
        out = build_root_main(nets, infras, peerings, clusters)
        # Refs resolve through the for_each key now, not a per-instance module name.
        self.assertIn('module.aws_odb_network[each.value.network_ref].network_id', out)


# ══════════════════════════════════════════════════════════════════════════════
#  VM Cluster
# ══════════════════════════════════════════════════════════════════════════════

class TestAwsVmCluster(unittest.TestCase):

    def setUp(self):
        self.mn  = 'odb_cluster'
        self.mn0 = 'odb_network'
        self.mn1 = 'odb_infra'
        self.d   = _aws_cluster_defaults(aws_cluster(self.mn), self.mn0, self.mn1)

    def test_main_contains_resource(self):
        out = mod3_main(self.mn)
        self.assertIn('aws_odb_cloud_vm_cluster', out)

    def test_vars_contains_gi_version(self):
        out = mod3_vars(self.mn, self.d, self.mn0, self.mn1)
        self.assertIn('gi_version', out)

    def test_vars_contains_ssh_keys(self):
        out = mod3_vars(self.mn, self.d, self.mn0, self.mn1)
        self.assertIn('ssh_public_keys', out)

    def test_outputs_contains_cluster_id(self):
        out = mod3_outputs(self.mn)
        self.assertIn('vm_cluster_id', out)

    def test_tfvars_contains_cpu_count(self):
        out = mod3_tfvars(self.mn, self.d, self.mn0, self.mn1)
        self.assertIn('16', out)

    def test_tfvars_contains_gi_version(self):
        out = mod3_tfvars(self.mn, self.d, self.mn0, self.mn1)
        self.assertIn('23.0.0.0', out)

    def test_infra_ref_wired_in_root(self):
        nets     = [_aws_net_defaults(aws_net(self.mn0))]
        infras   = [_aws_infra_defaults(aws_infra(self.mn1))]
        peerings = [_aws_peer_defaults(aws_peer())]
        clusters = [_aws_cluster_defaults(aws_cluster(self.mn, infra_ref=self.mn1, network_ref=self.mn0), self.mn0, self.mn1)]
        out = build_root_main(nets, infras, peerings, clusters)
        self.assertIn('module.aws_exadata_infra[each.value.infra_ref].infra_id', out)
        self.assertIn('module.aws_odb_network[each.value.network_ref].network_id', out)

    def test_license_included(self):
        out = mod3_tfvars(self.mn, self.d, self.mn0, self.mn1)
        self.assertIn('LICENSE_INCLUDED', out)

    def test_byol(self):
        d = _aws_cluster_defaults(aws_cluster(self.mn, license_model='BRING_YOUR_OWN_LICENSE'), self.mn0, self.mn1)
        out = mod3_tfvars(self.mn, d, self.mn0, self.mn1)
        self.assertIn('BRING_YOUR_OWN_LICENSE', out)


# ══════════════════════════════════════════════════════════════════════════════
#  AWS Root
# ══════════════════════════════════════════════════════════════════════════════

class TestAwsRoot(unittest.TestCase):

    def _build(self, nets=1, infras=1, peerings=1, clusters=1):
        ns  = [_aws_net_defaults(aws_net(f'net_{i}'))     for i in range(nets)]
        inf = [_aws_infra_defaults(aws_infra(f'inf_{i}')) for i in range(infras)]
        prs = [_aws_peer_defaults(aws_peer(f'peer_{i}', network_ref='net_0'), 'net_0')  for i in range(peerings)]
        cls = [_aws_cluster_defaults(aws_cluster(f'cl_{i}', infra_ref='inf_0', network_ref='net_0'), 'net_0', 'inf_0') for i in range(clusters)]
        return ns, inf, prs, cls

    def test_root_main_contains_provider(self):
        ns, inf, prs, cls = self._build()
        out = build_root_main(ns, inf, prs, cls)
        self.assertIn('hashicorp/aws', out)
        self.assertIn('required_version', out)

    # The root used to emit one module block per instance (module "net_0",
    # "net_1", ...). It now emits one for_each block per resource type, driven by
    # the maps in terraform.auto.tfvars, so instance names live in tfvars and the
    # module names are fixed.

    def test_root_main_has_all_modules(self):
        ns, inf, prs, cls = self._build()
        out = build_root_main(ns, inf, prs, cls)
        for mod in ('aws_odb_network', 'aws_exadata_infra',
                    'aws_peering', 'aws_vm_cluster'):
            self.assertIn(f'module "{mod}"', out)

    def test_root_main_modules_are_for_each_driven(self):
        ns, inf, prs, cls = self._build()
        out = build_root_main(ns, inf, prs, cls)
        for var in ('var.aws_networks', 'var.aws_infras',
                    'var.aws_peerings', 'var.aws_clusters'):
            self.assertIn(f'for_each = {var}', out)

    def test_root_main_shape_is_independent_of_instance_count(self):
        # Adding instances must not change main.tf - that is the whole point of
        # the for_each rewrite. Only terraform.auto.tfvars grows.
        one  = build_root_main(*self._build())
        many = build_root_main(*self._build(nets=3, infras=3, peerings=3, clusters=3))
        self.assertEqual(one, many)

    def test_root_main_emits_each_module_once(self):
        ns, inf, prs, cls = self._build(nets=3, peerings=3, clusters=3)
        out = build_root_main(ns, inf, prs, cls)
        for mod in ('aws_odb_network', 'aws_peering', 'aws_vm_cluster'):
            self.assertEqual(out.count(f'module "{mod}"'), 1, mod)

    def test_root_main_cluster_module_present(self):
        ns, inf, prs, cls = self._build(clusters=3)
        out = build_root_main(ns, inf, prs, cls)
        self.assertIn('module "aws_vm_cluster"', out)
        self.assertIn('for_each = var.aws_clusters', out)

    def test_root_main_outputs(self):
        ns, inf, prs, cls = self._build()
        out = build_root_main(ns, inf, prs, cls)
        self.assertIn('output', out)
        self.assertIn('network_id', out)
        self.assertIn('infra_id', out)

    def test_root_tfvars_contains_region(self):
        ns, inf, prs, cls = self._build()
        out = build_root_tfvars(ns, inf, prs, cls)
        self.assertIn('aws_region', out)

    def test_cluster_depends_on_infra_and_network(self):
        ns, inf, prs, cls = self._build()
        out = build_root_main(ns, inf, prs, cls)
        self.assertIn('depends_on', out)


if __name__ == '__main__':
    unittest.main()
