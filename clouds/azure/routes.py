"""Oracle Database@Azure page route."""
from flask import Blueprint

import regions
from core.pages import render_page

bp = Blueprint('azure', __name__)


@bp.route('/azure')
def page():
    # The region/AZ catalogue is injected rather than fetched, so the dropdowns
    # are populated on first paint. Edit config/azure_regions.json to change it.
    return render_page('azure.html',
                       azure_regions_json=regions.regions_json('azure'))
