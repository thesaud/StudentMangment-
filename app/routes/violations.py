# -*- coding: utf-8 -*-
"""سجل المخالفات (تسجيل/حذف + كتالوج الأنواع)."""

from flask import Blueprint, flash, redirect, render_template, request, url_for

from .. import db, students_to_json

bp = Blueprint("violations", __name__)


@bp.route("/violations")
def violations_page():
    all_students = db.get_all_students_flat()
    return render_template("violations.html",
                            violations=db.get_all_violations(),
                            all_students=all_students,
                            all_students_json=students_to_json(all_students),
                            catalog=db.get_violation_catalog(),
                            duration_categories=db.DURATION_CATEGORIES)


@bp.route("/violations/add", methods=["POST"])
def add_violation():
    student_id = int(request.form.get("student_id"))
    violation_type = request.form.get("violation_type", "").strip()
    duration_days = request.form.get("duration_days")
    duration_days = int(duration_days) if duration_days else None
    duration_label = db.format_duration_label(request.form.get("duration_category"), duration_days)
    notes = request.form.get("notes", "").strip()
    if student_id and violation_type:
        db.add_violation(student_id, violation_type, duration_label, notes)
        db.add_violation_catalog(violation_type, duration_label, notes)
        flash("تم تسجيل المخالفة", "ok")
    return redirect(url_for("violations.violations_page"))


@bp.route("/violations/<int:violation_id>/delete", methods=["POST"])
def delete_violation(violation_id):
    db.delete_violation(violation_id)
    flash("تم حذف المخالفة", "ok")
    return redirect(url_for("violations.violations_page"))
