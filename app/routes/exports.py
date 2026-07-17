# -*- coding: utf-8 -*-
"""مسارات تصدير Excel و PDF (طباعة HTML)."""

from datetime import datetime

from flask import Blueprint, flash, redirect, url_for

from .. import db, excel_utils
from ..services import export_service as ex

bp = Blueprint("exports", __name__)


# ---------------------------------------------------------------------------
# Excel exports
# ---------------------------------------------------------------------------

@bp.route("/export/full")
def export_full():
    return ex.send_xlsx(excel_utils.export_full_hierarchy, ex.full_hierarchy_payload(),
                        download_name="الهيكل_التنظيمي.xlsx")


@bp.route("/export/battalion/<int:battalion_id>")
def export_battalion(battalion_id):
    battalion = db.get_battalion(battalion_id)
    if not battalion:
        flash("الكتيبة غير موجودة", "error")
        return redirect(url_for("reports.reports"))
    name = ex.safe_filename_part(battalion["name"])
    return ex.send_xlsx(excel_utils.export_battalion_students, battalion["name"],
                        ex.battalion_payload(battalion_id), download_name=f"كتيبة_{name}.xlsx")


@bp.route("/export/company/<int:company_id>")
def export_company(company_id):
    company = db.get_company(company_id)
    if not company:
        flash("السرية غير موجودة", "error")
        return redirect(url_for("reports.reports"))
    battalion = db.get_battalion(company["battalion_id"])
    name = ex.safe_filename_part(company["name"])
    return ex.send_xlsx(excel_utils.export_company_students, company["name"],
                        battalion["name"] if battalion else "—",
                        ex.company_payload(company_id), download_name=f"سرية_{name}.xlsx")


@bp.route("/export/platoon/<int:platoon_id>")
def export_platoon(platoon_id):
    ctx = db.get_platoon_context(platoon_id)
    if not ctx:
        flash("الفصيل غير موجود", "error")
        return redirect(url_for("reports.reports"))
    name = ex.safe_filename_part(ctx["pname"])
    return ex.send_xlsx(excel_utils.export_platoon_students, ctx["pname"], ctx["cname"],
                        ctx["bname"], ex.platoon_students(platoon_id),
                        download_name=f"فصيل_{name}.xlsx")


@bp.route("/export/inquiry/<int:student_id>")
def export_inquiry(student_id):
    student_info = db.get_student_full_path(student_id)
    if not student_info:
        flash("الطالب غير موجود", "error")
        return redirect(url_for("inquiry.inquiry"))
    violations = db.get_violations_for_student(student_id)
    queues = db.get_queues_for_student(student_id)
    name = ex.safe_filename_part(student_info["sname"])
    return ex.send_xlsx(excel_utils.export_student_inquiry, student_info, violations, queues,
                        download_name=f"استعلام_{name}.xlsx")


@bp.route("/export/resigned")
def export_resigned():
    return ex.send_xlsx(excel_utils.export_resigned_students, db.get_resigned_students(),
                        download_name="الطلاب_المستقيلون.xlsx")


@bp.route("/export/violations")
def export_violations():
    return ex.send_xlsx(excel_utils.export_violation_catalog, db.get_all_violations(),
                        download_name="سجل_المخالفات.xlsx")


@bp.route("/export/queue/<int:queue_id>")
def export_queue(queue_id):
    q = next((row for row in db.get_queues() if row["id"] == queue_id), None)
    if not q:
        flash("الطابور غير موجود", "error")
        return redirect(url_for("queues.queues"))
    name = ex.safe_filename_part(q["name"])
    return ex.send_xlsx(excel_utils.export_queue, q["name"], q["queue_date"],
                        db.get_queue_students(queue_id), download_name=f"طابور_{name}.xlsx")


# ---------------------------------------------------------------------------
# PDF (printable HTML) exports
# ---------------------------------------------------------------------------

@bp.route("/print/full")
def print_full():
    return ex.print_students("كشف جميع الطلاب", ex.full_hierarchy_payload())


@bp.route("/print/battalion/<int:battalion_id>")
def print_battalion(battalion_id):
    battalion = db.get_battalion(battalion_id)
    if not battalion:
        flash("الكتيبة غير موجودة", "error")
        return redirect(url_for("reports.reports"))
    payload = ex.battalion_payload(battalion_id)
    # Wrap for print_students: needs [{companies: [{platoons: [{students}]}]}]
    students = []
    for c in payload:
        for p in c["platoons"]:
            for s in p["students"]:
                s["bname"] = battalion["name"]
                s["cname"] = c["name"]
                s["pname"] = p["name"]
                students.append(s)
    return ex.print_students(f"كشف طلاب كتيبة: {battalion['name']}", students)


@bp.route("/print/company/<int:company_id>")
def print_company(company_id):
    company = db.get_company(company_id)
    if not company:
        flash("السرية غير موجودة", "error")
        return redirect(url_for("reports.reports"))
    battalion = db.get_battalion(company["battalion_id"])
    payload = ex.company_payload(company_id)
    students = []
    for p in payload:
        for s in p["students"]:
            s["bname"] = battalion["name"] if battalion else ""
            s["cname"] = company["name"]
            s["pname"] = p["name"]
            students.append(s)
    return ex.print_students(f"كشف طلاب سرية: {company['name']}", students)


