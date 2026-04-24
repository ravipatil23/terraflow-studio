"""
Terraflow Studio — Comprehensive Test Suite
Covers: helpers, AWS modules, GCP modules, generate_all, all API routes, store backends.
Run with:  python -m pytest tests/ -v
"""

import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

# ── Make app importable from tests/ directory ─────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent.parent))
import app as app_module
from app import (
    app, generate_all, is_ref, parse_list, tf_bool,
    mod0_main, mod0_vars, mod0_outputs, mod0_tfvars,
    mod1_main, mod1_vars, mod1_outputs, mod1_tfvars,
    mod2_main, mod2_vars, mod2_outputs, mod2_tfvars,
    mod3_main, mod3_vars, mod3_outputs, mod3_tfvars,
    build_root_main, build_root_tfvars,
    gcp0_main, gcp0_vars, gcp0_outputs, gcp0_tfvars,
    gcp_subnet_main, gcp_subnet_vars, gcp_subnet_outputs, gcp_subnet_tfvars,
    gcp2_main, gcp2_vars, gcp2_outputs, gcp2_tfvars,
    gcp1_main, gcp1_vars, gcp1_outputs, gcp1_tfvars,
    gcp_build_root_main, gcp_build_root_tfvars,
    _aws_net_defaults, _aws_infra_defaults, _aws_peer_defaults, _aws_cluster_defaults,
    _gcp_net_defaults, _gcp_infra_defaults, _gcp_cluster_defaults,
)
from store import FileStore, _slug


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

def gcp_net(module_name='gcp_network', **kw):
    return {
        'module_name': module_name,
        'odb_network_id': 'my-odb-net',
        'location': 'us-east4',
        'network': 'projects/my-proj/global/networks/default',
        'project': 'my-proj',
        'gcp_oracle_zone': 'us-east4-b-r1',
        'deletion_protection': True,
        'client_subnet_module': f'{module_name}_client',
        'backup_subnet_module': f'{module_name}_backup',
        'client_subnet_id': 'client-subnet',
        'client_cidr': '10.0.1.0/24',
        'backup_subnet_id': 'backup-subnet',
        'backup_cidr': '10.0.2.0/24',
        'labels': {'env': 'test'},
        **kw,
    }

def gcp_infra(module_name='gcp_infra', **kw):
    return {
        'module_name': module_name,
        'cloud_exadata_infrastructure_id': 'my-infra',
        'display_name': 'My Infra',
        'location': 'us-east4',
        'gcp_oracle_zone': 'us-east4-b-r1',
        'project': 'my-proj',
        'shape': 'Exadata.X9M',
        'compute_count': 2,
        'storage_count': 3,
        'mw_preference': 'NO_PREFERENCE',
        'mw_patching_mode': 'ROLLING',
        **kw,
    }

