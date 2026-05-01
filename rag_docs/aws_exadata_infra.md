# AWS Exadata Infrastructure (aws_odb_cloud_exadata_infrastructure)

Provides the physical Exadata hardware layer. One infrastructure can host multiple VM Clusters.
Provisioning time: 15+ minutes.

## Required fields
- display_name: e.g. "exadb-infra-prod". Max 255 chars; letters/digits/underscores/hyphens; must start with letter or underscore; no consecutive hyphens.
- shape: hardware model — Exadata.X9M or Exadata.X11M (X11M is latest gen, recommended for new deployments). Note: X10M is no longer listed as an available shape.
- compute_count: number of database servers (nodes). Minimum 2, maximum 32. Must be even.
- storage_count: number of storage cells. Minimum 3, maximum 64. Must be a multiple of 3.
- availability_zone_id: AWS AZ ID where the infrastructure is located. Examples: use1-az4, use1-az6, usw2-az3, usw2-az4, euc1-az1, euc1-az2, apne1-az1, apne1-az4.

## Optional fields
- database_server_type: specific database server model. Only configurable on X11M (e.g. "X11M"). Fixed/not configurable on X9M.
- storage_server_type: specific storage server model. Only configurable on X11M (e.g. "X11M-HC" for high-capacity, "X11M-E" for extreme flash). Fixed on X9M.
- customer_contacts_to_send_to_oci: list of email addresses for Oracle maintenance notifications. Maximum 10 addresses.
- availability_zone: AZ name (e.g. "us-east-1a") — informational, auto-derived from availability_zone_id.
- region: AWS region string — informational, auto-derived.
- tags: map of string tags.

## Maintenance window
The maintenance_window block configures Oracle-managed patching schedules.
- preference: NO_PREFERENCE (Oracle chooses window) or CUSTOM_PREFERENCE (you specify schedule). Default: NO_PREFERENCE.
- patching_mode: ROLLING (nodes patched one at a time, zero downtime — recommended for production) or NON_ROLLING (all nodes patched simultaneously, faster but causes downtime — acceptable for dev/test). Note: the value is NON_ROLLING (with underscore), not NONROLLING.
- is_custom_action_timeout_enabled: bool, whether custom timeout is enforced. Default false.
- custom_action_timeout_in_mins: integer 15–120. Custom patching action timeout. Only applies when is_custom_action_timeout_enabled = true.
- When preference = CUSTOM_PREFERENCE: set lead_time_in_weeks (1–4), hours_of_day, days_of_week, weeks_of_month, months.

## Post-creation: getting DB server IDs
After infrastructure is created, query the DB server IDs with the data source:
```hcl
data "aws_odb_db_servers" "this" {
  cloud_exadata_infrastructure_id = module.<infra_module>.infra_id
}
```
These IDs are required when creating a VM Cluster (db_servers field).

## Module outputs
- infra_id: used as cloud_exadata_infrastructure_id in VM clusters and AVM clusters
- infra_arn: ARN for cross-account references

## Naming
module_name examples: odb_infra_prod, odb_exaInfra_us_east, exadb_infra_nonprod

## Capacity guidance
- X11M quarter rack: 2 compute, 3 storage — minimum viable configuration
- X11M half rack: 4 compute, 6 storage
- X11M full rack: 8 compute, 12 storage
- compute_count must be even; storage_count must be a multiple of 3