@bp.route("/print/platoon/<int:platoon_id>")
def print_platoon(platoon_id):
    ctx = db.get_platoon_context(platoon_id)
    if not ctx:
        flash("الفصيل غير موجود", "error")
        return redirect(url_for("reports.reports"))
    students = ex.platoon_students(platoon_id)
    for s in students:
        s["bname"] = ctx["bname"]
        s["cname"] = ctx["cname"]
        s["pname"] = ctx["pname"]
    return ex.print_students(f"كشف طلاب فصيل: {ctx['pname']}", students)


@bp.route("/print/inquiry/<int:student_id>")
def print_inquiry(student_id):
    student_info = db.get_student_full_path(student_id)
    if not student_info:
        flash("الطالب غير موجود", "error")
        return redirect(url_for("inquiry.inquiry"))
    violations = db.get_violations_for_student(student_id)
    queues = db.get_queues_for_student(student_id)

    info_fields = [
        ("اسم الطالب", ex._get(student_info, "sname")),
        ("رقم الهوية", ex._get(student_info, "national_id")),
        ("رقم الطالب", ex._student_number(student_info)),
        ("الكتيبة", ex._get(student_info, "bname")),
        ("السرية", ex._get(student_info, "cname")),
        ("الفصيل", ex._get(student_info, "pname")),
        ("ملاحظات", ex._get(student_info, "notes")),
    ]

    v_headers = ["#", "نوع المخالفة", "المدة", "تاريخ التسجيل", "ملاحظات"]
    v_rows = []
    for i, v in enumerate(violations, start=1):
        v_rows.append([i, ex._get(v, "violation_type"), ex._get(v, "duration"),
                        ex._get(v, "date_added"), ex._get(v, "notes")])

    q_headers = ["#", "اسم الطابور", "التاريخ", "الحالة"]
    q_rows = []
    for i, q in enumerate(queues, start=1):
        status = "نشط" if ex._get(q, "q_is_active", 1) else "منتهٍ"
        q_rows.append([i, ex._get(q, "qname"), ex._get(q, "queue_date"), status])

    sections = [
        {"title": "المخالفات السابقة", "headers": v_headers, "rows": v_rows,
         "empty_msg": "لا توجد مخالفات مسجّلة"},
        {"title": "سجل الطوابير الإضافية", "headers": q_headers, "rows": q_rows,
         "empty_msg": "لم يُدرج في أي طابور"},
    ]

    return ex.render_print_page(
        f"تقرير استعلام: {ex._get(student_info, 'sname')}",
        sections=sections, info_fields=info_fields,
    )


@bp.route("/print/violations")
def print_violations():
    violations = db.get_all_violations()
    headers = ["#", "اسم الطالب", "رقم الهوية", "رقم الطالب",
               "الكتيبة", "السرية", "الفصيل",
               "نوع المخالفة", "المدة", "التاريخ", "ملاحظات"]
    rows = []
    for i, v in enumerate(violations, start=1):
        rows.append([
            i, ex._safe(ex._get(v, "sname")), ex._safe(ex._get(v, "national_id")),
            ex._student_number(v),
            ex._safe(ex._get(v, "bname")), ex._safe(ex._get(v, "cname")), ex._safe(ex._get(v, "pname")),
            ex._safe(ex._get(v, "violation_type")), ex._safe(ex._get(v, "duration")),
            ex._safe(ex._get(v, "date_added")), ex._safe(ex._get(v, "notes")),
        ])
    return ex.render_print_page("سجل المخالفات", [{
        "title": "سجل المخالفات",
        "headers": headers,
        "rows": rows,
        "empty_msg": "لا توجد مخالفات مسجّلة",
    }])


@bp.route("/print/queue/<int:queue_id>")
def print_queue(queue_id):
    q = next((row for row in db.get_queues() if row["id"] == queue_id), None)
    if not q:
        flash("الطابور غير موجود", "error")
        return redirect(url_for("queues.queues"))
    members = db.get_queue_students(queue_id)
    headers = ["#", "اسم الطالب", "رقم الهوية", "رقم الطالب",
               "الكتيبة", "السرية", "الفصيل",
               "نوع المخالفة", "مدة المخالفة", "الحالة"]
    rows = []
    for i, m in enumerate(members, start=1):
        duration_label = db.format_duration_label(ex._get(m, "q_duration_category"), ex._get(m, "q_duration_days"))
        remaining_label = db.compute_remaining_label(ex._get(m, "q_expires_at"), ex._get(m, "q_duration_category"))
        rows.append([
            i, ex._safe(ex._get(m, "sname")), ex._safe(ex._get(m, "national_id")),
            ex._student_number(m),
            ex._safe(ex._get(m, "bname")), ex._safe(ex._get(m, "cname")), ex._safe(ex._get(m, "pname")),
            ex._safe(ex._get(m, "q_violation_type")),
            duration_label, remaining_label,
        ])
    return ex.render_print_page(f"كشف طابور: {q['name']}", [{
        "title": f"طابور: {q['name']} — {q['queue_date']}",
        "headers": headers,
        "rows": rows,
        "empty_msg": "لا يوجد طلاب في هذا الطابور",
    }])
