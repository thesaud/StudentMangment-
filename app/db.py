"""
db.py
طبقة قاعدة البيانات (SQLite) لتطبيق إدارة الكتائب.
تُستخدم SQLite كمحرك تخزين قوي وموثوق (يدعم العلاقات، ويمنع تلف البيانات
عند تعدد العمليات)، مع إمكانية التصدير والاستيراد الكامل من/إلى ملفات Excel
حسب طلب المستخدم.
"""

import sqlite3
import os
import re
from datetime import datetime, timedelta

from .config import DB_FILE

# فئات مدة المخالفة المعتمدة في كل الطوابير الإضافية (بالترتيب المطلوب).
# كل فئة عدا "للأمر الأخير" تحتاج عددًا دقيقًا من الأيام يقع ضمن مداها.
DURATION_CATEGORIES = [
    ("1day", "1 يوم", 1, 1),
    ("2to10", "2-10 أيام", 2, 10),
    ("11to30", "11-30 يوم", 11, 30),
    ("indefinite", "للأمر الأخير", None, None),
]


def format_duration_label(duration_category, duration_days):
    """نص عرض جاهز لمدة المخالفة، مثل: يوم واحد / 5 أيام / 20 يوم / للأمر الأخير."""
    if duration_category == "indefinite" or not duration_days:
        return "للأمر الأخير"
    days = int(duration_days)
    if days == 1:
        return "يوم واحد"
    if days == 2:
        return "يومان"
    if 3 <= days <= 10:
        return f"{days} أيام"
    return f"{days} يوم"


def compute_expiry_date(started_at_str, duration_category, duration_days):
    """يحسب تاريخ انتهاء المخالفة بالضبط من تاريخ البداية وعدد الأيام.
    يرجع None لفئة "للأمر الأخير" (بلا نهاية إلا بالإزالة اليدوية)."""
    if duration_category == "indefinite" or not duration_days:
        return None
    try:
        start = datetime.strptime((started_at_str or "").strip(), "%Y-%m-%d")
    except Exception:
        start = datetime.now()
    return (start + timedelta(days=int(duration_days))).strftime("%Y-%m-%d")


def guess_duration_category_from_label(label):
    """يحاول استنتاج (فئة، عدد أيام) من نص مدة حر قديم، لعرضه كتحديد مبدئي
    عند تعديل مدخل كتالوج مخالفات أُنشئ قبل اعتماد الفئات الدقيقة."""
    label = (label or "").strip()
    if not label:
        return "1day", 1
    if "أخير" in label:
        return "indefinite", None
    m = re.search(r"(\d+)", label)
    if m:
        n = int(m.group(1))
    elif "يومان" in label:
        n = 2
    else:
        n = 1
    if n <= 1:
        return "1day", 1
    if n <= 10:
        return "2to10", n
    if n <= 30:
        return "11to30", n
    return "11to30", 30


def compute_remaining_label(expires_at_str, duration_category):
    """نص العد التنازلي المعروض في واجهة الطابور الإضافي."""
    if duration_category == "indefinite" or not expires_at_str:
        return "للأمر الأخير"
    try:
        expires = datetime.strptime(expires_at_str.strip(), "%Y-%m-%d").date()
    except Exception:
        return ""
    remaining = (expires - datetime.now().date()).days
    if remaining > 1:
        return f"متبقي {remaining} يوم"
    if remaining == 1:
        return "متبقي يوم واحد"
    if remaining == 0:
        return "ينتهي اليوم"
    return "منتهية"


