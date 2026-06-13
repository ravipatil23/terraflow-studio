output "vm_cluster_id" {
  description = "ID of the VM cluster."
  value       = aws_odb_cloud_vm_cluster.this.id
}

output "vm_cluster_arn" {
  description = "ARN of the VM cluster."
  value       = aws_odb_cloud_vm_cluster.this.arn
}

output "ocid" {
  description = "OCI OCID of the VM cluster — used by the OCI provider for DB Home/CDB/PDB."
  value       = aws_odb_cloud_vm_cluster.this.ocid
}

output "display_name" {
  description = "Display name."
  value       = aws_odb_cloud_vm_cluster.this.display_name
}
