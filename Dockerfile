FROM python:3.12-slim AS runtime

ARG APP_UID=10001
ARG APP_GID=10001
ARG RELEASE_VERSION=11.0.0

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UMOJA_RELEASE_VERSION=${RELEASE_VERSION}

WORKDIR /app
RUN groupadd --system --gid "${APP_GID}" umoja \
    && useradd --system --uid "${APP_UID}" --gid "${APP_GID}" --home-dir /app --shell /usr/sbin/nologin umoja

COPY requirements-prod.txt /app/requirements-prod.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install --no-cache-dir -r /app/requirements-prod.txt

COPY --chown=umoja:umoja . /app
RUN python /app/scripts/check_migrations.py
RUN chmod 0555 /app/scripts/*.sh /app/scripts/*.py \
    && find /app -type d -exec chmod 0555 {} + \
    && find /app -type f ! -path '/app/scripts/*' -exec chmod 0444 {} +

USER ${APP_UID}:${APP_GID}
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health/ready', timeout=5)" || exit 1

CMD ["/app/scripts/start-production.sh"]
