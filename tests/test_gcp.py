"""
GCP Oracle Database tests — for_each / shared-module architecture.
Run with:  python -m unittest tests/test_gcp.py
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app, generate_all
from clouds.gcp.generator import (
    _gcp_net_defaults, _gcp_infra_defaults, _gcp_cluster_defaults,
    _gcp_shared_module_files,
    gcp_build_root_main, gcp_build_root_vars, gcp_build_root_tfvars,
    generate_gcp_tf,
    _GCP_MOD_NET, _GCP_MOD_INFRA, _GCP_MOD_CLUSTER,
)
from tf_validator import validate_terraform, summarise


# ══════════════════════════════════════════════════════════════════════════════
#  FIXTURES
# ══════════════════════════════════════════════════════════════════════════════

def gcp_net(module_name='gcp-odb-network', **kw):
    return {
        'module_name':   module_name,
        'odb_network_id': 'my-odb-net',
        'location':       'us-east4',
        'network':        'projects/my-proj/global/networks/default',
        'project':        'my-proj',
        'gcp_oracle_zone': 'us-east4-b-r1',
        'deletion_protection': True,
        'client_subnet_id':   'client-subnet',
        'client_cidr':        '10.0.1.0/24',
        'backup_subnet_id':   'backup-subnet',
        'backup_cidr':        '10.0.2.0/24',
        'labels': {'env': 'test'},
        **kw,
    }

def gcp_infra(module_name='gcp-exadata-infra', **kw):
    return {
        'module_name':    module_name,
        'cloud_exadata_infrastructure_id': 'my-infra',
        'display_name':   'My Infra',
        'location':       'us-east4',
        'gcp_oracle_zone': 'us-east4-b-r1',
        'project':        'my-proj',
        'shape':          'Exadata.X9M',
        'compute_count':  2,
        'storage_count':  3,
        'mw_preference':  'NO_PREFERENCE',
        'mw_patching_mode': 'ROLLING',
        **kw,
    }

def gcp_cluster(module_name='gcp-vm-cluster', net_module='gcp-odb-network', infra_module='gcp-exadata-infra', **kw):
    return {
        'module_name':       module_name,
        'cloud_vm_cluster_id': 'my-cluster',
        'display_name':      'My Cluster',
        'location':          'us-east4',
        'project':           'my-proj',
        'hostname_prefix':   'vm',
        'cpu_core_count':    16,
        'memory_size_gb':    60,
        'db_node_storage_size_gb': 120,
        'data_storage_size_tb':    4.0,
        'gi_version':        '23.0.0.0',
        'license_type':      'LICENSE_INCLUDED',
        'ssh_public_keys':   ['ssh-rsa AAAAB3Nz test@host'],
        'network_ref':       net_module,
        'infra_ref':         infra_module,
        **kw,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  Shared module files
# ══════════════════════════════════════════════════════════════════════════════

class TestGcpSharedModules(unittest.TestCase):

    def setUp(self):
        self.files = _gcp_shared_module_files()

    def test_exactly_nine_module_files(self):
        self.assertEqual(len(self.files), 9)

    def test_odb_network_main_has_resource(self):
        self.assertIn('google_oracle_database_odb_network',
                      self.files[f'modules/{_GCP_MOD_NET}/main.tf'])

    def test_odb_network_main_has_client_subnet(self):
        self.assertIn('google_oracle_database_odb_subnet',
                      self.files[f'modules/{_GCP_MOD_NET}/main.tf'])

    def test_odb_network_variables_has_odb_network_id(self):
        self.assertIn('odb_network_id', self.files[f'modules/{_GCP_MOD_NET}/variables.tf'])

    def test_odb_network_variables_has_cidr_range_vars(self):
        v = self.files[f'modules/{_GCP_MOD_NET}/variables.tf']
        self.assertIn('client_cidr_range', v)
        self.assertIn('backup_cidr_range', v)

    def test_odb_network_outputs_has_network_name(self):
        self.assertIn('odb_network_name', self.files[f'modules/{_GCP_MOD_NET}/outputs.tf'])

    def test_odb_network_outputs_has_subnet_names(self):
        o = self.files[f'modules/{_GCP_MOD_NET}/outputs.tf']
        self.assertIn('client_subnet_name', o)
        self.assertIn('backup_subnet_name', o)

    def test_exadata_infra_main_has_resource(self):
        self.assertIn('google_oracle_database_cloud_exadata_infrastructure',
                      self.files[f'modules/{_GCP_MOD_INFRA}/main.tf'])

    def test_exadata_infra_main_has_lifecycle(self):
        self.assertIn('ignore_changes', self.files[f'modules/{_GCP_MOD_INFRA}/main.tf'])

    def test_exadata_infra_variables_has_shape(self):
        self.assertIn('shape', self.files[f'modules/{_GCP_MOD_INFRA}/variables.tf'])

    def test_exadata_infra_outputs_has_infra_name(self):
        self.assertIn('infra_name', self.files[f'modules/{_GCP_MOD_INFRA}/outputs.tf'])

    def test_exadata_infra_outputs_has_self_link(self):
        self.assertIn('infra_self_link', self.files[f'modules/{_GCP_MOD_INFRA}/outputs.tf'])

    def test_vm_cluster_main_has_resource(self):
        self.assertIn('google_oracle_database_cloud_vm_cluster',
                      self.files[f'modules/{_GCP_MOD_CLUSTER}/main.tf'])

    def test_vm_cluster_main_has_memory_size_gb(self):
        self.assertIn('memory_size_gb', self.files[f'modules/{_GCP_MOD_CLUSTER}/main.tf'])

    def test_vm_cluster_main_has_data_storage_tb(self):
        self.assertIn('data_storage_size_tb', self.files[f'modules/{_GCP_MOD_CLUSTER}/main.tf'])

    def test_vm_cluster_main_has_timeouts(self):
        self.assertIn('timeouts', self.files[f'modules/{_GCP_MOD_CLUSTER}/main.tf'])

    def test_vm_cluster_main_has_lifecycle(self):
        self.assertIn('ignore_changes', self.files[f'modules/{_GCP_MOD_CLUSTER}/main.tf'])

    def test_vm_cluster_variables_has_all_storage_vars(self):
        v = self.files[f'modules/{_GCP_MOD_CLUSTER}/variables.tf']
        for var in ['memory_size_gb', 'db_node_storage_size_gb', 'data_storage_size_tb']:
            self.assertIn(var, v, msg=f'Missing {var} in vm-cluster variables.tf')

    def test_vm_cluster_outputs_has_cluster_name(self):
        self.assertIn('vm_cluster_name', self.files[f'modules/{_GCP_MOD_CLUSTER}/outputs.tf'])

    def test_all_module_files_non_empty(self):
        for path, content in self.files.items():
            self.assertGreater(len(content.strip()), 0, f'{path} is empty')


# ══════════════════════════════════════════════════════════════════════════════
#  Root templates
# ══════════════════════════════════════════════════════════════════════════════

class TestGcpRoot(unittest.TestCase):

    def _build(self, net_count=1, infra_count=1, cluster_count=1):
        nets     = [_gcp_net_defaults(gcp_net(f'gnet-{i}')) for i in range(net_count)]
        infras   = [_gcp_infra_defaults(gcp_infra(f'ginf-{i}')) for i in range(infra_count)]
        clusters = [_gcp_cluster_defaults(
            gcp_cluster(f'gcl-{i}', 'gnet-0', 'ginf-0'), nets[0], infras[0])
            for i in range(cluster_count)]
        return nets, infras, clusters

    def test_root_main_has_provider(self):
        ns, inf, cls = self._build()
        self.assertIn('hashicorp/google', gcp_build_root_main(ns, inf, cls))

    def test_root_main_uses_for_each_networks(self):
        ns, inf, cls = self._build()
        out = gcp_build_root_main(ns, inf, cls)
        self.assertIn('for_each = var.gcp_odb_networks', out)

    def test_root_main_uses_for_each_infras(self):
        ns, inf, cls = self._build()
        out = gcp_build_root_main(ns, inf, cls)
        self.assertIn('for_each = var.gcp_exadata_infras', out)

    def test_root_main_uses_for_each_clusters(self):
        ns, inf, cls = self._build()
        out = gcp_build_root_main(ns, inf, cls)
        self.assertIn('for_each = var.gcp_vm_clusters', out)

    def test_root_main_has_db_servers_data_source(self):
        ns, inf, cls = self._build()
        out = gcp_build_root_main(ns, inf, cls)
        self.assertIn('google_oracle_database_db_servers', out)

    def test_root_main_references_infra_key(self):
        ns, inf, cls = self._build()
        out = gcp_build_root_main(ns, inf, cls)
        self.assertIn('each.value.infra_key', out)

    def test_root_main_references_network_key(self):
        ns, inf, cls = self._build()
        out = gcp_build_root_main(ns, inf, cls)
        self.assertIn('each.value.network_key', out)

    def test_root_main_passes_memory_size_gb(self):
        ns, inf, cls = self._build()
        out = gcp_build_root_main(ns, inf, cls)
        self.assertIn('memory_size_gb', out)

    def test_root_main_passes_data_storage_size_tb(self):
        ns, inf, cls = self._build()
        out = gcp_build_root_main(ns, inf, cls)
        self.assertIn('data_storage_size_tb', out)

    def test_root_vars_has_map_object_networks(self):
        ns, inf, cls = self._build()
        out = gcp_build_root_vars(ns, inf, cls)
        self.assertIn('gcp_odb_networks', out)
        self.assertIn('map(object', out)

    def test_root_vars_has_map_object_infras(self):
        ns, inf, cls = self._build()
        out = gcp_build_root_vars(ns, inf, cls)
        self.assertIn('gcp_exadata_infras', out)

    def test_root_vars_has_map_object_clusters(self):
        ns, inf, cls = self._build()
        out = gcp_build_root_vars(ns, inf, cls)
        self.assertIn('gcp_vm_clusters', out)

    def test_root_vars_cluster_has_infra_key_field(self):
        ns, inf, cls = self._build()
        out = gcp_build_root_vars(ns, inf, cls)
        self.assertIn('infra_key', out)

    def test_root_vars_cluster_has_network_key_field(self):
        ns, inf, cls = self._build()
        out = gcp_build_root_vars(ns, inf, cls)
        self.assertIn('network_key', out)

    def test_root_tfvars_has_gcp_odb_networks_map(self):
        ns, inf, cls = self._build()
        out = gcp_build_root_tfvars(ns, inf, cls)
        self.assertIn('gcp_odb_networks', out)

    def test_root_tfvars_has_gcp_exadata_infras_map(self):
        ns, inf, cls = self._build()
        out = gcp_build_root_tfvars(ns, inf, cls)
        self.assertIn('gcp_exadata_infras', out)

    def test_root_tfvars_has_gcp_vm_clusters_map(self):
        ns, inf, cls = self._build()
        out = gcp_build_root_tfvars(ns, inf, cls)
        self.assertIn('gcp_vm_clusters', out)

    def test_root_tfvars_cluster_entry_has_infra_key(self):
        ns, inf, cls = self._build()
        out = gcp_build_root_tfvars(ns, inf, cls)
        self.assertIn('infra_key', out)

    def test_root_tfvars_cluster_entry_has_network_key(self):
        ns, inf, cls = self._build()
        out = gcp_build_root_tfvars(ns, inf, cls)
        self.assertIn('network_key', out)

    def test_root_tfvars_has_memory_size_gb(self):
        ns, inf, cls = self._build()
        out = gcp_build_root_tfvars(ns, inf, cls)
        self.assertIn('memory_size_gb', out)


# ══════════════════════════════════════════════════════════════════════════════
#  generate_gcp_tf — file count and structure
# ══════════════════════════════════════════════════════════════════════════════

class TestGenerateGcpTf(unittest.TestCase):

    def _base(self, net_count=1, infra_count=1, cluster_count=1):
        nets     = [gcp_net(f'gn-{i}')   for i in range(net_count)]
        infras   = [gcp_infra(f'gi-{i}') for i in range(infra_count)]
        clusters = [gcp_cluster(f'gc-{i}', 'gn-0', 'gi-0') for i in range(cluster_count)]
        return {'cloud': 'gcp', 'gcp_networks': nets, 'gcp_infras': infras, 'gcp_clusters': clusters}

    # 3 root files + 9 shared module files (3 modules × 3 files) + a generated
    # README = 13. The count is fixed: instances live in terraform.auto.tfvars,
    # so adding them grows that file rather than the file list.
    EXPECTED_FILES = 13

    def test_always_fixed_file_count_one_of_each(self):
        self.assertEqual(len(generate_gcp_tf(self._base())), self.EXPECTED_FILES)

    def test_always_fixed_file_count_two_networks(self):
        self.assertEqual(len(generate_gcp_tf(self._base(net_count=2))), self.EXPECTED_FILES)

    def test_always_fixed_file_count_two_clusters(self):
        self.assertEqual(len(generate_gcp_tf(self._base(cluster_count=2))), self.EXPECTED_FILES)

    def test_always_fixed_file_count_two_of_everything(self):
        self.assertEqual(len(generate_gcp_tf(self._base(2, 2, 2))), self.EXPECTED_FILES)

    def test_readme_is_generated(self):
        self.assertIn('README.md', generate_gcp_tf(self._base()))

    def test_has_root_main(self):
        self.assertIn('main.tf', generate_gcp_tf(self._base()))

    def test_has_root_variables(self):
        self.assertIn('variables.tf', generate_gcp_tf(self._base()))

    def test_has_root_tfvars(self):
        self.assertIn('terraform.auto.tfvars', generate_gcp_tf(self._base()))

    def test_has_shared_odb_network_module(self):
        files = generate_gcp_tf(self._base())
        for f in ['main.tf', 'variables.tf', 'outputs.tf']:
            self.assertIn(f'modules/{_GCP_MOD_NET}/{f}', files)

    def test_has_shared_exadata_infra_module(self):
        files = generate_gcp_tf(self._base())
        for f in ['main.tf', 'variables.tf', 'outputs.tf']:
            self.assertIn(f'modules/{_GCP_MOD_INFRA}/{f}', files)

    def test_has_shared_vm_cluster_module(self):
        files = generate_gcp_tf(self._base())
        for f in ['main.tf', 'variables.tf', 'outputs.tf']:
            self.assertIn(f'modules/{_GCP_MOD_CLUSTER}/{f}', files)

    def test_no_per_instance_module_dirs(self):
        files = generate_gcp_tf(self._base())
        # Old style: modules/gn-0/main.tf — should NOT exist
        self.assertNotIn('modules/gn-0/main.tf', files)
        self.assertNotIn('modules/gi-0/main.tf', files)

    def test_multiple_networks_appear_in_tfvars(self):
        files = generate_gcp_tf(self._base(net_count=2))
        tfv = files['terraform.auto.tfvars']
        self.assertIn('gn-0', tfv)
        self.assertIn('gn-1', tfv)

    def test_multiple_clusters_appear_in_tfvars(self):
        files = generate_gcp_tf(self._base(cluster_count=2))
        tfv = files['terraform.auto.tfvars']
        self.assertIn('gc-0', tfv)
        self.assertIn('gc-1', tfv)

    def test_root_main_google_provider(self):
        self.assertIn('hashicorp/google', generate_gcp_tf(self._base())['main.tf'])

    def test_all_files_non_empty(self):
        for path, content in generate_gcp_tf(self._base()).items():
            self.assertGreater(len(content.strip()), 0, f'{path} is empty')


# ══════════════════════════════════════════════════════════════════════════════
#  generate_all — GCP integration
# ══════════════════════════════════════════════════════════════════════════════

class TestGenerateAllGcp(unittest.TestCase):

    def _base(self):
        return {
            'cloud': 'gcp',
            'gcp_networks':  [gcp_net('gn-1')],
            'gcp_infras':    [gcp_infra('gi-1')],
            'gcp_clusters':  [gcp_cluster('gc-1', 'gn-1', 'gi-1')],
        }

    def test_returns_root_main(self):
        self.assertIn('main.tf', generate_all(self._base()))

    def test_returns_root_tfvars(self):
        self.assertIn('terraform.auto.tfvars', generate_all(self._base()))

    def test_returns_root_variables(self):
        self.assertIn('variables.tf', generate_all(self._base()))

    def test_shared_module_files_present(self):
        files = generate_all(self._base())
        for mod in [_GCP_MOD_NET, _GCP_MOD_INFRA, _GCP_MOD_CLUSTER]:
            for f in ['main.tf', 'variables.tf', 'outputs.tf']:
                self.assertIn(f'modules/{mod}/{f}', files)

    def test_no_aws_provider_in_gcp_output(self):
        files = generate_all(self._base())
        self.assertNotIn('hashicorp/aws', files['main.tf'])
        self.assertNotIn('hashicorp/azurerm', files['main.tf'])


# ══════════════════════════════════════════════════════════════════════════════
#  Default normalisers
# ══════════════════════════════════════════════════════════════════════════════

class TestGcpDefaultNormalisers(unittest.TestCase):

    def test_net_defaults_odb_network_id_fallback(self):
        self.assertEqual(_gcp_net_defaults({})['odb_network_id'], 'my-odb-network')

    def test_net_defaults_client_cidr_fallback(self):
        self.assertEqual(_gcp_net_defaults({})['client_cidr'], '10.0.1.0/24')

    def test_net_defaults_backup_cidr_fallback(self):
        self.assertEqual(_gcp_net_defaults({})['backup_cidr'], '10.0.2.0/24')

    def test_net_defaults_preserves_location(self):
        self.assertEqual(_gcp_net_defaults({'location': 'europe-west3'})['location'], 'europe-west3')

    def test_infra_defaults_shape_fallback(self):
        self.assertEqual(_gcp_infra_defaults({})['shape'], 'Exadata.X9M')

    def test_infra_defaults_compute_count_int(self):
        d = _gcp_infra_defaults({'compute_count': '4', 'storage_count': '6'})
        self.assertEqual(d['compute_count'], 4)
        self.assertEqual(d['storage_count'], 6)

    def test_infra_defaults_fallback_counts(self):
        d = _gcp_infra_defaults({})
        self.assertEqual(d['compute_count'], 2)
        self.assertEqual(d['storage_count'], 3)

    def test_cluster_defaults_network_ref_fallback(self):
        first_net = _gcp_net_defaults({'module_name': 'net-prod'})
        d = _gcp_cluster_defaults({}, first_net=first_net)
        self.assertEqual(d['network_ref'], 'net-prod')

    def test_cluster_defaults_infra_ref_fallback(self):
        first_infra = _gcp_infra_defaults({'module_name': 'infra-prod'})
        d = _gcp_cluster_defaults({}, first_infra=first_infra)
        self.assertEqual(d['infra_ref'], 'infra-prod')

    def test_cluster_defaults_memory_size_gb_int(self):
        d = _gcp_cluster_defaults({'memory_size_gb': '120'})
        self.assertEqual(d['memory_size_gb'], 120)

    def test_cluster_defaults_data_storage_float(self):
        d = _gcp_cluster_defaults({'data_storage_size_tb': '8'})
        self.assertEqual(d['data_storage_size_tb'], 8.0)

    def test_cluster_defaults_cpu_core_count_int(self):
        d = _gcp_cluster_defaults({'cpu_core_count': '32'})
        self.assertEqual(d['cpu_core_count'], 32)


# ══════════════════════════════════════════════════════════════════════════════
#  API Routes — GCP
# ══════════════════════════════════════════════════════════════════════════════

class TestApiRoutesGcp(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
        self.base = {
            'cloud': 'gcp',
            'gcp_networks':  [gcp_net('gn1')],
            'gcp_infras':    [gcp_infra('gi1')],
            'gcp_clusters':  [gcp_cluster('gc1', 'gn1', 'gi1')],
        }

    def test_generate_shared_net_module_variables(self):
        r = self.client.post('/api/generate',
            json={**self.base, 'file_key': f'modules/{_GCP_MOD_NET}/variables.tf'},
            content_type='application/json')
        self.assertIn('variable', r.get_json()['content'])

    def test_generate_shared_infra_module_variables(self):
        r = self.client.post('/api/generate',
            json={**self.base, 'file_key': f'modules/{_GCP_MOD_INFRA}/variables.tf'},
            content_type='application/json')
        self.assertIn('variable', r.get_json()['content'])

    def test_generate_shared_cluster_module_variables(self):
        r = self.client.post('/api/generate',
            json={**self.base, 'file_key': f'modules/{_GCP_MOD_CLUSTER}/variables.tf'},
            content_type='application/json')
        self.assertIn('variable', r.get_json()['content'])

    def test_generate_root_variables(self):
        r = self.client.post('/api/generate',
            json={**self.base, 'file_key': 'variables.tf'},
            content_type='application/json')
        self.assertIn('gcp_odb_networks', r.get_json()['content'])

    def test_download_gcp_filename_contains_gcp(self):
        r = self.client.post('/api/download', json=self.base, content_type='application/json')
        self.assertIn('gcp', r.headers.get('Content-Disposition', ''))

    def test_download_gcp_zip_magic_bytes(self):
        r = self.client.post('/api/download', json=self.base, content_type='application/json')
        self.assertEqual(r.data[:4], b'PK\x03\x04')

    def test_download_gcp_zip_contains_main_tf(self):
        import io, zipfile as zf_mod
        r = self.client.post('/api/download', json=self.base, content_type='application/json')
        z = zf_mod.ZipFile(io.BytesIO(r.data))
        self.assertTrue(any('main.tf' in n for n in z.namelist()))

    def test_download_gcp_main_tf_has_google_provider(self):
        import io, zipfile as zf_mod
        r = self.client.post('/api/download', json=self.base, content_type='application/json')
        z = zf_mod.ZipFile(io.BytesIO(r.data))
        main = next(n for n in z.namelist() if n.endswith('main.tf') and 'modules' not in n)
        self.assertIn('hashicorp/google', z.read(main).decode())

    def test_tf_validate_gcp_returns_200(self):
        r = self.client.post('/api/tf-validate', json=self.base, content_type='application/json')
        self.assertEqual(r.status_code, 200)

    def test_tf_validate_gcp_cloud_field(self):
        r = self.client.post('/api/tf-validate', json=self.base, content_type='application/json')
        self.assertEqual(r.get_json()['cloud'], 'gcp')

    def test_validate_gcp_tab13_pass(self):
        r = self.client.post('/api/validate', json={
            'cloud': 'gcp', 'tab': 13,
            'gcp_clusters': [{'module_name': 'gc', 'cloud_vm_cluster_id': 'cl',
                               'display_name': 'My Cluster',
                               'location': 'us-east4', 'hostname_prefix': 'vm',
                               'cpu_core_count': 16,
                               'ssh_public_keys': ['ssh-rsa AAA']}],
        })
        self.assertTrue(r.get_json()['valid'])

    def test_validate_gcp_tab13_missing_hostname(self):
        r = self.client.post('/api/validate', json={
            'cloud': 'gcp', 'tab': 13,
            'gcp_clusters': [{'module_name': 'gc', 'cloud_vm_cluster_id': 'cl',
                               'location': 'us-east4',
                               'cpu_core_count': 16,
                               'ssh_public_keys': ['ssh-rsa AAA']}],
        })
        d = r.get_json()
        self.assertFalse(d['valid'])
        self.assertIn('hostname_prefix', d['errors'])

    def test_validate_gcp_tab13_no_ssh_key(self):
        r = self.client.post('/api/validate', json={
            'cloud': 'gcp', 'tab': 13,
            'gcp_clusters': [{'module_name': 'gc', 'cloud_vm_cluster_id': 'cl',
                               'location': 'us-east4', 'hostname_prefix': 'vm',
                               'cpu_core_count': 16,
                               'ssh_public_keys': []}],
        })
        d = r.get_json()
        self.assertFalse(d['valid'])
        self.assertIn('ssh_public_keys', d['errors'])


# ══════════════════════════════════════════════════════════════════════════════
#  tf_validator — GCP
# ══════════════════════════════════════════════════════════════════════════════

class TestTfValidateGcp(unittest.TestCase):

    def _gen(self, net_count=1, infra_count=1, cluster_count=1):
        nets     = [gcp_net(f'tn-{i}')   for i in range(net_count)]
        infras   = [gcp_infra(f'ti-{i}') for i in range(infra_count)]
        clusters = [gcp_cluster(f'tc-{i}', 'tn-0', 'ti-0') for i in range(cluster_count)]
        return generate_gcp_tf({'cloud': 'gcp',
                                 'gcp_networks': nets,
                                 'gcp_infras':   infras,
                                 'gcp_clusters': clusters})

    def _fails(self, files):
        return [r for r in validate_terraform(files, 'gcp') if r.status == 'fail']

    def test_valid_gcp_has_no_failures(self):
        fails = self._fails(self._gen())
        self.assertEqual(fails, [],
            msg='\n'.join(f'{f.group} / {f.name}: {f.error}' for f in fails))

    def test_valid_gcp_passes_provider_check(self):
        results = validate_terraform(self._gen(), 'gcp')
        ok = [r for r in results if r.group == 'Provider' and 'google' in r.name and r.status == 'pass']
        self.assertTrue(len(ok) > 0)

    def test_valid_gcp_passes_file_structure(self):
        results = validate_terraform(self._gen(), 'gcp')
        fails = [r for r in results if r.group == 'File Structure' and r.status == 'fail']
        self.assertEqual(fails, [])

    def test_valid_gcp_passes_hcl_syntax(self):
        results = validate_terraform(self._gen(), 'gcp')
        fails = [r for r in results if r.group == 'HCL Syntax' and r.status == 'fail']
        self.assertEqual(fails, [])

    def test_missing_root_main_detected(self):
        files = self._gen()
        del files['main.tf']
        self.assertTrue(any('main.tf' in f.name for f in self._fails(files)))

    def test_missing_module_file_detected(self):
        files = self._gen()
        del files[f'modules/{_GCP_MOD_NET}/main.tf']
        self.assertTrue(any(_GCP_MOD_NET in f.name for f in self._fails(files)))

    def test_wrong_provider_detected(self):
        files = self._gen()
        files['main.tf'] = files['main.tf'].replace('hashicorp/google', 'hashicorp/aws')
        self.assertTrue(any('google' in f.name for f in self._fails(files)))

    def test_odb_network_resource_in_module(self):
        files = self._gen()
        self.assertIn('google_oracle_database_odb_network',
                      files[f'modules/{_GCP_MOD_NET}/main.tf'])

    def test_exadata_infra_resource_in_module(self):
        files = self._gen()
        self.assertIn('google_oracle_database_cloud_exadata_infrastructure',
                      files[f'modules/{_GCP_MOD_INFRA}/main.tf'])

    def test_vm_cluster_resource_in_module(self):
        files = self._gen()
        self.assertIn('google_oracle_database_cloud_vm_cluster',
                      files[f'modules/{_GCP_MOD_CLUSTER}/main.tf'])

    def test_multi_resource_keeps_fixed_file_count(self):
        files = self._gen(net_count=2, infra_count=2, cluster_count=2)
        self.assertEqual(len(files), 13)

    def test_summary_structure_complete(self):
        s = summarise(validate_terraform(self._gen(), 'gcp'))
        for key in ('passed', 'failed', 'warned', 'total', 'results'):
            self.assertIn(key, s)

    def test_summary_passed_greater_than_zero(self):
        s = summarise(validate_terraform(self._gen(), 'gcp'))
        self.assertGreater(s['passed'], 0)


if __name__ == '__main__':
    unittest.main()
