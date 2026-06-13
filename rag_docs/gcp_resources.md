# GCP Oracle Database Resources (DB@GCP)

Google Cloud Oracle Database deploys via the google provider (≥ 7.0) alongside the OCI provider (≥ 7.29.0).

## Creation order
1. google_oracle_database_odb_network (5–10 min)
2. google_oracle_database_odb_subnet — client and backup (2–3 min each, can run in parallel)
3. google_oracle_database_cloud_exadata_infrastructure (60–90 min)
4. google_oracle_database_exadb_vm_cluster (45–60 min, after infra is healthy)

---

## ODB Network (google_oracle_database_odb_network)
Foundation resource — all other GCP Oracle DB resources depend on it. Provisioning: 5–10 minutes.

Required fields:
- odb_network_id: unique short ID. 1–63 chars, lowercase letters/numbers/hyphens, must start AND end with lowercase letter or number. IMMUTABLE.
- display_name: user-facing name, letters/digits/underscores/hyphens, starts with letter or underscore.
- location: GCP region (e.g. us-east4, us-central1, europe-west1, europe-west4, asia-northeast1). IMMUTABLE.
- network: existing GCP VPC network ID or self-link. Must exist before creating the ODB network.
- gcp_oracle_zone: Oracle zone within the region, format "<region>-<letter>-r<number>" e.g. "us-east4-b-r1", "us-central1-a-r1". IMMUTABLE.
- project: GCP project ID.

Optional fields:
- deletion_protection: bool, default false.
- labels: map of string labels (Terraform-only; not visible in GCP Console).

Module outputs: odb_network_id, odb_network_name (full resource path used by subnets and VM clusters)

Naming: module_name examples: gcp_odb_net_prod, gcp_network_dev, odb_net_us_east4

Note: The first deployment creates an OCI service-managed compartment with restrictive IAM policies. Do NOT modify, move, or delete this compartment — the service will lose the ability to manage resources.

---

## ODB Subnet (google_oracle_database_odb_subnet)
Client and backup subnets are created as separate modules per ODB network. Provisioning: 2–3 minutes each.

Required fields:
- odb_subnet_id: unique short ID. 1–63 chars, lowercase letters/numbers/hyphens, starts with letter, ends with letter/number. IMMUTABLE.
- location: GCP region — must match the parent ODB network region. IMMUTABLE.
- odb_network: parent ODB Network short ID (the odb_network_id value, not the full resource path). IMMUTABLE.
- cidr_range: CIDR block for the subnet. Minimum /27, maximum /22. Must be RFC1918. IMMUTABLE.
  Examples: "10.2.0.0/24" for client, "10.2.1.0/24" for backup. Must not overlap each other or existing VPC subnets.
- purpose: CLIENT_SUBNET or BACKUP_SUBNET. IMMUTABLE — cannot be changed after creation; cannot convert between types.

Optional fields:
- project: GCP project ID.
- deletion_protection: bool, default false.
- labels: map of string labels.

Module outputs: odb_subnet_id, odb_subnet_name (full resource path, used by VM cluster)

The root main.tf creates two subnet modules per ODB network:
- client subnet: module name typically <network_module>_client_subnet — wired as odb_subnet in VM cluster
- backup subnet: module name typically <network_module>_backup_subnet — wired as backup_odb_subnet in VM cluster

---

## Exadata Infrastructure (google_oracle_database_cloud_exadata_infrastructure)
Physical Exadata hardware. Provisioning: 60–90 minutes. Must be fully healthy before creating VM clusters.

Required fields:
- cloud_exadata_infrastructure_id: unique short ID. 1–63 chars, lowercase. IMMUTABLE.
- display_name: user-facing name.
- location: GCP region. IMMUTABLE.
- gcp_oracle_zone: Oracle zone e.g. "us-east4-b-r1". IMMUTABLE.
- project: GCP project ID.

Properties block (required, nested inside resource):
- shape: Exadata hardware model. e.g. "Exadata.X9M", "Exadata.X11M" (latest, recommended). IMMUTABLE. Not all shapes available in all regions.
- compute_count: number of database servers. Minimum 2. IMMUTABLE.
- storage_count: number of storage servers. Minimum 3. IMMUTABLE.

Maintenance window (optional, nested inside properties):
- mw_preference (preference): NO_PREFERENCE or CUSTOM_PREFERENCE. Default NO_PREFERENCE.
- mw_patching_mode (patching_mode): ROLLING (zero downtime, recommended for production) or NON_ROLLING (faster, causes downtime).
- When CUSTOM_PREFERENCE: also set mw_months (e.g. ["JANUARY","APRIL"]), mw_weeks_of_month ([1,4]), mw_days_of_week (["SUNDAY"]), mw_hours_of_day ([2,14] in UTC), mw_lead_time_week (1–4).
- mw_is_custom_action_timeout_enabled: bool. mw_custom_action_timeout_mins: 15–120.

