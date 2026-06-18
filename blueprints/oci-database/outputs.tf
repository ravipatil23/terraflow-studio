output "db_home_id" {
  description = "OCID of the single Database Home."
  value       = module.db_home.db_home_id
}

output "cdbs" {
  description = "Container Databases keyed by their cdbs map key."
  value = { for k, v in module.cdb : k => {
    cdb_id  = v.cdb_id
    db_name = v.db_name
  } }
}

output "pdbs" {
  description = "Pluggable Databases keyed by \"<cdbKey>.<pdbKey>\"."
  value = { for k, v in module.pdb : k => {
    pdb_id   = v.pdb_id
    pdb_name = v.pdb_name
  } }
}
