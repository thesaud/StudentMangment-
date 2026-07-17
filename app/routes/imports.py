# -*- coding: utf-8 -*-
"""الاستيراد والتوزيع التلقائي.

التدفق (3 خطوات): رفع/تحليل -> مراجعة الأعمدة والبيانات -> تأكيد التنفيذ.
الجديد في هذه النسخة:
- عدد فصائل مستقل لكل سرية (platoon_counts قائمة بدل رقم واحد).
- منع تكرار الطلاب (إزالة الصفوف المكررة برقم الهوية قبل الحفظ).
- رقم طالب تسلسلي (1..N) يُعيَّن أثناء التوزيع ويُخزَّن بشكل دائم.
"""

import glob
import logging
import os
import secrets
import time

from flask import Blueprint, flash, redirect, render_template, request, url_for

from .. import db
from ..config import IMPORT_UPLOAD_MAX_AGE, UPLOADS_DIR
from ..services import import_service
from ..services.hierarchy_service import existing_national_ids, structure_snapshot

bp = Blueprint("imports", __name__)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# أدوات داخلية
# ---------------------------------------------------------------------------

def _cleanup_old_uploads():
    """يحذف ملفات الرفع المؤقتة الأقدم من ساعتين (تنظيف غير حرج)."""
    now_ts = time.time()
    for f in glob.glob(os.path.join(UPLOADS_DIR, "*.xlsx")):
        try:
            if now_ts - os.path.getmtime(f) > IMPORT_UPLOAD_MAX_AGE:
                os.remove(f)
        except OSError:
            pass


def _upload_path(token):
    return os.path.join(UPLOADS_DIR, token + ".xlsx")


def _read_structure_shape_from_form():
    """يقرأ (عدد الكتائب، قائمة فصائل كل سرية) من النموذج.
    platoon_counts تأتي كحقول متعددة بنفس الاسم — حقل لكل سرية."""
    battalion_count = request.form.get("battalion_count", "").strip()
    platoon_counts = [v.strip() for v in request.form.getlist("platoon_counts") if v.strip()]
    return battalion_count, platoon_counts


def _attach_validation(result):
    rows_with_warnings, validation_stats = import_service.validate_rows(
        result["rows"], existing_national_ids=existing_national_ids()
    )
    result["rows"] = rows_with_warnings
    result["stats"].update(validation_stats)
    return result


def _build_warnings(result):
    stats = result["stats"]
    warnings = []
    if result["detection_mode"] == "fallback_fixed_positions":
        warnings.append(
            "تعذّر التعرّف التلقائي على عناوين الأعمدة في هذا الملف، فتم استخدام ترتيب "
            "افتراضي (العمود الأول للاسم، والثاني لرقم الهوية). تحقّق من صحة المعاينة "
            "أدناه، أو عدّل الأعمدة يدوياً إن لزم."
        )
    if stats["skipped_missing_name"]:
        warnings.append(f"تم تجاهل {stats['skipped_missing_name']} صفاً لعدم وجود اسم طالب فيه.")
    if stats["duplicate_national_ids"]:
        warnings.append(
            "بعض أرقام الهوية مكررة داخل الملف نفسه: "
            + "، ".join(stats["duplicate_national_ids"])
            + (" ..." if len(stats["duplicate_national_ids"]) >= 8 else "")
            + " — سيُحفظ أول ظهور فقط لكل رقم هوية وتُستبعد التكرارات تلقائياً عند التنفيذ."
        )
    if stats.get("invalid_national_id_count"):
        warnings.append(
            f"يوجد {stats['invalid_national_id_count']} رقم هوية غير رقمي بالكامل "
            "(يحتوي حروفاً أو رموزاً) — تحقّق من العمود المختار لرقم الهوية."
        )
    if stats.get("short_name_count"):
        warnings.append(
            f"يوجد {stats['short_name_count']} اسم قصير جداً (أقل من حرفين) — قد يدل "
            "على اختيار عمود خاطئ لاسم الطالب."
        )
    if stats.get("existing_in_db_count"):
        warnings.append(
            f"يوجد {stats['existing_in_db_count']} رقم هوية يطابق طلاباً موجودين حالياً "
            "في النظام: " + "، ".join(stats["existing_in_db_samples"])
            + (" ..." if len(stats["existing_in_db_samples"]) >= 8 else "")
            + " — لا يشكّل ذلك تكراراً بعد التنفيذ لأن الهيكل الحالي يُستبدل بالكامل."
        )
    return warnings


def _build_preview(result, token, battalion_count, platoon_counts):
    return {
        "token": token,
        "sheet_name": result["sheet_name"],
        "header_row": result["header_row"],
        "detection_mode": result["detection_mode"],
        "mapping": result["mapping"],
        "column_options": result["column_options"],
        "sample_rows": result["rows"][:10],
        "stats": result["stats"],
        "warnings": _build_warnings(result),
        "battalion_count": battalion_count or "",
        "platoon_counts": platoon_counts or [],
    }


def _mapping_from_form():
    header_row = request.form.get("header_row") or None
    return (
        int(header_row) if header_row else None,
        request.form.get("name_col") or None,
        request.form.get("national_id_col") or None,
        request.form.get("phone_col") or None,
        request.form.get("notes_col") or None,
    )


# ---------------------------------------------------------------------------
# المسارات
# ---------------------------------------------------------------------------

