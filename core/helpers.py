"""Shared helpers used by all generator modules."""
import os
import re
from jinja2 import Environment, FileSystemLoader, StrictUndefined

_tf_env = Environment(
    loader=FileSystemLoader(
        os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates', 'tf')
    ),
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=True,
)


def render_tf(template_path: str, **ctx) -> str:
    return _tf_env.get_template(template_path).render(**ctx).rstrip('\n')


def is_ref(s: str) -> bool:
    if not s:
        return False
    return bool(re.match(r'^[a-z_][a-z0-9_.]*(\.[a-z_][a-z0-9_.\[\]*]*)+$', s))


def parse_list(s: str) -> list:
    if not s:
        return []
    return [x.strip() for x in s.split(',') if x.strip()]


def tf_bool(v) -> str:
    return 'true' if v else 'false'


def tf_num(v):
    """Coerce a form value to a number for HCL, or None when it should be omitted.

    Number inputs arrive from the browser as strings ('', '120', '8.5'), so blank
    and unparseable values become None and the caller leaves the attribute out.
    Integral floats render as ints so '8.0' does not become 8.0 in the output."""
    if v is None or v == '':
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return int(f) if f.is_integer() else f