def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # 1) إنشاء الجداول الأساسية أولاً (لو قاعدة البيانات جديدة تمامًا).
    cur.executescript(

        """
        CREATE TABLE IF NOT EXISTS battalions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            battalion_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            FOREIGN KEY (battalion_id) REFERENCES battalions(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS platoons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platoon_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            national_id TEXT,
            phone TEXT,
            notes TEXT,
            FOREIGN KEY (platoon_id) REFERENCES platoons(id) ON DELETE CASCADE
        );



        CREATE TABLE IF NOT EXISTS violation_catalog (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            violation_type TEXT NOT NULL,
            duration TEXT NOT NULL,
            date_added TEXT NOT NULL,
            notes TEXT,

            UNIQUE(violation_type, duration)
        );


        CREATE TABLE IF NOT EXISTS violations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            violation_type TEXT NOT NULL,
            duration TEXT NOT NULL,
            date_added TEXT NOT NULL,
            notes TEXT,

            -- الحذف التلقائي بعد انتهاء مدة المخالفة:
            -- نخزن تاريخ بداية المخالفة + تاريخ النهاية (محسوب).
            started_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,

            FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
        );




        CREATE TABLE IF NOT EXISTS queues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            queue_date TEXT NOT NULL,
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS queue_students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            queue_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            violation_type TEXT,
            duration_hours INTEGER,
            started_at TEXT,
            FOREIGN KEY (queue_id) REFERENCES queues(id) ON DELETE CASCADE,
            FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
            UNIQUE(queue_id, student_id)
        );
        """
    )
    conn.commit()

    # 2) ترقيات الأعمدة (تُطبَّق الآن دائمًا بعد التأكد من وجود الجداول،
    # سواء كانت قاعدة البيانات جديدة تمامًا أو قديمة تُحدَّث لأول مرة).
    # SQLite لا تدعم IF NOT EXISTS للـ ALTER بشكل كامل، لذا نستخدم المحاولة/الالتقاط.
    try:
        conn.execute("ALTER TABLE violations ADD COLUMN started_at TEXT NOT NULL DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE violations ADD COLUMN expires_at TEXT NOT NULL DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE students ADD COLUMN status TEXT NOT NULL DEFAULT 'active'")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE students ADD COLUMN resignation_reason TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE students ADD COLUMN resignation_date TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        # الرقم التسلسلي للطالب: يُعيَّن تلقائياً (1..N) أثناء التوزيع التلقائي
        # ويصبح جزءاً دائماً من بيانات الطالب المخزّنة.
        conn.execute("ALTER TABLE students ADD COLUMN student_number INTEGER")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE queue_students ADD COLUMN violation_type TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE queue_students ADD COLUMN duration_category TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE queue_students ADD COLUMN duration_days INTEGER")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE queue_students ADD COLUMN started_at TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE queue_students ADD COLUMN expires_at TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE queue_students ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1")
    except sqlite3.OperationalError:
        pass
    conn.commit()

    # 3) فهارس لتسريع الاستعلامات الأكثر استخدامًا (بحث/ربط) مهما كبر عدد
    # الطلاب. إنشاء فهرس على عمود موجود مسبقًا آمن ورخيص إن تكرر الاستدعاء.
    try:
        conn.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_companies_battalion ON companies(battalion_id);
            CREATE INDEX IF NOT EXISTS idx_platoons_company ON platoons(company_id);
            CREATE INDEX IF NOT EXISTS idx_students_platoon ON students(platoon_id);
            CREATE INDEX IF NOT EXISTS idx_students_status ON students(status);
            CREATE INDEX IF NOT EXISTS idx_students_national_id ON students(national_id);
            CREATE INDEX IF NOT EXISTS idx_students_phone ON students(phone);
            CREATE INDEX IF NOT EXISTS idx_students_number ON students(student_number);
            CREATE INDEX IF NOT EXISTS idx_violations_student ON violations(student_id);
            CREATE INDEX IF NOT EXISTS idx_queue_students_queue ON queue_students(queue_id);
            CREATE INDEX IF NOT EXISTS idx_queue_students_student ON queue_students(student_id);
            """
        )
        conn.commit()
    except sqlite3.OperationalError:
        pass



# ---------------------------------------------------------------------------

# كتائب / سرايا / فصائل
# ---------------------------------------------------------------------------

def add_battalion(name):
    conn = get_connection()
    conn.execute("INSERT INTO battalions (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()


def add_company(battalion_id, name):
    conn = get_connection()
    conn.execute(
        "INSERT INTO companies (battalion_id, name) VALUES (?, ?)",
        (battalion_id, name),
    )
    conn.commit()
    conn.close()


def add_platoon(company_id, name):
    conn = get_connection()
    conn.execute(
        "INSERT INTO platoons (company_id, name) VALUES (?, ?)",
        (company_id, name),
    )
    conn.commit()
    conn.close()


def delete_battalion(battalion_id):
    conn = get_connection()
    conn.execute("DELETE FROM battalions WHERE id=?", (battalion_id,))
    conn.commit()
    conn.close()


def delete_company(company_id):
    conn = get_connection()
    conn.execute("DELETE FROM companies WHERE id=?", (company_id,))
    conn.commit()
    conn.close()


def delete_platoon(platoon_id):
    conn = get_connection()
    conn.execute("DELETE FROM platoons WHERE id=?", (platoon_id,))
    conn.commit()
    conn.close()


def get_battalions():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM battalions ORDER BY name").fetchall()
    conn.close()
    return rows


def get_battalion(battalion_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM battalions WHERE id=?", (battalion_id,)).fetchone()
    conn.close()
    return row


def get_companies(battalion_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM companies WHERE battalion_id=? ORDER BY name", (battalion_id,)
    ).fetchall()
    conn.close()
    return rows


def get_company(company_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM companies WHERE id=?", (company_id,)).fetchone()
    conn.close()
    return row


def get_platoons(company_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM platoons WHERE company_id=? ORDER BY name", (company_id,)
    ).fetchall()
    conn.close()
    return rows


def get_platoon_context(platoon_id):
    """يرجع اسم الفصيل مع اسم السرية والكتيبة التابع لهما."""
    conn = get_connection()
    row = conn.execute(
        """
        SELECT p.name as pname, c.name as cname, b.name as bname
        FROM platoons p
        JOIN companies c ON p.company_id = c.id
        JOIN battalions b ON c.battalion_id = b.id
        WHERE p.id = ?
        """,
        (platoon_id,),
    ).fetchone()
    conn.close()
    return row


def get_full_hierarchy():
    """يرجع شجرة كاملة: كتيبة -> سرية -> فصيل -> عدد الطلاب"""
    conn = get_connection()
    battalions = conn.execute("SELECT * FROM battalions ORDER BY name").fetchall()
    tree = []
    for b in battalions:
        companies = conn.execute(
            "SELECT * FROM companies WHERE battalion_id=? ORDER BY name", (b["id"],)
        ).fetchall()
        c_list = []
        for c in companies:
            platoons = conn.execute(
                "SELECT * FROM platoons WHERE company_id=? ORDER BY name", (c["id"],)
            ).fetchall()
            p_list = []
            for p in platoons:
                count = conn.execute(
                    "SELECT COUNT(*) as c FROM students WHERE platoon_id=? AND (status IS NULL OR status='active')",
                    (p["id"],),
                ).fetchone()["c"]
                p_list.append({"row": p, "student_count": count})
            c_list.append({"row": c, "platoons": p_list})
        tree.append({"row": b, "companies": c_list})
    conn.close()
    return tree


# ---------------------------------------------------------------------------
# الطلاب
# ---------------------------------------------------------------------------

def add_student(platoon_id, name, national_id="", phone="", notes=""):
    conn = get_connection()
    conn.execute(
        "INSERT INTO students (platoon_id, name, national_id, phone, notes) "
        "VALUES (?, ?, ?, ?, ?)",
        (platoon_id, name, national_id, phone, notes),
    )
    conn.commit()
    conn.close()


def _clear_structure():
    """حذف الهيكل والطلاب (يُستخدم فقط داخل توزيع تلقائي لتجنب تكرار قديم)."""
    conn = get_connection()
    conn.execute("DELETE FROM battalions")
    conn.commit()
    conn.close()


def create_structure_and_distribute_from_rows(

    battalion_count: int,
    companies_per_battalion: int,
    platoons_per_company: int,
    rows: list[dict],
):
    """ينشئ هيكل كامل بالأعداد المعطاة ثم يوزع الطلاب بالتساوي على الفصائل.

    rows: قائمة dict بالشكل: {name, national_id, phone}
    - national_id يتم حفظه في students.national_id
    - phone يتم حفظه في students.phone (بحسب طلبك: رقم الطالب)

    """

    battalion_count = int(battalion_count)
    companies_per_battalion = int(companies_per_battalion)
    platoons_per_company = int(platoons_per_company)

    if battalion_count <= 0 or companies_per_battalion <= 0 or platoons_per_company <= 0:
        raise ValueError("الأعداد يجب أن تكون أكبر من صفر")

    # تصفير الهيكل والطلاب قبل إعادة التوزيع
    _clear_structure()

    conn = get_connection()
    cur = conn.cursor()

    platoon_ids = []

    # إنشاء الهيكل
    for b_idx in range(1, battalion_count + 1):
        b_name = f"الكتيبة {b_idx}"
        cur.execute("INSERT INTO battalions (name) VALUES (?)", (b_name,))
        b_id = cur.lastrowid

        for c_idx in range(1, companies_per_battalion + 1):
            c_name = f"السرية {c_idx}"
            cur.execute(
                "INSERT INTO companies (battalion_id, name) VALUES (?, ?)",
                (b_id, c_name),
            )
            c_id = cur.lastrowid

            for p_idx in range(1, platoons_per_company + 1):
                p_name = f"الفصيل {p_idx}"
                cur.execute(
                    "INSERT INTO platoons (company_id, name) VALUES (?, ?)",
                    (c_id, p_name),
                )
                p_id = cur.lastrowid
                platoon_ids.append(p_id)

    conn.commit()

    if not rows:
        conn.close()
        return

    # توزيع Round-robin بالتساوي على الفصائل
    for i, r in enumerate(rows):
        p_id = platoon_ids[i % len(platoon_ids)]
        conn.execute(
            "INSERT INTO students (platoon_id, name, national_id, phone, notes) VALUES (?, ?, ?, ?, ?)",
            (
                p_id,
                (r.get("name") or "").strip(),
                (r.get("national_id") or "").strip(),
                (r.get("phone") or "").strip(),
                (r.get("notes") or "").strip(),
            ),
        )

    conn.commit()
    conn.close()



def create_structure_and_distribute_custom(
    battalion_count: int,
    platoons_per_company_list: list[int],
    rows: list[dict],
):
    """النسخة المحسّنة من التوزيع التلقائي، وتدعم متطلبين جديدين:

    1) عدد فصائل مختلف لكل سرية: platoons_per_company_list قائمة أعداد،
       طولها = عدد السرايا في كل كتيبة، وقيمتها [i] = عدد فصائل السرية i+1.
       (يُطبَّق النمط نفسه على كل كتيبة). مثال: [3, 5, 2] تعني أن كل كتيبة
       تحتوي 3 سرايا: الأولى بـ3 فصائل، والثانية بـ5، والثالثة بـ2.

    2) رقم طالب تسلسلي: يُعيَّن لكل طالب مستورد رقم فريد متصل يبدأ من 1
       بترتيب وروده في الملف، ويُخزَّن في students.student_number بشكل دائم.

    التوزيع نفسه يبقى بالتساوي (Round-robin) على كل الفصائل الناتجة.
    العملية كلها تجري ضمن معاملة واحدة (transaction): إما أن تكتمل بالكامل
    أو لا يتغير شيء في قاعدة البيانات إن حدث خطأ في المنتصف.
    """
    battalion_count = int(battalion_count)
    platoons_per_company_list = [int(p) for p in platoons_per_company_list]

    if battalion_count <= 0:
        raise ValueError("عدد الكتائب يجب أن يكون أكبر من صفر")
    if not platoons_per_company_list:
        raise ValueError("يجب تحديد سرية واحدة على الأقل")
    if any(p <= 0 for p in platoons_per_company_list):
        raise ValueError("عدد الفصائل في كل سرية يجب أن يكون أكبر من صفر")

    conn = get_connection()
    try:
        cur = conn.cursor()

        # تصفير الهيكل والطلاب ضمن نفس المعاملة قبل إعادة البناء
        cur.execute("DELETE FROM queue_students")
        cur.execute("DELETE FROM queues")
        cur.execute("DELETE FROM violations")
        cur.execute("DELETE FROM students")
        cur.execute("DELETE FROM platoons")
        cur.execute("DELETE FROM companies")
        cur.execute("DELETE FROM battalions")

        platoon_ids = []
        for b_idx in range(1, battalion_count + 1):
            cur.execute("INSERT INTO battalions (name) VALUES (?)", (f"الكتيبة {b_idx}",))
            b_id = cur.lastrowid
            for c_idx, platoon_count in enumerate(platoons_per_company_list, start=1):
                cur.execute(
                    "INSERT INTO companies (battalion_id, name) VALUES (?, ?)",
                    (b_id, f"السرية {c_idx}"),
                )
                c_id = cur.lastrowid
                for p_idx in range(1, platoon_count + 1):
                    cur.execute(
                        "INSERT INTO platoons (company_id, name) VALUES (?, ?)",
                        (c_id, f"الفصيل {p_idx}"),
                    )
                    platoon_ids.append(cur.lastrowid)

        for i, r in enumerate(rows):
            p_id = platoon_ids[i % len(platoon_ids)]
            cur.execute(
                "INSERT INTO students (platoon_id, name, national_id, phone, notes, student_number)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (
                    p_id,
                    (r.get("name") or "").strip(),
                    (r.get("national_id") or "").strip(),
                    (r.get("phone") or "").strip(),
                    (r.get("notes") or "").strip(),
                    i + 1,  # الرقم التسلسلي: متصل وفريد يبدأ من 1
                ),
            )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return {
        "total_platoons": battalion_count * sum(platoons_per_company_list),
        "imported": len(rows),
    }


def update_student(student_id, name, national_id, phone, notes):
    conn = get_connection()
    conn.execute(
        "UPDATE students SET name=?, national_id=?, phone=?, notes=? WHERE id=?",
        (name, national_id, phone, notes, student_id),
    )
    conn.commit()
    conn.close()


def delete_student(student_id):
    conn = get_connection()
    conn.execute("DELETE FROM students WHERE id=?", (student_id,))
    conn.commit()
    conn.close()


def update_student_notes(student_id, notes):
    """تحديث ملاحظات الطالب فقط (لاستخدامها في التعديل السريع بضغطة واحدة)."""
    conn = get_connection()
    conn.execute("UPDATE students SET notes=? WHERE id=?", (notes, student_id))
    conn.commit()
    conn.close()


def transfer_student(student_id, new_platoon_id):
    """نقل طالب إلى فصيل آخر (وبالتالي سرية/كتيبة أخرى تلقائياً حسب الفصيل الجديد)."""
    conn = get_connection()
    conn.execute("UPDATE students SET platoon_id=? WHERE id=?", (new_platoon_id, student_id))
    conn.commit()
    conn.close()


def resign_student(student_id, reason):
    """تسجيل استقالة طالب: يبقى سجله محفوظاً بالكامل (كتيبته/سريته/فصيله/مخالفاته)
    لكنه لا يظهر بعد الآن في إدارة الكتائب أو نتائج البحث أو الكشوفات، ويظهر
    فقط في التقارير والإحصائيات ضمن قائمة المستقيلين."""
    conn = get_connection()
    conn.execute(
        "UPDATE students SET status='resigned', resignation_reason=?, resignation_date=? WHERE id=?",
        (reason, datetime.now().strftime("%Y-%m-%d %H:%M"), student_id),
    )
    conn.commit()
    conn.close()


def reinstate_student(student_id):
    """التراجع عن استقالة طالب (لتصحيح الأخطاء) وإعادته نشطاً في فصيله الأصلي."""
    conn = get_connection()
    conn.execute(
        "UPDATE students SET status='active', resignation_reason=NULL, resignation_date=NULL WHERE id=?",
        (student_id,),
    )
    conn.commit()
    conn.close()


def get_resigned_students():
    """كل الطلاب المستقيلين مع مسارهم التنظيمي الكامل وسبب/تاريخ الاستقالة."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT s.id as sid, s.name as sname, s.national_id, s.phone, s.notes,
               s.student_number, s.resignation_reason, s.resignation_date,
               p.name as pname, c.name as cname, b.name as bname
        FROM students s
        JOIN platoons p ON s.platoon_id = p.id
        JOIN companies c ON p.company_id = c.id
        JOIN battalions b ON c.battalion_id = b.id
        WHERE s.status = 'resigned'
        ORDER BY s.resignation_date DESC, s.id DESC
        """
    ).fetchall()
    conn.close()
    return rows


def get_students_by_platoon(platoon_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM students WHERE platoon_id=? AND (status IS NULL OR status='active') ORDER BY name",
        (platoon_id,),
    ).fetchall()
    conn.close()
    return rows


def get_students_multi(platoon_ids):
    """يرجع كل الطلاب النشطين ضمن مجموعة فصائل معًا (لاستعراض طلاب سرية أو
    كتيبة كاملة)، مع اسم الفصيل/السرية/الكتيبة التابعين لكل طالب."""
    if not platoon_ids:
        return []
    placeholders = ",".join("?" for _ in platoon_ids)
    conn = get_connection()
    rows = conn.execute(
        f"""
        SELECT s.*, p.name as pname, c.name as cname, b.name as bname
        FROM students s
        JOIN platoons p ON s.platoon_id = p.id
        JOIN companies c ON p.company_id = c.id
        JOIN battalions b ON c.battalion_id = b.id
        WHERE s.platoon_id IN ({placeholders})
          AND (s.status IS NULL OR s.status = 'active')
        ORDER BY b.name, c.name, p.name, s.name
        """,
        list(platoon_ids),
    ).fetchall()
    conn.close()
    return rows


def get_student_full_path(student_id):
    """يرجع بيانات الطالب الكاملة مع مساره التنظيمي: الاسم، الفصيل، السرية،
    الكتيبة، رقم الهوية، رقم الطالب، والملاحظات، ورقم الفصيل الداخلي."""
    conn = get_connection()
    row = conn.execute(
        """
        SELECT s.name as sname, p.name as pname, c.name as cname, b.name as bname,
               s.id as sid, s.national_id, s.phone, s.notes, s.student_number,
               s.platoon_id as platoon_id
        FROM students s
        JOIN platoons p ON s.platoon_id = p.id
        JOIN companies c ON p.company_id = c.id
        JOIN battalions b ON c.battalion_id = b.id
        WHERE s.id = ?
        """,
        (student_id,),
    ).fetchone()
    conn.close()
    return row


def get_all_students_flat():
    """كل الطلاب النشطين (غير المستقيلين) مع مسارهم التنظيمي الكامل - لاستخدامه في البحث السريع"""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT s.id as sid, s.name as sname, s.national_id, s.phone, s.student_number,
               p.name as pname, c.name as cname, b.name as bname
        FROM students s
        JOIN platoons p ON s.platoon_id = p.id
        JOIN companies c ON p.company_id = c.id
        JOIN battalions b ON c.battalion_id = b.id
        WHERE (s.status IS NULL OR s.status = 'active')
        ORDER BY b.name, c.name, p.name, s.name
        """
    ).fetchall()
    conn.close()
    return rows


