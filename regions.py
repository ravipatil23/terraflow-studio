"""Region / availability-zone catalogue, loaded from config/*.json.

One source of truth for data that used to be duplicated: a JavaScript literal in
the page template (region and AZ dropdowns) and a Python dict in the generator
(the OCI provider region). Keeping both by hand meant they drifted - the Python
side covered 8 of the 22 regions the dropdown offered, and everything else fell
back to us-ashburn-1 without saying so.

Edit config/aws_regions.json to add a region or AZ; no code change is needed.
"""
import json
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parent / 'config'

_cache = {}


class RegionConfigError(RuntimeError):
    """Raised when a catalogue file is missing, malformed, or internally inconsistent."""


def _validate(cloud, doc):
    """Fail loudly at load time rather than silently rendering an empty dropdown."""
    if not isinstance(doc, dict) or not isinstance(doc.get('regions'), list):
        raise RegionConfigError(f'{cloud}: expected an object with a "regions" list')
    if not doc['regions']:
        raise RegionConfigError(f'{cloud}: "regions" is empty')

    seen, seen_zones = set(), {}
    for i, entry in enumerate(doc['regions']):
        where = f'{cloud}: regions[{i}]'
        for field in ('region', 'label', 'zones', 'status'):
            if field not in entry:
                raise RegionConfigError(f'{where} is missing "{field}"')
        code = entry['region']
        if code in seen:
            raise RegionConfigError(f'{where}: duplicate region "{code}"')
        seen.add(code)
        if entry['status'] not in ('live', 'planned'):
            raise RegionConfigError(
                f'{where}: status must be "live" or "planned", got "{entry["status"]}"')
        if not isinstance(entry['zones'], list):
            raise RegionConfigError(f'{where}: "zones" must be a list')
        # AWS AZ IDs and GCP zones are globally unique, so a duplicate means a
        # typo that would make the zone -> region reverse lookup silently pick
        # one. Azure reuses bare numbers ('1', '2') across every region, so the
        # check would fire on correct data and is skipped there.
        if not doc.get('zones_are_region_scoped'):
            for z in entry['zones']:
                if z in seen_zones:
                    raise RegionConfigError(
                        f'{where}: zone "{z}" already listed under "{seen_zones[z]}"')
                seen_zones[z] = code
    return doc


def load(cloud='aws', refresh=False):
    """Return the parsed catalogue for a cloud. Cached after first read."""
    if refresh:
        _cache.pop(cloud, None)
    if cloud not in _cache:
        path = CONFIG_DIR / f'{cloud}_regions.json'
        try:
            with open(path, encoding='utf-8') as fh:
                doc = json.load(fh)
        except FileNotFoundError:
            raise RegionConfigError(f'{cloud}: catalogue not found at {path}')
        except json.JSONDecodeError as exc:
            raise RegionConfigError(f'{cloud}: invalid JSON in {path} - {exc}')
        _cache[cloud] = _validate(cloud, doc)
    return _cache[cloud]


def regions(cloud='aws'):
    """Region entries in file order, without the leading _comment block."""
    return load(cloud)['regions']


def regions_json(cloud='aws'):
    """Compact JSON for embedding directly in a <script> block."""
    return json.dumps(regions(cloud), separators=(',', ':'))


def zone_map(cloud='aws'):
    """region code -> list of zones (AWS AZ IDs, Azure zone numbers, GCP zones)."""
    return {r['region']: r['zones'] for r in regions(cloud)}


def zone_to_region(cloud='aws'):
    """zone -> region code. Only meaningful where zones are globally unique.

    Azure numbers its zones per region, so this collapses there and the caller
    should use zone_map() instead.
    """
    return {z: r['region'] for r in regions(cloud) for z in r['zones']}


def default_oci_region(cloud='aws'):
    return load(cloud).get('default_oci_region', 'us-ashburn-1')


def to_oci_region(cloud='aws'):
    """AWS region -> OCI region identifier, for regions that have one mapped.

    Entries with a null oci_region are omitted, so callers keep using .get()
    with the default and behave exactly as before for unmapped regions.
    """
    return {r['region']: r['oci_region'] for r in regions(cloud) if r.get('oci_region')}


def unmapped_oci_regions(cloud='aws'):
    """Region codes with no OCI region set - these silently take the default."""
    return [r['region'] for r in regions(cloud) if not r.get('oci_region')]
