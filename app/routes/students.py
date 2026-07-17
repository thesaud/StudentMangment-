# -*- coding: utf-8 -*-
"""شاشة عرض/إدارة الطلاب الموحّدة (فصيل/سرية/كتيبة) + دورة حياة الطالب."""

from datetime import datetime

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

from .. import config, db

bp = Blueprint("students", __name__)


def violation_remaining_label(expires_at):
    """نص حالة المخالفة: للأمر الأخير / متبقي N يوم / منتهية."""
    if not expires_at:
        return "للأمر الأخير"
    try:
        exp = datetime.strptime(expires_at, "%Y-%m-%d").date()
    except Exception:
        return ""
    remaining = (exp - datetime.now().date()).days
    if remaining > 1:
        return f"متبقي {remaining} يوم"
    if remaining == 1:
        return "متبقي يوم واحد"
    if remaining == 0:
        return "ينتهي اليوم"
    return "منتهية"


def _render_students_scope(scope_type, scope_id):
    """شاشة طلاب موحّدة لأي من المستويات الثلاثة بقالب واحد."""
    tree = db.get_full_hierarchy()

    if scope_type == "platoon":
        ctx = db.get_platoon_context(scope_id)
        if not ctx:
            flash("الفصيل غير موجود", "error")
            return redirect(url_for("battalions.battalions"))
        scope = {
            "type": "platoon", "id": scope_id,
            "label": f'طلاب فصيل: {ctx["pname"]} | سرية: {ctx["cname"]} | كتيبة: {ctx["bname"]}',
        }
        platoon_ids = [scope_id]
        export_url = url_for("exports.export_platoon", platoon_id=scope_id)
        print_url = url_for("exports.print_platoon", platoon_id=scope_id)

    elif scope_type == "company":
        company = db.get_company(scope_id)
        if not company:
            flash("السرية غير موجودة", "error")
            return redirect(url_for("battalions.battalions"))
        battalion = db.get_battalion(company["battalion_id"])
        scope = {
            "type": "company", "id": scope_id,
            "label": f'طلاب سرية: {company["name"]} | كتيبة: {battalion["name"] if battalion else "—"}',
        }
        platoon_ids = [p["id"] for p in db.get_platoons(scope_id)]
        export_url = url_for("exports.export_company", company_id=scope_id)
        print_url = url_for("exports.print_company", company_id=scope_id)

    elif scope_type == "battalion":
        battalion = db.get_battalion(scope_id)
        if not battalion:
            flash("الكتيبة غير موجودة", "error")
            return redirect(url_for("battalions.battalions"))
        platoon_ids = []
        for c in db.get_companies(scope_id):
            platoon_ids.extend(p["id"] for p in db.get_platoons(c["id"]))
        scope = {"type": "battalion", "id": scope_id, "label": f'طلاب كتيبة: {battalion["name"]}'}
        export_url = url_for("exports.export_battalion", battalion_id=scope_id)
        print_url = url_for("exports.print_battalion", battalion_id=scope_id)

    else:
        flash("نطاق غير معروف", "error")
        return redirect(url_for("battalions.battalions"))

    students = db.get_students_multi(platoon_ids)

    # قيم افتراضية لقوائم "إضافة طالب" المتتالية بحسب النطاق الحالي
    default_battalion_id = default_company_id = None
    default_platoon_id = platoon_ids[0] if platoon_ids else None
    for b in tree:
        if scope_type == "battalion" and b["row"]["id"] == scope_id:
            default_battalion_id = b["row"]["id"]
        for c in b["companies"]:
            if scope_type == "company" and c["row"]["id"] == scope_id:
                default_battalion_id, default_company_id = b["row"]["id"], c["row"]["id"]
            for p in c["platoons"]:
                if scope_type == "platoon" and p["row"]["id"] == scope_id:
                    default_battalion_id, default_company_id = b["row"]["id"], c["row"]["id"]

    in_range = config.STUDENT_COUNT_MIN <= len(students) <= config.STUDENT_COUNT_MAX

    return render_template(
        "students_view.html",
        scope=scope, students=students, in_range=in_range, tree=tree,
        export_url=export_url, print_url=print_url,
        default_battalion_id=default_battalion_id,
        default_company_id=default_company_id,
        default_platoon_id=default_platoon_id,
    )


@bp.route("/platoons/<int:platoon_id>")
def platoon_detail(platoon_id):
    return _render_students_scope("platoon", platoon_id)


@bp.route("/companies/<int:company_id>/students")
def company_students(company_id):
    return _render_students_scope("company", company_id)


@bp.route("/battalions/<int:battalion_id>/students")
def battalion_students(battalion_id):
    return _render_students_scope("battalion", battalion_id)


@bp.route("/students/add", methods=["POST"])
def add_student():
    platoon_id = int(request.form.get("platoon_id"))
    name = request.form.get("name", "").strip()
    if name:
        db.add_student(
            platoon_id, name,
            request.form.get("national_id", "").strip(),
            request.form.get("phone", "").strip(),
            request.form.get("notes", "").strip(),
        )
        flash(f"تمت إضافة الطالب «{name}»", "ok")
    return redirect(request.referrer or url_for("battalions.battalions"))


@bp.route("/students/<int:student_id>/update", methods=["POST"])
def update_student(student_id):
    db.update_student(
        student_id,
        request.form.get("name", "").strip(),
        request.form.get("national_id", "").strip(),
        request.form.get("phone", "").strip(),
        request.form.get("notes", "").strip(),
    )
    flash("تم تحديث بيانات الطالب", "ok")
    return redirect(request.referrer or url_for("battalions.battalions"))


@bp.route("/students/<int:student_id>/notes", methods=["POST"])
def update_student_notes(student_id):
    db.update_student_notes(student_id, request.form.get("notes", "").strip())
    return jsonify({"ok": True})


@bp.route("/students/<int:student_id>/delete", methods=["POST"])
def delete_student(student_id):
    db.delete_student(student_id)
    flash("تم حذف الطالب", "ok")
    return redirect(request.referrer or url_for("battalions.battalions"))


@bp.route("/students/<int:student_id>/transfer", methods=["POST"])
def transfer_student(student_id):
    new_platoon_id = request.form.get("new_platoon_id")
    if new_platoon_id:
        db.transfer_student(student_id, int(new_platoon_id))
        flash("تم نقل الطالب بنجاح", "ok")
    return redirect(request.referrer or url_for("battalions.battalions"))


@bp.route("/students/<int:student_id>/resign", methods=["POST"])
def resign_student(student_id):
    db.resign_student(student_id, request.form.get("reason", "").strip())
    flash("تم تسجيل استقالة الطالب", "ok")
    return redirect(request.referrer or url_for("battalions.battalions"))


@bp.route("/students/<int:student_id>/reinstate", methods=["POST"])
def reinstate_student(student_id):
    db.reinstate_student(student_id)
    flash("تم التراجع عن الاستقالة", "ok")
    return redirect(request.referrer or url_for("reports.reports"))