Optional fields:
- customer_contacts: list of email addresses for Oracle maintenance notifications. Max 10.
- total_storage_size_gb: total storage size override.
- labels: map of string labels.
- deletion_protection: bool.

Module outputs: infra_name (full resource path, wired as exadata_infrastructure in VM cluster)

---

## ExaDB VM Cluster (google_oracle_database_exadb_vm_cluster)
Runs Oracle databases on the Exadata Infrastructure. Provisioning: 45–60 minutes.

Required fields:
- exadb_vm_cluster_id: unique short ID. IMMUTABLE.
- display_name: user-facing name.
- location: GCP region. Must match infrastructure region. IMMUTABLE.
- odb_network: full ODB Network resource path — wired from module.<network>.odb_network_name. IMMUTABLE.
- odb_subnet: full client ODB Subnet resource path — wired from module.<client_subnet>.odb_subnet_name. IMMUTABLE.
- backup_odb_subnet: full backup ODB Subnet resource path — wired from module.<backup_subnet>.odb_subnet_name. IMMUTABLE.
- exadata_infrastructure: full Exadata Infrastructure resource path — wired from module.<infra>.infra_name. IMMUTABLE.
- project: GCP project ID.

Properties block (nested) — required fields:
- grid_image_id: full resource path of the Grid image. Format: "projects/<project>/locations/<region>/giVersions/<version>/dbServerVersions/<version>". Example: "projects/my-proj/locations/us-east4/giVersions/23.0.0.0/dbServerVersions/23.0.0.0.0". REQUIRED INPUT — do not confuse with gi_version which is a COMPUTED OUTPUT.
- exascale_db_storage_vault: full resource path of the Exascale DB Storage Vault. Format: "projects/<project>/locations/<region>/exascaleDbStorageVaults/<name>". REQUIRED INPUT.
- shape_attribute: SMART_STORAGE or BLOCK_STORAGE. Required. Default SMART_STORAGE.
- hostname_prefix: prefix for node hostnames. Max 12 chars, letters/numbers/hyphens, must start with letter. IMMUTABLE.
- node_count: number of VM nodes. Minimum 2. IMMUTABLE.
- enabled_ecpu_count_per_node: enabled ECPUs per node. Minimum 8, must be a multiple of 4. IMMUTABLE.
- ssh_public_keys: list of OpenSSH public key strings. At least 1 required. IMMUTABLE after creation.
- license_type: LICENSE_INCLUDED or BRING_YOUR_OWN_LICENSE. IMMUTABLE.

Properties block — optional fields:
- additional_ecpu_count_per_node: reserved ECPUs per node, 0–192, multiples of 4. Default 0.
- vm_file_system_storage_size_gbs: local file-system storage per node in GiB, 60–900. Default 60.
- cluster_name: GI cluster name, max 11 chars. IMMUTABLE.
- time_zone: NESTED BLOCK — must be: time_zone { id = "UTC" } — NOT a flat string assignment. Optional; defaults to UTC.
- memory_per_node_in_gbs: memory per node in GiB. Minimum 30.
- db_node_storage_size_per_vm_in_gbs: node storage in GiB, 60–900.
- data_storage_size_in_tbs: data storage in TiB, 2–238. Can be INCREASED post-creation but not decreased.
- spare_snapshot_space_in_gbs: snapshot space in GiB.
- disk_redundancy: HIGH (3-way) or NORMAL (2-way).

Diagnostics block (optional):
- dco_diagnostics (diagnostics_events_enabled): bool.
- dco_health (health_monitoring_enabled): bool.
- dco_incident_logs (incident_logs_enabled): bool.

CRITICAL — gi_version vs grid_image_id:
- grid_image_id is the REQUIRED INPUT to the resource (specify when creating).
- gi_version is a COMPUTED OUTPUT attribute — it appears in state after creation, do not set it as an input.
- Setting gi_version as an input will cause the Terraform plan to fail.

CRITICAL — time_zone is a nested block:
- CORRECT: time_zone { id = "UTC" }
- WRONG: time_zone = "UTC"

Module outputs: vm_cluster_name, ocid

---

## GCP Regions with Oracle DB support
- us-east4 (N. Virginia): gcp_oracle_zone examples: us-east4-b-r1
- us-central1 (Iowa): gcp_oracle_zone examples: us-central1-a-r1
- europe-west1 (Belgium)
- europe-west4 (Netherlands)
- asia-northeast1 (Tokyo)

## Root variables for GCP
gcp_project: GCP project ID
gcp_region: GCP region
labels: map of string labels applied to all resources