@bp.route("/import")
def import_page():
    _cleanup_old_uploads()
    return render_template("import.html", snapshot=structure_snapshot(), preview=None)


@bp.route("/import/analyze", methods=["POST"])
def import_analyze():
    _cleanup_old_uploads()
    snapshot = structure_snapshot()
    battalion_count, platoon_counts = _read_structure_shape_from_form()

    upload = request.files.get("excel_file")
    if not upload or not upload.filename:
        flash("الرجاء اختيار ملف Excel أولاً", "error")
        return redirect(url_for("imports.import_page"))

    ext = os.path.splitext(upload.filename)[1].lower()
    if ext not in (".xlsx", ".xlsm", ".xls"):
        flash("صيغة الملف غير مدعومة. الرجاء رفع ملف Excel بصيغة xlsx أو xls", "error")
        return redirect(url_for("imports.import_page"))

    token = secrets.token_hex(8)
    saved_path = _upload_path(token)
    upload.save(saved_path)

    try:
        result = _attach_validation(import_service.analyze_excel(saved_path))
    except Exception as exc:
        logger.exception("فشل تحليل ملف الاستيراد")
        try:
            os.remove(saved_path)
        except OSError:
            pass
        flash(f"تعذّرت قراءة الملف المرفوع: {exc}", "error")
        return redirect(url_for("imports.import_page"))

    preview = _build_preview(result, token, battalion_count, platoon_counts)
    return render_template("import.html", snapshot=snapshot, preview=preview)


@bp.route("/import/remap", methods=["POST"])
def import_remap():
    snapshot = structure_snapshot()
    token = request.form.get("token", "")
    battalion_count, platoon_counts = _read_structure_shape_from_form()

    if not token or not os.path.exists(_upload_path(token)):
        flash("انتهت صلاحية الملف المرفوع (تم تنظيفه تلقائياً)، الرجاء رفعه مرة أخرى", "error")
        return redirect(url_for("imports.import_page"))

    header_row, name_col, national_id_col, phone_col, notes_col = _mapping_from_form()
    try:
        result = _attach_validation(import_service.parse_with_manual_mapping(
            _upload_path(token), header_row, name_col, national_id_col, phone_col, notes_col
        ))
    except Exception as exc:
        logger.exception("فشل تطبيق تعيين الأعمدة")
        flash(f"تعذّر تطبيق تعيين الأعمدة المختار: {exc}", "error")
        return redirect(url_for("imports.import_page"))

    preview = _build_preview(result, token, battalion_count, platoon_counts)
    return render_template("import.html", snapshot=snapshot, preview=preview)


@bp.route("/import/confirm", methods=["POST"])
def import_confirm():
    token = request.form.get("token", "")
    saved_path = _upload_path(token)

    if not token or not os.path.exists(saved_path):
        flash("انتهت صلاحية الملف المرفوع (تم تنظيفه تلقائياً)، الرجاء رفعه مرة أخرى", "error")
        return redirect(url_for("imports.import_page"))

    if request.form.get("confirm_wipe") != "on":
        flash("الرجاء تأشير مربع تأكيد استبدال الهيكل الحالي قبل تنفيذ التوزيع", "error")
        return redirect(url_for("imports.import_page"))

    battalion_count_raw, platoon_counts_raw = _read_structure_shape_from_form()
    try:
        battalion_count = int(battalion_count_raw)
        platoon_counts = [int(p) for p in platoon_counts_raw]
        if battalion_count <= 0 or not platoon_counts or any(p <= 0 for p in platoon_counts):
            raise ValueError
    except ValueError:
        flash("الرجاء إدخال أعداد صحيحة أكبر من صفر لعدد الكتائب وفصائل كل سرية", "error")
        return redirect(url_for("imports.import_page"))

    header_row, name_col, national_id_col, phone_col, notes_col = _mapping_from_form()
    try:
        result = import_service.parse_with_manual_mapping(
            saved_path, header_row, name_col, national_id_col, phone_col, notes_col
        )
    except Exception as exc:
        logger.exception("فشل إعادة قراءة ملف الاستيراد عند التأكيد")
        flash(f"تعذّرت إعادة قراءة الملف: {exc}", "error")
        return redirect(url_for("imports.import_page"))

    rows, removed_duplicates = import_service.dedupe_rows(result["rows"])
    if not rows:
        flash("لم يتم العثور على أي طالب صالح للاستيراد في هذا الملف بهذا التعيين للأعمدة", "error")
        return redirect(url_for("imports.import_page"))

    outcome = db.create_structure_and_distribute_custom(battalion_count, platoon_counts, rows)
    logger.info("تم التوزيع التلقائي: %s طالب على %s فصيل", outcome["imported"], outcome["total_platoons"])

    try:
        os.remove(saved_path)
    except OSError:
        pass

    msg = (
        f"تم استيراد {len(rows)} طالباً بنجاح (بأرقام تسلسلية من 1 إلى {len(rows)}) "
        f"وتوزيعهم تلقائياً على {outcome['total_platoons']} فصيلاً "
        f"ضمن {len(platoon_counts)} سرية × {battalion_count} كتيبة."
    )
    if removed_duplicates:
        msg += f" (تم استبعاد {removed_duplicates} صفاً مكرراً برقم الهوية — حُفظ أول ظهور فقط)"
    flash(msg, "ok")
    return redirect(url_for("battalions.battalions"))
