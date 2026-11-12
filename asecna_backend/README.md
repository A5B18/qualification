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
│   ├── workflows/    ← Registre transversal des approbations (+ services.py)
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

> Les vestiges d'un `django-admin startproject` initial (`config/accounts/`,
> `config/career/`, `config/config/`, `config/core/`, `config/parameters/`,
> `config/reports/` et un second `manage.py`) ont été supprimés : ils n'étaient
> ni dans `INSTALLED_APPS` ni importés nulle part. `config/` ne contient plus
> que ce qui sert réellement.

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
GET    /api/v1/evaluations/sessions/{id}/answers/              → La copie de l'agent
POST   /api/v1/evaluations/sessions/{id}/grade-answer/         → Corriger une réponse
POST   /api/v1/evaluations/sessions/{id}/submit-for-approval/  → Soumettre au chef
POST   /api/v1/evaluations/sessions/{id}/approve/              → Approuver (chef)
POST   /api/v1/evaluations/sessions/{id}/reject/               → Rejeter avec motif
```

`GET .../answers/` est la brique qui relie l'interface au workflow :
`grade-answer` attend un `answer_id`, et rien ne listait les réponses d'une
session. Elle renvoie aussi `unanswered`, les questions laissées vides — elles
comptent pour 0 dans le score, le barème étant celui de l'examen complet.

La **réponse attendue** (`question_detail.correct_answer`) n'est jointe que pour
les profils habilités à corriger : un agent qui relit sa copie ne la reçoit pas.

### Examens
```
GET    /api/v1/evaluations/exams/{id}/questions/   → Énoncés (sans corrigé pour un agent)
POST   /api/v1/evaluations/exams/{id}/publish/     → Publier (refusé si aucune question)
POST   /api/v1/evaluations/exams/{id}/unpublish/   → Repasser en brouillon
POST   /api/v1/evaluations/exams/{id}/start-session/ → L'agent démarre son épreuve
```

Les questions se rattachent à un examen par `PATCH /evaluations/exams/{id}/`
avec la liste complète des identifiants (`{ "questions": [1, 2, 3] }`).

### Cours e-learning
```
GET    /api/v1/training/courses/?training=&is_published=  → Liste filtrée
POST   /api/v1/training/courses/{id}/publish/             → Publier (INSTRUCTEUR)
POST   /api/v1/training/courses/{id}/unpublish/           → Dépublier
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

### Registre d'approbation (transversal)
```
GET    /api/v1/workflows/                 → Registre, filtrable
GET    /api/v1/workflows/pending/         → Ce qui attend une décision
GET    /api/v1/workflows/?module=report   → Filtre par module d'origine
```

`ApprovalWorkflow` est le **registre transversal des décisions** : une ligne par
objet soumis, quel que soit son module. Il est alimenté par
`apps.workflows.services`, appelé depuis les rapports, les fiches de mentorat et
les corrections d'examen, dans la même transaction que leur transition métier.

Chaque module **garde** sa machine à états (`report_status`,
`mentoring_status`, `session_status`) : elle reste la source de vérité de son
propre cycle. Le registre sert à voir au même endroit tout ce qui attend une
décision — un rapport, un mentorat et une correction dans la même liste — et à
retracer qui a décidé quoi.

Chaque ligne porte `module`, `module_label` et `target` (l'objet soumis : son
intitulé, l'agent concerné, la route vers son écran). Sans ces champs, l'écran
d'approbation annonçait « N workflows en attente » sans pouvoir en nommer un
seul.

| Règle | Où |
|---|---|
| Une seule ligne par objet | Contrainte `unique_workflow_per_object` |
| Écritures idempotentes | Une resoumission met la ligne à jour |
| La trace survit à l'objet | `target.deleted` le signale |
| Cloisonnement | Sans rôle de décision, on ne voit que ses propres soumissions |

### Audit (ADMIN uniquement)
```
GET    /api/v1/audit/logs/     → Journal des actions mutantes
GET    /api/v1/audit/logins/   → Historique des connexions (succès et échecs)
```

### Filtres communs

Les listes acceptent `?page_size=<n>` (max 500) et, selon la ressource,
`?agent=`, `?book=`, `?unit=`, `?status=`, `?search=`.

`/agents/skills/`, `/agents/certifications/` et `/agents/performances/`
acceptent `?agent=<id>` : sans lui, les onglets de la fiche agent recevaient la
table entière et triaient dans le navigateur, après une pagination qui tronquait
déjà le résultat.

> **Pagination côté frontend** — le backend pagine à 20. Le client axios
> (`src/api/client.ts`) demande `page_size=200` par défaut sur tout GET qui ne
> précise ni `page_size` ni `page` : sans cela les listes étaient tronquées en
> silence (23 agents affichés comme 20) et le tableau de bord calculait ses
> compteurs sur la première page seulement.

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

**Résultats attendus :** `Ran 204 tests ... OK`

| Suite | Tests | Portée |
|---|---|---|
| `apps.*.tests` | 110 | Modèles, règles métier, contraintes |
| `apps.evaluations.tests_scoring` | 6 | Calcul du score d'une session d'examen |
| `tests.test_api_contract` | 45 | Vues, permissions, serializers, pages HTML |
| `tests.test_correction_workflow` | 25 | Workflow de correction via l'API, filtres de la fiche agent, cours, reset de mot de passe |
| `tests.test_workflow_ledger` | 17 | Alimentation du registre par les 3 modules, unicité, cloisonnement |

> **Lancez les tests depuis le `venv`.** Le projet exige Django 5.2.19. Avec une
> série 4.2 installée globalement, les 5 tests de `HtmlPagesTest` échouent sur
> une incompatibilité Django 4.2 / Python 3.14 (`Context.__copy__`) étrangère au
> code du projet.

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
| Barème = examen complet | Questions sans réponse notées 0 | `ExamSession.compute_score_from_items` |
| Examen vide non publiable | ≥ 1 question | `ExamViewSet.publish` |
| Corrigé jamais servi au candidat | — | `QuestionPublicSerializer` |

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

## 🔐 Réinitialisation d'un mot de passe

`POST /api/v1/auth/users/{id}/reset-password/` (ADMIN) génère un mot de passe
temporaire de 12 caractères et l'**envoie par courriel**.

La réponse porte `delivered_by_email`. Le mot de passe en clair n'y figure que
si l'envoi n'a pas pu aboutir — pas d'adresse connue, SMTP indisponible, ou
backend `console` en développement, où personne ne lit la sortie standard du
serveur. Auparavant il était renvoyé systématiquement : il se retrouvait dans
les journaux d'accès, dans le cache du navigateur et dans l'historique Swagger.

---

## 🔁 Intégration continue

`.github/workflows/ci.yml` rejoue à chaque poussée :

- **Backend** (Python 3.12 et 3.13) : `check`, `makemigrations --check`,
  `spectacular --fail-on-warn`, puis les 204 tests ;
- **Frontend** : `tsc -b`, `npm run lint`, `npm test` (29 tests), `npm run build`.

---

*Projet réalisé dans le cadre de la soutenance ASECNA — Système de Gestion des Agents*
