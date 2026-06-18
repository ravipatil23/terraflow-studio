# Multi-AZ Data Guard — Terraform Blueprint

Standalone Terraform that builds the **OCI-side network path for same-region (multi-AZ)
Oracle Data Guard** between two existing Exadata VM clusters in two Availability Domains of
the **same OCI region**. You only edit [`terraform.tfvars`](terraform.tfvars).

> **Same-region only.** This uses a pair of immediately-peered **Local Peering Gateways** —
> no DRG or Remote Peering Connection needed. For cross-region DR, use
> [`../cross-region-dataguard`](../cross-region-dataguard).
>
> **Scope:** the *network path* only (LPG peering, NSG rules, routes). It does not create
> the VM clusters or configure Data Guard at the database layer.

---

## Table of contents

1. [What this deploys](#1-what-this-deploys)
2. [Architecture](#2-architecture)
3. [Prerequisites](#3-prerequisites)
4. [Authentication](#4-authentication)
5. [Quick start](#5-quick-start)
6. [The route-table decision (read this)](#6-the-route-table-decision-read-this)
7. [Variable reference](#7-variable-reference)
8. [Outputs & verification](#8-outputs--verification)
9. [Destroying](#9-destroying)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. What this deploys

| Resource | Terraform resource | Purpose |
|----------|--------------------|---------|
| Primary + Standby LPG | `oci_core_local_peering_gateway` ×2 | Immediately peered (same-region link) |
| NSG ingress (1521) | `oci_core_network_security_group_security_rule` ×2 | Data Guard redo between the subnets |
| NSG ingress (22) *(optional)* | same | SSH between subnets when `add_ssh = true` |
| Cluster VCN routes *(optional)* | `oci_core_default_route_table` ×2 | DG route via LPG when `manage_route_table = true` (see §6) |

**Provider:** `oracle/oci >= 6.0.0` · **Terraform:** `>= 1.5.0` (or OpenTofu `>= 1.6.0`).

---

## 2. Architecture

```
        SAME OCI REGION (e.g. us-ashburn-1)
 ┌──────────────────────────┐        ┌──────────────────────────┐
 │ Primary AD               │        │ Standby AD               │
 │ Cluster VCN              │        │ Cluster VCN              │
 │ client 10.10.1.0/24      │        │ client 10.20.1.0/24      │
 │        primary_lpg  ◀━━━━━━ peered ━━━━━▶  standby_lpg        │
 └──────────────────────────┘        └──────────────────────────┘
              redo transport over TCP 1521 (NSG ingress each side)
```

The two LPGs are peered at creation in a single apply. Each VCN gets a route to the
other's client CIDR via its LPG, and each NSG allows 1521 from the peer subnet.

---

## 3. Prerequisites

1. **Two existing Exadata VM clusters** in two ADs of the **same** region, each in its own VCN.
2. For each, collect: **VCN OCID**, **NSG OCID**, **client subnet CIDR**, and (if
   `manage_route_table = true`) the **default route table OCID**.
3. **Non-overlapping** primary and standby client CIDRs.
4. **IAM** to manage `virtual-network-family` in the compartment.
5. **Terraform `>= 1.5.0`** and the `oracle/oci` provider (pulled automatically).

---

## 4. Authentication

The provider block sets only the region; credentials come from your OCI config:

```bash
oci setup config        # ~/.oci/config
# or export OCI_CLI_USER / OCI_CLI_TENANCY / OCI_CLI_FINGERPRINT / OCI_CLI_KEY_FILE / OCI_CLI_REGION
export TF_VAR_compartment_id="ocid1.compartment.oc1..."
```

---

## 5. Quick start

```bash
cd blueprints/multi-az-dataguard

# 1. authenticate to OCI (see §4)
# 2. edit terraform.tfvars — region, compartment, both VCN/NSG/CIDR sets

terraform init

# 3. IF manage_route_table = true, import both default route tables FIRST (see §6):
terraform import 'oci_core_default_route_table.primary_rt[0]' <primary-default-rt-ocid>
terraform import 'oci_core_default_route_table.standby_rt[0]' <standby-default-rt-ocid>

terraform plan
terraform apply
```

---

## 6. The route-table decision (read this)

The cluster VCNs already exist, so their **default route tables already exist**. To add the
DG route, Terraform must adopt an existing table via `manage_default_resource_id` — and if you
`apply` without importing it first, Terraform assumes it owns an empty table and **will remove
your existing routes**. Two safe options:

**Option A — `manage_route_table = true` (default): import, then apply.**
1. `terraform init`
2. Import both default route tables (commands in §5).
3. Preserve existing rules: `terraform state show 'oci_core_default_route_table.primary_rt[0]'`, then copy each pre-existing `route_rules` block into `main.tf` alongside the DG rule. Repeat for standby.
4. `terraform plan` — confirm it only **adds** the DG route, removes nothing.
5. `terraform apply`.

**Option B — `manage_route_table = false`: add the route by hand.**
Terraform skips the route tables. After `apply`, add one route to each cluster VCN's default
route table — target = that VCN's LPG, destination = the *other* subnet's CIDR:

```bash
terraform output primary_lpg_id    # target for the PRIMARY route (dest = standby_client_cidr)
terraform output standby_lpg_id    # target for the STANDBY route (dest = primary_client_cidr)
```
Add via the OCI Console (VCN → Route Tables → Default → Add Route Rule, Target Type = Local
Peering Gateway) or `oci network route-table update` (read existing rules first so you append).

> Unsure? **Option B never touches your existing routes** and is the lower-risk choice.

---

## 7. Variable reference

| Variable | Type | Required | Description |
|----------|------|----------|-------------|
| `prefix` | string | — | Name prefix for LPGs. Default `acme-dg`. |
| `oci_region` | string | ✅ | Region (same for both ADs). |
| `compartment_id` | string (sensitive) | ✅ | Compartment OCID. |
| `primary_vcn_id` / `standby_vcn_id` | string | ✅ | Cluster VCN OCIDs. |
| `primary_nsg_id` / `standby_nsg_id` | string | ✅ | Cluster NSG OCIDs (where 1521 is opened). |
| `primary_client_cidr` / `standby_client_cidr` | string | ✅ | Client subnet CIDRs — must not overlap. |
| `primary_route_table_id` / `standby_route_table_id` | string | ⚠️ | Default RT OCIDs. Required (and imported) when `manage_route_table = true`. |
| `manage_route_table` | bool | — | `true` (default): Terraform manages RTs (import first). `false`: manual. See §6. |
| `add_ssh` | bool | — | `false` (default). `true` also opens TCP 22 between subnets. |

---

## 8. Outputs & verification

| Output | Notes |
|--------|-------|
| `primary_lpg_peering_status` / `standby_lpg_peering_status` | **Watch these** — both should read `PEERED`. |
| `primary_lpg_id` / `standby_lpg_id` | LPG OCIDs (route targets for Option B). |

```bash
terraform output primary_lpg_peering_status    # expect: "PEERED"
```

Then confirm reachability on 1521 between the subnets and enable Data Guard at the database
layer (`dgmgrl` / Exadata tooling) — outside this blueprint.

---

## 9. Destroying

```bash
terraform destroy
```

Removes the LPGs and NSG rules. If `manage_route_table = true`, the adopted route tables are
reset to the rules in your config on destroy — make sure pre-existing rules are listed (§6), or
`terraform state rm` the route tables first.

---

## 10. Troubleshooting

| Symptom | Likely cause / fix |
|---------|--------------------|
| Existing routes vanished from a cluster VCN | Applied with `manage_route_table = true` without importing first. Re-add rules (§6); import before the next apply. |
| `peering_status` not `PEERED` | Re-run `apply`; ensure both VCNs are in the same region and OCIDs are correct. |
| `NotAuthorizedOrNotFound` on a VCN/NSG | Wrong region or missing IAM. |
| Can't reach peer on 1521 | Check the NSG rule landed, CIDRs are correct/non-overlapping, and (Option B) the manual route exists on both default RTs. |
| Plan shows `-` on an existing `route_rules` | Stop — a production route is about to be deleted. Add it to `main.tf` first (§6). |

Validate before applying: `terraform fmt -recursive && terraform validate`.