# ---------------------------------------------------------------------------
# المخالفات
# ---------------------------------------------------------------------------

def add_violation_catalog(violation_type, duration, notes=""):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO violation_catalog (violation_type, duration, date_added, notes) "
            "VALUES (?, ?, ?, ?)",
            (
                violation_type,
                duration,
                datetime.now().strftime("%Y-%m-%d"),
                notes,
            ),
        )
    except sqlite3.IntegrityError:
        # موجود مسبقاً لنفس (نوع+مدة)
        pass
    conn.commit()
    conn.close()



def get_violation_catalog():
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT id, violation_type, duration, date_added, notes
        FROM violation_catalog
        ORDER BY date_added DESC, id DESC
        """
    ).fetchall()
    conn.close()
    return rows


def get_violation_type_duration_map_from_catalog():
    """مرجع: نوع المخالفة -> مدة (آخر مدة محفوظة لنفس النوع)."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT violation_type, duration
        FROM violation_catalog
        ORDER BY date_added DESC, id DESC
        """
    ).fetchall()
    conn.close()

    mapping = {}
    for r in rows:
        # أول ظهور بعد ترتيب DESC هو الأحدث
        if r["violation_type"] not in mapping:
            mapping[r["violation_type"]] = r["duration"]
    return mapping


def _parse_duration_to_days(duration: str) -> int:
    """يحوّل 'duration' نصياً إلى عدد أيام.

    يدعم صيغ عربية شائعة مثل:
    - "يوم" / "يومان" / "يومين" / "3 أيام" / "10يوم"
    - "48 ساعة" / "24ساعه" / "24 ساعة"
    - رقم فقط (اعتباره أيام)

    إذا لم يمكن القياس: يرجّع 0.
    """

    if not duration:
        return 0

    s = str(duration).strip()
    if not s:
        return 0

    import re

    # توحيد بسيط للتباينات (مثل: "ساعه" و "ساعة")
    s_norm = s.replace("ة", "ه")  # "ساعة" و "ساعه" تتقاربان

    # ساعات
    m_hours = re.search(r"(\d+)\s*(?:ساعه|ساعة|ساعة)\b", s_norm)
    if m_hours:
        hours = int(m_hours.group(1))
        # تحويل تقريبي: أي أقل من 24 ساعة يعتبر يوم واحد لتجنب expiration فوراً
        return max(1, hours // 24) if hours >= 1 else 0

    # أيام بصيغ "يوم/يومان/يومين" أو "3 أيام"
    m_days = re.search(r"(\d+)\s*(?:يوم|أيام|يومان|يومين)\b", s_norm)
    if m_days:
        return max(0, int(m_days.group(1)))

    # حالات غير رقمية مثل: "يومين" بدون رقم
    if re.search(r"\b(يومان|يومين)\b", s_norm):
        return 2

    if re.search(r"\bيوم\b", s_norm):
        return 1

    # رقم فقط
    m_num = re.search(r"^(\d+)$", s)
    if m_num:
        return max(0, int(m_num.group(1)))

    return 0



def add_violation(student_id, violation_type, duration, notes=""):
    """إضافة مخالفة للطالب مع حساب تاريخ الانتهاء.

    - started_at = اليوم
    - expires_at = started_at + duration_days

    ملاحظة: إذا لم يمكن تحويل duration إلى أيام، نحفظ expires_at = started_at.
    """
    started_at_dt = datetime.now()
    started_at = started_at_dt.strftime("%Y-%m-%d")

    if "أخير" in (duration or ""):
        # فئة "للأمر الأخير": لا تنتهي إلا بالحذف اليدوي
        expires_at = ""
    else:
        days = _parse_duration_to_days(duration)
        from datetime import timedelta
        expires_dt = started_at_dt + timedelta(days=days)
        expires_at = expires_dt.strftime("%Y-%m-%d")

    conn = get_connection()
    conn.execute(
        "INSERT INTO violations (student_id, violation_type, duration, date_added, notes, started_at, expires_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            student_id,
            violation_type,
            duration,
            started_at,
            notes,
            started_at,
            expires_at,
        ),
    )
    conn.commit()
    conn.close()




def update_violation(violation_id, violation_type, duration, notes):
    conn = get_connection()

    # إعادة حساب مدة الانتهاء عند التعديل
    started_at_row = conn.execute(
        "SELECT started_at FROM violations WHERE id=?",
        (violation_id,),
    ).fetchone()

    if not started_at_row:
        conn.close()
        return

    started_at = started_at_row["started_at"]

    from datetime import datetime, timedelta

    if "أخير" in (duration or ""):
        expires_at = ""
    else:
        started_at_dt = datetime.strptime(started_at, "%Y-%m-%d")
        days = _parse_duration_to_days(duration)
        expires_dt = started_at_dt + timedelta(days=days)
        expires_at = expires_dt.strftime("%Y-%m-%d")

    conn.execute(
        "UPDATE violations SET violation_type=?, duration=?, notes=?, expires_at=? WHERE id=?",
        (violation_type, duration, notes, expires_at, violation_id),
    )
    conn.commit()
    conn.close()



def delete_violation(violation_id):
    conn = get_connection()
    conn.execute("DELETE FROM violations WHERE id=?", (violation_id,))
    conn.commit()
    conn.close()


def get_latest_violation_for_student(student_id):
    """يرجع آخر مخالفة مسجلة للطالب (الأحدث بتاريخ الإضافة)."""
    conn = get_connection()
    row = conn.execute(
        """
        SELECT violation_type, duration, date_added
        FROM violations
        WHERE student_id=?
        ORDER BY date_added DESC, id DESC
        LIMIT 1
        """,
        (student_id,),
    ).fetchone()
    conn.close()
    return row



def get_violation_types_for_queue():

    """(متروك) - بقيت للملاءمة القديمة.
    الجديد يعتمد على violation_catalog.
    """

    mapping = get_violation_type_duration_map_from_catalog()
    return sorted(list(mapping.keys()))




def delete_expired_students():
    """تنبيه: تم إلغاء هذه الدالة عمداً.

    كانت تحذف الطالب بالكامل من قاعدة البيانات (مع كل مخالفاته وسجل طوابيره)
    بمجرد انتهاء مدة إحدى مخالفاته، وهذا سلوك خطير وغير مقصود يسبب فقدان
    بيانات نهائياً. تم إبقاء اسم الدالة فارغاً (لا تفعل شيئاً) حفاظاً على
    توافق أي استدعاء قديم لها، لكنها لا تحذف أي شيء بعد الآن.
    استخدم بدلاً منها ميزة "الاستقالة" (resign_student) إن أردت إخراج طالب
    من الإدارة النشطة مع الحفاظ الكامل على سجله.
    """
    return




def get_all_violations():

    conn = get_connection()
    rows = conn.execute(

        """
        SELECT v.id as vid, v.violation_type, v.duration, v.date_added, v.notes,
               s.name as sname, s.national_id, s.student_number,
               p.name as pname, c.name as cname, b.name as bname
        FROM violations v
        JOIN students s ON v.student_id = s.id
        JOIN platoons p ON s.platoon_id = p.id
        JOIN companies c ON p.company_id = c.id
        JOIN battalions b ON c.battalion_id = b.id
        ORDER BY v.date_added DESC, v.id DESC
        """
    ).fetchall()
    conn.close()
    return rows


def get_violations_for_student(student_id):
    """كل المخالفات السابقة لطالب محدد (الأحدث أولاً) - لصفحة الاستعلام."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT id as vid, violation_type, duration, date_added, notes, started_at, expires_at
        FROM violations
        WHERE student_id = ?
        ORDER BY date_added DESC, id DESC
        """,
        (student_id,),
    ).fetchall()
    conn.close()
    return rows


# ---------------------------------------------------------------------------
# الطوابير الإضافية
# ---------------------------------------------------------------------------

def add_queue(name, queue_date, notes=""):
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO queues (name, queue_date, notes) VALUES (?, ?, ?)",
        (name, queue_date, notes),
    )
    conn.commit()
    qid = cur.lastrowid
    conn.close()
    return qid


def delete_queue(queue_id):
    conn = get_connection()
    conn.execute("DELETE FROM queues WHERE id=?", (queue_id,))
    conn.commit()
    conn.close()


def get_queues():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM queues ORDER BY queue_date DESC, id DESC").fetchall()
    conn.close()
    return rows


def add_student_to_queue(queue_id, student_id, violation_type=None,
                          duration_category=None, duration_days=None, started_at=None):
    """يضيف طالبًا لطابور مع تحديد نوع المخالفة وفئة/عدد أيام مدتها بدقة،
    ويحسب تاريخ الانتهاء تلقائيًا (فارغ = للأمر الأخير). إن كان الطالب
    مضافًا سابقًا لنفس الطابور (حتى لو أصبح غير نشط)، تُحدَّث بياناته
    ويُعاد تفعيله بدل تكرار الصف."""
    started_at = started_at or datetime.now().strftime("%Y-%m-%d")
    expires_at = compute_expiry_date(started_at, duration_category, duration_days)
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO queue_students
               (queue_id, student_id, violation_type, duration_category, duration_days,
                started_at, expires_at, is_active)
               VALUES (?, ?, ?, ?, ?, ?, ?, 1)""",
            (queue_id, student_id, violation_type, duration_category, duration_days,
             started_at, expires_at),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.execute(
            """UPDATE queue_students
               SET violation_type=?, duration_category=?, duration_days=?,
                   started_at=?, expires_at=?, is_active=1
               WHERE queue_id=? AND student_id=?""",
            (violation_type, duration_category, duration_days, started_at, expires_at,
             queue_id, student_id),
        )
        conn.commit()
    conn.close()


