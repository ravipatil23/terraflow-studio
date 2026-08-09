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

from clouds.aws.schema import AWS_SCHEMAS, AWS_RESOURCE_OUTPUTS
from clouds.gcp.schema import GCP_SCHEMAS, GCP_RESOURCE_OUTPUTS
from clouds.azure.schema import AZURE_SCHEMAS, AZURE_RESOURCE_OUTPUTS

# Resource types are globally unique across providers (aws_odb_*, google_*,
# azurerm_*), so a flat merge is unambiguous. Built here rather than in a shared
# package so adding a cloud means adding one line in one place, and no cloud
# package has to know the others exist.
ALL_SCHEMAS = {**AWS_SCHEMAS, **GCP_SCHEMAS, **AZURE_SCHEMAS}
RESOURCE_OUTPUTS = {
    **AWS_RESOURCE_OUTPUTS, **GCP_RESOURCE_OUTPUTS, **AZURE_RESOURCE_OUTPUTS,
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

    if cloud == 'azure':
        schemas = AZURE_SCHEMAS
        provider_name = 'azurerm'
        expected_source = 'hashicorp/azurerm'
    elif cloud == 'aws':
        schemas = AWS_SCHEMAS
        provider_name = 'aws'
        expected_source = 'hashicorp/aws'
    else:
        schemas = GCP_SCHEMAS
        provider_name = 'google'
        expected_source = 'hashicorp/google'

    # ── 1. File presence ──────────────────────────────────────────────────────
    grp = 'File Structure'
    for required in ['main.tf', 'terraform.auto.tfvars']:
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
        for ftype in ['main.tf', 'variables.tf', 'outputs.tf']:
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
        # Source path should be under ./modules/ (name may differ from module label, e.g. hyphens)
        if source.startswith('./modules/'):
            ok(grp, f'module.{mod_name}: source path correct')
            source_dir = source[len('./'):]  # strip './' → 'modules/gcp-odb-network'
        else:
            fail(grp, f'module.{mod_name}: source path correct',
                 f'Source must be under "./modules/", got "{source}"')
            source_dir = f'modules/{mod_name}'  # fallback for directory existence check

        # Module directory must exist in generated files
        mod_exists = any(p.startswith(f'{source_dir}/') for p in files)
        if mod_exists:
            ok(grp, f'module.{mod_name}: module directory exists')
        else:
            fail(grp, f'module.{mod_name}: module directory exists',
                 f'No files generated for {source_dir}/')

    # Check module output references in root are resolvable.
    # Note: for_each modules use module.name[key].attr syntax — _extract_module_output_refs
    # only finds direct module.name.attr references (no indexing), so for_each modules
    # produce no refs here — that is expected and correct.
    mod_output_refs = _extract_module_output_refs(root_main)
    for ref_mod, ref_attr in mod_output_refs:
        if ref_mod not in root_modules:
            fail(grp, f'module.{ref_mod}.{ref_attr}: module declared in root',
                 f'module.{ref_mod} referenced but not declared as a module block in root main.tf')
        else:
            # Resolve actual source directory for this module
            src = root_modules[ref_mod]
            source_dir = src[len('./'):] if src.startswith('./') else f'modules/{ref_mod}'
            mod_outputs_content = files.get(f'{source_dir}/outputs.tf', '')
            declared_outputs = set(_extract_single_blocks(mod_outputs_content, 'output'))
            if ref_attr in declared_outputs:
                ok(grp, f'module.{ref_mod}.{ref_attr}: output declared')
            else:
                # Could be a valid output not in our mock — warn instead of fail
                warn(grp, f'module.{ref_mod}.{ref_attr}: output declared',
                     f'Output "{ref_attr}" not found in {source_dir}/outputs.tf '
                     f'(may be valid — check outputs.tf)',
                     f'{source_dir}/outputs.tf')

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
