"""Oracle Database@GCP page route."""
from flask import Blueprint

import regions
from core.pages import render_page

bp = Blueprint('gcp', __name__)


@bp.route('/gcp')
def page():
    # The region/AZ catalogue is injected rather than fetched, so the dropdowns
    # are populated on first paint. Edit config/gcp_regions.json to change it.
    return render_page('gcp.html',
                       gcp_regions_json=regions.regions_json('gcp'))
