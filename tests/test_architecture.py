"""Dependency rules between packages.

The point of the split is that a change to one cloud cannot reach another. These
tests fail if that stops being true, which is cheaper than discovering it when an
AWS edit breaks GCP output.

    core            <- no dependencies on oci or any cloud
      ^
    oci             <- depends on core only
      ^
    generators/*    <- each cloud depends on core + oci, never on another cloud
"""
import ast
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, str(ROOT))

CLOUDS = ('aws', 'gcp', 'azure')


def _imports(path):
    """Top-level module names imported by a file, from real AST rather than grep."""
    tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name.split('.')[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:                     # relative import: same package
                names.add('.' * node.level + (node.module or ''))
            elif node.module:
                names.add(node.module.split('.')[0])
    return names


def _py_files(*parts):
    return sorted(p for p in (ROOT.joinpath(*parts)).rglob('*.py')
                  if '__pycache__' not in p.parts)


class TestCoreIsIndependent(unittest.TestCase):

    def test_core_imports_no_oci(self):
        for f in _py_files('core'):
            self.assertNotIn('oci', _imports(f), f'{f.name} imports oci')

    def test_core_imports_no_cloud(self):
        for f in _py_files('core'):
            imported = _imports(f)
            self.assertNotIn('generators', imported, f'{f.name} imports generators')
            for cloud in CLOUDS:
                self.assertNotIn(f'{cloud}_gen', imported, f'{f.name} imports {cloud}')

    def test_core_does_not_import_app(self):
        for f in _py_files('core'):
            self.assertNotIn('app', _imports(f), f'{f.name} imports app')


class TestOciIsIndependentOfClouds(unittest.TestCase):
    """OCI sits below the clouds: shared by all three, coupled to none."""

    def test_oci_imports_no_cloud_module(self):
        for f in _py_files('oci'):
            imported = _imports(f)
            self.assertNotIn('generators', imported, f'{f.name} imports generators')
            for cloud in CLOUDS:
                self.assertNotIn(f'{cloud}_gen', imported, f'{f.name} imports {cloud}_gen')

    def test_oci_renders_no_cloud_named_template(self):
        # The Data Guard templates were once called aws_dg_* despite containing
        # only oci_core_* resources. Renaming them is only durable if nothing
        # reintroduces a cloud-prefixed template path.
        #
        # Deliberately narrow: this checks render_tf() targets, not every string.
        # The <cloud>_oci_databases and <cloud>_dg_* payload keys are accepted
        # back-compat aliases and must not trip this.
        for f in _py_files('oci'):
            tree = ast.parse(f.read_text(encoding='utf-8'), filename=str(f))
            for node in ast.walk(tree):
                if (isinstance(node, ast.Call)
                        and getattr(node.func, 'id', None) == 'render_tf'
                        and node.args
                        and isinstance(node.args[0], ast.Constant)):
                    tmpl = node.args[0].value
                    for cloud in CLOUDS:
                        self.assertFalse(
                            tmpl.startswith(f'{cloud}_'),
                            f'{f.name} renders {cloud}-named template {tmpl!r}')

    def test_oci_templates_exist_under_oci_prefix(self):
        tf = ROOT / 'templates' / 'tf'
        for d in ('oci_dg_multi_az', 'oci_dg_cross_region'):
            self.assertTrue((tf / d).is_dir(), f'missing templates/tf/{d}')
        for cloud in CLOUDS:
            for d in (f'{cloud}_dg_multi_az', f'{cloud}_dg_cross_region'):
                self.assertFalse((tf / d).exists(), f'{d} should have been renamed')

    def test_dg_templates_declare_only_the_oci_provider(self):
        tf = ROOT / 'templates' / 'tf'
        for d in ('oci_dg_multi_az', 'oci_dg_cross_region'):
            main = tf / d / 'main.tf.j2'
            if not main.exists():
                continue
            src = main.read_text(encoding='utf-8')
            self.assertIn('oracle/oci', src, d)
            self.assertNotIn('hashicorp/aws', src, d)
            self.assertNotIn('hashicorp/google', src, d)
            self.assertNotIn('hashicorp/azurerm', src, d)


class TestCloudsDoNotImportEachOther(unittest.TestCase):

    def test_no_cross_cloud_imports(self):
        for cloud in CLOUDS:
            f = ROOT / 'generators' / f'{cloud}_gen.py'
            src = f.read_text(encoding='utf-8')
            for other in CLOUDS:
                if other == cloud:
                    continue
                self.assertNotIn(f'{other}_gen', src,
                                 f'{cloud}_gen imports {other}_gen')

    def test_clouds_reach_oci_through_the_package(self):
        # Importing oci.database / oci.dataguard directly bypasses the declared
        # surface in oci/__init__.py, which is what keeps the contract visible.
        for cloud in CLOUDS:
            src = (ROOT / 'generators' / f'{cloud}_gen.py').read_text(encoding='utf-8')
            self.assertNotIn('from oci.database import', src, cloud)
            self.assertNotIn('from oci.dataguard import', src, cloud)


class TestCloudPackagesAreIsolated(unittest.TestCase):
    """clouds/<cloud>/ owns that cloud's validation rules and provider schema."""

    def test_package_exists_per_cloud(self):
        for cloud in CLOUDS:
            pkg = ROOT / 'clouds' / cloud
            self.assertTrue((pkg / 'validator.py').is_file(), f'{cloud}/validator.py')
            self.assertTrue((pkg / 'schema.py').is_file(), f'{cloud}/schema.py')

    def test_no_cross_cloud_imports(self):
        for cloud in CLOUDS:
            for f in _py_files('clouds', cloud):
                src = f.read_text(encoding='utf-8')
                for other in CLOUDS:
                    if other == cloud:
                        continue
                    self.assertNotIn(f'clouds.{other}', src,
                                     f'clouds/{cloud}/{f.name} reaches into {other}')

    def test_cloud_packages_do_not_import_app(self):
        # Validation used to live in app.py. Importing back into it would
        # reintroduce the coupling this move removed, and create a cycle.
        for cloud in CLOUDS:
            for f in _py_files('clouds', cloud):
                self.assertNotIn('app', _imports(f), f'clouds/{cloud}/{f.name} imports app')

    def test_validators_expose_a_uniform_entry_point(self):
        import importlib
        for cloud in CLOUDS:
            mod = importlib.import_module(f'clouds.{cloud}.validator')
            self.assertTrue(callable(getattr(mod, 'validate', None)),
                            f'clouds/{cloud}/validator.py has no validate()')

    def test_validate_reports_errors_by_module(self):
        # Contract the /api/validate route depends on: errors is populated as
        # {module_name: {field: message}} and nothing is returned.
        import importlib
        for cloud in CLOUDS:
            mod = importlib.import_module(f'clouds.{cloud}.validator')
            errors = {}
            self.assertIsNone(mod.validate({'tab': -1}, errors), cloud)
            self.assertEqual(errors, {}, f'{cloud} invented errors for an unknown tab')

    def test_schemas_do_not_collide_across_clouds(self):
        # tf_validator merges all three into one flat dict, which is only
        # unambiguous while the resource-type names stay disjoint.
        from clouds.aws.schema import AWS_SCHEMAS
        from clouds.gcp.schema import GCP_SCHEMAS
        from clouds.azure.schema import AZURE_SCHEMAS
        pairs = (('aws', AWS_SCHEMAS), ('gcp', GCP_SCHEMAS), ('azure', AZURE_SCHEMAS))
        for i, (a, sa) in enumerate(pairs):
            for b, sb in pairs[i + 1:]:
                self.assertEqual(set(sa) & set(sb), set(),
                                 f'{a} and {b} declare the same resource type')


class TestOciPublicSurface(unittest.TestCase):
    """oci/__init__ is the contract the clouds are allowed to depend on."""

    def test_entry_points_exported(self):
        import oci
        for name in ('generate_oci_db_tf', 'generate_oci_dg_tf'):
            self.assertTrue(hasattr(oci, name), name)

    def test_everything_in_all_is_importable(self):
        import oci
        for name in oci.__all__:
            self.assertTrue(hasattr(oci, name), f'__all__ lists missing {name}')

    def test_clouds_only_use_exported_names(self):
        import oci
        exported = set(oci.__all__)
        for cloud in CLOUDS:
            src = (ROOT / 'generators' / f'{cloud}_gen.py').read_text(encoding='utf-8')
            tree = ast.parse(src)
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module == 'oci':
                    for alias in node.names:
                        self.assertIn(alias.name, exported,
                                      f'{cloud}_gen imports oci.{alias.name}, '
                                      'which is not in oci.__all__')


class TestDataGuardKeyAliases(unittest.TestCase):
    """Canonical payload keys, with the old cloud-prefixed ones still accepted."""

    def _entry(self):
        # oci_region is what _dg_maz_filled() checks; without it the generator
        # returns {} and an alias comparison would pass by comparing nothing.
        return {'module_name': 'dg1', 'display_name': 'dg',
                'oci_region': 'us-ashburn-1'}

    def test_canonical_key_accepted(self):
        from oci import generate_oci_dg_tf
        files = generate_oci_dg_tf({'dg_multi_az': [self._entry()]})
        self.assertGreater(len(files), 0)

    def test_cloud_prefixed_aliases_still_accepted(self):
        from oci import generate_oci_dg_tf
        canonical = generate_oci_dg_tf({'dg_multi_az': [self._entry()]})
        self.assertGreater(len(canonical), 0, 'fixture produced no files')
        for prefix in ('aws_', 'gcp_', 'azure_'):
            aliased = generate_oci_dg_tf({f'{prefix}dg_multi_az': [self._entry()]})
            self.assertEqual(aliased, canonical, prefix)

    def test_canonical_key_wins_over_alias(self):
        from oci import generate_oci_dg_tf
        both = generate_oci_dg_tf({
            'dg_multi_az':     [dict(self._entry(), module_name='canonical')],
            'aws_dg_multi_az': [dict(self._entry(), module_name='legacy')],
        })
        self.assertTrue(any('canonical' in k for k in both))
        self.assertFalse(any('legacy' in k for k in both))

    def test_empty_payload_produces_nothing(self):
        from oci import generate_oci_dg_tf
        self.assertEqual(generate_oci_dg_tf({}), {})


if __name__ == '__main__':
    unittest.main()
