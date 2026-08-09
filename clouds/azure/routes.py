"""Oracle Database@Azure page route."""
from flask import Blueprint

import regions
from core.pages import render_page

# template_folder puts this cloud's page next to the route that serves
# it, rather than in a shared templates/ directory.
bp = Blueprint('azure', __name__, template_folder='pages')


@bp.route('/azure')
def page():
    # The region/AZ catalogue is injected rather than fetched, so the dropdowns
    # are populated on first paint. Edit config/azure_regions.json to change it.
    return render_page('azure.html',
                       azure_regions_json=regions.regions_json('azure'))
