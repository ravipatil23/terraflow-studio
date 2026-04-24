# Terraflow Studio v5.1 — Design Document

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Frontend — Single-Page Application](#3-frontend--single-page-application)
4. [Backend — Flask Application](#4-backend--flask-application)
5. [Terraform Template Engine](#5-terraform-template-engine)
6. [Storage Layer](#6-storage-layer)
7. [Mock Terraform Validator](#7-mock-terraform-validator)
8. [Testing](#8-testing)
9. [Data Flow](#9-data-flow)
10. [Key Design Decisions](#10-key-design-decisions)
11. [Known Constraints](#11-known-constraints)

---

## 1. Overview

Terraflow Studio is a Python/Flask single-page application that generates production-ready, modular Terraform for Oracle Database@AWS and Oracle AI Database@Google Cloud. The user fills in a card-based form, the app renders Jinja2 templates server-side, and returns either a single file preview or a ZIP download.

**Stack:**
- Backend: Python 3.12, Flask 3, Jinja2
- Frontend: Vanilla JS (no framework), inline `<style>`, single `<script>` block
- Storage: FileStore (default) or CouchDB
- Tests: stdlib `unittest`, 210 tests, 19 classes

---

## 2. Architecture

```
Browser
  │
  │  GET /                → index.html (SPA, no-cache)
  │  POST /api/generate   → { content: "..." }
  │  POST /api/validate   → { valid, errors, errors_by_module }
  │  POST /api/download   → application/zip stream
  │  POST /api/test       → { passed, failed, results[] }
  │  POST /api/tf-validate→ { passed, failed, warned, results[] }
  │  POST /api/config/save
  │  GET  /api/config/load/<customer>/<cloud>
  │  GET  /api/config/list
  │  DELETE /api/config/delete/<customer>/<cloud>
  │  GET  /api/config/backend
  │
Flask (app.py)
  │
  ├── generate_all(data) ──────────────────────────────────────────┐
  │     Normalises input → calls mod/gcp generators → returns      │
  │     { "path/to/file.tf": "content", ... }                      │
  │                                                                 │
  ├── Jinja2 template engine                                        │
  │     templates/tf/<resource>/<file>.j2                          │
  │     36 templates across 10 directories                          │
  │                                                                 │
  ├── store.py (FileStore | CouchDBStore)                           │
  │     Auto-selected at startup via COUCHDB_URL env var            │
  │                                                                 │
  └── tf_validator.py                                               │
        Pure-Python structural HCL validator                        │
        8 check groups, no Terraform binary required                │
```

---

## 3. Frontend — Single-Page Application

### 3.1 Structure

`templates/index.html` is a single file (~2,041 lines) containing:
- All CSS in a `<style>` block
- All HTML (nav bars, tab panels, modals)
- All JavaScript in a single `<script>` block (~1,350 lines, 123 functions)

No build step, no bundler, no external JS framework. The Flask `render_template` call serves it directly; `Cache-Control: no-store` prevents stale caching.

### 3.2 State Model

Seven arrays hold all form state. Each element is a plain JS object corresponding to one Terraform module.

```javascript
// AWS
let awsNets     = [];   // aws_odb_network instances
let awsInfras   = [];   // aws_odb_cloud_exadata_infrastructure instances
let awsPeerings = [];   // aws_odb_network_peering_connection instances
let awsClusters = [];   // aws_odb_cloud_vm_cluster instances

// GCP
let gcpNets     = [];   // google_oracle_database_odb_network instances
let gcpInfras   = [];   // google_oracle_database_cloud_exadata_infrastructure instances
let gcpClusters = [];   // google_oracle_database_exadb_vm_cluster instances
```

A global `cloud` variable (`'aws'` | `'gcp'`) and `cur` (active tab index) control the active view. No reactive framework — the app manually calls `render*()` functions when state changes.

### 3.3 Card System

Each resource type has three functions:

| Function | Purpose |
|----------|---------|
| `def<Resource>(i)` | Returns a default state object for index `i` |
| `read<Resource>(i)` | Reads the DOM and updates `array[i]` |
| `<resource>CardHTML(d, i)` | Returns HTML string for one card |
| `render<Resource>s()` | Rebuilds the card list, calls `updateTree()` + `injectTooltips()` |

Cards are accordion-style: clicking the header toggles the `open` class. The first card is always open on init.

**Default module names** follow the pattern: first instance gets a clean name (`odb_network`), subsequent instances get a numbered suffix (`odb_network_2`, `odb_network_3`).

### 3.4 Reference Dropdowns

VM cluster and peering cards contain `<select>` dropdowns that reference infra and network modules. These are kept in sync via:

```
renderAwsNets()     → _renderClusterAndPeeringDropdowns()
renderAwsInfras()   → _renderClusterAndPeeringDropdowns()
renderGcpNets()     → _renderGcpClusterDropdowns()
renderGcpInfras()   → _renderGcpClusterDropdowns()
```

`_renderClusterAndPeeringDropdowns()` surgically updates only the `<select>` innerHTML in existing cards — it does not rebuild the full card, which would lose open/closed state and any partially entered values.

### 3.5 Region & AZ Dropdowns

`ODB_REGIONS` (AWS) and `GCP_REGIONS` (GCP) are JS constants sourced from Oracle's official regional availability documentation. Each entry has `{ region, label, azs/zones, oci/ociLabel, status }`.

- Region `<select>` is split into `<optgroup label="Live">` and `<optgroup label="Planned">`.
- Selecting a region calls `onRegionChange()` / `onGcpRegionChange()`, which repopulates the AZ/zone dropdown with valid options for that region.
- GCP cards also show an OCI paired-region hint (`🔗 Paired OCI region: ...`) that updates on change.

### 3.6 File Tree

`updateTree()` rebuilds the file tree sidebar from the current state arrays. `renderEditor()` calls `POST /api/generate` with the current `activeFile` key and renders the result in the code panel. Both are debounced via `refresh()` (300ms).

### 3.7 Validation UI

`vgen(tab, isGcp)` POSTs to `/api/validate`. On failure:
- Finds the failing card by matching the `module-name-field` input value to `errors_by_module` keys
- Opens the card (`card.classList.add('open')`)
- Inserts a red banner at the top of the card body
- Adds `.invalid` class to individual field inputs

`refresh()` clears all `.invalid` classes and error banners each time any field changes.

### 3.8 Test Modal

The 🧪 Test button (enabled when a customer name is entered) opens a modal with two tabs:

- **⚙ Functional Tests** — calls `POST /api/test`
- **🔬 Mock TF Validate** — calls `POST /api/tf-validate`

`switchTestTab(tab)` switches the active tab and re-runs the selected test against the current form state. Results are grouped by category with pass ✅ / warn ⚠️ / fail ❌ icons and inline error messages.

### 3.9 Customer Bar

The customer bar (`#cust-bar`) provides:
- `saveConfig()` → `POST /api/config/save`
- `loadConfig()` → `GET /api/config/load/<name>/<cloud>` → `applyConfig(doc)`
- `deleteConfig()` → `DELETE /api/config/delete/<name>/<cloud>`
- `onCustSelect()` → loads a config when the dropdown changes
- `updateTestBtn()` → enables/disables the Test button when a name is typed or a config is loaded

`applyConfig(doc)` repopulates all seven state arrays from the loaded document, then calls `renderAll()` and `updateTestBtn()`.

---

## 4. Backend — Flask Application

### 4.1 File: `app.py` (1,143 lines)

Organised into sections:

```
Helpers          render_tf(), is_ref(), parse_list(), tf_bool(), _s3_val()
AWS Generators   mod0_* through mod3_* + build_root_*
GCP Generators   gcp0_* through gcp1_* + gcp_subnet_* + gcp_build_root_*
Defaults         _aws_net_defaults() ... _gcp_cluster_defaults()
Core             generate_all()
Routes           index(), api_generate(), api_download(), api_validate(),
                 api_config_*, api_test(), api_tf_validate()
```

### 4.2 Generator Naming Convention

Each resource type has four file generators and one context builder:

```python
# Pattern: mod<N>_<file>(module_name, [data, refs...])
_mod3_ctx(d, mn0, mn1)    # builds the Jinja2 context dict
mod3_main(mn, d, mn0, mn1) # renders main.tf.j2
mod3_vars(mn, d, mn0, mn1) # renders variables.tf.j2
mod3_outputs(mn)            # renders outputs.tf.j2
mod3_tfvars(mn, d, mn0, mn1)# renders terraform.tfvars.j2
```

AWS modules: `mod0` (network), `mod1` (infra), `mod2` (peering), `mod3` (VM cluster).  
GCP modules: `gcp0` (ODB network), `gcp_subnet` (ODB subnet), `gcp2` (Exadata infra), `gcp1` (VM cluster).

GCP VM cluster takes four module name references: `mn0` (ODB network), `mn1` (client subnet), `mn2` (backup subnet), `mn3` (Exadata infra).

### 4.3 `generate_all(data)` — Core Orchestrator

`generate_all` receives the full form payload and returns a `dict` mapping file paths to content strings.

**Input normalisation flow (AWS):**
1. Read `aws_networks`, `aws_infras`, `aws_peerings`, `aws_clusters` arrays (or fall back to legacy `module_0..3` single-instance keys for backward compat)
2. Apply `_aws_*_defaults()` to each element (fills in display names, coerces types, sets `vm_mode='arn'` default, etc.)
3. Determine `first_net_name` and `first_inf_name` for auto-wiring fallbacks
4. Loop over each module and call the four generator functions
5. Call `build_root_main()` and `build_root_tfvars()` to produce root files

**GCP** follows the same pattern but the cluster generator takes four module refs instead of two, because GCP subnets are separate modules that must be resolved from the network's `client_subnet_module` / `backup_subnet_module` fields.

### 4.4 Default Normalisation

`_aws_net_defaults(d)` and similar functions coerce user input before it reaches templates:
- `s3_access` / `zero_etl_access`: boolean → `'ENABLED'`/`'DISABLED'` string via `_s3_val(v)`. Direct `bool`-to-string conversion is intentionally avoided because `'DISABLED'` is truthy in Python/JS — `_s3_val` checks the string value explicitly.
- `compute_count` / `storage_count`: cast to `int`, with minimums
- `vm_mode`: defaults to `'arn'` (AWS prefers ARN references)
- `db_servers_mode`: defaults to `'auto'` (data source discovery)
- `region` / `infra_ref` / `network_ref`: filled from first available instance if blank

### 4.5 ARN vs ID Wiring

AWS VM clusters support two reference modes, controlled by `vm_mode`:

| `vm_mode` | Root wires | Module declares | Data source uses |
|-----------|-----------|----------------|-----------------|
| `'arn'` (default) | `module.<infra>.infra_arn` | `cloud_exadata_infrastructure_arn` | `cloud_exadata_infrastructure_arn` |
| `'id'` | `module.<infra>.infra_id` | `cloud_exadata_infrastructure_id` | `cloud_exadata_infrastructure_id` |

The Jinja2 template `aws_vm_cluster/main.tf.j2` uses `{% if vm_mode == 'id' %}` to select which block to emit. In ARN mode no `_id` variables are declared at all, and vice versa. This keeps generated files clean with no unused variables.

### 4.6 Validation Route

`POST /api/validate` accepts `{ tab, aws_networks: [...], ... }` and returns:

```json
{
  "valid": false,
  "errors": { "display_name": "Required", "client_subnet_cidr": "Valid CIDR required" },
  "errors_by_module": {
    "odb_network": { "display_name": "Required", "client_subnet_cidr": "Valid CIDR required" }
  }
}
```

`errors` is a flat merge for backward compat; `errors_by_module` is keyed by module name and is what the UI uses to find and highlight the correct card. Validation always operates on **raw** input (before defaults are applied) so empty fields are caught correctly.

### 4.7 `/api/test` Route

Runs four check groups programmatically against the payload (or a saved config if `customer` is provided):

1. **Input Validation** — checks raw arrays for required fields, CIDR formats, minimum values
2. **Module Generation** — calls `generate_all()` and checks all expected files exist and are non-empty
3. **Content Checks** — verifies root `main.tf` contains correct provider, module references, and cross-wiring
4. **Uniqueness** — checks for duplicate module names

Results are returned as `{ group, name, status, error }` records.

### 4.8 `/api/tf-validate` Route

Calls `generate_all()` then passes the file dict to `validate_terraform(files, cloud)` from `tf_validator.py`. Returns the same `{ passed, failed, warned, total, results[] }` structure as `/api/test`.

---

## 5. Terraform Template Engine

### 5.1 Template Location

All Jinja2 templates live under `templates/tf/`. The Jinja2 environment is configured with `autoescape=False` (content is HCL, not HTML) and `undefined=StrictUndefined` so missing context variables raise errors immediately rather than silently rendering as empty.

```
templates/tf/
├── aws_odb_network/         main, variables, outputs, tfvars
├── aws_exadata_infra/       main, variables, outputs, tfvars
├── aws_peering/             main, variables, outputs, tfvars
├── aws_vm_cluster/          main, variables, outputs, tfvars
├── aws_root/                main, tfvars
├── gcp_odb_network/         main, variables, outputs, tfvars
├── gcp_odb_subnet/          main, variables, outputs, tfvars
├── gcp_exadb_infra/         main, variables, outputs, tfvars
├── gcp_exadb_vm_cluster/    main, variables, outputs, tfvars
└── gcp_root/                main, tfvars
```

36 templates total. Root modules do not have `variables.tf` or `outputs.tf` (all outputs are declared inline in `main.tf.j2`).

### 5.2 AWS VM Cluster Template — Special Cases

`aws_vm_cluster/main.tf.j2` handles three conditional behaviours:

**db_servers (auto mode):**
```hcl
data "aws_odb_db_servers" "{{ module_name }}" {
  {% if vm_mode == 'id' %}
  cloud_exadata_infrastructure_id = var.cloud_exadata_infrastructure_id
  {% else %}
  cloud_exadata_infrastructure_arn = var.cloud_exadata_infrastructure_arn
  {% endif %}
}
...
db_servers = data.aws_odb_db_servers.{{ module_name }}.db_servers[*].id
```

**db_servers (manual mode):**
```hcl
db_servers = var.db_servers
```

**db_servers (empty / omitted):** No `db_servers` argument emitted at all.

**Infrastructure references (ARN vs ID):** Only the selected pair is emitted; the other is entirely absent from both `main.tf` and `variables.tf`.

### 5.3 GCP VM Cluster Template — db_servers Blocks

GCP uses a repeated nested block syntax rather than a flat list:

```hcl
{% for ocid in db_servers %}
db_servers {
  ocid = "{{ ocid }}"
}
{% endfor %}
```

Empty `db_servers` → no blocks emitted → GCP uses all available servers automatically.

### 5.4 Root Template Wiring

`aws_root/main.tf.j2` iterates over all four resource lists and wires them:

```hcl
{% for cl in clusters %}
module "{{ cl.module_name }}" {
  ...
  {% if cl.vm_mode == 'id' %}
  cloud_exadata_infrastructure_id = module.{{ cl.infra_ref }}.infra_id
  odb_network_id                  = module.{{ cl.network_ref }}.network_id
  {% else %}
  cloud_exadata_infrastructure_arn = module.{{ cl.infra_ref }}.infra_arn
  odb_network_arn                  = module.{{ cl.network_ref }}.network_arn
  {% endif %}
  depends_on = [module.{{ cl.infra_ref }}, module.{{ cl.network_ref }}]
}
{% endfor %}
```

Root outputs expose both `_id` and `_arn` for every network and infra module.

`gcp_root/main.tf.j2` iterates networks (each generating three modules: ODB network + client subnet + backup subnet), then infras, then clusters. Cluster references resolve via the network's `client_subnet_module` / `backup_subnet_module` fields.

---

## 6. Storage Layer

`store.py` provides a pluggable backend selected at startup.

### 6.1 Backend Selection

```python
def _make_backend():
    if COUCHDB_URL:
        try:
            # probe the CouchDB server
            store = CouchDBStore(COUCHDB_URL, COUCHDB_DB)
            return store
        except Exception:
            pass  # fall through to FileStore
    return FileStore()
```

The singleton `storage = _make_backend()` is imported by `app.py`.

### 6.2 FileStore

```
data/
  {customer-slug}/
    aws.json
    gcp.json
```

`_slug(customer)` converts the customer name to a safe directory name (lowercase, special chars → `-`, max 64 chars). Each document is the full form payload plus `customer`, `cloud`, and `updated` (ISO-8601 UTC).

### 6.3 CouchDBStore

Uses only stdlib `urllib` (no `requests` dependency). Document IDs are `{slug}_{cloud}`. On save, the existing document is fetched first to get `_rev` for update; without `_rev` CouchDB rejects the PUT as a conflict.

### 6.4 Interface

Both backends implement the same four methods:

```python
save(customer, cloud, payload) → { ok, id }
load(customer, cloud) → dict | None
list_customers() → [{ customer, slug, clouds }]
delete(customer, cloud) → bool
```

---

## 7. Mock Terraform Validator

`tf_validator.py` (515 lines) performs structural validation of generated files without requiring a Terraform binary.

### 7.1 HCL Parser

A lightweight regex-based parser handles:
- `_strip_comments(text)` — removes `# ...`, `// ...`, and `/* ... */`
- `_check_balanced(text, filename)` — validates `{}[]()` balance after stripping comments and string literals
- `_extract_blocks(text, block_type)` — finds `resource "type" "name" { ... }` blocks
- `_extract_single_blocks(text, block_type)` — finds `variable "name" { ... }` and `output "name" { ... }`
- `_extract_module_blocks(text)` — finds `module "name" { source = "..." }` and extracts source path
- `_extract_var_refs(text)` — finds all `var.<n>` references
- `_extract_module_output_refs(text)` — finds all `module.<n>.<attr>` references

### 7.2 Provider Schemas

`AWS_SCHEMAS` and `GCP_SCHEMAS` dicts map resource type strings to `{ required: [...], optional: [...] }` argument lists. `RESOURCE_OUTPUTS` maps resource types to known output attributes. These are used to validate that generated resources declare required arguments and that outputs reference valid attributes.

### 7.3 Check Groups

| Group | Logic |
|-------|-------|
| File Structure | `path in files` for all expected files |
| HCL Syntax | `_check_balanced()` on every `.tf` file |
| Provider | `expected_source in root_main` + version constraint present |
| Resource Schema | Resource type in `ALL_SCHEMAS`; each required arg present |
| Variable Resolution | `var_refs - declared_vars == ∅` |
| Output Validity | Output `value` references `<resource_type>.this.<attr>` where `attr` is in `RESOURCE_OUTPUTS` |
| Module Cross-References | Source paths are `./modules/<name>`; `module.<n>` declared; `module.<n>.<attr>` in outputs |
| tfvars Completeness | `declared_vars - tfvars_keys` → warnings for variables using defaults |

### 7.4 Result Type

```python
@dataclass
class CheckResult:
    group:  str
    name:   str
    status: str   # 'pass' | 'fail' | 'warn'
    error:  Optional[str]
    file:   Optional[str]
```

`summarise(results)` converts a list of `CheckResult` to the JSON-serialisable dict returned by the API.

---

## 8. Testing

### 8.1 Test Structure

`tests/test_all.py` — 210 tests across 19 `unittest.TestCase` classes. No external test framework (pytest not available in the sandboxed environment).

| Class | Tests | Focus |
|-------|-------|-------|
| `TestHelpers` | 15 | `is_ref`, `parse_list`, `tf_bool` |
| `TestAwsOdbNetwork` | 10 | `mod0_*` file generators |
| `TestAwsExadataInfra` | 9 | `mod1_*`, maintenance window |
| `TestAwsPeering` | 5 | `mod2_*`, network ref wiring |
| `TestAwsVmCluster` | 9 | `mod3_*`, ARN/ID, license, db_servers |
| `TestAwsRoot` | 8 | Multi-instance wiring, outputs, depends_on |
| `TestGcpOdbNetwork` | 7 | `gcp0_*` |
| `TestGcpOdbSubnet` | 6 | Client + backup subnet generators |
| `TestGcpExadataInfra` | 6 | `gcp2_*` |
| `TestGcpVmCluster` | 7 | `gcp1_*`, db_servers blocks |
| `TestGcpRoot` | 10 | Subnet auto-wiring, multi-cluster |
| `TestGenerateAll` | 14 | End-to-end, backward-compat, cross-wiring |
| `TestDefaultNormalisers` | 9 | `_aws_*_defaults`, `_gcp_*_defaults` |
| `TestApiRoutes` | 33 | All HTTP routes, all validation tabs |
| `TestFileStore` | 12 | CRUD, slugs, multi-cloud, overwrite |
| `TestConfigApiRoutes` | 9 | Mocked storage layer |
| `TestCouchDBStore` | 7 | Mocked urllib, rev handling |
| `TestApiTestRoute` | 15 | `/api/test` validation, wiring checks |
| `TestTFValidator` | 19 | HCL syntax, schema, var resolution, cross-refs |

### 8.2 Notable Test Patterns

**Mocking the storage backend:**
```python
with patch.object(app_module, 'storage', mock_store):
    r = self.client.post('/api/config/save', json={...})
```

**CouchDB tests** use `MagicMock` to stub `_get` and `_put` at the method level rather than mocking `urllib.request.urlopen`, avoiding complex call-sequence matching.

**TF Validator tests** inject broken files to verify detection:
```python
files['modules/odb_network/main.tf'] += '\n  undefined_arg = var.does_not_exist\n'
results = self._validate(files, 'aws')
# assert failure detected
```

### 8.3 Test-Driven Bug Catches

The test suite has caught three real bugs:

1. **`s3_access`/`zero_etl_access` always ENABLED** — `_aws_net_defaults` converted `False` → `'DISABLED'` (a truthy string), then `mod0_tfvars` re-evaluated `d.get('s3_access')` which was truthy → always emitted `ENABLED`. Fixed with `_s3_val(v)` which compares the string value.

2. **Validation always failing** — `/api/validate` read `module_0`/`module_1` (old single-instance keys) but the UI had been sending `aws_networks`/`aws_infras` arrays for months. Fixed by rewriting the route to read arrays with fallback.

3. **`mod3_main` missing `vm_mode`** — `gcp1_main` and `mod3_main` were called without the data context, causing `UndefinedError` in templates that used `{% if vm_mode %}`. Fixed by adding `d=None` optional context and fallback dicts.

---

## 9. Data Flow

### 9.1 Form → Generated Terraform (AWS, single network)

```
User fills Network card
  │
  └── oninput="readAwsNet(0); refresh()"
        │
        ├── readAwsNet(0): awsNets[0] = { display_name: "prod-net", ... }
        │
        └── refresh() → debounced 300ms
              │
              └── updateTree() + renderEditor()
                    │
                    └── POST /api/generate
                          { cloud: "aws",
                            file_key: "modules/odb_network/main.tf",
                            aws_networks: [{ module_name: "odb_network", ... }],
                            aws_infras: [...], ... }
                          │
                          └── generate_all(data)
                                │
                                ├── _aws_net_defaults(d)
                                ├── mod0_main("odb_network", d)
                                │     └── render_tf("aws_odb_network/main.tf.j2", ...)
                                │
                                └── { "modules/odb_network/main.tf": "# Generated HCL..." }
```

### 9.2 Download Flow

```
User clicks Download ZIP
  │
  └── dlZip() → POST /api/download with buildPayload()
        │
        └── api_download()
              │
              ├── generate_all(data) → { path: content, ... }
              │
              └── zipfile.ZipFile() → in-memory BytesIO
                    │
                    └── send_file(buf, mimetype='application/zip')
```

### 9.3 Save / Load Flow

```
Save:  onCustInput() → getCustName() → saveConfig()
         → POST /api/config/save { customer, cloud, aws_networks: [...], ... }
         → storage.save(customer, cloud, payload)
         → FileStore: data/{slug}/{cloud}.json

Load:  onCustSelect() or loadConfig()
         → GET /api/config/load/{customer}/{cloud}
         → storage.load(customer, cloud) → full payload dict
         → applyConfig(doc): repopulates awsNets[], awsInfras[], etc.
         → renderAll() → updateTestBtn()
```

---

## 10. Key Design Decisions

### No frontend framework

The SPA uses vanilla JS throughout. This keeps the deployment trivially simple (one Python process, no Node.js, no build step) and makes the `<script>` block directly inspectable. The trade-off is manual DOM management via `render*()` calls, but the card-based architecture makes this tractable — each resource type has one render function.

### JS syntax validated at every change

Before any package is delivered, the extracted JS is checked with `node --check`. This caught several silent bugs where `str_replace` operations accidentally deleted function headers, leaving orphaned code at the top level that broke the entire page silently.

### Jinja2 for Terraform generation

Server-side Jinja2 templates are simpler to reason about and test than string concatenation. The `StrictUndefined` environment means a missing context variable raises an error immediately rather than silently emitting blank Terraform, which would pass syntax checks but fail at `terraform plan`.

### ARN default for AWS VM clusters

AWS documentation and official sample code both use ARN-based cross-references as the recommended pattern, particularly when infra and cluster are provisioned in the same Terraform run (ARNs are available as outputs before `apply` completes, while IDs sometimes require a refresh). ID mode remains available as an explicit opt-in.

### db_servers auto-discovery for AWS

DB server IDs are not known at write time — they only exist after the Exadata infrastructure is provisioned. The `data "aws_odb_db_servers"` data source reads them at plan time. Hardcoding IDs would make configs non-portable across accounts or re-provisioning scenarios.

### Surgical dropdown updates

When a new infra or network is added, the cluster dropdown must reflect the new option. Rebuilding the entire cluster card HTML (the naive approach) loses the open/closed state, focused inputs, and any in-progress edits. `_renderClusterAndPeeringDropdowns()` instead finds the existing `<select>` by ID and updates only its `innerHTML`, touching nothing else.

### `errors_by_module` in validation response

The original validation response returned a flat `errors` dict. This was extended to `errors_by_module: { "odb_network": { "field": "message" } }` so the UI can locate the exact card by matching the module name, rather than just showing a generic toast. The flat `errors` dict is preserved for backward compat.

### FileStore as default

CouchDB adds an external dependency. FileStore works out of the box with no configuration and is sufficient for single-instance deployments. CouchDB is opt-in via `COUCHDB_URL` for teams who need shared persistence or horizontal scaling.

---

## 11. Known Constraints

| Constraint | Notes |
|------------|-------|
| Single-threaded by default | Run with Gunicorn (`-w 4`) for production concurrent load |
| No authentication | The app has no login — deploy behind a VPN or auth proxy in shared environments |
| GCP db_servers manual only | No GCP data source equivalent to `aws_odb_db_servers`; OCIDs must be provided manually |
| Mock validator schema coverage | `RESOURCE_OUTPUTS` in `tf_validator.py` may not cover every valid attribute; unknown attributes generate warnings rather than failures |
| Backward-compat payload | `generate_all` still accepts the old `module_0`/`module_1` single-instance keys; this path is tested but no longer generated by the UI |
| Planned GCP regions | 2 planned regions (Mexico, Turin) are shown in the dropdown as non-selectable; AZ data unavailable until GA |
| Terraform binary not bundled | The mock validator covers structural correctness; actual provider-level validation (`terraform validate`) still requires a local Terraform installation |
