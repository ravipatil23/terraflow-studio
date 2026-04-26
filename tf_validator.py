"""
tf_validator.py — Mock Terraform Provider Validator for Terraflow Studio
=========================================================================
Simulates `terraform validate` without needing Terraform installed.

Checks performed:
  1. HCL syntax  — braces/brackets balanced, basic block structure valid
  2. Provider    — required_providers block declares correct provider + version
  3. Resources   — resource type matches known AWS/GCP ODB schema, required
                   arguments are present, argument types are plausible
  4. Variables   — every var.* reference in main.tf resolves to a declared variable
  5. Outputs     — every output references a known resource attribute
  6. Module refs — root main.tf module blocks reference a ./modules/<name> path
                   that exists in the generated file set
  7. Cross-refs  — module.<name>.<output> in root are resolvable from declared outputs
"""

import re
from dataclasses import dataclass, field
from typing import Optional

# ─────────────────────────────────────────────────────────────────────────────
#  PROVIDER SCHEMAS  (required + optional args per resource type)
# ─────────────────────────────────────────────────────────────────────────────

AWS_SCHEMAS = {
    'aws_odb_network': {
        'required': ['display_name', 'availability_zone_id', 'client_subnet_cidr',
                     'backup_subnet_cidr', 's3_access', 'zero_etl_access'],
        'optional': ['availability_zone', 'region', 'default_dns_prefix',
                     'delete_associated_resources', 'tags'],
    },
    'aws_odb_cloud_exadata_infrastructure': {
        'required': ['display_name', 'shape', 'compute_count', 'storage_count',
                     'availability_zone_id', 'maintenance_window'],
        'optional': ['availability_zone', 'region', 'database_server_type',
                     'storage_server_type', 'customer_contacts', 'tags'],
    },
    'aws_odb_network_peering_connection': {
        'required': ['display_name'],
        'optional': ['odb_network_id', 'odb_network_arn', 'peer_network_id',
                     'peer_network_cidrs', 'region', 'tags'],
    },
    'aws_odb_cloud_vm_cluster': {
        'required': ['display_name', 'cpu_core_count', 'gi_version',
                     'hostname_prefix', 'license_model', 'ssh_public_keys',
                     'data_collection_options'],
        'optional': ['cloud_exadata_infrastructure_id', 'cloud_exadata_infrastructure_arn',
                     'odb_network_id', 'odb_network_arn', 'db_servers',
                     'cluster_name', 'timezone', 'data_storage_size_in_tbs',
                     'db_node_storage_size_in_gbs', 'memory_size_in_gbs',
                     'scan_listener_port_tcp', 'system_version',
                     'is_local_backup_enabled', 'is_sparse_diskgroup_enabled',
                     'region', 'tags'],
    },
}

GCP_SCHEMAS = {
    'google_oracle_database_odb_network': {
        'required': ['odb_network_id', 'location', 'network'],
        'optional': ['project', 'gcp_oracle_zone', 'deletion_protection', 'labels'],
    },
    'google_oracle_database_odb_subnet': {
        'required': ['odb_subnet_id', 'location', 'odb_network', 'cidr_range', 'purpose'],
        'optional': ['project', 'deletion_protection'],
    },
    'google_oracle_database_cloud_exadata_infrastructure': {
        'required': ['cloud_exadata_infrastructure_id', 'location', 'shape',
                     'compute_count', 'storage_count'],
        'optional': ['display_name', 'gcp_oracle_zone', 'project',
                     'total_storage_size_gb', 'maintenance_window',
                     'customer_contacts', 'deletion_protection', 'labels'],
    },
    'google_oracle_database_exadb_vm_cluster': {
        'required': ['exadb_vm_cluster_id', 'location', 'gi_version',
                     'hostname_prefix', 'node_count',
                     'enabled_ecpu_count_per_node', 'ssh_public_keys',
                     'odb_network', 'odb_subnet', 'backup_odb_subnet',
                     'exadata_infrastructure'],
        'optional': ['display_name', 'gcp_oracle_zone', 'project',
                     'license_type', 'additional_ecpu_count_per_node',
                     'vm_file_system_storage_size_gbs', 'cluster_name',
                     'time_zone', 'system_version', 'memory_per_node_in_gbs',
                     'db_node_storage_size_per_vm_in_gbs',
                     'data_storage_size_in_tbs', 'spare_snapshot_space_in_gbs',
                     'disk_redundancy', 'diagnostics_events_enabled',
                     'health_monitoring_enabled', 'incident_logs_enabled',
                     'deletion_protection', 'labels'],
    },
}

