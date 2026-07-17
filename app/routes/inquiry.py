# -*- coding: utf-8 -*-
"""الاستعلام عن طالب (بحث + ملف كامل)."""

from flask import Blueprint, render_template, request

from .. import db

bp = Blueprint("inquiry", __name__)


@bp.route("/inquiry")
def inquiry():
    students = db.get_all_students_flat()
    selected_id = request.args.get("sid", type=int)
    selected, violations, queues = None, [], []
    if selected_id:
        selected = db.get_student_full_path(selected_id)
        if selected:
            violations = db.get_violations_for_student(selected_id)
            queues = db.get_queues_for_student(selected_id)
    return render_template("inquiry.html", students=students, selected=selected,
                            selected_id=selected_id, violations=violations, queues=queues)
