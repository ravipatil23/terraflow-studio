"""OCI Data Guard generator — cross-region and multi-AZ networking."""
import datetime
from .helpers import render_tf


# ── Defaults ──────────────────────────────────────────────────────────────────

def _dg_maz_defaults(d):
    return {**d,
        'prefix':                 d.get('prefix') or 'dg',
        'oci_region':             d.get('oci_region') or 'us-ashburn-1',
        'compartment_id':         d.get('compartment_id') or '',
        'primary_vcn_id':         d.get('primary_vcn_id') or '',
        'primary_nsg_id':         d.get('primary_nsg_id') or '',
        'primary_client_cidr':    d.get('primary_client_cidr') or '10.10.1.0/24',
        'primary_route_table_id': d.get('primary_route_table_id') or '',
        'standby_vcn_id':         d.get('standby_vcn_id') or '',
        'standby_nsg_id':         d.get('standby_nsg_id') or '',
        'standby_client_cidr':    d.get('standby_client_cidr') or '10.20.1.0/24',
        'standby_route_table_id': d.get('standby_route_table_id') or '',
        'add_ssh':                bool(d.get('add_ssh', False)),
    }


def _dg_cr_defaults(d):
    return {**d,
        'prefix':                   d.get('prefix') or 'dg',
        'primary_oci_region':       d.get('primary_oci_region') or 'us-ashburn-1',
        'standby_oci_region':       d.get('standby_oci_region') or 'us-portland-1',
        'compartment_id':           d.get('compartment_id') or '',
        'primary_vcn_id':           d.get('primary_vcn_id') or '',
        'primary_nsg_id':           d.get('primary_nsg_id') or '',
        'primary_client_cidr':      d.get('primary_client_cidr') or '10.10.1.0/24',
        'primary_route_table_id':   d.get('primary_route_table_id') or '',
        'primary_hub_cidr':         d.get('primary_hub_cidr') or '10.15.0.0/24',
        'standby_vcn_id':           d.get('standby_vcn_id') or '',
        'standby_nsg_id':           d.get('standby_nsg_id') or '',
        'standby_client_cidr':      d.get('standby_client_cidr') or '10.30.1.0/24',
        'standby_route_table_id':   d.get('standby_route_table_id') or '',
        'standby_hub_cidr':         d.get('standby_hub_cidr') or '10.16.0.0/24',
        'add_ssh':                  bool(d.get('add_ssh', False)),
    }


# ── DG Multi-AZ ───────────────────────────────────────────────────────────────

def dg_maz_main(mn, d):
    return render_tf('aws_dg_multi_az/main.tf.j2',
        prefix=d.get('prefix', 'dg'),
        add_ssh=d.get('add_ssh', False),
        primary_route_table_id=d.get('primary_route_table_id', ''),
        standby_route_table_id=d.get('standby_route_table_id', ''),
    )


def dg_maz_vars(mn, d):
    return render_tf('aws_dg_multi_az/variables.tf.j2',
        prefix=d.get('prefix', 'dg'),
        oci_region=d.get('oci_region', ''),
        compartment_id=d.get('compartment_id', ''),
        primary_vcn_id=d.get('primary_vcn_id', ''),
        primary_nsg_id=d.get('primary_nsg_id', ''),
        primary_client_cidr=d.get('primary_client_cidr', '10.10.1.0/24'),
        primary_route_table_id=d.get('primary_route_table_id', ''),
        standby_vcn_id=d.get('standby_vcn_id', ''),
        standby_nsg_id=d.get('standby_nsg_id', ''),
        standby_client_cidr=d.get('standby_client_cidr', '10.20.1.0/24'),
        standby_route_table_id=d.get('standby_route_table_id', ''),
    )


def dg_maz_outputs(mn):
    return render_tf('aws_dg_multi_az/outputs.tf.j2')


def dg_maz_readme(mn, d):
    return render_tf('aws_dg_multi_az/README.md.j2',
        prefix=d.get('prefix', 'dg'),
        customer_name=d.get('customer_name', ''),
        oci_region=d.get('oci_region', ''),
        primary_client_cidr=d.get('primary_client_cidr', '10.10.1.0/24'),
        primary_route_table_id=d.get('primary_route_table_id', ''),
        standby_client_cidr=d.get('standby_client_cidr', '10.20.1.0/24'),
        standby_route_table_id=d.get('standby_route_table_id', ''),
        add_ssh=d.get('add_ssh', False),
        generated_date=datetime.date.today().isoformat(),
    )


def dg_maz_tfvars(mn, d):
    return render_tf('aws_dg_multi_az/terraform.tfvars.j2',
        prefix=d.get('prefix', 'dg'),
        oci_region=d.get('oci_region', ''),
        compartment_id=d.get('compartment_id', ''),
        primary_vcn_id=d.get('primary_vcn_id', ''),
        primary_nsg_id=d.get('primary_nsg_id', ''),
        primary_client_cidr=d.get('primary_client_cidr', '10.10.1.0/24'),
        primary_route_table_id=d.get('primary_route_table_id', ''),
        standby_vcn_id=d.get('standby_vcn_id', ''),
        standby_nsg_id=d.get('standby_nsg_id', ''),
        standby_client_cidr=d.get('standby_client_cidr', '10.20.1.0/24'),
        standby_route_table_id=d.get('standby_route_table_id', ''),
    )


# ── DG Cross-Region: reusable child modules ───────────────────────────────────

def dg_cr_region_main(d):
    return render_tf('oci_dg_region/main.tf.j2',
        add_ssh=d.get('add_ssh', False),
    )


def dg_cr_region_vars():
    return render_tf('oci_dg_region/variables.tf.j2')


def dg_cr_region_outputs():
    return render_tf('oci_dg_region/outputs.tf.j2')


