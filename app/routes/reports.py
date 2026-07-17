# -*- coding: utf-8 -*-
"""التقارير والإحصائيات + قائمة المستقيلين."""

from flask import Blueprint, render_template

from .. import db
from ..services.hierarchy_service import hierarchy_totals

bp = Blueprint("reports", __name__)


@bp.route("/reports")
def reports():
    totals = hierarchy_totals()
    totals["total_queues"] = len(db.get_queues())
    totals["total_violations"] = len(db.get_all_violations())
    return render_template("reports.html",
                            resigned=db.get_resigned_students(),
                            battalions=db.get_battalions(),
                            **totals)
