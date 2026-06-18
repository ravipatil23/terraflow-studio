# ─────────────────────────────────────────────────────────────────────────────
# Multi-AZ (same-region) Data Guard networking — fill in your values here.
# Connects two EXISTING Exadata VM cluster VCNs in two ADs of the same region.
# ─────────────────────────────────────────────────────────────────────────────

prefix         = "acme-dg"
oci_region     = "us-ashburn-1"
compartment_id = "ocid1.compartment.oc1..xxxxxxxx"

# ── Primary AD (existing VM cluster) ──────────────────────────────────────────
primary_vcn_id         = "ocid1.vcn.oc1.iad.xxxxxxxx"
primary_nsg_id         = "ocid1.networksecuritygroup.oc1.iad.xxxxxxxx"
primary_client_cidr    = "10.10.1.0/24"
primary_route_table_id = "ocid1.routetable.oc1.iad.xxxxxxxx" # default RT of the primary VCN (import before apply)

# ── Standby AD (existing VM cluster) ──────────────────────────────────────────
standby_vcn_id         = "ocid1.vcn.oc1.iad.yyyyyyyy"
standby_nsg_id         = "ocid1.networksecuritygroup.oc1.iad.yyyyyyyy"
standby_client_cidr    = "10.20.1.0/24"
standby_route_table_id = "ocid1.routetable.oc1.iad.yyyyyyyy" # default RT of the standby VCN (import before apply)

# ── Toggles ───────────────────────────────────────────────────────────────────
# manage_route_table = true  -> Terraform manages both default route tables.
#   You MUST import both before the first apply (see README), or set it to false
#   and add the single DG route to each VCN by hand after apply.
manage_route_table = true

# add_ssh = true -> also open TCP 22 between the two subnets (default: only 1521).
add_ssh = false
