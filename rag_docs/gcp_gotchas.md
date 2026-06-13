# Oracle DB@GCP — Gotchas, Immutable Fields, and Provisioning Notes

## Provisioning times
- google_oracle_database_odb_network: 5–10 minutes
- google_oracle_database_odb_subnet: 2–3 minutes each (client and backup can be created in parallel)
- google_oracle_database_cloud_exadata_infrastructure: 60–90 minutes
- google_oracle_database_exadb_vm_cluster: 45–60 minutes

Creation order: ODB Network → Subnets (parallel) + Exadata Infrastructure (can start in parallel with subnets) → VM Cluster (must wait for infrastructure to be healthy).

## IMMUTABLE fields — cannot change after creation
google_oracle_database_odb_network:
- odb_network_id, location, gcp_oracle_zone, network (VPC association)

google_oracle_database_odb_subnet:
- odb_subnet_id, location, odb_network (parent), cidr_range, purpose (CLIENT_SUBNET / BACKUP_SUBNET)

google_oracle_database_cloud_exadata_infrastructure:
- cloud_exadata_infrastructure_id, location, gcp_oracle_zone, shape, compute_count, storage_count

google_oracle_database_exadb_vm_cluster:
- exadb_vm_cluster_id, location, odb_network, odb_subnet, backup_odb_subnet, exadata_infrastructure
- hostname_prefix, node_count, enabled_ecpu_count_per_node, ssh_public_keys, license_type, cluster_name

## grid_image_id is the required INPUT — gi_version is a computed OUTPUT
The most common mistake on GCP ExaDB VM Cluster:
- CORRECT: set grid_image_id to the full resource path of the Grid image
- WRONG: set gi_version (this is a read-only computed attribute that Terraform populates after creation)
- grid_image_id format: "projects/<project>/locations/<region>/giVersions/<version>/dbServerVersions/<version>"
- Example: "projects/my-proj/locations/us-east4/giVersions/23.0.0.0/dbServerVersions/23.0.0.0.0"

## time_zone is a nested block — not a string
CORRECT Terraform HCL:
  time_zone {
    id = "UTC"
  }
WRONG:
  time_zone = "UTC"
Using the flat string form will fail at plan time with a schema error.

## exascale_db_storage_vault is required
The exascale_db_storage_vault field in the properties block is required for google_oracle_database_exadb_vm_cluster.
Format: "projects/<project>/locations/<region>/exascaleDbStorageVaults/<vault-name>"
Example: "projects/my-proj/locations/us-east4/exascaleDbStorageVaults/my-vault"

## shape_attribute is required
shape_attribute must be set in the properties block. Valid values: SMART_STORAGE or BLOCK_STORAGE.
SMART_STORAGE is recommended for most workloads.

## ODB subnet purpose is immutable — plan CLIENT vs BACKUP upfront
Cannot change a CLIENT_SUBNET to a BACKUP_SUBNET or vice versa after creation.
The root module always creates two subnets per ODB network: one CLIENT_SUBNET, one BACKUP_SUBNET.

## CIDR range is immutable on subnets
Once a subnet is created, its cidr_range cannot be changed. Plan non-overlapping CIDRs carefully.
Subnets must not overlap each other or existing GCP VPC subnets in the same region.
Minimum subnet size: /27. Maximum: /22.

## Infrastructure must be fully healthy before VM cluster creation
Exadata Infrastructure provisioning takes 60–90 minutes. Do not attempt to create a VM Cluster until the infrastructure lifecycle_state = ACTIVE. Terraform handles this automatically via resource dependencies.

## Service-managed OCI compartment — do not modify
The first ODB Network deployment automatically creates an OCI compartment for the service.
Do NOT rename, move, or delete this compartment. The service will lose the ability to manage Oracle resources in the project.

## labels are Terraform-only — not visible in GCP Console
Resource labels applied via Terraform are not shown in the Google Cloud Console for Oracle DB resources. This is expected behaviour — labels are still applied and queryable via the API.

## data_storage_size_in_tbs can increase but not decrease
The data storage allocation for a VM Cluster can be expanded post-creation but cannot be reduced.
Other storage-related fields (db_node_storage_size_per_vm_in_gbs, spare_snapshot_space_in_gbs) are set at creation and may be immutable depending on provider version.

## Exadata Infrastructure shape availability is region-specific
Not all Exadata shapes are available in all GCP regions. Verify shape availability for your target region before configuring. Exadata.X11M is generally available in us-east4 and us-central1.

## Resource ID naming rules (odb_network_id, odb_subnet_id, etc.)
- 1–63 characters
- Lowercase letters, numbers, hyphens only
- Must start with a lowercase letter or number
- Must end with a lowercase letter or number
- No consecutive hyphens
