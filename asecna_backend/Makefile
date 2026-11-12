.PHONY: help install shell run migrations migrate superuser test fixtures demo clean

SETTINGS = config.settings.development
PYTHON   = .\venv\Scripts\python
PIP      = .\venv\Scripts\pip

help:
	@echo "Commandes disponibles (sans Docker) :"
	@echo "  install     Installe les dependances de developpement"
	@echo "  run         Lance le serveur (SQLite, DEBUG=True)"
	@echo "  migrations  Genere les fichiers de migration"
	@echo "  migrate     Applique les migrations sur SQLite"
	@echo "  superuser   Cree un superutilisateur admin"
	@echo "  fixtures    Charge les donnees initiales (unites, specialites)"
	@echo "  demo        Charge le jeu de donnees de demonstration"
	@echo "  test        Lance tous les tests unitaires"
	@echo "  shell       Lance le shell Django interactif"
	@echo "  clean       Supprime les fichiers __pycache__ et .pyc"

install:
	$(PIP) install -r requirements\development.txt

run:
	$(PYTHON) manage.py runserver --settings=$(SETTINGS)

migrations:
	$(PYTHON) manage.py makemigrations --settings=$(SETTINGS)

migrate:
	$(PYTHON) manage.py migrate --settings=$(SETTINGS)

superuser:
	$(PYTHON) manage.py createsuperuser --settings=$(SETTINGS)

fixtures:
	$(PYTHON) manage.py loaddata fixtures/initial_data.json --settings=$(SETTINGS)

# `scripts/create_demo_data.py` etait l'ancien script autonome : il ne
# couvrait plus tous les modules et n'etait pas idempotent. La commande
# de gestion `seed_demo` l'a remplace (c'est elle que documentent le
# README et le guide de tests).
demo:
	$(PYTHON) manage.py seed_demo --settings=$(SETTINGS)

test:
	$(PYTHON) manage.py test --settings=$(SETTINGS) --verbosity=2

shell:
	$(PYTHON) manage.py shell --settings=$(SETTINGS)

clean:
	for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
	del /s /q *.pyc 2>nul || true
