# Multi-AZ Data Guard — Terraform Blueprint

Standalone Terraform that builds the **OCI-side network path for same-region (multi-AZ)
Oracle Data Guard** between two existing Exadata VM clusters in two Availability Domains of
the **same OCI region**. You only edit [`terraform.tfvars`](terraform.tfvars).

> **Same-region only.** This uses a pair of immediately-peered **Local Peering Gateways** —
> no DRG or Remote Peering Connection needed. For cross-region DR, use
> [`../cross-region-dataguard`](../cross-region-dataguard).
>
> **Scope:** the *network path* only — LPG peering + NSG rules. It does **not** manage the
> VM cluster VCN route tables (you add the Data Guard route manually — see §6), and it does
> not create the VM clusters or configure Data Guard at the database layer.

---

## Table of contents

1. [What this deploys](#1-what-this-deploys)
2. [Architecture](#2-architecture)
3. [Prerequisites](#3-prerequisites)
4. [Authentication](#4-authentication)
5. [Quick start](#5-quick-start)
6. [Adding the Data Guard routes (manual)](#6-adding-the-data-guard-routes-manual)
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

> **Route tables are intentionally not managed by Terraform** (same approach as the
> cross-region blueprint's manual mode) — adopting a pre-existing default route table risks
> wiping its current routes. Add the one Data Guard route per VCN by hand after apply (§6).

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

The two LPGs are peered at creation in a single apply, and each NSG allows 1521 from the peer
subnet. The per-VCN route to the other subnet (via the LPG) is added manually after apply (§6).

---

## 3. Prerequisites

1. **Two existing Exadata VM clusters** in two ADs of the **same** region, each in its own VCN.
2. For each, collect: **VCN OCID**, **NSG OCID**, and the **client subnet CIDR**.
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
terraform plan
terraform apply

# 3. add the Data Guard route to each cluster VCN by hand (see §6)
```

---

## 6. Adding the Data Guard routes (manual)

This blueprint does not touch the existing VM cluster VCN route tables. After `apply`, add
**one route to each cluster VCN's default route table** — target = that VCN's LPG, destination =
the *other* subnet's CIDR. Get the LPG OCIDs from the outputs:

```bash
terraform output primary_lpg_id    # target for the PRIMARY VCN route (dest = standby client CIDR)
terraform output standby_lpg_id    # target for the STANDBY VCN route (dest = primary client CIDR)
```

**OCI Console:** Networking → Virtual Cloud Networks → *cluster VCN* → Route Tables → Default
Route Table → **Add Route Rules** → Target Type: **Local Peering Gateway** → pick the LPG →
Destination CIDR: the other subnet's CIDR.

**OCI CLI** (reads existing rules first so you *append*, never overwrite):

```bash
# Primary VCN -> standby subnet
EXISTING=$(oci network route-table get --rt-id <primary-default-rt-ocid> \
  --query 'data."route-rules"' --raw-output)
oci network route-table update --rt-id <primary-default-rt-ocid> --force \
  --route-rules "$(echo "$EXISTING" | jq '. + [{
    "destination":"<standby-client-cidr>","destinationType":"CIDR_BLOCK",
    "networkEntityId":"<primary-lpg-ocid>","description":"Data Guard: to standby via LPG"}]')"

# Standby VCN -> primary subnet (repeat with standby RT, standby LPG, primary CIDR)
```

> **Never pass only the new rule** to `route-table update` — the OCI API replaces the entire
> rule array, so you must include the existing rules. The `jq` append above does this.

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
| `add_ssh` | bool | — | `false` (default). `true` also opens TCP 22 between subnets. |

---

## 8. Outputs & verification

| Output | Notes |
|--------|-------|
| `primary_lpg_peering_status` / `standby_lpg_peering_status` | **Watch these** — both should read `PEERED`. |
| `primary_lpg_id` / `standby_lpg_id` | LPG OCIDs — the route targets for the manual step (§6). |

```bash
terraform output primary_lpg_peering_status    # expect: "PEERED"
```

After adding the routes (§6), confirm reachability on 1521 between the subnets and enable Data
Guard at the database layer (`dgmgrl` / Exadata tooling) — outside this blueprint.

---

## 9. Destroying

```bash
terraform destroy
```

Removes the LPGs and NSG rules. The cluster VCN route tables are untouched by Terraform, so any
Data Guard route you added manually (§6) must also be removed manually.

---

## 10. Troubleshooting

| Symptom | Likely cause / fix |
|---------|--------------------|
| `peering_status` not `PEERED` | Re-run `apply`; ensure both VCNs are in the same region and OCIDs are correct. |
| `NotAuthorizedOrNotFound` on a VCN/NSG | Wrong region or missing IAM. |
| Can't reach peer on 1521 | Check the NSG rule landed, CIDRs are correct/non-overlapping, and the manual route (§6) exists on **both** default route tables. |
| Manual `route-table update` wiped existing routes | You passed only the new rule — always read + append existing rules (the `jq` snippet in §6). |

Validate before applying: `terraform fmt -recursive && terraform validate`.
