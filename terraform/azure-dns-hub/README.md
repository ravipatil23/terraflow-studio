# Database@Azure — Custom DNS, Scenario #2 (Network Anchor as DNS Hub)

Terraform that wires one or more **Exadata VCNs** to a central **DNS Hub VCN**
(the Network Anchor), implementing Scenario #2 from the A-Team article
*“Custom DNS for Oracle AI Database@Azure”* and the Oracle docs
*“DNS for Oracle AI Database@Azure”*.

## What it does

For each Exadata environment (e.g. `prod`, `nonprod`) this creates the wiring
between that environment's Exadata VCN and the shared DNS Hub VCN:

| # | Resource | Purpose |
|---|----------|---------|
| 1 | `oci_core_local_peering_gateway` ×2 | 1:1 LPG pair (Exadata VCN ⇄ Hub VCN). LPG peering is strictly 1:1, so **each environment gets its own pair**. |
| 2 | `oci_dns_resolver_endpoint` (forwarding) | Forwarding endpoint on the Exadata VCN resolver — egress queries from the databases. |
| 3 | `oci_dns_resolver` rule (`FORWARD`) | Sends the configured Azure domains to the Hub **listening** endpoint, so databases resolve Azure FQDNs. |
| 4 | `oci_core_network_security_group_security_rule` | Opens DNS (UDP/TCP 53) across the peering. |
| 5 | `oci_core_default_route_table` *(optional)* | Routes the resolver subnets to each other over the LPG pair. |

The **root module** additionally owns the hub-side shared objects:
the **listening** endpoint (which Azure queries), the **forwarding** endpoint,
and one **private view + private zone** per environment.

```
Azure private resolver ─▶ Hub LISTENING endpoint ─▶ private views/zones ─▶ OCI private IPs
Database (prod/nonprod) ─▶ Exadata FORWARDING endpoint ─▶ FORWARD rule ─▶ Hub LISTENING endpoint ─▶ Azure
```

## Prerequisites (already provisioned)

- A **DNS Hub VCN** with a dedicated subnet + NSG for DNS resolver endpoints.
- One **Exadata VCN per environment**, each with a resolver subnet (+ NSG).
- The OCIDs and CIDRs of all of the above (fill into `terraform.tfvars`).

## Usage

```bash
cd terraform/azure-dns-hub
cp terraform.tfvars.example terraform.tfvars   # then edit the OCIDs
terraform init
terraform plan
terraform apply
```

After apply, point Azure's DNS forwarding ruleset at the hub listener:

```bash
terraform output hub_listening_endpoint_ip
```

## Routing note

DNS packets must route between the two resolver subnets over the LPG pair.

- If the resolver subnets use **dedicated** route tables you manage elsewhere,
  add a rule on each: *destination = peer resolver subnet CIDR, target = the
  LPG on that side* (LPG OCIDs are in the `links` output). Leave
  `manage_route_tables = false`.
- If they use each VCN's **default** route table and you want Terraform to own
  it, set `manage_route_tables = true`, supply `*_route_table_id`, and import
  the existing default route tables first:

  ```bash
  terraform import 'module.link["prod"].oci_core_default_route_table.exadata[0]' <prod-default-rt-ocid>
  terraform import 'module.link["prod"].oci_core_default_route_table.hub[0]'     <hub-default-rt-ocid>
  ```

  Then copy any pre-existing routes from `terraform state show` into the
  `route_rules` blocks in `modules/exadata-dns-link/main.tf` so they aren't
  dropped on the next apply.

## Adding another environment

Add a key to the `environments` map in `terraform.tfvars` — a new LPG pair,
forwarding endpoint, rule, NSG rules and private zone are created for it.
```
