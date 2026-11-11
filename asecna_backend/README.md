# ASECNA Backend — Système de Gestion des Agents

> API REST Django pour la gestion du cycle de vie des agents ASECNA (probation, mentorat, évaluations, ARCEP, formations).

---

## 🚀 Démarrage rapide

### Prérequis
- Python 3.10 → 3.14
- pip

Le projet tourne sous **Django 5.2 LTS** (support assuré jusqu'en avril 2028),
validé ici sous Python 3.14.

### Installation

```powershell
# 1. Cloner et entrer dans le backend
cd asecna_backend

# 2. Créer l'environnement virtuel
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. Installer les dépendances (les fichiers sont dans requirements/)
pip install -r requirements/development.txt

# 4. Créer les variables d'environnement
copy .env.example .env

# 5. Appliquer les migrations (SQLite en développement)
python manage.py migrate --settings=config.settings.development

# 6. Charger les données initiales (unités, spécialités, rôles)
python manage.py loaddata fixtures/initial_data.json --settings=config.settings.development

# 7. Créer un superutilisateur admin
python manage.py createsuperuser --settings=config.settings.development

# 8. Charger le jeu de données de démonstration (tous les modules)
python manage.py seed_demo --settings=config.settings.development

# 9. Lancer le serveur
python manage.py runserver --settings=config.settings.development
```

### Interfaces disponibles

| Interface | URL |
|---|---|
| **API Swagger** | http://127.0.0.1:8000/api/docs/ |
| **API ReDoc** | http://127.0.0.1:8000/api/redoc/ |
| **Admin Django** | http://127.0.0.1:8000/admin/ |

---

## 🗂️ Architecture

```
asecna_backend/
├── apps/
│   ├── accounts/     ← Utilisateurs, profils agents, rôles fonctionnels
│   ├── units/        ← Unités organisationnelles
│   ├── probation/    ← Périodes d'essai (max 2 tentatives, score 70/100)
│   ├── mentoring/    ← Fiches de mentorat
│   ├── arcep/        ← Carnets ARCEP (signature chef d'unité)
│   ├── training/     ← Formations, cours, stages, maintien qualification
│   ├── evaluations/  ← QCM avec correction manuelle par évaluateur
│   ├── reports/      ← Rapports de période
│   ├── agents/       ← Compétences, certifications, performances
│   ├── workflows/    ← Templates de workflows d'approbation
│   └── audit/        ← Logs d'audit et historique de connexions
├── core/
│   ├── permissions.py ← Permissions DRF par rôle fonctionnel
│   └── mixins.py      ← SoftDeleteMixin
├── config/
│   ├── settings/
│   │   ├── base.py         ← Paramètres communs
│   │   └── development.py  ← SQLite + DEBUG
│   └── urls.py             ← Routeur principal API
└── fixtures/
    └── initial_data.json   ← Données initiales (unités, spécialités, rôles)
```

> **Code mort à ignorer** — `config/` contient aussi les dossiers
> `accounts/`, `career/`, `config/`, `core/`, `parameters/`, `reports/` et un
> second `manage.py`, vestiges d'un `django-admin startproject` initial. Aucun
> n'est dans `INSTALLED_APPS` et aucun n'est importé : seuls `config/settings/`,
> `config/urls.py`, `config/wsgi.py` et `config/asgi.py` sont utilisés. Lancer
> `python config/manage.py` (au lieu du `manage.py` racine) ne fonctionnera pas.

---

## 🔑 Authentification

L'API utilise **JWT (JSON Web Tokens)** via `djangorestframework-simplejwt`.

```http
POST /api/v1/auth/login/
Content-Type: application/json

{ "matricule": "ASE-2024-0001", "password": "votre_mot_de_passe" }
```

**Réponse :**
```json
{ "access": "eyJ...", "refresh": "eyJ..." }
```

Inclure le token dans chaque requête :
```
Authorization: Bearer eyJ...
```

---

## 👥 Rôles fonctionnels

| Rôle | Code | Accès |
|---|---|---|
| Administrateur | `ADMIN` | Tout |
| Chef d'unité | `UNIT_CHIEF` | Validation, signatures ARCEP, approbation évaluations |
| Évaluateur | `EVALUATOR` | Correction évaluations, saisie scores probation, maintien QF |
| Instructeur | `INSTRUCTOR` | Création/publication cours e-learning |
| Mentor | `MENTOR` | Fiches de mentorat |
| Approbateur | `APPROVER` | Équivalent chef d'unité pour workflows |

---

## 📋 Principaux endpoints API

### Probation
```
GET    /api/v1/probation/                  → Liste (admin/chef/évaluateur) ou mes probations
POST   /api/v1/probation/                  → Créer (chef d'unité)
POST   /api/v1/probation/{id}/finalize/    → Finaliser avec score (EVALUATEUR)
GET    /api/v1/probation/evaluation-due/   → Sessions à évaluer dans 14 jours
```

### Évaluations (correction manuelle)
```
POST   /api/v1/evaluations/sessions/{id}/grade-answer/         → Corriger une réponse
POST   /api/v1/evaluations/sessions/{id}/submit-for-approval/  → Soumettre au chef
POST   /api/v1/evaluations/sessions/{id}/approve/              → Approuver (chef)
POST   /api/v1/evaluations/sessions/{id}/reject/               → Rejeter avec motif
```

### Maintien de qualification
```
GET    /api/v1/training/maintenances/              → Liste des contrôles
POST   /api/v1/training/maintenances/{id}/finalize/ → Saisir le score
POST   /api/v1/training/maintenances/{id}/waive/    → Dispenser l'agent
GET    /api/v1/training/maintenances/overdue/       → Contrôles en retard
```

### ARCEP
```
GET    /api/v1/arcep/books/                        → Carnets (lecture seule)
POST   /api/v1/arcep/entries/                      → Ajouter une entrée (agent)
POST   /api/v1/arcep/signatures/                   → Signer une période (UNIT_CHIEF)
GET    /api/v1/arcep/signatures/{id}/covered-entries/ → Entrées couvertes
```

`POST /arcep/signatures/` accepte `{ book, comment }` : si `period_start` et
`period_end` sont omis, la période est déduite des entrées du carnet qui ne sont
pas encore couvertes par une signature.

### Audit (ADMIN uniquement)
```
GET    /api/v1/audit/logs/     → Journal des actions mutantes
GET    /api/v1/audit/logins/   → Historique des connexions (succès et échecs)
```

### Filtres communs

Les listes acceptent `?page_size=<n>` (max 500) et, selon la ressource,
`?agent=`, `?book=`, `?unit=`, `?status=`, `?search=`.

---

## 🏃 Tests

```powershell
# Tous les tests (la découverte complète nécessite apps/__init__.py)
python manage.py test --settings=config.settings.development

# Par app (recommandé pour éviter les conflits)
python manage.py test apps.probation.tests --settings=config.settings.development
python manage.py test apps.training.tests --settings=config.settings.development
python manage.py test apps.evaluations.tests --settings=config.settings.development
python manage.py test apps.mentoring.tests --settings=config.settings.development
```

**Résultats attendus :** `Ran 161 tests ... OK`

| Suite | Tests | Portée |
|---|---|---|
| `apps.*.tests` | 110 | Modèles, règles métier, contraintes |
| `apps.evaluations.tests_scoring` | 6 | Calcul du score d'une session d'examen |
| `tests.test_api_contract` | 45 | Vues, permissions, serializers, pages HTML |

> `tests/test_api_contract.py` traverse réellement l'API : il vérifie qu'aucun
> endpoint ne renvoie d'erreur serveur, que chaque rôle accède aux écrans de son
> menu, que les filtres `?agent=` / `?book=` s'appliquent et qu'une saisie
> invalide produit un 400 explicite.

---

## 🧪 Jeu de données de démonstration

```powershell
# Complète l'existant, sans créer de doublon (idempotent)
python manage.py seed_demo --settings=config.settings.development

# Repart d'une base métier propre
python manage.py seed_demo --reset --settings=config.settings.development
```

La commande peuple **tous** les modules et représente **chaque état de chaque
workflow**, afin qu'aucun écran ne soit vide :

| Module | Ce qui est couvert |
|---|---|
| Comptes | 23 agents, les 7 rôles fonctionnels (dont un cumul), les 7 statuts de parcours |
| Périodes d'essai | En cours, alerte J-14, réussie, 2<sup>e</sup> tentative, double échec |
| Mentorat | `DRAFT`, `SUBMITTED`, `APPROVED`, `REJECTED`, `COMPLETED` |
| ARCEP | Un carnet par agent qualifié, entrées signées **et** non signées |
| Évaluations | 6 questions (3 types, 3 formats), 3 examens, une session dans **chacun** des 6 états |
| Maintien QF | `PENDING`, en retard, `PASSED`, `FAILED`, `WAIVED` |
| Formations | Qualifiante, e-learning, atelier, cours publiés et brouillon, stages |
| Rapports | 3 types × 4 statuts |
| Workflows | `SUBMITTED`, `APPROVED`, `REJECTED` |
| Agents | Compétences, certifications (dont une expirée), performances sur 3 ans |

Les identifiants sont affichés en fin d'exécution et le mot de passe de chaque
compte de démonstration est **réappliqué à chaque lancement**.

> Le déroulé de test complet (par rôle, par règle métier, sécurité et API) est
> dans **[`../GUIDE_DE_TESTS.md`](../GUIDE_DE_TESTS.md)**.

---

## 📊 Règles métier

| Règle | Seuil | Implémentation |
|---|---|---|
| Probation réussie | ≥ 70/100 | `ProbationPeriod.PASSING_SCORE = 70` |
| Max tentatives | 2 | Contrainte DB `unique_probation_per_agent_attempt` |
| Alerte évaluation | J-14 | `evaluation_is_due`, endpoint `/evaluation-due/` |
| Qualification initiale | 80/100 | `Training.passing_score = 80` (EAMAC) |
| Maintien qualification | 70/100 tous les 2 ans | `QualificationMaintenance.MAINTENANCE_SCORE = 70` |
| Suspension si échec maintien | Automatique | `finalize()` met `AgentStatus.SUSPENDED` |
| Correction évaluation | Manuelle par EVALUATEUR | Workflow 4 étapes (grade → submit → approve/reject) |
| ARCEP créé automatiquement | À la qualification | Signal `post_save` sur `AgentProfile` |
| Signature ARCEP obligatoire | Chef d'unité | `is_validated`, permission `IsUnitChief` |

---

## 📦 Pile technique

| Paquet | Version | Pourquoi |
|---|---|---|
| Django | 5.2.19 | LTS → avril 2028 ; 1re série compatible Python 3.13/3.14 |
| djangorestframework | 3.18.3 | Requis pour Django 5.2 |
| djangorestframework-simplejwt | 5.5.1 | Déclare Django 5.2 (métadonnées Python en retard, fonctionne sous 3.14) |
| drf-spectacular | 0.30.0 | Schéma OpenAPI |
| django-cors-headers | 4.9.0 | CORS |
| django-debug-toolbar | 8.0.0 | Dév — 1re série compatible Django 5.2 |

La série Django 4.2 utilisée précédemment est **en fin de vie** (dernière
version : 4.2.30 du 07/04/2026) et ne dépassait pas Python 3.12.

`requirements/rollback-django42.txt` contient le gel exact des versions
d'avant la montée, pour revenir en arrière si besoin :

```powershell
pip install -r requirements/rollback-django42.txt
```

---

## 🔧 Variables d'environnement (.env)

Les noms ci-dessous sont ceux réellement lus par `config/settings/` — voir
`.env.example`. (`DATABASE_URL` n'est pas utilisé : la connexion PostgreSQL se
configure via les variables `DB_*`.)

```env
SECRET_KEY=votre_cle_secrete_django
ALLOWED_HOSTS=localhost,127.0.0.1

# PostgreSQL — utilisé par config.settings.production uniquement.
# En développement, config.settings.development force SQLite (aucune config requise).
DB_NAME=asecna_dev
DB_USER=postgres
DB_PASSWORD=
DB_HOST=localhost
DB_PORT=5432

# JWT
JWT_ACCESS_TOKEN_LIFETIME_MINUTES=60
JWT_REFRESH_TOKEN_LIFETIME_DAYS=7
```

**Production uniquement** (lues par `config/settings/production.py`) :

```env
CORS_ALLOWED_ORIGINS=https://mon-frontend.example
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
```

### Frontend

Le frontend lit l'URL du backend dans `asecna_frontend/.env` :

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

---

## 📁 Base de données

**Développement :** SQLite (`db.sqlite3`) — aucune configuration requise.

**Production :** PostgreSQL (voir `docker/postgres/init.sql` pour la création initiale).

Pour développer sur PostgreSQL sans passer en configuration de production,
poser dans `.env` :

```env
USE_POSTGRES=True
DB_NAME=asecna_dev
DB_USER=postgres
DB_PASSWORD=...
DB_HOST=localhost
DB_PORT=5432
```

puis `python manage.py migrate` et `python manage.py seed_demo`.
Sans cette variable, le développement reste sur SQLite.

---

*Projet réalisé dans le cadre de la soutenance ASECNA — Système de Gestion des Agents*
