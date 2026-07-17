# -*- coding: utf-8 -*-
"""الطوابير الإضافية (قائمة + تفاصيل في تخطيط رئيسي/تفصيلي واحد)."""

from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for

from .. import db, students_to_json

bp = Blueprint("queues", __name__)


def _queues_context(selected_id=None):
    db.expire_overdue_queue_entries()
    qs = db.get_queues()
    queue_counts = {row["id"]: len(db.get_queue_students(row["id"])) for row in qs}
    ctx = dict(queues=qs, queue_counts=queue_counts, q=None, members=[],
               all_students=[], all_students_json="[]", catalog=[],
               duration_categories=db.DURATION_CATEGORIES)
    if selected_id is not None:
        q = next((row for row in qs if row["id"] == selected_id), None)
        if q is None:
            return None
        all_students = db.get_all_students_flat()
        ctx.update(q=q, members=db.get_queue_students(selected_id),
                   all_students=all_students,
                   all_students_json=students_to_json(all_students),
                   catalog=db.get_violation_catalog())
    return ctx


@bp.route("/queues")
def queues():
    return render_template("queues.html", **_queues_context())


@bp.route("/queues/<int:queue_id>")
def queue_detail(queue_id):
    ctx = _queues_context(queue_id)
    if ctx is None:
        flash("الطابور غير موجود", "error")
        return redirect(url_for("queues.queues"))
    return render_template("queues.html", **ctx)


@bp.route("/queues/add", methods=["POST"])
def add_queue():
    name = request.form.get("name", "").strip()
    queue_date = request.form.get("queue_date") or datetime.now().strftime("%Y-%m-%d")
    if name:
        db.add_queue(name, queue_date, request.form.get("notes", "").strip())
        flash(f"تم إنشاء طابور «{name}»", "ok")
    return redirect(url_for("queues.queues"))


@bp.route("/queues/<int:queue_id>/delete", methods=["POST"])
def delete_queue(queue_id):
    db.delete_queue(queue_id)
    flash("تم حذف الطابور", "ok")
    return redirect(url_for("queues.queues"))


@bp.route("/queues/<int:queue_id>/add_student", methods=["POST"])
def queue_add_student(queue_id):
    duration_days = request.form.get("duration_days")
    db.add_student_to_queue(
        queue_id,
        int(request.form.get("student_id")),
        request.form.get("violation_type", "").strip(),
        request.form.get("duration_category"),
        int(duration_days) if duration_days else None,
    )
    flash("تمت إضافة الطالب للطابور", "ok")
    return redirect(url_for("queues.queue_detail", queue_id=queue_id))


@bp.route("/queues/<int:queue_id>/remove_student/<int:student_id>", methods=["POST"])
def queue_remove_student(queue_id, student_id):
    db.remove_student_from_queue(queue_id, student_id)
    flash("تمت إزالة الطالب من الطابور", "ok")
    return redirect(url_for("queues.queue_detail", queue_id=queue_id))