def update_queue_student_duration(queue_id, student_id, duration_category, duration_days):
    """تعديل فئة/عدد أيام مدة مخالفة طالب داخل طابور معيّن، مع إعادة حساب
    تاريخ الانتهاء اعتمادًا على تاريخ الإضافة الأصلي (بدون تغييره)،
    وإعادة تفعيل العضوية في حال كانت قد انتهت سابقًا."""
    conn = get_connection()
    row = conn.execute(
        "SELECT started_at FROM queue_students WHERE queue_id=? AND student_id=?",
        (queue_id, student_id),
    ).fetchone()
    started_at = (row["started_at"] if row and row["started_at"] else None) or datetime.now().strftime("%Y-%m-%d")
    expires_at = compute_expiry_date(started_at, duration_category, duration_days)
    conn.execute(
        """UPDATE queue_students
           SET duration_category=?, duration_days=?, expires_at=?, is_active=1
           WHERE queue_id=? AND student_id=?""",
        (duration_category, duration_days, expires_at, queue_id, student_id),
    )
    conn.commit()
    conn.close()


def expire_overdue_queue_entries():
    """يُخفي (دون حذف الطالب أو سجله نهائياً) أي عضوية طابور انتهت مدتها
    من العرض النشط فقط، مع الحفاظ الكامل على السجل التاريخي لاستخدامه لاحقاً
    في صفحة الاستعلام."""
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_connection()
    conn.execute(
        """UPDATE queue_students SET is_active = 0
           WHERE is_active = 1 AND expires_at IS NOT NULL AND expires_at != '' AND expires_at < ?""",
        (today,),
    )
    conn.commit()
    conn.close()


