"""Oracle Database@GCP page route."""
from flask import Blueprint

import regions
from core.pages import render_page

# template_folder puts this cloud's page next to the route that serves
# it, rather than in a shared templates/ directory.
bp = Blueprint('gcp', __name__, template_folder='pages')


@bp.route('/gcp')
def page():
    # The region/AZ catalogue is injected rather than fetched, so the dropdowns
    # are populated on first paint. Edit config/gcp_regions.json to change it.
    return render_page('gcp.html',
                       gcp_regions_json=regions.regions_json('gcp'))
