# -*- coding: utf-8 -*-
"""اللوحة الرئيسية (Dashboard)."""

from flask import Blueprint, render_template

from .. import db
from ..services.hierarchy_service import hierarchy_totals

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    totals = hierarchy_totals()
    totals["total_queues"] = len(db.get_queues())
    totals["total_violations"] = len(db.get_all_violations())
    return render_template("index.html", **totals)