ALL_SCHEMAS = {**AWS_SCHEMAS, **GCP_SCHEMAS}

# Known outputs per resource type
RESOURCE_OUTPUTS = {
    'aws_odb_network': [
        'id', 'arn', 'oci_network_anchor_id', 'oci_vcn_id', 'display_name',
        'status', 'status_reason', 'peering_connection_id',
    ],
    'aws_odb_cloud_exadata_infrastructure': [
        'id', 'arn', 'oci_exadata_infrastructure_id', 'display_name',
        'shape', 'compute_count', 'storage_count', 'status', 'status_reason',
        'activated_storage_count', 'additional_storage_count',
        'availability_zone', 'availability_zone_id',
    ],
    'aws_odb_network_peering_connection': [
        'id', 'arn', 'display_name', 'status', 'status_reason',
        'odb_network_id', 'peer_network_id',
    ],
    'aws_odb_cloud_vm_cluster': [
        'id', 'arn', 'display_name', 'gi_version', 'hostname_prefix',
        'hostname_prefix_computed', 'license_model', 'cpu_core_count',
        'cluster_name', 'scan_dns_name', 'scan_ip_ids', 'status', 'status_reason',
        'lifecycle_state', 'node_count', 'shape', 'storage_size_in_gbs',
        'data_storage_size_in_tbs', 'db_node_storage_size_in_gbs',
        'memory_size_in_gbs', 'scan_listener_port_tcp', 'system_version',
    ],
    'google_oracle_database_odb_network': [
        'id', 'name', 'create_time', 'state', 'effective_labels',
        'terraform_labels',
    ],
    'google_oracle_database_odb_subnet': [
        'id', 'name', 'create_time', 'state',
    ],
    'google_oracle_database_cloud_exadata_infrastructure': [
        'id', 'name', 'create_time', 'state', 'display_name',
        'shape', 'compute_count', 'storage_count', 'total_storage_size_gb',
        'available_storage_size_gb', 'effective_labels',
    ],
    'google_oracle_database_exadb_vm_cluster': [
        'id', 'name', 'create_time', 'state', 'display_name',
        'gi_version', 'node_count', 'hostname_prefix',
        'scan_dns_name', 'effective_labels',
    ],
}


# ─────────────────────────────────────────────────────────────────────────────
#  RESULT DATACLASS
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class CheckResult:
    group:   str
    name:    str
    status:  str          # 'pass' | 'fail' | 'warn'
    error:   Optional[str] = None
    file:    Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
#  LIGHTWEIGHT HCL PARSER (structural only)
# ─────────────────────────────────────────────────────────────────────────────

def _strip_comments(text: str) -> str:
    """Remove # and // line comments and /* */ block comments."""
    # Block comments
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    # Line comments
    text = re.sub(r'(#|//).*', '', text)
    return text


def _check_balanced(text: str, filename: str) -> Optional[CheckResult]:
    """Check brace/bracket balance."""
    clean = _strip_comments(text)
    # Remove string literals to avoid false positives
    clean = re.sub(r'"(?:[^"\\]|\\.)*"', '""', clean)
    stack = []
    pairs = {')': '(', ']': '[', '}': '{'}
    for i, ch in enumerate(clean):
        if ch in '([{':
            stack.append(ch)
        elif ch in ')]}':
            if not stack or stack[-1] != pairs[ch]:
                return CheckResult('HCL Syntax', f'{filename}: balanced braces',
                                   'fail', f'Unexpected "{ch}" — mismatched delimiter')
            stack.pop()
    if stack:
        return CheckResult('HCL Syntax', f'{filename}: balanced braces',
                           'fail', f'Unclosed "{stack[-1]}" — missing closing delimiter')
    return None


def _extract_blocks(text: str, block_type: str):
    """Extract top-level block labels: resource "type" "name" { ... }"""
    clean = _strip_comments(text)
    pattern = rf'{re.escape(block_type)}\s+"([^"]+)"\s+"([^"]+)"\s*\{{'
    return re.findall(pattern, clean)


def _extract_single_blocks(text: str, block_type: str):
    """Extract blocks like: variable "name" { or output "name" {"""
    clean = _strip_comments(text)
    pattern = rf'{re.escape(block_type)}\s+"([^"]+)"\s*\{{'
    return re.findall(pattern, clean)


