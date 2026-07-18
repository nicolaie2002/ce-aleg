FROM python:3.12-slim-bookworm AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_NO_CACHE_DIR=1

RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH

COPY requirements.txt /tmp/requirements.txt
RUN python -m pip install --requirement /tmp/requirements.txt

FROM python:3.12-slim-bookworm AS runner

ENV APP_ENV=production
ENV FLASK_DEBUG=false
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH=/opt/venv/bin:$PATH
ENV PORT=5001

WORKDIR /app

RUN groupadd --system --gid 10001 cealeg \
    && useradd --system --uid 10001 --gid cealeg --home-dir /app --shell /usr/sbin/nologin cealeg \
    && mkdir -p /app/instance /app/uploads/submissions \
    && chown -R cealeg:cealeg /app

COPY --from=builder /opt/venv /opt/venv
COPY --chown=cealeg:cealeg *.py ./

USER cealeg

EXPOSE 5001

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '5001') + '/health', timeout=3)"

CMD ["sh", "-c", "exec gunicorn 'app:create_application()' --bind 0.0.0.0:${PORT} --worker-class gthread --workers 1 --threads 4 --timeout 60 --graceful-timeout 30 --keep-alive 5 --access-logfile - --error-logfile -"]
