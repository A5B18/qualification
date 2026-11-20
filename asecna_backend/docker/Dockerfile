# Image de production du backend ASECNA.
#
# 3.12 est la version visee par l'integration continue et la production ;
# l'image partait sur 3.11, non couverte par la CI.
FROM python:3.12-slim

ENV DJANGO_SETTINGS_MODULE=config.settings.production     PYTHONDONTWRITEBYTECODE=1     PYTHONUNBUFFERED=1     PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependances systeme de psycopg
RUN apt-get update && apt-get install -y --no-install-recommends     gcc     libpq-dev     && rm -rf /var/lib/apt/lists/*

# Les dependances changent moins souvent que le code : les copier d'abord
# permet a Docker de reutiliser le cache de cette couche.
COPY requirements/ requirements/
RUN pip install --no-cache-dir -r requirements/production.txt

COPY . .

# `config.settings.production` exige desormais une SECRET_KEY explicite.
# La collecte des fichiers statiques n'en signe rien : une valeur jetable
# suffit, et surtout elle ne persiste pas dans l'image.
RUN SECRET_KEY=build-time-only python manage.py collectstatic --noinput

# Un conteneur applicatif n'a aucune raison de tourner en root : une faille
# d'execution de code y donnerait les pleins pouvoirs sur le systeme de
# fichiers de l'image.
RUN useradd --system --create-home --uid 10001 asecna     && mkdir -p /app/logs /app/media     && chown -R asecna:asecna /app
USER asecna

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
