# -*- coding: utf-8 -*-
"""API صغيرة للقوائم المتتالية (كتيبة -> سرية -> فصيل) والبحث اللحظي."""

from flask import Blueprint, jsonify

from .. import db

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.route("/battalions")
def api_battalions():
    return jsonify([{"id": b["id"], "name": b["name"]} for b in db.get_battalions()])


@bp.route("/companies/<int:battalion_id>")
def api_companies(battalion_id):
    return jsonify([{"id": c["id"], "name": c["name"]} for c in db.get_companies(battalion_id)])


@bp.route("/platoons/<int:company_id>")
def api_platoons(company_id):
    return jsonify([{"id": p["id"], "name": p["name"]} for p in db.get_platoons(company_id)])


@bp.route("/students")
def api_students():
    rows = db.get_all_students_flat()
    return jsonify([{
        "sid": r["sid"], "sname": r["sname"], "national_id": r["national_id"] or "",
        "phone": r["phone"] or "", "pname": r["pname"], "cname": r["cname"], "bname": r["bname"],
    } for r in rows])
