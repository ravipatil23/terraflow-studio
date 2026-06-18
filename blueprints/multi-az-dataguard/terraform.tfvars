# ─────────────────────────────────────────────────────────────────────────────
# Multi-AZ (same-region) Data Guard networking — fill in your values here.
# Connects two EXISTING Exadata VM cluster VCNs in two ADs of the same region.
#
# This blueprint does NOT manage the VM cluster VCN route tables — after apply,
# add one Data Guard route to each VCN manually (see the README).
# ─────────────────────────────────────────────────────────────────────────────

prefix         = "acme-dg"
oci_region     = "us-ashburn-1"
compartment_id = "ocid1.compartment.oc1..xxxxxxxx"

# ── Primary AD (existing VM cluster) ──────────────────────────────────────────
primary_vcn_id      = "ocid1.vcn.oc1.iad.xxxxxxxx"
primary_nsg_id      = "ocid1.networksecuritygroup.oc1.iad.xxxxxxxx"
primary_client_cidr = "10.10.1.0/24"

# ── Standby AD (existing VM cluster) ──────────────────────────────────────────
standby_vcn_id      = "ocid1.vcn.oc1.iad.yyyyyyyy"
standby_nsg_id      = "ocid1.networksecuritygroup.oc1.iad.yyyyyyyy"
standby_client_cidr = "10.20.1.0/24"

# add_ssh = true -> also open TCP 22 between the two subnets (default: only 1521).
add_ssh = false
