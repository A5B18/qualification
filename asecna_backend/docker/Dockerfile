FROM python:3.11-slim

WORKDIR /app

# Sans cette variable, gunicorn utilise le defaut de config/wsgi.py, soit
# config.settings.development : l'image tournait donc en DEBUG=True sur SQLite
# au lieu de PostgreSQL. A surcharger pour un usage de developpement.
ENV DJANGO_SETTINGS_MODULE=config.settings.production \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Dépendances système pour psycopg2
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/production.txt .
RUN pip install --no-cache-dir -r production.txt

COPY . .

RUN python manage.py collectstatic --noinput

EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
