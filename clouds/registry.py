"""What app.py needs to know about each cloud, in one table.

Generation and download used to be if/elif chains repeated in several routes, so
adding a cloud meant finding every chain and remembering to extend it. They are
now lookups against this registry: one entry per cloud, and a missing entry fails
visibly rather than silently falling through to AWS.

The registry imports the cloud packages; no cloud package imports the registry.
That direction matters - it is what keeps the clouds unaware of each other.
"""
from dataclasses import dataclass
from typing import Callable, Optional

from generators.aws_gen import generate_aws_tf
from generators.gcp_gen import generate_gcp_tf
from generators.azure_gen import generate_azure_tf
from oci import generate_oci_db_tf, generate_oci_dg_tf

import clouds.aws.validator as _aws_validator
import clouds.gcp.validator as _gcp_validator
import clouds.azure.validator as _azure_validator


@dataclass(frozen=True)
class CloudSpec:
    """Everything the generic routes need in order to serve one cloud."""

    name: str
    generate: Callable[[dict], dict]
    zip_name: str
    #: None where a product is validated in the browser only. Distinct from a
    #: no-op so "nothing to check here" cannot be confused with a missing entry.
    validate: Optional[Callable[[dict, dict], None]] = None


REGISTRY = {
    spec.name: spec for spec in (
        CloudSpec('aws',   generate_aws_tf,    'terraflow-studio-aws',
                  _aws_validator.validate),
        CloudSpec('gcp',   generate_gcp_tf,    'terraflow-studio-gcp',
                  _gcp_validator.validate),
        CloudSpec('azure', generate_azure_tf,  'terraflow-studio-azure',
                  _azure_validator.validate),
        CloudSpec('oci',   generate_oci_db_tf, 'terraflow-studio-oci'),
        CloudSpec('dg',    generate_oci_dg_tf, 'terraflow-studio-dg'),
    )
}

DEFAULT_CLOUD = 'aws'


def get(cloud):
    """Spec for `cloud`, falling back to AWS as the routes have always done."""
    return REGISTRY.get(cloud) or REGISTRY[DEFAULT_CLOUD]