def gcp_cluster(module_name='gcp_cluster', net_module='gcp_network', infra_module='gcp_infra', **kw):
    net = gcp_net(net_module)
    return {
        'module_name': module_name,
        'exadb_vm_cluster_id': 'my-cluster',
        'display_name': 'My Cluster',
        'location': 'us-east4',
        'gcp_oracle_zone': 'us-east4-b-r1',
        'project': 'my-proj',
        'gi_version': '23.0.0.0',
        'hostname_prefix': 'vm',
        'license_type': 'LICENSE_INCLUDED',
        'node_count': 2,
        'enabled_ecpu_count_per_node': 8,
        'ssh_public_keys': ['ssh-rsa AAAAB3Nz test@host'],
        'network_ref': net_module,
        'client_subnet_ref': net['client_subnet_module'],
        'backup_subnet_ref': net['backup_subnet_module'],
        'infra_ref': infra_module,
        **kw,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  1. HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

class TestHelpers(unittest.TestCase):

    # is_ref
    def test_is_ref_valid_module_ref(self):
        self.assertTrue(is_ref('module.odb_network.network_id'))

    def test_is_ref_valid_data_ref(self):
        self.assertTrue(is_ref('data.aws_odb_db_servers.this.db_servers'))

    def test_is_ref_bare_string(self):
        self.assertFalse(is_ref('vpc-0abc123'))

    def test_is_ref_empty(self):
        self.assertFalse(is_ref(''))

    def test_is_ref_none(self):
        self.assertFalse(is_ref(None))

    def test_is_ref_arn(self):
        self.assertFalse(is_ref('arn:aws:odb:us-east-1:123:network/abc'))

    # parse_list
    def test_parse_list_comma_separated(self):
        self.assertEqual(parse_list('a, b, c'), ['a', 'b', 'c'])

    def test_parse_list_empty_string(self):
        self.assertEqual(parse_list(''), [])

    def test_parse_list_none(self):
        self.assertEqual(parse_list(None), [])

    def test_parse_list_single(self):
        self.assertEqual(parse_list('only'), ['only'])

    def test_parse_list_trims_whitespace(self):
        self.assertEqual(parse_list('  x , y  '), ['x', 'y'])

    # tf_bool
    def test_tf_bool_true(self):
        self.assertEqual(tf_bool(True), 'true')

    def test_tf_bool_false(self):
        self.assertEqual(tf_bool(False), 'false')

    def test_tf_bool_truthy(self):
        self.assertEqual(tf_bool(1), 'true')

    def test_tf_bool_falsy(self):
        self.assertEqual(tf_bool(0), 'false')


# ══════════════════════════════════════════════════════════════════════════════
#  2. AWS MODULE 0 — aws_odb_network
# ══════════════════════════════════════════════════════════════════════════════

class TestAwsOdbNetwork(unittest.TestCase):

    def setUp(self):
        self.mn = 'odb_network'
        self.d  = _aws_net_defaults(aws_net(self.mn))

    def test_main_contains_resource(self):
        out = mod0_main(self.mn)
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
        out = mod0_main(mn)
        self.assertIn(mn, out)

    def test_tags_rendered_in_vars(self):
        out = mod0_vars(self.mn, self.d)
        self.assertIn('tags', out)


# ══════════════════════════════════════════════════════════════════════════════
#  3. AWS MODULE 1 — aws_odb_cloud_exadata_infrastructure
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
#  4. AWS MODULE 2 — aws_odb_network_peering_connection
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
        self.assertIn(f'module.{self.mn0}.network_id', out)


# ══════════════════════════════════════════════════════════════════════════════
#  5. AWS MODULE 3 — aws_odb_cloud_vm_cluster
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
        self.assertIn(f'module.{self.mn1}.infra_id', out)
        self.assertIn(f'module.{self.mn0}.network_id', out)

    def test_license_included(self):
        out = mod3_tfvars(self.mn, self.d, self.mn0, self.mn1)
        self.assertIn('LICENSE_INCLUDED', out)

    def test_byol(self):
        d = _aws_cluster_defaults(aws_cluster(self.mn, license_model='BRING_YOUR_OWN_LICENSE'), self.mn0, self.mn1)
        out = mod3_tfvars(self.mn, d, self.mn0, self.mn1)
        self.assertIn('BRING_YOUR_OWN_LICENSE', out)


# ══════════════════════════════════════════════════════════════════════════════
#  6. AWS ROOT
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

    def test_root_main_has_all_modules(self):
        ns, inf, prs, cls = self._build()
        out = build_root_main(ns, inf, prs, cls)
        self.assertIn('module "net_0"', out)
        self.assertIn('module "inf_0"', out)
        self.assertIn('module "peer_0"', out)
        self.assertIn('module "cl_0"', out)

    def test_root_main_multi_network(self):
        ns, inf, prs, cls = self._build(nets=3)
        out = build_root_main(ns, inf, prs, cls)
        self.assertIn('module "net_0"', out)
        self.assertIn('module "net_1"', out)
        self.assertIn('module "net_2"', out)

    def test_root_main_multi_peering(self):
        ns, inf, prs, cls = self._build(peerings=3)
        out = build_root_main(ns, inf, prs, cls)
        self.assertIn('module "peer_0"', out)
        self.assertIn('module "peer_1"', out)
        self.assertIn('module "peer_2"', out)

    def test_root_main_multi_cluster(self):
        ns, inf, prs, cls = self._build(clusters=3)
        out = build_root_main(ns, inf, prs, cls)
        self.assertIn('module "cl_0"', out)
        self.assertIn('module "cl_2"', out)

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


# ══════════════════════════════════════════════════════════════════════════════
#  7. GCP MODULE 0 — google_oracle_database_odb_network
# ══════════════════════════════════════════════════════════════════════════════

class TestGcpOdbNetwork(unittest.TestCase):

    def setUp(self):
        self.mn = 'gcp_network'
        self.d  = _gcp_net_defaults(gcp_net(self.mn))

    def test_main_contains_resource(self):
        out = gcp0_main(self.mn)
        self.assertIn('google_oracle_database_odb_network', out)

    def test_vars_contains_odb_network_id(self):
        out = gcp0_vars(self.mn, self.d)
        self.assertIn('odb_network_id', out)

    def test_vars_contains_location(self):
        out = gcp0_vars(self.mn, self.d)
        self.assertIn('location', out)

    def test_outputs_contains_odb_network_name(self):
        out = gcp0_outputs(self.mn)
        self.assertIn('odb_network_name', out)

    def test_tfvars_contains_network_id_value(self):
        out = gcp0_tfvars(self.mn, self.d)
        self.assertIn('my-odb-net', out)

    def test_tfvars_contains_location_value(self):
        out = gcp0_tfvars(self.mn, self.d)
        self.assertIn('us-east4', out)

    def test_deletion_protection_true(self):
        out = gcp0_vars(self.mn, self.d)
        self.assertIn('deletion_protection', out)


# ══════════════════════════════════════════════════════════════════════════════
#  8. GCP ODB Subnet
# ══════════════════════════════════════════════════════════════════════════════

class TestGcpOdbSubnet(unittest.TestCase):

    def setUp(self):
        self.mn  = 'gcp_client_subnet'
        self.mn0 = 'gcp_network'
        self.d   = {
            'odb_subnet_id': 'my-client-subnet',
            'location': 'us-east4',
            'cidr_range': '10.0.1.0/24',
            'purpose': 'CLIENT_SUBNET',
            'project': 'my-proj',
            'deletion_protection': True,
        }

    def test_main_contains_resource(self):
        out = gcp_subnet_main(self.mn)
        self.assertIn('google_oracle_database_odb_subnet', out)

    def test_vars_contains_cidr(self):
        out = gcp_subnet_vars(self.mn, self.d, self.mn0)
        self.assertIn('cidr_range', out)

    def test_vars_contains_purpose(self):
        out = gcp_subnet_vars(self.mn, self.d, self.mn0)
        self.assertIn('purpose', out)

    def test_outputs_contains_subnet_name(self):
        out = gcp_subnet_outputs(self.mn)
        self.assertIn('odb_subnet_name', out)

    def test_tfvars_contains_cidr_value(self):
        out = gcp_subnet_tfvars(self.mn, self.d, self.mn0)
        self.assertIn('10.0.1.0/24', out)

    def test_backup_subnet_purpose(self):
        d = {**self.d, 'purpose': 'BACKUP_SUBNET', 'cidr_range': '10.0.2.0/24'}
        out = gcp_subnet_tfvars('gcp_backup_subnet', d, self.mn0)
        self.assertIn('10.0.2.0/24', out)


# ══════════════════════════════════════════════════════════════════════════════
#  9. GCP MODULE 2 — google_oracle_database_cloud_exadata_infrastructure
# ══════════════════════════════════════════════════════════════════════════════

class TestGcpExadataInfra(unittest.TestCase):

    def setUp(self):
        self.mn = 'gcp_infra'
        self.d  = _gcp_infra_defaults(gcp_infra(self.mn))

    def test_main_contains_resource(self):
        out = gcp2_main(self.mn)
        self.assertIn('google_oracle_database_cloud_exadata_infrastructure', out)

    def test_vars_contains_shape(self):
        out = gcp2_vars(self.mn, self.d)
        self.assertIn('shape', out)

    def test_vars_contains_counts(self):
        out = gcp2_vars(self.mn, self.d)
        self.assertIn('compute_count', out)
        self.assertIn('storage_count', out)

    def test_outputs_contains_infra_name(self):
        out = gcp2_outputs(self.mn)
        self.assertIn('infra_name', out)

    def test_tfvars_contains_infra_id(self):
        out = gcp2_tfvars(self.mn, self.d)
        self.assertIn('my-infra', out)

    def test_tfvars_contains_shape_value(self):
        out = gcp2_tfvars(self.mn, self.d)
        self.assertIn('Exadata.X9M', out)


# ══════════════════════════════════════════════════════════════════════════════
#  10. GCP MODULE 1 — google_oracle_database_exadb_vm_cluster
# ══════════════════════════════════════════════════════════════════════════════

class TestGcpVmCluster(unittest.TestCase):

    def setUp(self):
        self.mn   = 'gcp_cluster'
        self.mn0  = 'gcp_network'
        self.mn1  = f'{self.mn0}_client'
        self.mn2  = f'{self.mn0}_backup'
        self.mn3  = 'gcp_infra'
        self.net  = _gcp_net_defaults(gcp_net(self.mn0))
        self.d    = _gcp_cluster_defaults(gcp_cluster(self.mn, self.mn0, self.mn3), self.net)

    def test_main_contains_resource(self):
        out = gcp1_main(self.mn)
        self.assertIn('google_oracle_database_exadb_vm_cluster', out)

    def test_vars_contains_gi_version(self):
        out = gcp1_vars(self.mn, self.d, self.mn0, self.mn1, self.mn2, self.mn3)
        self.assertIn('gi_version', out)

    def test_vars_contains_node_count(self):
        out = gcp1_vars(self.mn, self.d, self.mn0, self.mn1, self.mn2, self.mn3)
        self.assertIn('node_count', out)

    def test_vars_contains_ecpu(self):
        out = gcp1_vars(self.mn, self.d, self.mn0, self.mn1, self.mn2, self.mn3)
        self.assertIn('enabled_ecpu_count_per_node', out)

    def test_outputs_contains_cluster_name(self):
        out = gcp1_outputs(self.mn)
        self.assertIn('vm_cluster_name', out)

    def test_tfvars_contains_cluster_id(self):
        out = gcp1_tfvars(self.mn, self.d, self.mn0, self.mn1, self.mn2, self.mn3)
        self.assertIn('my-cluster', out)

    def test_tfvars_contains_gi_version(self):
        out = gcp1_tfvars(self.mn, self.d, self.mn0, self.mn1, self.mn2, self.mn3)
        self.assertIn('23.0.0.0', out)


# ══════════════════════════════════════════════════════════════════════════════
#  11. GCP ROOT
# ══════════════════════════════════════════════════════════════════════════════

class TestGcpRoot(unittest.TestCase):

    def _build(self, net_count=1, infra_count=1, cluster_count=1):
        nets     = [_gcp_net_defaults(gcp_net(f'gnet_{i}')) for i in range(net_count)]
        infras   = [_gcp_infra_defaults(gcp_infra(f'ginf_{i}')) for i in range(infra_count)]
        clusters = [_gcp_cluster_defaults(gcp_cluster(f'gcl_{i}', 'gnet_0', 'ginf_0'), nets[0]) for i in range(cluster_count)]
        return nets, infras, clusters

    def test_root_main_contains_provider(self):
        ns, inf, cls = self._build()
        out = gcp_build_root_main(ns, inf, cls)
        self.assertIn('hashicorp/google', out)

    def test_root_main_has_network_module(self):
        ns, inf, cls = self._build()
        out = gcp_build_root_main(ns, inf, cls)
        self.assertIn('module "gnet_0"', out)

    def test_root_main_has_subnet_modules(self):
        ns, inf, cls = self._build()
        out = gcp_build_root_main(ns, inf, cls)
        net = _gcp_net_defaults(gcp_net('gnet_0'))
        self.assertIn(f'module "{net["client_subnet_module"]}"', out)
        self.assertIn(f'module "{net["backup_subnet_module"]}"', out)

    def test_root_main_has_infra_module(self):
        ns, inf, cls = self._build()
        out = gcp_build_root_main(ns, inf, cls)
        self.assertIn('module "ginf_0"', out)

    def test_root_main_has_cluster_module(self):
        ns, inf, cls = self._build()
        out = gcp_build_root_main(ns, inf, cls)
        self.assertIn('module "gcl_0"', out)

    def test_root_main_cluster_references_subnet(self):
        ns, inf, cls = self._build()
        out = gcp_build_root_main(ns, inf, cls)
        self.assertIn('odb_subnet_name', out)

    def test_root_main_multi_network(self):
        ns, inf, cls = self._build(net_count=2)
        out = gcp_build_root_main(ns, inf, cls)
        self.assertIn('module "gnet_0"', out)
        self.assertIn('module "gnet_1"', out)

    def test_root_main_multi_cluster(self):
        ns, inf, cls = self._build(cluster_count=2)
        out = gcp_build_root_main(ns, inf, cls)
        self.assertIn('module "gcl_0"', out)
        self.assertIn('module "gcl_1"', out)

    def test_root_tfvars_contains_project(self):
        ns, inf, cls = self._build()
        out = gcp_build_root_tfvars(ns, inf, cls)
        self.assertIn('gcp_project', out)

    def test_root_tfvars_contains_region(self):
        ns, inf, cls = self._build()
        out = gcp_build_root_tfvars(ns, inf, cls)
        self.assertIn('gcp_region', out)


# ══════════════════════════════════════════════════════════════════════════════
#  12. generate_all — multi-instance
# ══════════════════════════════════════════════════════════════════════════════

class TestGenerateAll(unittest.TestCase):

    # ── AWS single-instance backward-compat ──────────────────────────────────
    def test_aws_single_backward_compat(self):
        files = generate_all({
            'cloud': 'aws',
            'module_names': {'0': 'net', '1': 'inf', '2': 'peer', '3': 'cl'},
            'module_0': aws_net('net'),
            'module_1': aws_infra('inf'),
            'module_2': aws_peer('peer'),
            'module_3': {**aws_cluster('cl'), 'vm_mode': 'id',
                         'cloud_exadata_infrastructure_id': '',
                         'odb_network_id': ''},
        })
        self.assertEqual(len(files), 18)
        self.assertIn('main.tf', files)
        self.assertIn('modules/net/main.tf', files)

    # ── AWS multi-instance ────────────────────────────────────────────────────
    def test_aws_multi_two_networks(self):
        files = generate_all({
            'cloud': 'aws',
            'aws_networks':  [aws_net('n1'), aws_net('n2')],
            'aws_infras':    [aws_infra('i1')],
            'aws_peerings':  [aws_peer('p1', network_ref='n1')],
            'aws_clusters':  [aws_cluster('c1', infra_ref='i1', network_ref='n1')],
        })
        # 2 nets + 1 infra + 1 peer + 1 cluster = 5 modules × 4 files + 2 root = 22
        self.assertEqual(len(files), 22)
        self.assertIn('modules/n1/main.tf', files)
        self.assertIn('modules/n2/main.tf', files)

    def test_aws_multi_two_infras(self):
        files = generate_all({
            'cloud': 'aws',
            'aws_networks':  [aws_net('n1')],
            'aws_infras':    [aws_infra('i1'), aws_infra('i2')],
            'aws_peerings':  [aws_peer('p1', network_ref='n1')],
            'aws_clusters':  [aws_cluster('c1', infra_ref='i1', network_ref='n1')],
        })
        self.assertIn('modules/i1/main.tf', files)
        self.assertIn('modules/i2/main.tf', files)

    def test_aws_multi_two_peerings(self):
        files = generate_all({
            'cloud': 'aws',
            'aws_networks':  [aws_net('n1'), aws_net('n2')],
            'aws_infras':    [aws_infra('i1')],
            'aws_peerings':  [aws_peer('p1', network_ref='n1'), aws_peer('p2', network_ref='n2')],
            'aws_clusters':  [aws_cluster('c1', infra_ref='i1', network_ref='n1')],
        })
        root = files['main.tf']
        self.assertIn('module "p1"', root)
        self.assertIn('module "p2"', root)
        self.assertIn('module.n1.network_id', root)
        self.assertIn('module.n2.network_id', root)

    def test_aws_multi_two_clusters(self):
        files = generate_all({
            'cloud': 'aws',
            'aws_networks':  [aws_net('n1')],
            'aws_infras':    [aws_infra('i1')],
            'aws_peerings':  [aws_peer('p1', network_ref='n1')],
            'aws_clusters':  [
                aws_cluster('c1', infra_ref='i1', network_ref='n1'),
                aws_cluster('c2', infra_ref='i1', network_ref='n1'),
            ],
        })
        root = files['main.tf']
        self.assertIn('module "c1"', root)
        self.assertIn('module "c2"', root)

    def test_aws_cluster_cross_wired_to_correct_infra(self):
        files = generate_all({
            'cloud': 'aws',
            'aws_networks':  [aws_net('n1'), aws_net('n2')],
            'aws_infras':    [aws_infra('i_prod'), aws_infra('i_dev')],
            'aws_peerings':  [aws_peer('p1', network_ref='n1')],
            'aws_clusters':  [
                aws_cluster('c_prod', infra_ref='i_prod', network_ref='n1'),
                aws_cluster('c_dev',  infra_ref='i_dev',  network_ref='n2'),
            ],
        })
        root = files['main.tf']
        self.assertIn('module.i_prod.infra_id', root)
        self.assertIn('module.i_dev.infra_id', root)
        self.assertIn('module.n2.network_id', root)

    # ── GCP single-instance backward-compat ──────────────────────────────────
    def test_gcp_single_backward_compat(self):
        files = generate_all({
            'cloud': 'gcp',
            'gcp_module_names': {'0': 'gnet', '1': 'csub', '2': 'bsub', '3': 'ginf', '4': 'gcl'},
            'gcp_module_0': gcp_net('gnet'),
            'gcp_module_1': {'odb_subnet_id': 'csub', 'location': 'us-east4', 'cidr_range': '10.0.1.0/24', 'purpose': 'CLIENT_SUBNET'},
            'gcp_module_2': {'odb_subnet_id': 'bsub', 'location': 'us-east4', 'cidr_range': '10.0.2.0/24', 'purpose': 'BACKUP_SUBNET'},
            'gcp_module_3': gcp_infra('ginf'),
            'gcp_module_4': {**gcp_cluster('gcl', 'gnet', 'ginf'), 'odb_network': '', 'odb_subnet': '', 'backup_odb_subnet': '', 'exadata_infrastructure': ''},
        })
        self.assertEqual(len(files), 22)
        self.assertIn('main.tf', files)

    # ── GCP multi-instance ────────────────────────────────────────────────────
    def test_gcp_multi_two_networks(self):
        n1 = gcp_net('gnet1')
        n2 = gcp_net('gnet2')
        files = generate_all({
            'cloud': 'gcp',
            'gcp_networks': [n1, n2],
            'gcp_infras':   [gcp_infra('ginf1')],
            'gcp_clusters': [gcp_cluster('gcl1', 'gnet1', 'ginf1')],
        })
        # 2 nets × 3 (net+client+backup) + 1 infra + 1 cluster = 8 modules × 4 + 2 = 34
        self.assertEqual(len(files), 34)

    def test_gcp_multi_cluster_cross_wired(self):
        n1 = _gcp_net_defaults(gcp_net('gnet1'))
        n2 = _gcp_net_defaults(gcp_net('gnet2'))
        files = generate_all({
            'cloud': 'gcp',
            'gcp_networks': [n1, n2],
            'gcp_infras':   [gcp_infra('ginf1')],
            'gcp_clusters': [
                gcp_cluster('gcl_prod', 'gnet1', 'ginf1'),
                gcp_cluster('gcl_dev',  'gnet2', 'ginf1'),
            ],
        })
        root = files['main.tf']
        self.assertIn(f'module.{n1["client_subnet_module"]}.odb_subnet_name', root)
        self.assertIn(f'module.{n2["client_subnet_module"]}.odb_subnet_name', root)

    # ── File content quality checks ───────────────────────────────────────────
    def test_all_files_are_non_empty(self):
        files = generate_all({
            'cloud': 'aws',
            'aws_networks':  [aws_net('n1')],
            'aws_infras':    [aws_infra('i1')],
            'aws_peerings':  [aws_peer('p1', network_ref='n1')],
            'aws_clusters':  [aws_cluster('c1', infra_ref='i1', network_ref='n1')],
        })
        for path, content in files.items():
            self.assertGreater(len(content.strip()), 0, f'{path} is empty')

    def test_all_tf_files_have_valid_structure(self):
        files = generate_all({
            'cloud': 'aws',
            'aws_networks':  [aws_net('n1')],
            'aws_infras':    [aws_infra('i1')],
            'aws_peerings':  [aws_peer('p1', network_ref='n1')],
            'aws_clusters':  [aws_cluster('c1', infra_ref='i1', network_ref='n1')],
        })
        for path, content in files.items():
            if path.endswith('.tf'):
                self.assertIn('{', content, f'{path} missing opening brace')


# ══════════════════════════════════════════════════════════════════════════════
#  13. DEFAULT NORMALISER FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

class TestDefaultNormalisers(unittest.TestCase):

    def test_aws_net_defaults_s3_enabled(self):
        d = _aws_net_defaults({'s3_access': True})
        self.assertEqual(d['s3_access'], 'ENABLED')

    def test_aws_net_defaults_s3_disabled(self):
        d = _aws_net_defaults({'s3_access': False})
        self.assertEqual(d['s3_access'], 'DISABLED')

    def test_aws_infra_defaults_compute_int(self):
        d = _aws_infra_defaults({'compute_count': '4', 'storage_count': '5'})
        self.assertEqual(d['compute_count'], 4)
        self.assertEqual(d['storage_count'], 5)

    def test_aws_infra_defaults_fallback(self):
        d = _aws_infra_defaults({})
        self.assertEqual(d['compute_count'], 2)
        self.assertEqual(d['storage_count'], 3)

    def test_aws_peer_defaults_network_ref(self):
        d = _aws_peer_defaults({}, 'my_network')
        self.assertEqual(d['network_ref'], 'my_network')

    def test_aws_cluster_defaults_refs(self):
        d = _aws_cluster_defaults({}, 'my_net', 'my_inf')
        self.assertEqual(d['network_ref'], 'my_net')
        self.assertEqual(d['infra_ref'], 'my_inf')

    def test_gcp_net_defaults_auto_subnet_modules(self):
        d = _gcp_net_defaults({'module_name': 'mynet'})
        self.assertIn('mynet', d['client_subnet_module'])
        self.assertIn('mynet', d['backup_subnet_module'])

    def test_gcp_infra_defaults_shape_fallback(self):
        d = _gcp_infra_defaults({})
        self.assertEqual(d['shape'], 'Exadata.X9M')

    def test_gcp_cluster_defaults_auto_subnet_refs(self):
        first_net = _gcp_net_defaults({'module_name': 'net1'})
        d = _gcp_cluster_defaults({}, first_net=first_net)
        self.assertEqual(d['network_ref'], 'net1')
        self.assertIn('net1', d['client_subnet_ref'])
        self.assertIn('net1', d['backup_subnet_ref'])


# ══════════════════════════════════════════════════════════════════════════════
#  14. API ROUTES
# ══════════════════════════════════════════════════════════════════════════════

class TestApiRoutes(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
        self.base_aws = {
            'cloud': 'aws',
            'aws_networks':  [aws_net('n1')],
            'aws_infras':    [aws_infra('i1')],
            'aws_peerings':  [aws_peer('p1', network_ref='n1')],
            'aws_clusters':  [aws_cluster('c1', infra_ref='i1', network_ref='n1')],
        }
        self.base_gcp = {
            'cloud': 'gcp',
            'gcp_networks':  [gcp_net('gnet1')],
            'gcp_infras':    [gcp_infra('ginf1')],
            'gcp_clusters':  [gcp_cluster('gcl1', 'gnet1', 'ginf1')],
        }

    # GET /
    def test_index_returns_200(self):
        r = self.client.get('/')
        self.assertEqual(r.status_code, 200)

    def test_index_contains_html(self):
        r = self.client.get('/')
        self.assertIn(b'Terraflow', r.data)

    def test_index_no_cache_header(self):
        r = self.client.get('/')
        self.assertIn('no-cache', r.headers.get('Cache-Control', ''))

    def test_index_contains_version(self):
        r = self.client.get('/')
        self.assertIn(b'v5', r.data)

    # POST /api/generate — AWS
    def test_generate_aws_root_main(self):
        r = self.client.post('/api/generate',
            json={**self.base_aws, 'file_key': 'main.tf'},
            content_type='application/json')
        self.assertEqual(r.status_code, 200)
        d = r.get_json()
        self.assertIn('content', d)
        self.assertIn('module "n1"', d['content'])

    def test_generate_aws_root_tfvars(self):
        r = self.client.post('/api/generate',
            json={**self.base_aws, 'file_key': 'terraform.tfvars'},
            content_type='application/json')
        d = r.get_json()
        self.assertIn('content', d)
        self.assertIn('aws_region', d['content'])

    def test_generate_aws_module_main(self):
        r = self.client.post('/api/generate',
            json={**self.base_aws, 'file_key': 'modules/n1/main.tf'},
            content_type='application/json')
        d = r.get_json()
        self.assertIn('content', d)
        self.assertIn('aws_odb_network', d['content'])

    def test_generate_aws_module_variables(self):
        r = self.client.post('/api/generate',
            json={**self.base_aws, 'file_key': 'modules/n1/variables.tf'},
            content_type='application/json')
        d = r.get_json()
        self.assertIn('variable', d['content'])

    def test_generate_aws_module_outputs(self):
        r = self.client.post('/api/generate',
            json={**self.base_aws, 'file_key': 'modules/n1/outputs.tf'},
            content_type='application/json')
        d = r.get_json()
        self.assertIn('output', d['content'])

    def test_generate_aws_infra_module(self):
        r = self.client.post('/api/generate',
            json={**self.base_aws, 'file_key': 'modules/i1/main.tf'},
            content_type='application/json')
        d = r.get_json()
        self.assertIn('aws_odb_cloud_exadata_infrastructure', d['content'])

    def test_generate_aws_peering_module(self):
        r = self.client.post('/api/generate',
            json={**self.base_aws, 'file_key': 'modules/p1/main.tf'},
            content_type='application/json')
        d = r.get_json()
        self.assertIn('aws_odb_network_peering_connection', d['content'])

    def test_generate_aws_cluster_module(self):
        r = self.client.post('/api/generate',
            json={**self.base_aws, 'file_key': 'modules/c1/main.tf'},
            content_type='application/json')
        d = r.get_json()
        self.assertIn('aws_odb_cloud_vm_cluster', d['content'])

    def test_generate_unknown_file_key_returns_error(self):
        r = self.client.post('/api/generate',
            json={**self.base_aws, 'file_key': 'modules/nonexistent/main.tf'},
            content_type='application/json')
        d = r.get_json()
        self.assertIn('error', d)

    # POST /api/generate — GCP
    def test_generate_gcp_root_main(self):
        r = self.client.post('/api/generate',
            json={**self.base_gcp, 'file_key': 'main.tf'},
            content_type='application/json')
        d = r.get_json()
        self.assertIn('content', d)
        self.assertIn('module "gnet1"', d['content'])

    def test_generate_gcp_network_module(self):
        r = self.client.post('/api/generate',
            json={**self.base_gcp, 'file_key': 'modules/gnet1/main.tf'},
            content_type='application/json')
        d = r.get_json()
        self.assertIn('google_oracle_database_odb_network', d['content'])

    def test_generate_gcp_infra_module(self):
        r = self.client.post('/api/generate',
            json={**self.base_gcp, 'file_key': 'modules/ginf1/main.tf'},
            content_type='application/json')
        d = r.get_json()
        self.assertIn('google_oracle_database_cloud_exadata_infrastructure', d['content'])

    def test_generate_gcp_cluster_module(self):
        r = self.client.post('/api/generate',
            json={**self.base_gcp, 'file_key': 'modules/gcl1/main.tf'},
            content_type='application/json')
        d = r.get_json()
        self.assertIn('google_oracle_database_exadb_vm_cluster', d['content'])

    # POST /api/download
    def test_download_aws_returns_zip(self):
        r = self.client.post('/api/download',
            json=self.base_aws,
            content_type='application/json')
        self.assertEqual(r.status_code, 200)
        self.assertIn('zip', r.content_type)
        self.assertTrue(r.data[:4] == b'PK\x03\x04')  # ZIP magic bytes

    def test_download_gcp_returns_zip(self):
        r = self.client.post('/api/download',
            json=self.base_gcp,
            content_type='application/json')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data[:4] == b'PK\x03\x04')

    # POST /api/validate — AWS passing
    def test_validate_aws_tab0_pass(self):
        r = self.client.post('/api/validate', json={
            'tab': 0,
            'module_0': {
                'display_name': 'my-net',
                'availability_zone_id': 'use1-az6',
                'client_subnet_cidr': '10.0.0.0/24',
                'backup_subnet_cidr': '10.0.1.0/24',
            },
        })
        d = r.get_json()
        self.assertTrue(d['valid'])

    def test_validate_aws_tab0_missing_fields(self):
        r = self.client.post('/api/validate', json={'tab': 0, 'module_0': {}})
        d = r.get_json()
        self.assertFalse(d['valid'])
        self.assertIn('display_name', d['errors'])
        self.assertIn('availability_zone_id', d['errors'])

    def test_validate_aws_tab0_bad_cidr(self):
        r = self.client.post('/api/validate', json={
            'tab': 0,
            'module_0': {
                'display_name': 'n', 'availability_zone_id': 'use1-az6',
                'client_subnet_cidr': 'not-a-cidr',
                'backup_subnet_cidr': '10.0.0.0/24',
            },
        })
        d = r.get_json()
        self.assertFalse(d['valid'])
        self.assertIn('client_subnet_cidr', d['errors'])

    def test_validate_aws_tab1_pass(self):
        r = self.client.post('/api/validate', json={
            'tab': 1,
            'module_1': {
                'display_name': 'inf', 'shape': 'Exadata.X11M',
                'availability_zone_id': 'use1-az6',
                'compute_count': 2, 'storage_count': 3,
            },
        })
        d = r.get_json()
        self.assertTrue(d['valid'])

    def test_validate_aws_tab1_low_compute(self):
        r = self.client.post('/api/validate', json={
            'tab': 1,
            'module_1': {
                'display_name': 'i', 'shape': 'Exadata.X11M',
                'availability_zone_id': 'use1-az6',
                'compute_count': 1, 'storage_count': 3,
            },
        })
        d = r.get_json()
        self.assertFalse(d['valid'])
        self.assertIn('compute_count', d['errors'])

    def test_validate_aws_tab2_pass(self):
        r = self.client.post('/api/validate', json={
            'tab': 2,
            'module_2': {
                'display_name': 'p', 'odb_network_id': 'mod.n.id',
                'peer_network_id': 'vpc-abc',
            },
        })
        d = r.get_json()
        self.assertTrue(d['valid'])

    def test_validate_aws_tab3_pass(self):
        r = self.client.post('/api/validate', json={
            'tab': 3,
            'module_3': {
                'display_name': 'c', 'cpu_core_count': 16,
                'gi_version': '23.0.0.0', 'hostname_prefix': 'vm',
                'vm_mode': 'id',
                'cloud_exadata_infrastructure_id': 'mod.i.id',
                'odb_network_id': 'mod.n.id',
                'ssh_public_keys': ['ssh-rsa AAA'],
            },
        })
        d = r.get_json()
        self.assertTrue(d['valid'])

    def test_validate_aws_tab3_no_ssh_key(self):
        r = self.client.post('/api/validate', json={
            'tab': 3,
            'module_3': {
                'display_name': 'c', 'cpu_core_count': 16,
                'gi_version': '23.0.0.0', 'hostname_prefix': 'vm',
                'vm_mode': 'id',
                'cloud_exadata_infrastructure_id': 'x', 'odb_network_id': 'y',
                'ssh_public_keys': [],
            },
        })
        d = r.get_json()
        self.assertFalse(d['valid'])
        self.assertIn('ssh_public_keys', d['errors'])

    # POST /api/validate — GCP
    def test_validate_gcp_tab10_pass(self):
        r = self.client.post('/api/validate', json={
            'tab': 10,
            'gcp_networks': [{
                'module_name': 'gcp_network', 'odb_network_id': 'my-net',
                'location': 'us-east4', 'network': 'projects/p/global/networks/n',
                'client_cidr': '10.0.1.0/24', 'backup_cidr': '10.0.2.0/24',
            }],
        })
        d = r.get_json()
        self.assertTrue(d['valid'])

    def test_validate_gcp_tab10_missing(self):
        r = self.client.post('/api/validate', json={'tab': 10, 'gcp_networks': [{'module_name':'gnet'}]})
        d = r.get_json()
        self.assertFalse(d['valid'])
        self.assertIn('odb_network_id', d['errors'])
        self.assertIn('location', d['errors'])
        self.assertIn('network', d['errors'])

    def test_validate_gcp_tab12_pass(self):
        r = self.client.post('/api/validate', json={
            'tab': 12,
            'gcp_module_3': {
                'cloud_exadata_infrastructure_id': 'inf', 'location': 'us-east4',
                'shape': 'Exadata.X9M', 'compute_count': 2, 'storage_count': 3,
            },
        })
        d = r.get_json()
        self.assertTrue(d['valid'])

    def test_validate_gcp_tab12_low_storage(self):
        r = self.client.post('/api/validate', json={
            'tab': 12,
            'gcp_module_3': {
                'cloud_exadata_infrastructure_id': 'i', 'location': 'us-east4',
                'shape': 'Exadata.X9M', 'compute_count': 2, 'storage_count': 2,
            },
        })
        d = r.get_json()
        self.assertFalse(d['valid'])
        self.assertIn('storage_count', d['errors'])

    # GET /api/config/backend
    def test_config_backend(self):
        r = self.client.get('/api/config/backend')
        self.assertEqual(r.status_code, 200)
        d = r.get_json()
        self.assertIn('backend', d)

    # GET /api/config/list
    def test_config_list(self):
        r = self.client.get('/api/config/list')
        self.assertEqual(r.status_code, 200)
        self.assertIsInstance(r.get_json(), list)


# ══════════════════════════════════════════════════════════════════════════════
#  15. FILESTORE (mocked filesystem)
# ══════════════════════════════════════════════════════════════════════════════

class TestFileStore(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store = FileStore()
        # Patch DATA_DIR to use temp dir
        import store as store_mod
        self._orig_data_dir = store_mod.DATA_DIR
        store_mod.DATA_DIR = Path(self.tmpdir)
        self.store_mod = store_mod

    def tearDown(self):
        self.store_mod.DATA_DIR = self._orig_data_dir
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_slug_alphanumeric(self):
        self.assertEqual(_slug('MyCustomer'), 'mycustomer')

    def test_slug_spaces_become_dashes(self):
        self.assertEqual(_slug('Acme Corp'), 'acme-corp')

    def test_slug_special_chars_removed(self):
        self.assertEqual(_slug('test@company.com'), 'test-company-com')

    def test_slug_empty_fallback(self):
        self.assertEqual(_slug(''), 'unnamed')

    def test_save_creates_file(self):
        self.store_mod.DATA_DIR.mkdir(parents=True, exist_ok=True)
        result = self.store.save('Acme', 'aws', {'cloud': 'aws', 'aws_networks': []})
        self.assertTrue(result['ok'])
        p = Path(self.tmpdir) / 'acme' / 'aws.json'
        self.assertTrue(p.exists())

    def test_save_and_load_roundtrip(self):
        self.store_mod.DATA_DIR.mkdir(parents=True, exist_ok=True)
        payload = {'cloud': 'aws', 'aws_networks': [{'module_name': 'n1'}]}
        self.store.save('TestCo', 'aws', payload)
        doc = self.store.load('TestCo', 'aws')
        self.assertIsNotNone(doc)
        self.assertEqual(doc['customer'], 'TestCo')
        self.assertEqual(doc['cloud'], 'aws')

    def test_load_nonexistent_returns_none(self):
        result = self.store.load('NonExistent', 'aws')
        self.assertIsNone(result)

    def test_list_customers_empty(self):
        result = self.store.list_customers()
        self.assertIsInstance(result, list)

    def test_list_customers_after_save(self):
        self.store_mod.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.store.save('Acme', 'aws', {'cloud': 'aws'})
        self.store.save('Beta', 'gcp', {'cloud': 'gcp'})
        result = self.store.list_customers()
        slugs = [r['slug'] for r in result]
        self.assertIn('acme', slugs)
        self.assertIn('beta', slugs)

    def test_delete_removes_file(self):
        self.store_mod.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.store.save('DelCo', 'aws', {'cloud': 'aws'})
        deleted = self.store.delete('DelCo', 'aws')
        self.assertTrue(deleted)
        self.assertIsNone(self.store.load('DelCo', 'aws'))

    def test_delete_nonexistent_returns_false(self):
        result = self.store.delete('Nobody', 'aws')
        self.assertFalse(result)

    def test_save_overwrites_existing(self):
        self.store_mod.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.store.save('Acme', 'aws', {'cloud': 'aws', 'version': 1})
        self.store.save('Acme', 'aws', {'cloud': 'aws', 'version': 2})
        doc = self.store.load('Acme', 'aws')
        self.assertEqual(doc.get('version'), 2)

    def test_backend_name(self):
        self.assertIn('file:', self.store.backend_name)

    def test_multiple_clouds_same_customer(self):
        self.store_mod.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.store.save('Multi', 'aws', {'cloud': 'aws'})
        self.store.save('Multi', 'gcp', {'cloud': 'gcp'})
        customers = self.store.list_customers()
        multi = next((c for c in customers if c['slug'] == 'multi'), None)
        self.assertIsNotNone(multi)
        self.assertIn('aws', multi['clouds'])
        self.assertIn('gcp', multi['clouds'])


# ══════════════════════════════════════════════════════════════════════════════
#  16. CONFIG API ROUTES (mocked store)
# ══════════════════════════════════════════════════════════════════════════════

class TestConfigApiRoutes(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
        # Create a mock storage backend
        self.mock_store = MagicMock()
        self.mock_store.backend_name = 'file:mock'
        self.patcher = patch.object(app_module, 'storage', self.mock_store)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def test_config_save_success(self):
        self.mock_store.save.return_value = {'ok': True, 'id': 'acme/aws'}
        r = self.client.post('/api/config/save', json={
            'customer': 'Acme', 'cloud': 'aws',
            'aws_networks': [{'module_name': 'n1'}],
        })
        self.assertEqual(r.status_code, 200)
        d = r.get_json()
        self.assertTrue(d.get('ok'))
        self.mock_store.save.assert_called_once()

    def test_config_save_missing_customer(self):
        r = self.client.post('/api/config/save', json={'cloud': 'aws'})
        self.assertEqual(r.status_code, 400)

    def test_config_save_missing_cloud_defaults_to_aws(self):
        self.mock_store.save.return_value = {'ok': True, 'id': 'acme/aws'}
        r = self.client.post('/api/config/save', json={'customer': 'Acme'})
        self.assertEqual(r.status_code, 200)
        # cloud defaults to 'aws' if not provided
        call_args = self.mock_store.save.call_args
        self.assertEqual(call_args[0][1], 'aws')

    def test_config_load_found(self):
        self.mock_store.load.return_value = {
            'customer': 'Acme', 'cloud': 'aws', 'aws_networks': []
        }
        r = self.client.get('/api/config/load/acme/aws')
        self.assertEqual(r.status_code, 200)
        d = r.get_json()
        self.assertEqual(d['customer'], 'Acme')

    def test_config_load_not_found(self):
        self.mock_store.load.return_value = None
        r = self.client.get('/api/config/load/nobody/aws')
        self.assertEqual(r.status_code, 404)

    def test_config_list_success(self):
        self.mock_store.list_customers.return_value = [
            {'customer': 'Acme', 'slug': 'acme', 'clouds': ['aws']},
            {'customer': 'Beta', 'slug': 'beta', 'clouds': ['gcp']},
        ]
        r = self.client.get('/api/config/list')
        self.assertEqual(r.status_code, 200)
        d = r.get_json()
        self.assertEqual(len(d), 2)

    def test_config_delete_success(self):
        self.mock_store.delete.return_value = True
        r = self.client.delete('/api/config/delete/acme/aws')
        self.assertEqual(r.status_code, 200)
        d = r.get_json()
        self.assertTrue(d.get('ok'))

    def test_config_delete_not_found(self):
        self.mock_store.delete.return_value = False
        r = self.client.delete('/api/config/delete/nobody/aws')
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.get_json()['ok'])

    def test_config_backend_endpoint(self):
        r = self.client.get('/api/config/backend')
        self.assertEqual(r.status_code, 200)
        d = r.get_json()
        self.assertIn('backend', d)


# ══════════════════════════════════════════════════════════════════════════════
#  17. COUCHDB STORE (fully mocked urllib)
# ══════════════════════════════════════════════════════════════════════════════

class TestCouchDBStore(unittest.TestCase):

    def _make_mock_response(self, data: dict, status: int = 200):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(data).encode()
        mock_resp.status = status
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        return mock_resp

    def test_save_new_document(self):
        from store import CouchDBStore
        store = CouchDBStore.__new__(CouchDBStore)
        store.base = 'http://localhost:5984/testdb'
        # Mock _get (returns None = new doc) and _put
        store._get = MagicMock(return_value=None)
        store._put = MagicMock(return_value={'ok': True, 'rev': '1-abc'})
        result = store.save('Acme', 'aws', {'cloud': 'aws', 'data': 1})
        self.assertTrue(result['ok'])
        store._put.assert_called_once()

    def test_save_existing_document_includes_rev(self):
        from store import CouchDBStore
        store = CouchDBStore.__new__(CouchDBStore)
        store.base = 'http://localhost:5984/testdb'
        store._get = MagicMock(return_value={'_id': 'acme_aws', '_rev': '2-xyz'})
        store._put = MagicMock(return_value={'ok': True, 'rev': '3-new'})
        result = store.save('Acme', 'aws', {'cloud': 'aws'})
        self.assertTrue(result['ok'])
        # _rev must be included in the PUT body
        put_doc = store._put.call_args[0][1]
        self.assertEqual(put_doc['_rev'], '2-xyz')

    @patch('store.urllib.request.urlopen')
    def test_load_existing(self, mock_urlopen):
        from store import CouchDBStore
        doc = {'_id': 'acme_aws', 'customer': 'Acme', 'cloud': 'aws'}
        mock_urlopen.return_value = self._make_mock_response(doc)
        store = CouchDBStore.__new__(CouchDBStore)
        store.base = 'http://localhost:5984/testdb'
        result = store._get('acme_aws')
        self.assertEqual(result['customer'], 'Acme')

    @patch('store.urllib.request.urlopen')
    def test_load_not_found(self, mock_urlopen):
        from store import CouchDBStore
        import urllib.error
        mock_urlopen.side_effect = urllib.error.HTTPError('url', 404, 'not found', {}, None)
        store = CouchDBStore.__new__(CouchDBStore)
        store.base = 'http://localhost:5984/testdb'
        result = store._get('nobody_aws')
        self.assertIsNone(result)

    @patch('store.urllib.request.urlopen')
    def test_list_customers(self, mock_urlopen):
        from store import CouchDBStore
        data = {
            'rows': [
                {'doc': {'_id': 'acme_aws', 'customer': 'Acme', 'cloud': 'aws'}},
                {'doc': {'_id': 'beta_gcp', 'customer': 'Beta', 'cloud': 'gcp'}},
            ]
        }
        mock_urlopen.return_value = self._make_mock_response(data)
        store = CouchDBStore.__new__(CouchDBStore)
        store.base = 'http://localhost:5984/testdb'
        result = store.list_customers()
        self.assertEqual(len(result), 2)

    @patch('store.urllib.request.urlopen')
    def test_delete_success(self, mock_urlopen):
        from store import CouchDBStore
        import urllib.error
        existing = {'_id': 'acme_aws', '_rev': '1-abc'}
        mock_urlopen.side_effect = [
            self._make_mock_response(existing),  # _get
            self._make_mock_response({'ok': True}),  # DELETE
        ]
        store = CouchDBStore.__new__(CouchDBStore)
        store.base = 'http://localhost:5984/testdb'
        result = store.delete('Acme', 'aws')
        self.assertTrue(result)

    def test_backend_name(self):
        from store import CouchDBStore
        store = CouchDBStore.__new__(CouchDBStore)
        store.base = 'http://localhost:5984/testdb'
        self.assertIn('couchdb', store.backend_name)


if __name__ == '__main__':
    unittest.main(verbosity=2)


# ══════════════════════════════════════════════════════════════════════════════
#  18. /api/test ROUTE
# ══════════════════════════════════════════════════════════════════════════════

class TestApiTestRoute(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
        self.good_aws = {
            'cloud': 'aws',
            'aws_networks': [aws_net('n1')],
            'aws_infras':   [aws_infra('i1')],
            'aws_peerings': [aws_peer('p1', network_ref='n1')],
            'aws_clusters': [aws_cluster('c1', infra_ref='i1', network_ref='n1')],
        }
        self.good_gcp = {
            'cloud': 'gcp',
            'gcp_networks':  [gcp_net('gnet1')],
            'gcp_infras':    [gcp_infra('ginf1')],
            'gcp_clusters':  [gcp_cluster('gcl1', 'gnet1', 'ginf1')],
        }

    def test_returns_200(self):
        r = self.client.post('/api/test', json=self.good_aws)
        self.assertEqual(r.status_code, 200)

    def test_response_has_required_fields(self):
        r = self.client.post('/api/test', json=self.good_aws)
        d = r.get_json()
        for field in ('passed', 'failed', 'total', 'results', 'cloud'):
            self.assertIn(field, d)

    def test_all_pass_on_valid_aws_payload(self):
        r = self.client.post('/api/test', json=self.good_aws)
        d = r.get_json()
        self.assertEqual(d['failed'], 0)
        self.assertGreater(d['passed'], 0)

    def test_all_pass_on_valid_gcp_payload(self):
        r = self.client.post('/api/test', json=self.good_gcp)
        d = r.get_json()
        self.assertEqual(d['failed'], 0)
        self.assertGreater(d['passed'], 0)

    def test_catches_missing_availability_zone_id(self):
        payload = {**self.good_aws,
                   'aws_networks': [{**aws_net('n1'), 'availability_zone_id': ''}]}
        r = self.client.post('/api/test', json=payload)
        d = r.get_json()
        self.assertGreater(d['failed'], 0)
        names = [row['name'] for row in d['results'] if row['status'] == 'fail']
        self.assertTrue(any('availability_zone_id' in n for n in names))

    def test_catches_invalid_cidr(self):
        payload = {**self.good_aws,
                   'aws_networks': [{**aws_net('n1'), 'client_subnet_cidr': 'not-a-cidr'}]}
        r = self.client.post('/api/test', json=payload)
        d = r.get_json()
        self.assertGreater(d['failed'], 0)

    def test_catches_low_compute_count(self):
        payload = {**self.good_aws,
                   'aws_infras': [{**aws_infra('i1'), 'compute_count': 1}]}
        r = self.client.post('/api/test', json=payload)
        d = r.get_json()
        self.assertGreater(d['failed'], 0)

    def test_catches_missing_ssh_key(self):
        payload = {**self.good_aws,
                   'aws_clusters': [{**aws_cluster('c1'), 'ssh_public_keys': []}]}
        r = self.client.post('/api/test', json=payload)
        d = r.get_json()
        self.assertGreater(d['failed'], 0)

    def test_catches_duplicate_module_names(self):
        payload = {**self.good_aws,
                   'aws_networks': [aws_net('same'), aws_net('same')]}
        r = self.client.post('/api/test', json=payload)
        d = r.get_json()
        self.assertGreater(d['failed'], 0)

    def test_results_grouped_by_category(self):
        r = self.client.post('/api/test', json=self.good_aws)
        d = r.get_json()
        groups = {row['group'] for row in d['results']}
        self.assertIn('Input Validation', groups)
        self.assertIn('Module Generation', groups)
        self.assertIn('Content Checks', groups)
        self.assertIn('Uniqueness', groups)

    def test_verifies_infra_wiring_in_root(self):
        r = self.client.post('/api/test', json=self.good_aws)
        d = r.get_json()
        wiring_tests = [row for row in d['results'] if 'wired to infra' in row['name']]
        self.assertTrue(len(wiring_tests) > 0)
        self.assertTrue(all(t['status'] == 'pass' for t in wiring_tests))

    def test_gcp_checks_provider(self):
        r = self.client.post('/api/test', json=self.good_gcp)
        d = r.get_json()
        provider_check = next((row for row in d['results'] if 'GCP provider' in row['name']), None)
        self.assertIsNotNone(provider_check)
        self.assertEqual(provider_check['status'], 'pass')

    def test_loads_saved_config_by_customer_name(self):
        mock_store = MagicMock()
        mock_store.load.return_value = {**self.good_aws, 'customer': 'AcmeCorp', 'cloud': 'aws'}
        import app as app_mod
        with patch.object(app_mod, 'storage', mock_store):
            r = self.client.post('/api/test',
                json={'customer': 'AcmeCorp', 'cloud': 'aws'},
                content_type='application/json')
        self.assertEqual(r.status_code, 200)
        mock_store.load.assert_called_once_with('AcmeCorp', 'aws')

    def test_uses_posted_payload_when_no_saved_config(self):
        mock_store = MagicMock()
        mock_store.load.return_value = None  # not saved
        import app as app_mod
        with patch.object(app_mod, 'storage', mock_store):
            r = self.client.post('/api/test', json=self.good_aws)
        d = r.get_json()
        self.assertEqual(d['failed'], 0)

    def test_multi_network_all_checked(self):
        payload = {
            'cloud': 'aws',
            'aws_networks': [aws_net('n1'), aws_net('n2'), aws_net('n3')],
            'aws_infras':   [aws_infra('i1')],
            'aws_peerings': [aws_peer('p1', network_ref='n1')],
            'aws_clusters': [aws_cluster('c1', infra_ref='i1', network_ref='n1')],
        }
        r = self.client.post('/api/test', json=payload)
        d = r.get_json()
        # Should check all 3 networks
        net_checks = [row for row in d['results'] if '"n1"' in row['name'] or '"n2"' in row['name'] or '"n3"' in row['name']]
        self.assertGreaterEqual(len(net_checks), 3)


# ══════════════════════════════════════════════════════════════════════════════
#  19. MOCK TERRAFORM VALIDATOR  (tf_validator.py)
# ══════════════════════════════════════════════════════════════════════════════

class TestTFValidator(unittest.TestCase):

    def _validate(self, files, cloud):
        from tf_validator import validate_terraform, summarise
        return summarise(validate_terraform(files, cloud))['results']

    def _gen_aws(self, **kw):
        base = {
            'cloud': 'aws',
            'aws_networks':  [aws_net('odb_network')],
            'aws_infras':    [aws_infra('odb_infra')],
            'aws_peerings':  [aws_peer('odb_peering', network_ref='odb_network')],
            'aws_clusters':  [aws_cluster('odb_cluster', infra_ref='odb_infra',
                                          network_ref='odb_network')],
        }
        base.update(kw)
        return generate_all(base)

    def _gen_gcp(self):
        n = gcp_net('gcp_network')
        return generate_all({
            'cloud': 'gcp',
            'gcp_networks':  [n],
            'gcp_infras':    [gcp_infra('gcp_infra')],
            'gcp_clusters':  [gcp_cluster('gcp_cluster', 'gcp_network', 'gcp_infra')],
        })

    # ── File structure ─────────────────────────────────────────────────────
    def test_aws_all_files_present(self):
        files = self._gen_aws()
        results = self._validate(files, 'aws')
        struct = [r for r in results if r['group'] == 'File Structure' and r['status'] == 'fail']
        self.assertEqual(struct, [], f'File structure failures: {struct}')

    def test_gcp_all_files_present(self):
        files = self._gen_gcp()
        results = self._validate(files, 'gcp')
        struct = [r for r in results if r['group'] == 'File Structure' and r['status'] == 'fail']
        self.assertEqual(struct, [], f'File structure failures: {struct}')

    # ── HCL syntax ─────────────────────────────────────────────────────────
    def test_valid_hcl_no_syntax_errors(self):
        files = self._gen_aws()
        results = self._validate(files, 'aws')
        syntax_fails = [r for r in results if r['group'] == 'HCL Syntax' and r['status'] == 'fail']
        self.assertEqual(syntax_fails, [], f'HCL syntax failures: {syntax_fails}')

    def test_broken_hcl_detected(self):
        from tf_validator import _check_balanced
        bad = 'resource "aws_odb_network" "this" { display_name = var.display_name'
        result = _check_balanced(bad, 'test.tf')
        self.assertIsNotNone(result)
        self.assertEqual(result.status, 'fail')

    def test_balanced_hcl_passes(self):
        from tf_validator import _check_balanced
        good = 'resource "aws_odb_network" "this" { display_name = var.display_name }'
        result = _check_balanced(good, 'test.tf')
        self.assertIsNone(result)

    def test_comments_not_counted_in_balance(self):
        from tf_validator import _check_balanced
        with_comment = '# This { has braces\nresource "x" "y" { a = 1 }'
        result = _check_balanced(with_comment, 'test.tf')
        self.assertIsNone(result)

    # ── Provider checks ────────────────────────────────────────────────────
    def test_aws_provider_declared(self):
        files = self._gen_aws()
        results = self._validate(files, 'aws')
        prov = [r for r in results if r['group'] == 'Provider' and r['status'] == 'fail']
        self.assertEqual(prov, [])

    def test_gcp_provider_declared(self):
        files = self._gen_gcp()
        results = self._validate(files, 'gcp')
        prov = [r for r in results if r['group'] == 'Provider' and r['status'] == 'fail']
        self.assertEqual(prov, [])

    # ── Resource schema ────────────────────────────────────────────────────
    def test_aws_resource_types_known(self):
        files = self._gen_aws()
        results = self._validate(files, 'aws')
        schema_fails = [r for r in results if r['group'] == 'Resource Schema' and r['status'] == 'fail']
        self.assertEqual(schema_fails, [], f'Schema failures: {schema_fails}')

    def test_gcp_resource_types_known(self):
        files = self._gen_gcp()
        results = self._validate(files, 'gcp')
        schema_fails = [r for r in results if r['group'] == 'Resource Schema' and r['status'] == 'fail']
        self.assertEqual(schema_fails, [], f'Schema failures: {schema_fails}')

    # ── Variable resolution ────────────────────────────────────────────────
    def test_no_unresolved_var_refs(self):
        files = self._gen_aws()
        results = self._validate(files, 'aws')
        var_fails = [r for r in results
                     if r['group'] == 'Variable Resolution' and r['status'] == 'fail']
        self.assertEqual(var_fails, [], f'Unresolved vars: {var_fails}')

    def test_unresolved_var_detected(self):
        files = self._gen_aws()
        # Inject a broken main.tf with an undefined variable
        files['modules/odb_network/main.tf'] += '\n  undefined_arg = var.does_not_exist\n'
        results = self._validate(files, 'aws')
        var_fails = [r for r in results
                     if r['group'] == 'Variable Resolution' and r['status'] == 'fail'
                     and 'does_not_exist' in (r.get('error') or '')]
        self.assertGreater(len(var_fails), 0, 'Should detect unresolved var.does_not_exist')

    # ── Module cross-references ────────────────────────────────────────────
    def test_module_source_paths_correct(self):
        files = self._gen_aws()
        results = self._validate(files, 'aws')
        xref_fails = [r for r in results
                      if r['group'] == 'Module Cross-References' and r['status'] == 'fail']
        self.assertEqual(xref_fails, [], f'Cross-ref failures: {xref_fails}')

    def test_broken_source_path_detected(self):
        files = self._gen_aws()
        # Break the source path for one module
        files['main.tf'] = files['main.tf'].replace(
            'source = "./modules/odb_network"',
            'source = "./modules/wrong_path"')
        results = self._validate(files, 'aws')
        src_fails = [r for r in results
                     if r['group'] == 'Module Cross-References' and r['status'] == 'fail'
                     and 'source' in (r.get('name') or '').lower()]
        self.assertGreater(len(src_fails), 0, 'Should detect wrong source path')

    # ── Overall: no failures on valid config ──────────────────────────────
    def test_valid_aws_config_zero_failures(self):
        files = self._gen_aws()
        results = self._validate(files, 'aws')
        failures = [r for r in results if r['status'] == 'fail']
        self.assertEqual(failures, [], f'Unexpected failures: {failures}')

    def test_valid_gcp_config_zero_failures(self):
        files = self._gen_gcp()
        results = self._validate(files, 'gcp')
        failures = [r for r in results if r['status'] == 'fail']
        self.assertEqual(failures, [], f'Unexpected failures: {failures}')

    def test_multi_module_aws_zero_failures(self):
        files = generate_all({
            'cloud': 'aws',
            'aws_networks': [aws_net('net1'), aws_net('net2')],
            'aws_infras':   [aws_infra('inf1'), aws_infra('inf2')],
            'aws_peerings': [aws_peer('peer1', network_ref='net1'),
                             aws_peer('peer2', network_ref='net2')],
            'aws_clusters': [aws_cluster('cl1', infra_ref='inf1', network_ref='net1'),
                             aws_cluster('cl2', infra_ref='inf2', network_ref='net2')],
        })
        results = self._validate(files, 'aws')
        failures = [r for r in results if r['status'] == 'fail']
        self.assertEqual(failures, [], f'Multi-module failures: {failures}')

    # ── /api/tf-validate endpoint ─────────────────────────────────────────
    def test_api_tf_validate_returns_200(self):
        c = app.test_client()
        r = c.post('/api/tf-validate', json={
            'cloud': 'aws',
            'aws_networks': [aws_net('odb_network')],
            'aws_infras':   [aws_infra('odb_infra')],
            'aws_peerings': [aws_peer('odb_peering', network_ref='odb_network')],
            'aws_clusters': [aws_cluster('odb_cluster', infra_ref='odb_infra', network_ref='odb_network')],
        })
        self.assertEqual(r.status_code, 200)

    def test_api_tf_validate_response_fields(self):
        c = app.test_client()
        r = c.post('/api/tf-validate', json={
            'cloud': 'aws',
            'aws_networks': [aws_net('odb_network')],
            'aws_infras':   [aws_infra('odb_infra')],
            'aws_peerings': [aws_peer('odb_peering', network_ref='odb_network')],
            'aws_clusters': [aws_cluster('odb_cluster', infra_ref='odb_infra', network_ref='odb_network')],
        })
        d = r.get_json()
        for field in ('passed', 'failed', 'warned', 'total', 'results', 'files_generated'):
            self.assertIn(field, d)

    def test_api_tf_validate_zero_failures_valid_config(self):
        c = app.test_client()
        r = c.post('/api/tf-validate', json={
            'cloud': 'aws',
            'aws_networks': [aws_net('odb_network')],
            'aws_infras':   [aws_infra('odb_infra')],
            'aws_peerings': [aws_peer('odb_peering', network_ref='odb_network')],
            'aws_clusters': [aws_cluster('odb_cluster', infra_ref='odb_infra', network_ref='odb_network')],
        })
        d = r.get_json()
        self.assertEqual(d['failed'], 0, f"Unexpected failures: {[x for x in d['results'] if x['status']=='fail']}")
