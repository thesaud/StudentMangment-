# -*- coding: utf-8 -*-
"""
app/services/hierarchy_service.py — منطق قراءة/تجميع الهيكل التنظيمي المشترك
بين أكثر من مسار (اللوحة الرئيسية، التقارير، الاستيراد، التصدير) بدل تكراره.
"""

from .. import db


def hierarchy_totals(tree=None):
    """إجماليات السرايا/الفصائل/الطلاب من شجرة get_full_hierarchy()."""
    if tree is None:
        tree = db.get_full_hierarchy()
    total_companies = sum(len(b["companies"]) for b in tree)
    total_platoons = sum(len(c["platoons"]) for b in tree for c in b["companies"])
    total_students = sum(
        p["student_count"] for b in tree for c in b["companies"] for p in c["platoons"]
    )
    return {
        "total_battalions": len(tree),
        "total_companies": total_companies,
        "total_platoons": total_platoons,
        "total_students": total_students,
    }


def structure_snapshot():
    """لقطة سريعة من حجم الهيكل الحالي (تحذير ما قبل التوزيع التلقائي)."""
    return hierarchy_totals()


def tree_with_students(tree=None):
    """يثري شجرة get_full_hierarchy() بقائمة طلاب كل فصيل (مفتاح "students")
    كقواميس عادية بدل sqlite3.Row، لأن excel_utils.export_full_hierarchy
    يتوقع p.get("students", []) و s.get("phone")."""
    if tree is None:
        tree = db.get_full_hierarchy()
    enriched = []
    for b in tree:
        c_list = []
        for c in b["companies"]:
            p_list = []
            for p in c["platoons"]:
                students = [
                    student_export_dict(s)
                    for s in db.get_students_by_platoon(p["row"]["id"])
                ]
                p_list.append({**p, "students": students})
            c_list.append({**c, "platoons": p_list})
        enriched.append({**b, "companies": c_list})
    return enriched


def student_export_dict(row):
    """يحوّل صف طالب إلى dict جاهز للتصدير مع student_number كحقل مستقل.
    يتوفر المفتاح "student_number" صراحةً لاستخدامه في ترتيب الأعمدة الموحّد."""
    d = dict(row)
    keys = row.keys() if hasattr(row, "keys") else d.keys()
    if "student_number" not in d or d["student_number"] is None:
        if "student_number" in keys and d.get("student_number"):
            pass
        else:
            d["student_number"] = ""
    return d


def existing_national_ids():
    """أرقام هوية الطلاب النشطين الحاليين (للتحقق من التكرار عبر النظام)."""
    return {r["national_id"] for r in db.get_all_students_flat() if r["national_id"]}


def all_platoons_flat():
    """كل الفصائل مع مسارها الكامل (احتياطي لقوائم النقل)."""
    out = []
    for b in db.get_full_hierarchy():
        for c in b["companies"]:
            for p in c["platoons"]:
                out.append({
                    "id": p["row"]["id"],
                    "label": f'{b["row"]["name"]} / {c["row"]["name"]} / {p["row"]["name"]}',
                })
    return out
