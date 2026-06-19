output "db_homes" {
  description = "Database Homes keyed by their db_homes map key."
  value = { for k, v in module.db_home : k => {
    db_home_id = v.db_home_id
  } }
}

output "cdbs" {
  description = "Container Databases keyed by \"<homeKey>.<cdbKey>\"."
  value = { for k, v in module.cdb : k => {
    cdb_id  = v.cdb_id
    db_name = v.db_name
  } }
}

output "pdbs" {
  description = "Pluggable Databases keyed by \"<homeKey>.<cdbKey>.<pdbKey>\"."
  value = { for k, v in module.pdb : k => {
    pdb_id   = v.pdb_id
    pdb_name = v.pdb_name
  } }
}
