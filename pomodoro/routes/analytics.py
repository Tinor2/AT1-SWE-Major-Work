from flask import Blueprint, render_template, request
from flask_login import login_required, current_user

from ..models.analytics import get_analytics_dashboard

bp = Blueprint("analytics", __name__, url_prefix="/analytics")


@bp.route("/")
@login_required
def index():
    days = request.args.get("days", default=30, type=int)
    if days not in (7, 30, 90):
        days = 30
    summary = get_analytics_dashboard(current_user.id, period_days=days)
    return render_template(
        "analytics/index.html",
        summary=summary,
        period_days=days,
    )
