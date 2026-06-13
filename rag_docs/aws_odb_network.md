# AWS ODB Network (aws_odb_network)

The ODB Network is the virtual network container required by all ODB@AWS resources.
Every Exadata Infrastructure and VM Cluster must reference an ODB Network.
Provisioning time: 2–5 minutes.

## Required fields
- display_name: human-readable name, e.g. "odb-network-prod". Max 255 chars; letters/digits/underscores/hyphens; must start with letter or underscore; no consecutive hyphens.
- availability_zone_id: AZ ID where the network is located, e.g. "use1-az4", "use1-az6", "usw2-az3". Use AZ IDs (not AZ names) — AZ IDs are consistent across accounts.
- client_subnet_cidr: CIDR block for the client subnet (Oracle Net traffic from clients to DB). Minimum /27 (32 IPs). Recommended /24 for room to grow. Example: "10.2.0.0/24".
- backup_subnet_cidr: CIDR block for the backup subnet (RMAN backup traffic). Minimum /28 (16 IPs). Recommended /24. Example: "10.2.1.0/24".

## Optional fields
- s3_access: ENABLED or DISABLED. Controls whether Oracle DB nodes can access Amazon S3 directly for data loading, exports, and self-managed backups. Default DISABLED. Set to ENABLED if using S3-based backups.
- zero_etl_access: ENABLED or DISABLED. Enables Oracle-to-Redshift Zero-ETL replication. Default DISABLED.
- availability_zone: AZ name (e.g. "us-east-1a") — informational only; auto-derived from availability_zone_id. Optional.
- region: AWS region string, e.g. "us-east-1" — informational only. Optional.
- delete_associated_resources: bool — when true, deleting the network also destroys associated subnets and peerings. Default false.
- tags: map of string tags, e.g. {"Env" = "prod", "Team" = "dba"}.

## DNS: custom_domain_name vs default_dns_prefix
These two fields are mutually exclusive — use one or the other, never both:
- default_dns_prefix: 1–15 alphanumeric chars, must start with letter. IMPORTANT: do NOT use hyphens — hyphens in default_dns_prefix cause VM Cluster creation to fail.
- custom_domain_name: fully qualified custom domain (e.g. "db.internal.example.com") — for organisations that manage DNS centrally.
If neither is set, the provider assigns a system-generated prefix.

## CIDR constraints and forbidden ranges
- client_subnet_cidr and backup_subnet_cidr must NOT overlap each other.
- ODB subnet CIDRs must NOT overlap the customer VPC CIDRs in the same region.
- ODB subnet CIDRs must NOT overlap on-premises networks reachable via AWS Transit Gateway or Cloud WAN.
- Forbidden ranges (will be rejected): 100.64.0.0/10 (cluster interconnect), 169.254.0.0/16 (OCI reserved), 224.0.0.0–255.255.255.255 (Class D/E multicast).
- Supernet blocks that group multiple existing subnets are not allowed in peered configurations.

## IP consumption (for capacity planning)
For 1 VM cluster with 2 nodes, you need approximately:
- Client subnet: 18 IPs (6 service + 3 SCAN + 4 per node × 2 nodes) → /27 is sufficient.
- Backup subnet: 9 IPs (3 service + 3 per node × 2 nodes) → /28 is sufficient.
For larger clusters or room to add more clusters later, use /24 for each.

## Module outputs
- network_id: used as odb_network_id in VM clusters and peerings
- network_arn: ARN for cross-account references (used as odb_network_arn)
- network_name: display name

## Naming conventions
module_name examples: odb_network_prod, odb_net_dev, odb_network_nonprod, vpc_odb_hr
Use snake_case, keep it short and environment-specific.

## Relationships
One ODB Network can support multiple Exadata Infrastructures and VM Clusters.
Network Peering (aws_odb_network_peering_connection) connects an ODB Network to a customer VPC.
Each VM Cluster references the ODB Network via odb_network_id (from module.<network>.network_id).

## Typical setup
For each environment (prod, nonprod, dev) create one ODB Network.
All Exadata Infrastructures and VM Clusters in that environment share the same ODB Network.
Example: client_subnet_cidr="10.2.0.0/24", backup_subnet_cidr="10.2.1.0/24", s3_access="ENABLED", zero_etl_access="DISABLED"