def remove_student_from_queue(queue_id, student_id):
    """إزالة يدوية لطالب من الطابور النشط. لا تحذف السجل نهائياً بل تُخفيه
    فقط (نفس منطق انتهاء المدة تلقائياً)، حفاظاً على تاريخه الكامل للاستعلام."""
    conn = get_connection()
    conn.execute(
        "UPDATE queue_students SET is_active = 0 WHERE queue_id=? AND student_id=?",
        (queue_id, student_id),
    )
    conn.commit()
    conn.close()


def get_queue_students(queue_id):
    """طلاب الطابور النشطون حالياً فقط (الذين لم تنتهِ مدتهم بعد)."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT s.id as sid, s.name as sname, s.national_id, s.phone, s.student_number,
               p.name as pname, c.name as cname, b.name as bname,
               qs.violation_type as q_violation_type,
               qs.duration_category as q_duration_category,
               qs.duration_days as q_duration_days,
               qs.started_at as q_started_at,
               qs.expires_at as q_expires_at
        FROM queue_students qs
        JOIN students s ON qs.student_id = s.id
        JOIN platoons p ON s.platoon_id = p.id
        JOIN companies c ON p.company_id = c.id
        JOIN battalions b ON c.battalion_id = b.id
        WHERE qs.queue_id = ? AND qs.is_active = 1
        ORDER BY b.name, c.name, p.name, s.name
        """,
        (queue_id,),
    ).fetchall()
    conn.close()
    return rows


def get_queues_for_student(student_id):
    """سجل كل الطوابير الإضافية التي أُضيف إليها طالب محدد عبر كل الوقت
    (نشطة كانت أو منتهية)، مع مدتها وحالتها - لصفحة الاستعلام."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT q.id as qid, q.name as qname, q.queue_date, q.notes as qnotes,
               qs.violation_type as q_violation_type,
               qs.duration_category as q_duration_category,
               qs.duration_days as q_duration_days,
               qs.started_at as q_started_at,
               qs.expires_at as q_expires_at,
               qs.is_active as q_is_active
        FROM queue_students qs
        JOIN queues q ON qs.queue_id = q.id
        WHERE qs.student_id = ?
        ORDER BY q.queue_date DESC, q.id DESC
        """,
        (student_id,),
    ).fetchall()
    conn.close()
    return rows
