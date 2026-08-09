"""Region / zone catalogues loaded from config/<cloud>_regions.json."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import regions
from regions import RegionConfigError
from clouds.aws.generator import _oci_region_for as aws_oci_region
from clouds.gcp.generator import _oci_region_for as gcp_oci_region
from app import app

CLOUDS = ('aws', 'azure', 'gcp')


class TestCataloguesLoad(unittest.TestCase):
    """Shape rules that hold for every cloud."""

    def test_all_catalogues_non_empty(self):
        for cloud in CLOUDS:
            self.assertGreater(len(regions.regions(cloud)), 0, cloud)

    def test_every_entry_has_required_fields(self):
        for cloud in CLOUDS:
            for r in regions.regions(cloud):
                for field in ('region', 'label', 'zones', 'status'):
                    self.assertIn(field, r, f'{cloud}/{r.get("region")} missing {field}')

    def test_region_codes_unique(self):
        for cloud in CLOUDS:
            codes = [r['region'] for r in regions.regions(cloud)]
            self.assertEqual(len(codes), len(set(codes)), cloud)

    def test_status_values_valid(self):
        for cloud in CLOUDS:
            for r in regions.regions(cloud):
                self.assertIn(r['status'], ('live', 'planned'), f'{cloud}/{r["region"]}')

    def test_planned_regions_have_no_zones(self):
        # A planned region is not selectable, so offering zones for it would be
        # a dropdown that leads nowhere.
        for cloud in CLOUDS:
            for r in regions.regions(cloud):
                if r['status'] == 'planned':
                    self.assertEqual(r['zones'], [],
                                     f'{cloud}/{r["region"]} is planned but lists zones')

    def test_zones_are_lists(self):
        for cloud in CLOUDS:
            for r in regions.regions(cloud):
                self.assertIsInstance(r['zones'], list, f'{cloud}/{r["region"]}')


class TestGloballyUniqueZones(unittest.TestCase):
    """AWS AZ IDs and GCP zones are globally unique; Azure numbers are not."""

    def test_zones_unique_for_aws_and_gcp(self):
        for cloud in ('aws', 'gcp'):
            zs = [z for r in regions.regions(cloud) for z in r['zones']]
            self.assertEqual(len(zs), len(set(zs)), cloud)

    def test_zone_to_region_round_trips(self):
        for cloud in ('aws', 'gcp'):
            zmap, z2r = regions.zone_map(cloud), regions.zone_to_region(cloud)
            for code, zs in zmap.items():
                for z in zs:
                    self.assertEqual(z2r[z], code, f'{cloud}/{z}')

    def test_azure_reuses_zone_numbers_across_regions(self):
        # Not a defect: '1' in eastus is unrelated to '1' in uksouth. This is why
        # the catalogue sets zones_are_region_scoped and skips the uniqueness check.
        zs = [z for r in regions.regions('azure') for z in r['zones']]
        self.assertGreater(len(zs), len(set(zs)))

    def test_azure_zone_map_keeps_regions_separate(self):
        zmap = regions.zone_map('azure')
        self.assertEqual(zmap['eastus'], ['1', '3'])
        self.assertEqual(zmap['uksouth'], ['1', '2'])


class TestOciRegionMapping(unittest.TestCase):
    """The catalogues replaced hardcoded dicts; behaviour must be unchanged."""

    OLD_AWS = {
        'us-east-1': 'us-ashburn-1',        'us-east-2': 'us-chicago-1',
        'us-west-1': 'us-sanjose-1',        'us-west-2': 'us-portland-1',
        'eu-west-1': 'eu-frankfurt-1',      'eu-central-1': 'eu-frankfurt-1',
        'ap-southeast-1': 'ap-singapore-1', 'ap-northeast-1': 'ap-tokyo-1',
    }
    OLD_GCP = {
        'us-east4': 'us-ashburn-1',                  'us-central1': 'us-desmoines-1',
        'us-west3': 'us-saltlake-2',                 'northamerica-northeast1': 'ca-montreal-1',
        'northamerica-northeast2': 'ca-toronto-1',   'europe-west3': 'eu-frankfurt-1',
        'europe-west2': 'uk-london-1',               'europe-west8': 'eu-milan-1',
        'asia-south2': 'ap-delhi-1',                 'australia-southeast2': 'ap-melbourne-1',
        'asia-south1': 'ap-mumbai-1',                'asia-northeast2': 'ap-osaka-1',
        'australia-southeast1': 'ap-sydney-1',       'asia-northeast1': 'ap-tokyo-1',
        'southamerica-east1': 'sa-saopaulo-1',
    }

    def test_aws_matches_previous_hardcoded_mapping(self):
        for r in regions.regions('aws'):
            code = r['region']
            self.assertEqual(aws_oci_region(code),
                             self.OLD_AWS.get(code, 'us-ashburn-1'), code)

    def test_gcp_matches_previous_hardcoded_mapping(self):
        for r in regions.regions('gcp'):
            code = r['region']
            self.assertEqual(gcp_oci_region(code),
                             self.OLD_GCP.get(code, 'us-ashburn-1'), code)

    def test_unknown_region_falls_back_to_default(self):
        self.assertEqual(aws_oci_region('no-such-region-1'), regions.default_oci_region('aws'))
        self.assertEqual(gcp_oci_region('no-such-region-1'), regions.default_oci_region('gcp'))

    def test_gcp_live_regions_all_mapped(self):
        # Unlike AWS, GCP's mapping is complete - a null here means a live region
        # would silently generate an OCI provider pointing at Ashburn.
        for r in regions.regions('gcp'):
            if r['status'] == 'live':
                self.assertTrue(r['oci_region'], f'{r["region"]} is live but unmapped')

    def test_mapped_and_unmapped_partition_the_catalogue(self):
        for cloud in ('aws', 'gcp'):
            mapped = set(regions.to_oci_region(cloud))
            unmapped = set(regions.unmapped_oci_regions(cloud))
            self.assertEqual(mapped & unmapped, set(), cloud)
            self.assertEqual(len(mapped) + len(unmapped), len(regions.regions(cloud)), cloud)


class TestValidationRejectsBadConfig(unittest.TestCase):
    """Malformed config fails at load, rather than rendering an empty dropdown."""

    def _load(self, doc):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / 'bad_regions.json').write_text(json.dumps(doc), encoding='utf-8')
            orig, regions.CONFIG_DIR = regions.CONFIG_DIR, Path(td)
            try:
                return regions.load('bad', refresh=True)
            finally:
                regions.CONFIG_DIR = orig
                regions._cache.pop('bad', None)

    def test_missing_regions_key(self):
        with self.assertRaises(RegionConfigError):
            self._load({'nope': []})

    def test_empty_regions(self):
        with self.assertRaises(RegionConfigError):
            self._load({'regions': []})

    def test_duplicate_region_code(self):
        e = {'region': 'us-east-1', 'label': 'x', 'zones': [], 'status': 'live'}
        with self.assertRaises(RegionConfigError):
            self._load({'regions': [e, dict(e)]})

    def test_duplicate_zone_across_regions(self):
        with self.assertRaises(RegionConfigError):
            self._load({'regions': [
                {'region': 'a', 'label': 'A', 'zones': ['z1'], 'status': 'live'},
                {'region': 'b', 'label': 'B', 'zones': ['z1'], 'status': 'live'},
            ]})

    def test_duplicate_zone_allowed_when_region_scoped(self):
        doc = self._load({
            'zones_are_region_scoped': True,
            'regions': [
                {'region': 'a', 'label': 'A', 'zones': ['1'], 'status': 'live'},
                {'region': 'b', 'label': 'B', 'zones': ['1'], 'status': 'live'},
            ]})
        self.assertEqual(len(doc['regions']), 2)

    def test_bad_status(self):
        with self.assertRaises(RegionConfigError):
            self._load({'regions': [
                {'region': 'a', 'label': 'A', 'zones': [], 'status': 'maybe'}]})

    def test_zones_not_a_list(self):
        with self.assertRaises(RegionConfigError):
            self._load({'regions': [
                {'region': 'a', 'label': 'A', 'zones': 'one', 'status': 'live'}]})

    def test_missing_field(self):
        with self.assertRaises(RegionConfigError):
            self._load({'regions': [{'region': 'a', 'label': 'A', 'zones': []}]})

    def test_missing_file(self):
        with self.assertRaises(RegionConfigError):
            regions.load('does-not-exist', refresh=True)


class TestPagesRenderCatalogue(unittest.TestCase):

    PAGES = (('/aws', 'ODB_REGIONS', 'aws'),
             ('/azure', 'AZURE_REGIONS', 'azure'),
             ('/gcp', 'GCP_REGIONS', 'gcp'))

    def setUp(self):
        self.client = app.test_client()

    def test_pages_embed_their_catalogue(self):
        for path, const, _ in self.PAGES:
            html = self.client.get(path).get_data(as_text=True)
            self.assertIn(f'const {const} = [', html, path)

    def test_no_unrendered_jinja_left(self):
        for path, _, cloud in self.PAGES:
            html = self.client.get(path).get_data(as_text=True)
            self.assertNotIn(f'{cloud}_regions_json', html, path)

    def test_every_region_reaches_the_page(self):
        for path, _, cloud in self.PAGES:
            html = self.client.get(path).get_data(as_text=True)
            for r in regions.regions(cloud):
                self.assertIn(f'"{r["region"]}"', html, f'{path} {r["region"]}')

    def test_every_zone_reaches_the_page(self):
        for path, _, cloud in self.PAGES:
            html = self.client.get(path).get_data(as_text=True)
            for r in regions.regions(cloud):
                for z in r['zones']:
                    self.assertIn(f'"{z}"', html, f'{path} {z}')

    def test_azure_groups_survive(self):
        # The location dropdown builds its optgroups from this field.
        html = self.client.get('/azure').get_data(as_text=True)
        for group in {r['group'] for r in regions.regions('azure')}:
            self.assertIn(group, html)


if __name__ == '__main__':
    unittest.main()
