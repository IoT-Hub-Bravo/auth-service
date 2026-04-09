FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install --no-install-recommends -y \
    libpq-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY src/ .
COPY pytest.ini .
RUN BUILD_TIME=1 \
    DJANGO_SETTINGS_MODULE=config.settings \
    SECRET_KEY=unsafe-build-time-secret-do-not-use-in-production \
    python manage.py collectstatic --noinput

RUN addgroup --gid 10001 --system django \
    && adduser --no-create-home --shell /bin/false \
               --disabled-password --uid 10001 --system --group django \
    && chown -R django:django /app

COPY --chown=django:django docker/entrypoint.sh /entrypoint.sh
COPY --chown=django:django docker/start.sh /start.sh
RUN sed -i "s/\r$//" /entrypoint.sh /start.sh \
    && chmod 555 /entrypoint.sh /start.sh

USER django

EXPOSE 8001

ENTRYPOINT ["/entrypoint.sh"]
CMD ["/start.sh"]
