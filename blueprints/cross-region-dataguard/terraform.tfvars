# ─────────────────────────────────────────────────────────────────────────────
# Cross-Region Data Guard networking — fill in your values here. This is the ONLY
# file you normally edit.
#
# These resources connect TWO EXISTING Exadata VM cluster VCNs (one per region).
# Create the VM clusters first (see ../db-at-aws or your OCI Exadata setup), then
# supply their VCN / NSG / route-table OCIDs and client CIDRs below.
# ─────────────────────────────────────────────────────────────────────────────

prefix         = "acme-dg"
compartment_id = "ocid1.compartment.oc1..xxxxxxxx"

primary_region = "us-ashburn-1"
dr_region      = "us-phoenix-1"

# ── Primary region (existing VM cluster) ──────────────────────────────────────
primary_vcn_id         = "ocid1.vcn.oc1.iad.xxxxxxxx"
primary_nsg_id         = "ocid1.networksecuritygroup.oc1.iad.xxxxxxxx"
primary_client_cidr    = "10.10.1.0/24"
primary_route_table_id = "ocid1.routetable.oc1.iad.xxxxxxxx" # default RT of the primary VCN (import before apply)
primary_hub_cidr       = "10.15.0.0/24"                      # NEW transit VCN — must not overlap anything

# ── DR region (existing VM cluster) ───────────────────────────────────────────
dr_vcn_id         = "ocid1.vcn.oc1.phx.xxxxxxxx"
dr_nsg_id         = "ocid1.networksecuritygroup.oc1.phx.xxxxxxxx"
dr_client_cidr    = "10.30.1.0/24"
dr_route_table_id = "ocid1.routetable.oc1.phx.xxxxxxxx" # default RT of the DR VCN (import before apply)
dr_hub_cidr       = "10.16.0.0/24"                      # NEW transit VCN — must not overlap anything

# ── Toggles ───────────────────────────────────────────────────────────────────
# manage_route_table = true  -> Terraform manages the cluster VCN default route
#   tables. You MUST import both before the first apply (see README), or set this
#   to false and add the single DG route by hand after apply.
manage_route_table = true

# add_ssh = true -> also open TCP 22 between regions (default: only TCP 1521).
add_ssh = false
