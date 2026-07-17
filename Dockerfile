# =============================================================================
# Dockerfile — نظام إدارة الكتائب والطلاب (إنتاجي)
#
# البناء والتشغيل بأمر واحد عبر docker compose (انظر docker-compose.yml):
#   docker compose up -d
# =============================================================================

FROM python:3.12-slim

# منع بايثون من كتابة ملفات pyc وتفعيل الإخراج الفوري للسجلات
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /srv/kataeb

# تثبيت الاعتماديات أولاً (طبقة قابلة للتخزين المؤقت ما لم تتغير requirements)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نسخ كود التطبيق
COPY run.py .
COPY app ./app

# مجلدات التخزين الدائم (تُركَّب فوقها وحدات تخزين من docker-compose)
ENV KATAEB_DATA_DIR=/data \
    KATAEB_UPLOADS_DIR=/uploads \
    KATAEB_EXPORTS_DIR=/exports \
    KATAEB_LOGS_DIR=/logs

RUN mkdir -p /data /uploads /exports /logs

# مستخدم غير جذري للتشغيل (أفضل ممارسات الأمان)
RUN useradd --create-home --shell /usr/sbin/nologin kataeb \
    && chown -R kataeb:kataeb /srv/kataeb /data /uploads /exports /logs
USER kataeb

EXPOSE 5000

# فحص صحة بسيط: الصفحة الرئيسية يجب أن ترد 200
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:5000/').status==200 else 1)"

# خادم إنتاجي (gunicorn) بدل خادم التطوير المدمج في Flask
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "4", \
     "--access-logfile", "/logs/access.log", "--error-logfile", "/logs/gunicorn.log", \
     "app:create_app()"]
