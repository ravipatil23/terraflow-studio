# ─────────────────────────────────────────────────────────────────────────────
# Oracle Database — many DB Homes, each with many CDBs, each with many PDBs.
#
# Scale by editing this file only:
#   • add a DB Home -> add an entry to `db_homes`
#   • add a CDB     -> add an entry to that home's nested `cdbs` map
#   • add a PDB     -> add an entry to that CDB's nested `pdbs` map
#
# Commented lines inside the entries show OPTIONAL parameters with default/sample
# values — uncomment and edit any you need.
#
# Passwords are NOT set here — supply them as JSON via environment variables, keyed
# to match the map keys ("<home>.<cdb>" for CDBs, "<home>.<cdb>.<pdb>" for PDBs):
#   export TF_VAR_cdb_admin_passwords='{"home19.sales":"Str0ng#1","home19.hr":"Str0ng#2","home23.dw":"Str0ng#3"}'
#   export TF_VAR_pdb_admin_passwords='{"home19.sales.app":"Str0ng#4","home19.sales.rpt":"Str0ng#5","home19.hr.emp":"Str0ng#6","home23.dw.mart":"Str0ng#7"}'
# ─────────────────────────────────────────────────────────────────────────────

oci_region      = "us-ashburn-1"
vm_cluster_ocid = "ocid1.cloudvmcluster.oc1.iad.xxxxxxxx" # default cluster for all homes

# ── DB Homes (each its own Oracle version), their CDBs, and their PDBs ─────────
db_homes = {
  home19 = {
    db_version = "19.28.0.0.0"

    # ── optional per-home (defaults shown) ──
    # display_name    = "home19"                                  # defaults to the home key
    # vm_cluster_ocid = "ocid1.cloudvmcluster.oc1.iad.yyyyyyyy"   # put this home on a different cluster

    cdbs = {
      sales = {
        db_name = "SALES"

        # ── optional per-CDB (defaults shown) ──
        # character_set           = "AL32UTF8"
        # ncharacter_set          = "AL16UTF16"
        # db_unique_name          = ""           # defaults to db_name
        # sid_prefix              = ""
        # auto_backup_enabled     = false
        # auto_backup_window      = "SLOT_TWO"   # used only when auto_backup_enabled = true
        # recovery_window_in_days = 30           # used only when auto_backup_enabled = true

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
  }

  home23 = {
    db_version = "23.0.0.0"
    cdbs = {
      dw = {
        db_name = "DW"
        pdbs = {
          mart = { pdb_name = "DWMART" }
        }
      }
    }
  }
}
