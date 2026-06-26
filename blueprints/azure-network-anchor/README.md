# Oracle Database@Azure — Network Anchor — Terraform Blueprint

Standalone Terraform that provisions an **Oracle Database@Azure Network Anchor** — the
component that bridges an Azure delegated subnet to OCI and is a **prerequisite for an
Oracle Base Database**. You only edit [`terraform.tfvars`](terraform.tfvars).

> **Why AzAPI?** `azurerm` has **no native resource** for the Network Anchor, but it exists
> as the ARM type [`Oracle.Database/networkAnchors`](https://learn.microsoft.com/en-us/azure/templates/oracle.database/networkanchors?pivots=deployment-language-terraform),
> so this blueprint uses the **`azapi`** provider to create it directly. (Oracle's own docs
> describe only the Azure Portal wizard; this is the Terraform equivalent.)

---

## 1. What this deploys

| Resource | ARM type | Provider |
|----------|----------|----------|
| Network Anchor | `Oracle.Database/networkAnchors@2025-09-01` | `Azure/azapi` (`azapi_resource`) |

Creating it provisions an **OCI VCN** (named after the anchor) and, if you enable the DNS
options, **OCI DNS resolver endpoints/rules**.

**Provider:** `Azure/azapi >= 2.0.0` · **Terraform:** `>= 1.5.0` (or OpenTofu `>= 1.6.0`).

---

## 2. Prerequisites

These must already exist (the anchor references them by Azure resource ID):

1. **Resource Anchor** — maps to an OCI compartment. Get its ID:
   ```bash
   az resource show -g <rg> --name <ra-name> \
     --resource-type Oracle.Database/resourceAnchors --query id -o tsv
   ```
2. **Delegated subnet** — a subnet delegated to `Oracle.Database/networkAttachment` (the
   `db-at-azure` blueprint's `azure_vnets` creates exactly this delegation). Get its ID:
   ```bash
   az network vnet subnet show -g <rg> --vnet-name <vnet> -n <subnet> --query id -o tsv
   ```
3. A **region/AZ** that offers Oracle Base Database, and IAM rights on the resource group.
4. **Terraform `>= 1.5.0`** and the `azapi` provider (pulled automatically).

---

## 3. Authentication

`azapi` uses the same Azure credential chain as `azurerm`:

```bash
az login
az account set --subscription "00000000-0000-0000-0000-000000000000"
# or service principal: export ARM_CLIENT_ID / ARM_CLIENT_SECRET / ARM_TENANT_ID / ARM_SUBSCRIPTION_ID
```

Set the same `subscription_id` in `terraform.tfvars` — it's used for provider auth and to
build each anchor's parent resource-group ID.

---

## 4. Quick start

```bash
cd blueprints/azure-network-anchor

# 1. az login  (see §3)
# 2. edit terraform.tfvars — subscription, and per anchor: name, RG, location,
#    resource_anchor_id, subnet_id (+ optional DNS settings)

terraform init
terraform plan
terraform apply
```

---

## 5. Variable reference

Top level: `subscription_id` (required) and the `network_anchors` map.

**`network_anchors` entry fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | ✅ | Anchor name — `^[a-zA-Z0-9-]{3,24}$` (3–24 chars, letters/numbers/hyphens). |
| `resource_group_name` | string | ✅ | Existing resource group that holds the anchor. |
| `location` | string | ✅ | Azure region (must offer Oracle Base Database). |
| `resource_anchor_id` | string | ✅ | Azure resource ID of the existing Resource Anchor. |
| `subnet_id` | string | ✅ | Azure resource ID of the delegated client subnet. |
| `zones` | list(string) | — | AZ(s) where the Base Database resides, e.g. `["2"]`. |
| `tags` | map(string) | — | Resource tags. |
| `oci_vcn_dns_label` | string | — | OCI VCN DNS label (optional if DNS config is provided). |
| `oci_backup_cidr_block` | string | — | OCI backup subnet CIDR (not needed for Base Database). |
| `dns_listening_endpoint_enabled` | bool | — | Lets Azure apps resolve DB FQDNs. Default `false`. |
| `dns_listening_allowed_cidrs` | string | — | Comma-separated CIDRs allowed to query the listening endpoint. |
| `dns_forwarding_endpoint_enabled` | bool | — | Lets DB instances resolve Azure private FQDNs. Default `false`. |
| `dns_forwarding_rules` | list(object) | — | Each: `{ domain_names = "a.com,b.com", forwarding_ip_address = "10.0.0.10" }`. |
| `dns_zone_sync_enabled` | bool | — | Replicate DB private DNS zones from OCI to Azure. Default `false`. |

> **DNS overlap:** "Replicate DNS Private Zones" (`dns_zone_sync_enabled`) and the listening
> endpoint (`dns_listening_endpoint_enabled`) overlap in function — pick the one that fits.

Optional fields are only sent to the API when set, so unset ones get Azure/OCI defaults.

---

## 6. Outputs

| Output | Notes |
|--------|-------|
| `network_anchors` | Map keyed by your map key → `{ id, name }`. The `id` feeds downstream Base Database provisioning. |

```bash
terraform output network_anchors
```

---

## 7. Notes & gotchas

- **API version** is pinned to `2025-09-01` in `main.tf` — bump it there if you need a newer one.
- **Renaming a map key** destroys and recreates that anchor (Terraform identity is the key).
- **Scope:** this creates the Network Anchor only; create its prerequisites (Resource Anchor,
  delegated subnet) first, and provision the Base Database afterward.
- **OpenTofu** works — replace `terraform` with `tofu`.

---

## 8. Destroying

```bash
terraform destroy
```

Removes the Network Anchor(s) and the OCI VCN/DNS resources Azure created for them. The
Resource Anchor and subnet (inputs) are untouched.
