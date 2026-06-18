terraform {
  required_providers {
    oci = {
      source  = "oracle/oci"
      version = ">= 6.0.0"
    }
  }
}

# Database Home on an existing Exadata VM cluster.
resource "oci_database_db_home" "this" {
  vm_cluster_id = var.vm_cluster_ocid
  source        = "VM_CLUSTER_NEW"
  display_name  = var.display_name
  db_version    = var.db_version
}
