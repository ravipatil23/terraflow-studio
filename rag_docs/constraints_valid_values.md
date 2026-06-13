# Constraints and Valid Values

## Shapes
- Exadata.X9M: older generation quarter rack
- Exadata.X10M: previous generation quarter rack
- Exadata.X11M: latest generation quarter rack (default, recommended)

## AWS Regions with live ODB support
- us-east-1 (N. Virginia): AZ IDs use1-az4, use1-az6
- us-east-2 (Ohio): AZ IDs use2-az1, use2-az2
- us-west-2 (Oregon): AZ IDs usw2-az3, usw2-az4
- eu-central-1 (Frankfurt): AZ IDs euc1-az1, euc1-az2
- ap-northeast-1 (Tokyo): AZ IDs apne1-az1, apne1-az4

## availability_zone_id vs availability_zone (AWS)
These are two separate fields — both exist on aws_odb_network and aws_odb_cloud_exadata_infrastructure:
- availability_zone_id: the AZ ID (e.g. "use1-az4") — this is the PRIMARY required field for ODB resources. AZ IDs are consistent across accounts; use this to target a specific ODB-enabled AZ.
- availability_zone: the AZ name (e.g. "us-east-1a") — informational/optional. AZ names vary per account and are less reliable for cross-account coordination.
Always set availability_zone_id. Setting availability_zone is optional and only needed for informational tagging.

## s3_access and zero_etl_access (aws_odb_network)
- s3_access: ENABLED or DISABLED. Controls whether Oracle DB nodes can access Amazon S3 directly for data loading, exports, and backups to S3. Default ENABLED.
- zero_etl_access: ENABLED or DISABLED. Enables AWS Zero-ETL integration so Oracle DB data can replicate to Amazon Redshift or other analytics services without ETL pipelines. Default DISABLED.
Both fields accept only the string values "ENABLED" or "DISABLED" — not booleans.

## Compute and storage counts
- Minimum: compute_count=2, storage_count=3 (quarter rack)
- Half rack: compute_count=4, storage_count=6
- Full rack: compute_count=8, storage_count=12
- compute_count must be even; storage_count must be a multiple of 3

## Grid Infrastructure versions (gi_version — AWS only)
AWS aws_odb_cloud_vm_cluster uses gi_version as a required INPUT:
- "23.0.0.0.0" — latest, recommended for new clusters
- "21.0.0.0.0" — previous long-term support
- "19.0.0.0.0" — older long-term support

## GCP grid_image_id (GCP ExaDB VM Cluster — replaces gi_version)
GCP google_oracle_database_exadb_vm_cluster uses grid_image_id as the required INPUT.
gi_version is a COMPUTED OUTPUT on GCP — do not use it as an input.
grid_image_id format: projects/<project>/locations/<region>/giVersions/<version>/dbServerVersions/<version>
Example: projects/my-proj/locations/us-east4/giVersions/23.0.0.0/dbServerVersions/23.0.0.0.0

## GCP shape_attribute
Required for google_oracle_database_exadb_vm_cluster:
- SMART_STORAGE: Exascale smart storage (recommended for most workloads)
- BLOCK_STORAGE: Block storage configuration

## License models
- LICENSE_INCLUDED: Oracle license included in service cost
- BRING_YOUR_OWN_LICENSE: customer provides Oracle license, lower cost

## Naming constraints
- module_name: snake_case, letters/digits/underscores only, unique across all modules
- db_name: max 8 characters, alphanumeric, must start with a letter (e.g. ORCL, MYDB, HR, FINDB)
- pdb_name: same rules as db_name (e.g. MYPDB, HRPDB, APP1)
- hostname_prefix: lowercase alphanumeric, recommended max 12 chars (e.g. exa-prod, vmc-hr)
- display_name: free text, human readable

## SCAN listener port
- Default: 1521
- Valid range: 1024-8999
- Reserved (do not use): 2484, 6100, 6200, 7060, 7070, 7085, 7879

## Patching modes
- ROLLING: nodes patched one at a time, database stays online (recommended for production)
- NON_ROLLING: all nodes patched simultaneously, faster but causes downtime (acceptable for dev/test)
Note: the correct Terraform value is NON_ROLLING (with underscore). NONROLLING is invalid and will fail provider validation.

## Auto backup windows (OCI)
SLOT_TWO=02:00-04:00 UTC, SLOT_FOUR=04:00-06:00, SLOT_SIX=06:00-08:00, SLOT_EIGHT=08:00-10:00
SLOT_TEN=10:00-12:00, SLOT_TWELVE=12:00-14:00, SLOT_FOURTEEN=14:00-16:00

## Sensitive variables
Never hardcode: admin_password, oci_tenancy_ocid, oci_user_ocid, oci_fingerprint, oci_private_key_path
Set via TF_VAR_ environment variables: export TF_VAR_oci_database_admin_password=...

## data_storage_size_in_tbs
Minimum: 2 TB. Increment: 1 TB. dev/test: 2, production: 4-20+ depending on workload.