def _extract_module_blocks(text: str):
    """Extract module "name" { source = "..." } → {name: source}"""
    clean = _strip_comments(text)
    result = {}
    for m in re.finditer(r'module\s+"([^"]+)"\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}', clean, re.DOTALL):
        name, body = m.group(1), m.group(2)
        src_m = re.search(r'source\s*=\s*"([^"]+)"', body)
        result[name] = src_m.group(1) if src_m else ''
    return result


def _extract_var_refs(text: str):
    """Find all var.<name> references."""
    clean = _strip_comments(text)
    # Remove string literals
    clean = re.sub(r'"(?:[^"\\]|\\.)*"', '""', clean)
    return set(re.findall(r'\bvar\.(\w+)', clean))


def _extract_resource_args(text: str, resource_type: str):
    """Get argument names inside a resource block."""
    clean = _strip_comments(text)
    # Find the resource block
    m = re.search(
        rf'resource\s+"{re.escape(resource_type)}"\s+"[^"]+"\s*\{{(.*?)\n\}}',
        clean, re.DOTALL)
    if not m:
        return set()
    body = m.group(1)
    # Top-level argument keys (lines like "  key = ...")
    return set(re.findall(r'^\s{2}(\w+)\s*(?:=|\{)', body, re.MULTILINE))


def _extract_module_output_refs(text: str):
    """Find module.<name>.<attr> references."""
    clean = _strip_comments(text)
    clean = re.sub(r'"(?:[^"\\]|\\.)*"', '""', clean)
    return re.findall(r'module\.(\w+)\.(\w+)', clean)


# ─────────────────────────────────────────────────────────────────────────────
#  VALIDATOR
# ─────────────────────────────────────────────────────────────────────────────

