# -*- coding: utf-8 -*-
"""إدارة الكتائب/السرايا/الفصائل (شجرة الهيكل + إضافتها وحذفها)."""

from flask import Blueprint, flash, redirect, render_template, request, url_for

from .. import db

bp = Blueprint("battalions", __name__)


@bp.route("/battalions")
def battalions():
    return render_template("battalions.html", tree=db.get_full_hierarchy())


@bp.route("/battalions/add", methods=["POST"])
def add_battalion():
    name = request.form.get("name", "").strip()
    if name:
        try:
            db.add_battalion(name)
            flash(f"تمت إضافة كتيبة «{name}»", "ok")
        except Exception:
            flash("تعذّرت إضافة الكتيبة (قد يكون الاسم مكرراً)", "error")
    return redirect(url_for("battalions.battalions"))


@bp.route("/companies/add", methods=["POST"])
def add_company():
    battalion_id = request.form.get("battalion_id")
    name = request.form.get("name", "").strip()
    if battalion_id and name:
        db.add_company(int(battalion_id), name)
        flash(f"تمت إضافة سرية «{name}»", "ok")
    return redirect(url_for("battalions.battalions"))


@bp.route("/platoons/add", methods=["POST"])
def add_platoon():
    company_id = request.form.get("company_id")
    name = request.form.get("name", "").strip()
    if company_id and name:
        db.add_platoon(int(company_id), name)
        flash(f"تمت إضافة فصيل «{name}»", "ok")
    return redirect(url_for("battalions.battalions"))


@bp.route("/battalions/<int:battalion_id>/delete", methods=["POST"])
def delete_battalion(battalion_id):
    db.delete_battalion(battalion_id)
    flash("تم حذف الكتيبة وكل ما بداخلها", "ok")
    return redirect(url_for("battalions.battalions"))


@bp.route("/companies/<int:company_id>/delete", methods=["POST"])
def delete_company(company_id):
    db.delete_company(company_id)
    flash("تم حذف السرية وكل ما بداخلها", "ok")
    return redirect(url_for("battalions.battalions"))


@bp.route("/platoons/<int:platoon_id>/delete", methods=["POST"])
def delete_platoon(platoon_id):
    db.delete_platoon(platoon_id)
    flash("تم حذف الفصيل وكل ما بداخله", "ok")
    return redirect(url_for("battalions.battalions"))