def dg_cr_peering_main():
    return render_tf('oci_dg_peering/main.tf.j2')


def dg_cr_peering_vars():
    return render_tf('oci_dg_peering/variables.tf.j2')


def dg_cr_peering_outputs():
    return render_tf('oci_dg_peering/outputs.tf.j2')


# ── DG Cross-Region: root module ─────────────────────────────────────────────

def dg_cr_root_main():
    return render_tf('oci_dg_root/main.tf.j2')


def dg_cr_root_vars(d):
    return render_tf('oci_dg_root/variables.tf.j2',
        prefix=d.get('prefix', 'dg'),
        compartment_id=d.get('compartment_id', ''),
        primary_oci_region=d.get('primary_oci_region', ''),
        standby_oci_region=d.get('standby_oci_region', ''),
        primary_vcn_id=d.get('primary_vcn_id', ''),
        primary_nsg_id=d.get('primary_nsg_id', ''),
        primary_client_cidr=d.get('primary_client_cidr', '10.10.1.0/24'),
        primary_route_table_id=d.get('primary_route_table_id', ''),
        primary_hub_cidr=d.get('primary_hub_cidr', '10.15.0.0/24'),
        standby_vcn_id=d.get('standby_vcn_id', ''),
        standby_nsg_id=d.get('standby_nsg_id', ''),
        standby_client_cidr=d.get('standby_client_cidr', '10.30.1.0/24'),
        standby_route_table_id=d.get('standby_route_table_id', ''),
        standby_hub_cidr=d.get('standby_hub_cidr', '10.16.0.0/24'),
    )


def dg_cr_root_tfvars(d):
    return render_tf('oci_dg_root/terraform.tfvars.j2',
        prefix=d.get('prefix', 'dg'),
        compartment_id=d.get('compartment_id', ''),
        primary_oci_region=d.get('primary_oci_region', ''),
        standby_oci_region=d.get('standby_oci_region', ''),
        primary_vcn_id=d.get('primary_vcn_id', ''),
        primary_nsg_id=d.get('primary_nsg_id', ''),
        primary_client_cidr=d.get('primary_client_cidr', '10.10.1.0/24'),
        primary_route_table_id=d.get('primary_route_table_id', ''),
        primary_hub_cidr=d.get('primary_hub_cidr', '10.15.0.0/24'),
        standby_vcn_id=d.get('standby_vcn_id', ''),
        standby_nsg_id=d.get('standby_nsg_id', ''),
        standby_client_cidr=d.get('standby_client_cidr', '10.30.1.0/24'),
        standby_route_table_id=d.get('standby_route_table_id', ''),
        standby_hub_cidr=d.get('standby_hub_cidr', '10.16.0.0/24'),
    )


def dg_cr_root_readme(d):
    return render_tf('oci_dg_root/README.md.j2',
        prefix=d.get('prefix', 'dg'),
        customer_name=d.get('customer_name', ''),
        primary_oci_region=d.get('primary_oci_region', 'us-ashburn-1'),
        standby_oci_region=d.get('standby_oci_region', 'us-portland-1'),
        primary_client_cidr=d.get('primary_client_cidr', '10.10.1.0/24'),
        primary_hub_cidr=d.get('primary_hub_cidr', '10.15.0.0/24'),
        primary_route_table_id=d.get('primary_route_table_id', ''),
        standby_client_cidr=d.get('standby_client_cidr', '10.30.1.0/24'),
        standby_hub_cidr=d.get('standby_hub_cidr', '10.16.0.0/24'),
        standby_route_table_id=d.get('standby_route_table_id', ''),
        generated_date=datetime.date.today().isoformat(),
    )


# ── Main entry point ──────────────────────────────────────────────────────────

def generate_oci_dg_tf(data: dict) -> dict:
    """Return a files dict for all OCI Data Guard modules present in data."""
    files = {}

    for dg in (data.get('aws_dg_multi_az') or data.get('dg_multi_az') or []):
        dg = _dg_maz_defaults(dg)
        mn = dg.get('module_name', 'primary')
        files[f'dg_multi_az_{mn}/main.tf']          = dg_maz_main(mn, dg)
        files[f'dg_multi_az_{mn}/variables.tf']     = dg_maz_vars(mn, dg)
        files[f'dg_multi_az_{mn}/outputs.tf']       = dg_maz_outputs(mn)
        files[f'dg_multi_az_{mn}/terraform.tfvars'] = dg_maz_tfvars(mn, dg)
        files[f'dg_multi_az_{mn}/README.md']        = dg_maz_readme(mn, dg)

    for dg in (data.get('aws_dg_cross_region') or data.get('dg_cross_region') or []):
        dg = _dg_cr_defaults(dg)
        mn = dg.get('module_name', 'dg')
        base = f'dg_cross_region_{mn}'
        files[f'{base}/main.tf']                            = dg_cr_root_main()
        files[f'{base}/variables.tf']                       = dg_cr_root_vars(dg)
        files[f'{base}/terraform.tfvars']                   = dg_cr_root_tfvars(dg)
        files[f'{base}/README.md']                          = dg_cr_root_readme(dg)
        files[f'{base}/modules/oci-dg-region/main.tf']      = dg_cr_region_main(dg)
        files[f'{base}/modules/oci-dg-region/variables.tf'] = dg_cr_region_vars()
        files[f'{base}/modules/oci-dg-region/outputs.tf']   = dg_cr_region_outputs()
        files[f'{base}/modules/oci-dg-peering/main.tf']     = dg_cr_peering_main()
        files[f'{base}/modules/oci-dg-peering/variables.tf'] = dg_cr_peering_vars()
        files[f'{base}/modules/oci-dg-peering/outputs.tf']  = dg_cr_peering_outputs()

    return files
