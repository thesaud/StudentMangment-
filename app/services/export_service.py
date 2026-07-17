# -*- coding: utf-8 -*-
"""
app/services/export_service.py — طبقة التصدير الموحّدة.

يدعم تصديرين:
  - Excel (.xlsx): يُبنى في الذاكرة ويُحفظ نسخة دائمة في مجلد exports
  - PDF (طباعة HTML): يُعرض كصفحة قابلة للطباعة مباشرة من المتصفح
"""

import io
import logging
import os
from datetime import datetime

from flask import render_template, send_file

from .. import db, excel_utils
from ..config import EXPORTS_DIR, XLSX_MIME
from .hierarchy_service import student_export_dict, tree_with_students

logger = logging.getLogger(__name__)


def safe_filename_part(text):
    """يزيل رموزاً غير صالحة في أسماء ملفات ويندوز/لينكس من نص عربي حر."""
    cleaned = "".join(ch for ch in (text or "") if ch not in '\\/:*?"<>|').strip()
    return cleaned or "بدون_اسم"


def _student_number(s):
    """قراءة رقم الطالب التسلسلي (مشترك بين Excel و PDF)."""
    try:
        keys = s.keys()
        sn = s["student_number"] if "student_number" in keys else None
    except (AttributeError, TypeError):
        sn = s.get("student_number") if s else None
    if sn:
        return str(sn)
    try:
        return s.get("phone") or ""
    except (AttributeError, TypeError):
        return ""


def _safe(val):
    return "" if val is None else val


def _get(obj, key, default=""):
    try:
        keys = obj.keys()
        return obj[key] if key in keys else default
    except (AttributeError, TypeError):
        return obj.get(key, default) if obj else default


# ---------------------------------------------------------------------------
# Excel
# ---------------------------------------------------------------------------

def send_xlsx(export_fn, *args, download_name):
    """يبني المصنّف في الذاكرة، يحفظ نسخة في مجلد exports، ثم يرسله."""
    bio = io.BytesIO()
    export_fn(bio, *args)
    data = bio.getvalue()

    try:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base = safe_filename_part(os.path.splitext(download_name)[0])
        archive_path = os.path.join(EXPORTS_DIR, f"{stamp}_{base}.xlsx")
        with open(archive_path, "wb") as f:
            f.write(data)
    except OSError as exc:
        logger.warning("تعذّر حفظ نسخة التصدير: %s", exc)

    return send_file(
        io.BytesIO(data),
        as_attachment=True,
        download_name=download_name,
        mimetype=XLSX_MIME,
    )


# ---------------------------------------------------------------------------
# PDF (طباعة HTML)
# ---------------------------------------------------------------------------

_STUDENT_HEADERS = ["#", "اسم الطالب", "رقم الهوية", "رقم الطالب",
                    "الكتيبة", "السرية", "الفصيل", "ملاحظات"]


def _student_print_row(s, idx, bat="", co="", pl=""):
    return [
        idx,
        _safe(_get(s, "name") or _get(s, "sname")),
        _safe(_get(s, "national_id")),
        _student_number(s),
        _safe(bat or _get(s, "bname")),
        _safe(co or _get(s, "cname")),
        _safe(pl or _get(s, "pname")),
        _safe(_get(s, "notes")),
    ]


def render_print_page(title, sections, info_fields=None):
    """يُرجع HTML قابل للطباعة (Ctrl+P → حفظ كـ PDF) للتقارير."""
    return render_template("print_report.html",
        title=title,
        sections=sections,
        info_fields=info_fields or [],
        now=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )


def print_students(title, students_data):
    """قسم طلاب واحد للطباعة (فصيل/سرية/كتيبة/كامل)."""
    rows = []
    idx = 0
    for item in students_data:
        if isinstance(item, dict) and "companies" in item:
            # هيكل كامل: battalion → companies → platoons → students
            for c in item["companies"]:
                for p in c["platoons"]:
                    for s in p.get("students", []):
                        idx += 1
                        rows.append(_student_print_row(s, idx, item["row"]["name"], c["row"]["name"], p["row"]["name"]))
        elif isinstance(item, dict) and "platoons" in item:
            # سرية: platoons → students
            for p in item["platoons"]:
                for s in p.get("students", []):
                    idx += 1
                    rows.append(_student_print_row(s, idx, "", item.get("name", ""), p["name"]))
        elif isinstance(item, dict) and "students" in item:
            # فصيل: students
            for s in item["students"]:
                idx += 1
                rows.append(_student_print_row(s, idx))
        else:
            # قائمة طلاب مسطّحة
            idx += 1
            rows.append(_student_print_row(item, idx))

    return render_print_page(title, [{
        "title": "كشف الطلاب",
        "headers": _STUDENT_HEADERS,
        "rows": rows,
        "empty_msg": "لا يوجد طلاب",
    }])


# ---------------------------------------------------------------------------
# بناة الحمولات (payloads)
# ---------------------------------------------------------------------------

def battalion_payload(battalion_id):
    companies_payload = []
    for c in db.get_companies(battalion_id):
        platoons_payload = []
        for p in db.get_platoons(c["id"]):
            students = [student_export_dict(s) for s in db.get_students_by_platoon(p["id"])]
            platoons_payload.append({"name": p["name"], "students": students})
        companies_payload.append({"name": c["name"], "platoons": platoons_payload})
    return companies_payload


def company_payload(company_id):
    platoons_payload = []
    for p in db.get_platoons(company_id):
        students = [student_export_dict(s) for s in db.get_students_by_platoon(p["id"])]
        platoons_payload.append({"name": p["name"], "students": students})
    return platoons_payload


def platoon_students(platoon_id):
    return [student_export_dict(s) for s in db.get_students_by_platoon(platoon_id)]


def full_hierarchy_payload():
    return tree_with_students()
