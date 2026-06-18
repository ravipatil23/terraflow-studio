# ─────────────────────────────────────────────────────────────────────────────
# Oracle Database — one DB Home, many CDBs, each with many PDBs.
#
# Scale by editing this file only:
#   • add a CDB   -> add an entry to `cdbs`
#   • add a PDB   -> add an entry to that CDB's nested `pdbs` map
#
# Passwords are NOT set here — supply them as JSON via environment variables, keyed
# to match the map keys below:
#   export TF_VAR_cdb_admin_passwords='{"sales":"Str0ng#Pass1","hr":"Str0ng#Pass2"}'
#   export TF_VAR_pdb_admin_passwords='{"sales.app":"Str0ng#Pass3","sales.rpt":"Str0ng#Pass4","hr.emp":"Str0ng#Pass5"}'
# ─────────────────────────────────────────────────────────────────────────────

oci_region      = "us-ashburn-1"
vm_cluster_ocid = "ocid1.cloudvmcluster.oc1.iad.xxxxxxxx" # from your VM cluster blueprint output

# ── The single DB Home ────────────────────────────────────────────────────────
db_home_display_name = "dbhome-prod"
db_version           = "19.28.0.0.0"

# ── CDBs and their PDBs ───────────────────────────────────────────────────────
cdbs = {
  sales = {
    db_name = "SALES"
    pdbs = {
      app = { pdb_name = "SALESAPP" }
      rpt = { pdb_name = "SALESRPT" }
    }
  }

  hr = {
    db_name             = "HR"
    auto_backup_enabled = true
    pdbs = {
      emp = { pdb_name = "HREMP" }
    }
  }
}
