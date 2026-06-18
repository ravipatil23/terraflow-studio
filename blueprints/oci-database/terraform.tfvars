# ─────────────────────────────────────────────────────────────────────────────
# Oracle Database (DB Home -> CDB -> PDB) — fill in your values here.
# Passwords are NOT set here — export them as environment variables:
#   export TF_VAR_admin_password='YourStr0ng#Pass1'
#   export TF_VAR_pdb_admin_password='YourStr0ng#Pass2'
# ─────────────────────────────────────────────────────────────────────────────

oci_region      = "us-ashburn-1"
vm_cluster_ocid = "ocid1.cloudvmcluster.oc1.iad.xxxxxxxx" # from your VM cluster blueprint output

# ── DB Home ───────────────────────────────────────────────────────────────────
db_home_display_name = "dbhome-prod"
db_version           = "19.28.0.0.0"

# ── Container Database ─────────────────────────────────────────────────────────
db_name        = "ORCL"
character_set  = "AL32UTF8"
ncharacter_set = "AL16UTF16"
# initial_pdb_name     = "PDB0"     # optional PDB created together with the CDB
# auto_backup_enabled  = true
# auto_backup_window   = "SLOT_TWO"
# recovery_window_in_days = 30

# ── Pluggable Database ─────────────────────────────────────────────────────────
create_pdb = true
pdb_name   = "PDB1"