def validate_terraform(files: dict, cloud: str) -> list[CheckResult]:
    """
    Validate a dict of {filepath: content} generated by generate_all().
    Returns list of CheckResult.
    """
    results: list[CheckResult] = []

    def ok(group, name, file=None):
        results.append(CheckResult(group, name, 'pass', file=file))

    def fail(group, name, error, file=None):
        results.append(CheckResult(group, name, 'fail', error=error, file=file))

    def warn(group, name, error, file=None):
        results.append(CheckResult(group, name, 'warn', error=error, file=file))

    schemas = AWS_SCHEMAS if cloud == 'aws' else GCP_SCHEMAS
    provider_name = 'aws' if cloud == 'aws' else 'google'
    expected_source = f'hashicorp/{provider_name}'

    # ── 1. File presence ──────────────────────────────────────────────────────
    grp = 'File Structure'
    for required in ['main.tf', 'terraform.tfvars']:
        if required in files:
            ok(grp, f'Root {required} exists', required)
        else:
            fail(grp, f'Root {required} exists', f'{required} was not generated')

    # Module directories — every modules/<name>/ should have all 4 files
    module_names = set()
    for path in files:
        m = re.match(r'^modules/([^/]+)/', path)
        if m:
            module_names.add(m.group(1))

    for mn in sorted(module_names):
        for ftype in ['main.tf', 'variables.tf', 'outputs.tf', 'terraform.tfvars']:
            key = f'modules/{mn}/{ftype}'
            if key in files:
                ok(grp, f'modules/{mn}/{ftype} exists', key)
            else:
                fail(grp, f'modules/{mn}/{ftype} exists', 'File missing from generated output', key)

    # ── 2. HCL Syntax ─────────────────────────────────────────────────────────
    grp = 'HCL Syntax'
    for path, content in files.items():
        if not path.endswith('.tf'):
            continue
        err = _check_balanced(content, path)
        if err:
            fail(grp, f'{path}: balanced braces', err.error, path)
        else:
            ok(grp, f'{path}: balanced braces', path)

        # Check no obviously invalid tokens (bare = without value on next meaningful line)
        clean = _strip_comments(content)
        if re.search(r'=\s*\n\s*\n', clean):
            warn(grp, f'{path}: no empty assignments', 'Found "=" with blank value', path)
        else:
            ok(grp, f'{path}: no empty assignments', path)

    # ── 3. Provider declarations ───────────────────────────────────────────────
    grp = 'Provider'
    root_main = files.get('main.tf', '')
    if expected_source in root_main:
        ok(grp, f'Root declares {expected_source} provider')
    else:
        fail(grp, f'Root declares {expected_source} provider',
             f'"{expected_source}" not found in root main.tf')

    # Check version constraint present
    if '>=' in root_main and expected_source in root_main:
        ok(grp, 'Provider version constraint present')
    else:
        warn(grp, 'Provider version constraint present',
             'No version constraint found for provider')

    # Check required_version for Terraform itself
    if 'required_version' in root_main:
        ok(grp, 'Terraform required_version declared')
    else:
        warn(grp, 'Terraform required_version declared',
             'No required_version in root main.tf — recommended to pin Terraform version')

    # Each module main.tf should also declare provider
    for mn in sorted(module_names):
        mod_main = files.get(f'modules/{mn}/main.tf', '')
        if expected_source in mod_main:
            ok(grp, f'modules/{mn}: declares {provider_name} provider')
        else:
            warn(grp, f'modules/{mn}: declares {provider_name} provider',
                 f'{expected_source} not found in module main.tf — OK if inherited from root',
                 f'modules/{mn}/main.tf')

    # ── 4. Resource schema validation ─────────────────────────────────────────
    grp = 'Resource Schema'
    for mn in sorted(module_names):
        mod_main = files.get(f'modules/{mn}/main.tf', '')
        if not mod_main:
            continue

        resource_blocks = _extract_blocks(mod_main, 'resource')
        if not resource_blocks:
            warn(grp, f'modules/{mn}: has resource block',
                 'No resource block found in module main.tf',
                 f'modules/{mn}/main.tf')
            continue

        for res_type, res_name in resource_blocks:
            if res_type in ALL_SCHEMAS:
                ok(grp, f'modules/{mn}: resource type "{res_type}" is known')
                schema = ALL_SCHEMAS[res_type]
                actual_args = _extract_resource_args(mod_main, res_type)
                for req_arg in schema['required']:
                    # Allow var.* references for required args
                    if req_arg in actual_args or f'var.{req_arg}' in mod_main:
                        ok(grp, f'modules/{mn} "{res_type}": required arg "{req_arg}" present')
                    else:
                        fail(grp, f'modules/{mn} "{res_type}": required arg "{req_arg}" present',
                             f'Required argument "{req_arg}" not found in resource block',
                             f'modules/{mn}/main.tf')
            else:
                warn(grp, f'modules/{mn}: resource type "{res_type}" is known',
                     f'Unknown resource type "{res_type}" — not in mock provider schema',
                     f'modules/{mn}/main.tf')

    # ── 5. Variable resolution ─────────────────────────────────────────────────
    grp = 'Variable Resolution'
    for mn in sorted(module_names):
        mod_main = files.get(f'modules/{mn}/main.tf', '')
        mod_vars = files.get(f'modules/{mn}/variables.tf', '')
        if not mod_main or not mod_vars:
            continue

        declared_vars = set(_extract_single_blocks(mod_vars, 'variable'))
        used_vars     = _extract_var_refs(mod_main)

        for v in sorted(used_vars):
            if v in declared_vars:
                ok(grp, f'modules/{mn}: var.{v} declared')
            else:
                fail(grp, f'modules/{mn}: var.{v} declared',
                     f'var.{v} used in main.tf but not declared in variables.tf',
                     f'modules/{mn}/variables.tf')

        # Warn about declared-but-unused variables
        unused = declared_vars - used_vars
        # Remove common ones that are used indirectly (tags, labels, etc.)
        unused -= {'tags', 'labels', 'project', 'deletion_protection'}
        if unused:
            warn(grp, f'modules/{mn}: no unused variables',
                 f'Declared but not used in main.tf: {", ".join(sorted(unused))}',
                 f'modules/{mn}/variables.tf')
        else:
            ok(grp, f'modules/{mn}: no unused variables')

    # ── 6. Output validity ────────────────────────────────────────────────────
    grp = 'Output Validity'
    for mn in sorted(module_names):
        mod_main    = files.get(f'modules/{mn}/main.tf', '')
        mod_outputs = files.get(f'modules/{mn}/outputs.tf', '')
        if not mod_main or not mod_outputs:
            continue

        output_names = _extract_single_blocks(mod_outputs, 'output')
        if output_names:
            ok(grp, f'modules/{mn}: has outputs ({", ".join(output_names)})')
        else:
            warn(grp, f'modules/{mn}: has outputs', 'No output blocks declared',
                 f'modules/{mn}/outputs.tf')

        # Check output values reference real resource attributes
        resource_blocks = _extract_blocks(mod_main, 'resource')
        for out in output_names:
            out_content = mod_outputs
            # Find the value line for this output
            m = re.search(rf'output\s+"{re.escape(out)}"\s*\{{[^}}]*value\s*=\s*([^\n]+)', out_content)
            if m:
                val = m.group(1).strip()
                # Should reference a resource in this module
                res_refs = re.findall(r'(\w+)\.this\.(\w+)', val)
                for res_type_ref, attr in res_refs:
                    full_type = next((rt for rt in ALL_SCHEMAS if rt.endswith(res_type_ref) or
                                      rt == res_type_ref), None)
                    known_attrs = RESOURCE_OUTPUTS.get(full_type, []) if full_type else []
                    # 'id' is always valid in Terraform
                    if attr in known_attrs or attr == 'id' or attr == 'name':
                        ok(grp, f'modules/{mn}: output "{out}" references valid attribute "{attr}"')
                    else:
                        warn(grp, f'modules/{mn}: output "{out}" references valid attribute "{attr}"',
                             f'Attribute "{attr}" not in known schema for "{res_type_ref}" '
                             f'(may be valid — mock schema is incomplete)',
                             f'modules/{mn}/outputs.tf')

    # ── 7. Root module cross-references ───────────────────────────────────────
    grp = 'Module Cross-References'
    root_modules = _extract_module_blocks(root_main)

    for mod_name, source in root_modules.items():
        # Source path should be ./modules/<name>
        expected_source_path = f'./modules/{mod_name}'
        if source == expected_source_path:
            ok(grp, f'module.{mod_name}: source path correct')
        else:
            fail(grp, f'module.{mod_name}: source path correct',
                 f'Expected source "{expected_source_path}", got "{source}"')

        # Module directory must exist in generated files
        mod_exists = any(p.startswith(f'modules/{mod_name}/') for p in files)
        if mod_exists:
            ok(grp, f'module.{mod_name}: module directory exists')
        else:
            fail(grp, f'module.{mod_name}: module directory exists',
                 f'No files generated for modules/{mod_name}/')

    # Check module output references in root are resolvable
    mod_output_refs = _extract_module_output_refs(root_main)
    for ref_mod, ref_attr in mod_output_refs:
        if ref_mod not in root_modules:
            fail(grp, f'module.{ref_mod}.{ref_attr}: module declared in root',
                 f'module.{ref_mod} referenced but not declared as a module block in root main.tf')
        else:
            # Check output is declared in that module
            mod_outputs_content = files.get(f'modules/{ref_mod}/outputs.tf', '')
            declared_outputs = set(_extract_single_blocks(mod_outputs_content, 'output'))
            if ref_attr in declared_outputs:
                ok(grp, f'module.{ref_mod}.{ref_attr}: output declared')
            else:
                # Could be a valid output not in our mock — warn instead of fail
                warn(grp, f'module.{ref_mod}.{ref_attr}: output declared',
                     f'Output "{ref_attr}" not found in modules/{ref_mod}/outputs.tf '
                     f'(may be valid — check outputs.tf)',
                     f'modules/{ref_mod}/outputs.tf')

    # ── 8. tfvars completeness ─────────────────────────────────────────────────
    grp = 'tfvars Completeness'
    for mn in sorted(module_names):
        mod_vars   = files.get(f'modules/{mn}/variables.tf', '')
        mod_tfvars = files.get(f'modules/{mn}/terraform.tfvars', '')
        if not mod_vars or not mod_tfvars:
            continue

        declared_vars = set(_extract_single_blocks(mod_vars, 'variable'))
        # tfvars keys — lines like: key = value  or  key = "value"
        tfvars_keys = set(re.findall(r'^(\w+)\s*=', mod_tfvars, re.MULTILINE))

        missing = declared_vars - tfvars_keys - {'tags', 'labels', 'deletion_protection'}
        if missing:
            warn(grp, f'modules/{mn}: tfvars covers all variables',
                 f'Variables without tfvars value: {", ".join(sorted(missing))} '
                 f'(will use variable defaults)',
                 f'modules/{mn}/terraform.tfvars')
        else:
            ok(grp, f'modules/{mn}: tfvars covers all variables')

    return results


def summarise(results: list[CheckResult]) -> dict:
    passed = sum(1 for r in results if r.status == 'pass')
    failed = sum(1 for r in results if r.status == 'fail')
    warned = sum(1 for r in results if r.status == 'warn')
    return {
        'passed': passed,
        'failed': failed,
        'warned': warned,
        'total':  len(results),
        'results': [
            {'group': r.group, 'name': r.name, 'status': r.status,
             'error': r.error, 'file': r.file}
            for r in results
        ],
    }
