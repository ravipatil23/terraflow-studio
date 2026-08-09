"""Oracle Database@AWS page route."""
from flask import Blueprint

import regions
from core.pages import render_page

bp = Blueprint('aws', __name__)


@bp.route('/aws')
def page():
    # The region/AZ catalogue is injected rather than fetched, so the dropdowns
    # are populated on first paint. Edit config/aws_regions.json to change it.
    return render_page('aws.html',
                       aws_regions_json=regions.regions_json('aws'))
