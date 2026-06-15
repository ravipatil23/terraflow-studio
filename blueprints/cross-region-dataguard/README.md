# Cross-Region Data Guard — Terraform Blueprint

Standalone Terraform that builds the **OCI-side network plumbing** to run **Oracle
Data Guard across two regions** between two existing Oracle Exadata VM clusters
(Oracle Database@AWS, Oracle Database@Azure, or native OCI Exadata — they all sit on
OCI VCNs underneath). You only edit [`terraform.tfvars`](terraform.tfvars).

> **Scope:** this provisions the *network path* (transit VCNs, peering, routes,
> firewall rules) so the primary and standby databases can exchange redo on TCP 1521.
> It does **not** create the VM clusters or configure Data Guard itself — you create
> the clusters first (e.g. with the `db-at-aws` blueprint) and enable Data Guard at
> the database layer afterward.

---

## Table of contents

1. [What this deploys](#1-what-this-deploys)
2. [Architecture](#2-architecture)
3. [Prerequisites](#3-prerequisites)
4. [Authentication](#4-authentication)
5. [Repository layout](#5-repository-layout)
6. [Quick start](#6-quick-start)
7. [The route-table decision (read this)](#7-the-route-table-decision-read-this)
8. [Variable reference](#8-variable-reference)
9. [Outputs](#9-outputs)
10. [Verifying the peering](#10-verifying-the-peering)
11. [Destroying](#11-destroying)
12. [Troubleshooting](#12-troubleshooting)
13. [FAQ](#13-faq)

---

## 1. What this deploys

Per region (built twice — primary and DR — from one reusable `region` module):

| Resource | Terraform resource | Purpose |
|----------|--------------------|---------|
| Hub (transit) VCN | `oci_core_vcn` | Carries cross-region traffic |
| Hub LPG + Cluster LPG | `oci_core_local_peering_gateway` ×2 | Peers the hub VCN with the existing cluster VCN |
| DRG + attachment | `oci_core_drg`, `oci_core_drg_attachment` | Cross-region transit endpoint |
| Transit route tables | `oci_core_route_table` ×2 | Steer traffic hub↔cluster↔DRG |
| Cluster DG route | `oci_core_default_route_table` | Route to the remote region (optional — see §7) |
| NSG ingress rule(s) | `oci_core_network_security_group_security_rule` | Allow TCP 1521 (and optionally 22) from the peer region |

Then once, across regions (the `peering` module):

| Resource | Terraform resource | Purpose |
|----------|--------------------|---------|
| Remote Peering Connection ×2 | `oci_core_remote_peering_connection` | Connects the two DRGs (DR = acceptor, primary = requester) |

**Provider:** `oracle/oci >= 6.0.0` · **Terraform:** `>= 1.5.0` (or OpenTofu `>= 1.6.0`).

---

## 2. Architecture

```
        PRIMARY REGION (us-ashburn-1)                 DR REGION (us-phoenix-1)
 ┌─────────────────────────────────────┐      ┌─────────────────────────────────────┐
 │  Cluster VCN (existing)             │      │  Cluster VCN (existing)             │
 │  client subnet 10.10.1.0/24         │      │  client subnet 10.30.1.0/24         │
 │            │ cluster_lpg            │      │            │ cluster_lpg            │
 │            ▼                        │      │            ▼                        │
 │  Hub VCN 10.15.0.0/24               │      │  Hub VCN 10.16.0.0/24               │
 │     hub_lpg ── DRG ── attachment    │      │     hub_lpg ── DRG ── attachment    │
 │                 │                   │      │                 │                   │
 └─────────────────┼───────────────────┘      └─────────────────┼───────────────────┘
                   │   Remote Peering Connection (DRG ↔ DRG)    │
                   └────────────────────────────────────────────┘
                         redo transport over TCP 1521
```

Traffic path: primary cluster VCN → cluster LPG → hub LPG → DRG → **RPC** → DR DRG →
hub LPG → cluster LPG → DR cluster VCN (and the reverse). Each leg has a matching
route-table rule and the destination NSG allows 1521.

---

## 3. Prerequisites

1. **Two existing Exadata VM clusters**, one per region, each in its own VCN — created
   beforehand (e.g. via the [`db-at-aws`](../db-at-aws) blueprint or your OCI Exadata
   provisioning). This blueprint connects them; it does not create them.
2. For each region, collect:
   - the **cluster VCN OCID**,
   - the **cluster NSG OCID** (the NSG attached to the cluster's client VNICs),
   - the **client subnet CIDR**,
   - the **default route table OCID** of the cluster VCN (only if `manage_route_table = true`).
3. **Non-overlapping CIDRs** — the two client CIDRs and the two hub CIDRs must all be
   distinct and non-overlapping (Data Guard needs end-to-end routable addresses).
4. **IAM**: permission to manage `virtual-network-family` and `drg`/`remote-peering` in
   the compartment, in both regions.
5. **Terraform `>= 1.5.0`** and the `oracle/oci` provider (pulled automatically).

---

## 4. Authentication

The two `provider "oci"` blocks set only the region; credentials come from your
standard OCI config — no secrets in this code. Use either:

```bash
# ~/.oci/config (default profile), created by:
oci setup config
```

or environment variables:

```bash
export TF_VAR_compartment_id="ocid1.compartment.oc1..."
export OCI_CLI_USER=ocid1.user.oc1..              # or TF_VAR_* / OCI_* provider vars
export OCI_CLI_TENANCY=ocid1.tenancy.oc1..
export OCI_CLI_FINGERPRINT=...
export OCI_CLI_KEY_FILE=~/.oci/oci_api_key.pem
export OCI_CLI_REGION=us-ashburn-1
```

The same credentials/principal must be authorized in **both** regions.

---

## 5. Repository layout

```
cross-region-dataguard/
├── main.tf              # two provider aliases + 3 module calls (do not need to edit)
├── variables.tf         # variable definitions (do not need to edit)
├── outputs.tf           # outputs (do not need to edit)
├── terraform.tfvars     # ◀── YOU EDIT THIS
└── modules/
    ├── region/          # per-region transit networking (used twice)
    └── peering/         # cross-region DRG remote peering
```

---

## 6. Quick start

```bash
cd blueprints/cross-region-dataguard

# 1. authenticate to OCI (see §4) — must work in both regions
# 2. edit terraform.tfvars — regions, compartment, both VCN/NSG/CIDR sets

terraform init

# 3. IF manage_route_table = true, import both default route tables FIRST (see §7):
terraform import 'module.primary.oci_core_default_route_table.cluster_rt[0]' <primary-default-rt-ocid>
terraform import 'module.dr.oci_core_default_route_table.cluster_rt[0]'      <dr-default-rt-ocid>

terraform plan
terraform apply
```

---

## 7. The route-table decision (read this)

The cluster VCNs already exist, so their **default route tables already exist**. To add
the Data Guard route, Terraform has to adopt an existing object via
`manage_default_resource_id` — and if you `apply` without importing it first, Terraform
assumes it owns an empty table and **will remove your existing routes** (internet/NAT
gateways, etc.). You have two safe options:

**Option A — `manage_route_table = true` (default): import, then apply.**
1. `terraform init`
2. Import both default route tables (commands in §6).
3. **Preserve existing rules:** `terraform state show 'module.primary.oci_core_default_route_table.cluster_rt[0]'`, then copy each pre-existing `route_rules` block into `modules/region/main.tf` (there's a commented template there). Repeat for DR.
4. `terraform plan` — confirm it only **adds** the DG route, removes nothing.
5. `terraform apply`.

**Option B — `manage_route_table = false`: add the route by hand.**
Terraform skips the default route table entirely. After `apply`, add one route to each
cluster VCN's default route table — target = the cluster LPG, destination = the *remote*
client CIDR:

```bash
terraform output primary_cluster_lpg_id    # target for the PRIMARY route (dest = dr_client_cidr)
terraform output dr_cluster_lpg_id         # target for the DR route      (dest = primary_client_cidr)
```
Then via OCI Console (VCN → Route Tables → Default → Add Route Rule, Target Type = Local
Peering Gateway) or `oci network route-table update`.

> If you're unsure, **Option B is the lower-risk choice** — it never touches your
> existing routes. Option A gives you full IaC ownership but requires the import dance.

---

## 8. Variable reference

| Variable | Type | Required | Description |
|----------|------|----------|-------------|
| `prefix` | string | ✅ | Name prefix for all created resources. |
| `compartment_id` | string (sensitive) | ✅ | Compartment OCID for all resources. |
| `primary_region` / `dr_region` | string | ✅ | OCI region identifiers (e.g. `us-ashburn-1`, `us-phoenix-1`). |
| `primary_vcn_id` / `dr_vcn_id` | string | ✅ | OCIDs of the existing cluster VCNs. |
| `primary_nsg_id` / `dr_nsg_id` | string | ✅ | OCIDs of the cluster NSGs (where 1521 is opened). |
| `primary_client_cidr` / `dr_client_cidr` | string | ✅ | Client subnet CIDRs — must not overlap. |
| `primary_hub_cidr` / `dr_hub_cidr` | string | ✅ | CIDRs for the NEW transit VCNs — must not overlap anything. |
| `primary_route_table_id` / `dr_route_table_id` | string | ⚠️ | Default RT OCIDs. Required (and must be imported) when `manage_route_table = true`. |
| `manage_route_table` | bool | — | `true` (default): Terraform manages cluster default RTs (import first). `false`: add the DG route manually. See §7. |
| `add_ssh` | bool | — | `false` (default). `true` also opens TCP 22 between regions in the NSGs. |

---

## 9. Outputs

| Output | Notes |
|--------|-------|
| `peering_status` | **Watch this** — should read `PEERED` after a successful apply. |
| `primary_drg_id` / `dr_drg_id` | The two DRGs. |
| `primary_rpc_id` / `dr_rpc_id` | The two Remote Peering Connections. |
| `primary_hub_vcn_id` / `dr_hub_vcn_id` | The transit VCNs. |
| `primary_cluster_lpg_id` / `dr_cluster_lpg_id` | Cluster-side LPGs — the route targets if you chose Option B. |

```bash
terraform output peering_status      # expect: "PEERED"
```

---

## 10. Verifying the peering

After `apply`:
1. `terraform output peering_status` should be **`PEERED`**.
2. From a host in the primary client subnet, confirm reachability to a standby SCAN/VIP
   on 1521 (e.g. `nc -vz <standby-ip> 1521`). It should connect.
3. Then enable Data Guard at the database layer (e.g. via `dgmgrl` / the Exadata tooling)
   — that step is outside this blueprint.

---

## 11. Destroying

```bash
terraform destroy
```

This removes the transit VCNs, LPGs, DRGs, RPCs, transit route tables, and NSG rules.
**Note:** if `manage_route_table = true`, the cluster default route tables were *adopted*
(not created), so `destroy` resets them to the rules currently in your config — make sure
your config still lists the pre-existing rules (§7) before destroying, or remove the
resource from state first with `terraform state rm`.

---

## 12. Troubleshooting

| Symptom | Likely cause / fix |
|---------|--------------------|
| Existing routes disappeared from a cluster VCN | You applied with `manage_route_table = true` **without importing first**. Re-add the rules (§7) or restore from the console. Import before the next apply. |
| `peering_status` stuck `PENDING`/`NEW` | RPC peering not completed — re-run `apply`; ensure the same principal is authorized in both regions and `dr_region` is correct. |
| `NotAuthorizedOrNotFound` on a VCN/NSG | OCID is from the wrong region, or missing IAM in that region. Each OCID must belong to its stated region. |
| Can't reach standby on 1521 | Check the NSG rule landed, the remote CIDR is correct/non-overlapping, and (Option B) the manual DG route exists on both default RTs. |
| `manage_default_resource_id` errors / no rules | You set `manage_route_table = true` but didn't supply / import the route table OCID. Provide it and import, or switch to Option B. |

Validate before applying:

```bash
terraform fmt -recursive
terraform validate
```

---

## 13. FAQ

**Does this work for Oracle Database@AWS and @Azure?**
Yes — both run Exadata on OCI VCNs, and this builds the OCI-side cross-region path. You
supply the OCI VCN/NSG/route-table OCIDs that back your ODB@AWS / @Azure clusters. (For
ODB@GCP, cross-region DR uses a different mechanism and isn't covered here.)

**Why a Hub/transit VCN instead of peering the cluster VCNs directly?**
Cross-region connectivity needs a DRG, and the hub VCN keeps the DRG/transit concerns out
of your existing cluster VCNs — only a single LPG and one route are added to each cluster
VCN, minimizing changes to production networks.

**Can I run it with OpenTofu?**
Yes. Replace `terraform` with `tofu`.

**Is the state safe to commit?**
No — `terraform.tfstate` and `compartment_id` are sensitive. Use a remote backend and keep
state out of git.
