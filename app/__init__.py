# -*- coding: utf-8 -*-
"""
app/__init__.py — مصنع تطبيق Flask (Application Factory).

python run.py           للتطوير المحلي
gunicorn "app:create_app()"   للإنتاج (وهو ما يستخدمه Dockerfile)
"""

import json
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler
import os

from flask import Flask

from . import config, db


def create_app():
    app = Flask(__name__)
    app.secret_key = config.SECRET_KEY

    _configure_logging(app)

    db.init_db()
    app.logger.info("قاعدة البيانات جاهزة: %s", config.DB_FILE)

    _register_context_processors(app)
    _register_blueprints(app)

    return app


def _configure_logging(app):
    """سجل دوّار في مجلد logs (يعمل محلياً وداخل Docker على حد سواء)."""
    log_path = os.path.join(config.LOGS_DIR, "app.log")
    handler = RotatingFileHandler(log_path, maxBytes=2_000_000, backupCount=5, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)
    logging.getLogger("app").addHandler(handler)


def _register_context_processors(app):
    from .routes.students import violation_remaining_label

    @app.context_processor
    def inject_helpers():
        return dict(
            remaining_label=violation_remaining_label,
            compute_remaining_label=db.compute_remaining_label,
            format_duration_label=db.format_duration_label,
            DURATION_CATEGORIES=db.DURATION_CATEGORIES,
            STUDENT_COUNT_MIN=config.STUDENT_COUNT_MIN,
            STUDENT_COUNT_MAX=config.STUDENT_COUNT_MAX,
            now=datetime.now(),
        )


def _register_blueprints(app):
    from .routes import (
        api,
        battalions,
        dashboard,
        exports,
        imports,
        inquiry,
        queues,
        reports,
        students,
        violations,
    )

    app.register_blueprint(dashboard.bp)
    app.register_blueprint(battalions.bp)
    app.register_blueprint(students.bp)
    app.register_blueprint(inquiry.bp)
    app.register_blueprint(queues.bp)
    app.register_blueprint(violations.bp)
    app.register_blueprint(imports.bp)
    app.register_blueprint(reports.bp)
    app.register_blueprint(exports.bp)
    app.register_blueprint(api.bp)


def students_to_json(rows):
    """تحويل صفوف الطلاب إلى JSON للبحث اللحظي من جهة العميل."""
    items = []
    for r in rows:
        d = dict(r)
        items.append({
            "sid": d["sid"], "sname": d["sname"], "national_id": d.get("national_id") or "",
            "phone": d.get("phone") or "", "student_number": d.get("student_number") or "",
            "pname": d["pname"], "cname": d["cname"], "bname": d["bname"],
        })
    return json.dumps(items, ensure_ascii=False)
