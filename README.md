# نظام إدارة الكتائب والطلاب

نظام ويب عربي (RTL) لإدارة الهيكل التنظيمي (كتائب ← سرايا ← فصائل ← طلاب)،
مع الطوابير الإضافية والمخالفات والتقارير والاستيراد/التصدير من وإلى Excel.

## التشغيل

### عبر Docker (أمر واحد — موصى به للإنتاج)
```bash
docker compose up -d
```
ثم افتح: http://localhost:5000

كل البيانات دائمة داخل `./storage/`:
| المجلد | المحتوى |
|---|---|
| `storage/data` | قاعدة البيانات SQLite |
| `storage/uploads` | ملفات Excel المرفوعة مؤقتاً أثناء الاستيراد |
| `storage/exports` | نسخة دائمة (بطابع زمني) من كل ملف تصدير |
| `storage/logs` | سجلات التطبيق و gunicorn |

### محلياً (تطوير)
```bash
pip install -r requirements.txt
python run.py
```
يعمل على ويندوز ولينكس وماك دون أي تعديل (كل المسارات عبر
متغيرات بيئة `KATAEB_*` ولها افتراضيات محمولة — انظر `app/config.py`).

## بنية المشروع
```
run.py                  نقطة تشغيل التطوير
Dockerfile              صورة إنتاجية (gunicorn، مستخدم غير جذري، healthcheck)
docker-compose.yml      تشغيل بأمر واحد + وحدات تخزين دائمة
app/
  __init__.py           مصنع التطبيق (create_app) + السجلات
  config.py             الإعدادات والمسارات المركزية (قابلة للتهيئة بالبيئة)
  db.py                 طبقة قاعدة البيانات (SQLite) — نقطة الوصول الوحيدة
  excel_utils.py        بناء ملفات Excel (تقبل مسارات أو كائنات ذاكرة)
  routes/               مسارات مقسّمة Blueprints حسب المجال
  services/             منطق الأعمال المشترك (استيراد/تصدير/هيكل)
  templates/ static/    الواجهة (Jinja + CSS/JS)
```

## الانتقال المستقبلي إلى PostgreSQL
الوصول لقاعدة البيانات محصور بالكامل في `app/db.py` (لا يوجد SQL في أي
مسار أو قالب). للانتقال: استبدل `get_connection()` بموصل PostgreSQL
(مثل psycopg مع `row_factory=dict_row`)، وعدّل عبارات `AUTOINCREMENT`
إلى `SERIAL/IDENTITY` في `init_db()` — بقية الكود لن يحتاج تعديلاً.
