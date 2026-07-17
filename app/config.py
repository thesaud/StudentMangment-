# -*- coding: utf-8 -*-
"""
app/config.py — الإعدادات المركزية للتطبيق.

كل المسارات قابلة للتهيئة عبر متغيرات البيئة (وهو ما يسمح بتشغيل التطبيق
محلياً على ويندوز/لينكس/ماك أو داخل Docker دون أي تعديل في الكود):

  KATAEB_DATA_DIR     مجلد قاعدة البيانات        (افتراضياً: ./storage/data)
  KATAEB_UPLOADS_DIR  مجلد ملفات الرفع المؤقتة   (افتراضياً: ./storage/uploads)
  KATAEB_EXPORTS_DIR  مجلد نسخ ملفات التصدير     (افتراضياً: ./storage/exports)
  KATAEB_LOGS_DIR     مجلد السجلات               (افتراضياً: ./storage/logs)
  KATAEB_SECRET_KEY   المفتاح السري لجلسات Flask
"""

import os

# جذر المشروع = المجلد الأب لحزمة app
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_STORAGE = os.path.join(PROJECT_ROOT, "storage")


def _dir_from_env(env_key, default_subdir):
    path = os.environ.get(env_key) or os.path.join(_DEFAULT_STORAGE, default_subdir)
    os.makedirs(path, exist_ok=True)
    return path


DATA_DIR = _dir_from_env("KATAEB_DATA_DIR", "data")
UPLOADS_DIR = _dir_from_env("KATAEB_UPLOADS_DIR", "uploads")
EXPORTS_DIR = _dir_from_env("KATAEB_EXPORTS_DIR", "exports")
LOGS_DIR = _dir_from_env("KATAEB_LOGS_DIR", "logs")

DB_FILE = os.path.join(DATA_DIR, "security_app.db")

SECRET_KEY = os.environ.get("KATAEB_SECRET_KEY", "dev-secret-change-in-production")

# نطاق عدد الطلاب "الطبيعي" المطلوب لكل فصيل/سرية/كتيبة (شارة تنبيه بصرية فقط)
STUDENT_COUNT_MIN = int(os.environ.get("KATAEB_STUDENT_COUNT_MIN", "60"))
STUDENT_COUNT_MAX = int(os.environ.get("KATAEB_STUDENT_COUNT_MAX", "100"))

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

# عمر ملفات الرفع المؤقتة قبل تنظيفها تلقائياً (ثانية)
IMPORT_UPLOAD_MAX_AGE = 2 * 60 * 60
