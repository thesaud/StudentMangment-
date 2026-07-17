# -*- coding: utf-8 -*-
"""نقطة تشغيل التطوير المحلي: python run.py ثم http://127.0.0.1:5000
(للإنتاج يُستخدم gunicorn عبر Docker — انظر Dockerfile)."""

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
