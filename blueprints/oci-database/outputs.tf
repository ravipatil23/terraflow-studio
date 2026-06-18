output "db_home_id" {
  description = "OCID of the Database Home."
  value       = module.db_home.db_home_id
}

output "cdb_id" {
  description = "OCID of the Container Database."
  value       = module.cdb.cdb_id
}

output "db_name" {
  description = "Name of the Container Database."
  value       = module.cdb.db_name
}

output "pdb_id" {
  description = "OCID of the Pluggable Database (null when create_pdb = false)."
  value       = var.create_pdb ? module.pdb[0].pdb_id : null
}

output "pdb_name" {
  description = "Name of the Pluggable Database (null when create_pdb = false)."
  value       = var.create_pdb ? module.pdb[0].pdb_name : null
}
