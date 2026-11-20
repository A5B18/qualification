# Audit technique — rapport et corrections

**Projet :** ASECNA Career Management (backend Django 5.2 / DRF, frontend React 19 / TypeScript)
**Date :** 20 novembre 2026
**Périmètre :** architecture, code source, conventions des technologies employées, sécurité, performance, tests, outillage et déploiement.

---

## 1. Résumé

Huit failles de sécurité ont été corrigées, dont deux permettaient de contourner entièrement le circuit
d'approbation depuis l'API publique. L'architecture d'origine n'a pas été modifiée : les corrections la
resserrent.

**Volume :** 69 fichiers modifiés, 13 créés, 1 supprimé — +1 845 / −848 lignes.

| Indicateur | Avant | Après |
|---|---|---|
| Tests backend | 230 | **254** |
| Durée de la suite backend | 270 s | **2,4 s** |
| `manage.py check --deploy` | avertissements | **aucun** |
| Couverture `apps` + `core` | non mesurée | **76 %** |
| `GET /auth/users/` (23 agents) | 23 requêtes | **3** |
| `GET /workflows/` (12 lignes) | 20 requêtes | **5** |
| Tests frontend | 45 | 45 (inchangés, aucun cassé) |

---

## 2. Problèmes détectés

### 2.1 Sécurité

Les deux premiers sont les plus graves : ils laissaient un agent ordinaire court-circuiter le circuit
d'approbation.

| # | Faille | Conséquence concrète |
|---|---|---|
| S1 | `report_status`, `mentoring_status`, `probation_status`, `workflow_status` modifiables par l'API (`fields = '__all__'` sans `read_only_fields`) | Un agent faisait passer **son propre rapport** à `APPROVED` par un simple `PATCH`. Contrôle de rôle, transition d'état et inscription au registre contournés |
| S2 | Écriture des rapports ouverte à tout compte authentifié (`IsAuthenticated`) | N'importe qui créait un rapport sur n'importe qui, et modifiait ou supprimait ceux le concernant. L'interface masquait le bouton : **la règle n'existait que dans le navigateur** |
| S3 | Journal d'audit ne masquant que les mots de passe | `POST /auth/logout/` transporte un refresh token : la table d'audit conservait des **jetons réutilisables**, lisibles par tout administrateur |
| S4 | `AUTH_PASSWORD_VALIDATORS` configurés mais jamais exécutés par l'API | `password123` et `12345678` acceptés à la création d'un compte comme au changement de mot de passe |
| S5 | Aucune limitation de débit sur `/auth/login/` | Force brute libre ; `LoginHistory` documentait l'attaque sans la gêner |
| S6 | Suppression d'une certification non contrôlée, alors que la modification l'était | Un chef d'unité effaçait la certification d'un agent sans pouvoir la corriger |
| S7 | `SECRET_KEY` de production avec repli public `django-insecure-…` | Signatures de session et de jetons forgeables |
| S8 | Pas de `.dockerignore`, `COPY . .`, conteneur exécuté en root | L'image embarquait `.env`, `db.sqlite3`, `venv/` et `.git/` |

### 2.2 Conception et correction

| # | Problème |
|---|---|
| C1 | `apps/training/qualification_maintenance.py` : **second modèle `QualificationMaintenance`**, 130 lignes jamais importées |
| C2 | `training.overdue` et `probation.evaluation-due` : la classe de permission autorisait les approbateurs, un contrôle écrit dans le corps de la vue leur renvoyait 403 — **deux règles contradictoires pour une même porte** |
| C3 | `except Exception: pass` dans `QualificationMaintenance.finalize()` et `_update_agent_status_after_probation()` — un contrôle pouvait passer à `FAILED` **sans que l'agent soit suspendu**, sans trace |
| C4 | `SoftDeleteMixin` importé par `training/views.py` sans être branché : un `DELETE` sur une spécialité effaçait réellement la ligne, et les profils qui la référençaient perdaient leur spécialité |
| C5 | `datetime.date.today()` avec `USE_TZ=True` et `TIME_ZONE='Africa/Dakar'` — échéances calculées sur l'horloge de l'hôte, pas sur celle du projet |
| C6 | `IsApproverOrUnitChief` et `IsEvaluatorOrInstructor` réécrites à la main en dupliquant le corps de la fabrique ; `IsReadOnly` redéfinissait `SAFE_METHODS` de DRF |
| C7 | 13 fichiers frontend réimplémentaient le même prédicat de rôle, avec des variantes de typage ; `detectRole` dupliqué entre le menu latéral et le tableau de bord |
| C8 | 17 imports morts, une vingtaine d'imports en milieu de fonction sans raison circulaire, `UserViewSet.destroy` recopiant `SoftDeleteMixin` |
| C9 | Dépendances déclarées inutilisées, commentaire à l'appui : `factory-boy`, `pytest-django`, `django-storages` |
| C10 | Incohérence de versions : Dockerfile sur Python 3.11, intégration continue sur 3.12 / 3.13 |

### 2.3 Performance

| # | Problème | Mesure |
|---|---|---|
| P1 | `get_active_roles()` filtrait en base, contournant le `prefetch_related` de la vue | `/auth/users/` : **23 requêtes pour 23 lignes** |
| P2 | Clé générique résolue ligne par ligne dans le registre d'approbation | `/workflows/` : **20 requêtes pour 12 lignes** |
| P3 | `UnitSerializer` cherchait le chef et comptait les agents par unité | 2 requêtes par unité |
| P4 | Jusqu'à 6 requêtes de rôles par appel (permission + cloisonnement + règle métier) | — |
| P5 | `django.db.backends` en DEBUG permanent | Suite de tests : **270 s** |
| P6 | `self.get_object()` dans `perform_update`, `qs.count()` après sérialisation | Requêtes en double |
| P7 | Valeur du contexte React reconstruite à chaque rendu | Tous les écrans se re-rendaient |

---

## 3. Corrections apportées

### 3.1 Sécurité

| Fichiers | Correction |
|---|---|
| `apps/{reports,mentoring,probation,workflows}/serializers.py` | Champs de statut, scores et avis passés en `read_only_fields`. Les transitions ne passent plus que par `submit` / `approve` / `reject` / `finalize`, qui portent déjà le rôle, l'état et le registre |
| `apps/reports/views.py` | Écriture réservée à `IsEvaluatorOrUnitChiefOrApprover` ; modification et suppression limitées au brouillon |
| `apps/audit/middleware.py` | `SENSITIVE_FIELDS` masque aussi `refresh`, `access`, `token`, `temp_password` ; extraction du corps isolée dans `_safe_body()` ; `except (json.JSONDecodeError, Exception)` remplacé par les exceptions réellement attendues |
| `apps/accounts/serializers.py` | `run_password_validators()` applique `AUTH_PASSWORD_VALIDATORS` à la création et au changement, avec l'identité de l'agent en contexte ; `save(update_fields=['password'])` |
| `core/throttling.py` *(nouveau)*, `config/settings/base.py` | `LoginRateThrottle` (10/min par IP) et `PasswordChangeRateThrottle` (5/min par compte), quotas configurables par variable d'environnement |
| `apps/agents/views.py` | `OwnRecordWriteMixin` : un seul contrôle de propriété, appliqué à la création, la modification **et** la suppression des trois ressources |
| `config/settings/production.py` | `SECRET_KEY` obligatoire ; ajout de `CSRF_TRUSTED_ORIGINS`, `SECURE_PROXY_SSL_HEADER`, `SESSION_COOKIE_HTTPONLY`, `SAMESITE`, `SECURE_REFERRER_POLICY`, `DEFAULT_FROM_EMAIL` |
| `.dockerignore` *(nouveau)*, `docker/Dockerfile` | Secrets et base locale exclus du contexte de build ; Python 3.12 ; utilisateur non-root (`uid 10001`) ; couche de dépendances séparée pour le cache |

### 3.2 Conception

- `core/permissions.py` réécrit : une seule fabrique, les classes composées en dérivent, `SAFE_METHODS` de DRF réutilisé.
- `apps/training/qualification_maintenance.py` **supprimé** (doublon mort).
- `overdue` / `evaluation-due` : contrôle inline retiré, la classe de permission fait foi — les approbateurs accèdent enfin aux écrans que la vue leur annonçait.
- `finalize()` et `_update_agent_status_after_probation()` : `except AgentProfile.DoesNotExist` nommé et journalisé ; `finalize()` passe en `transaction.atomic()` (le résultat et la suspension sont indissociables).
- `SoftDeleteMixin` branché sur `Specialty`, `Training` et `UserViewSet`.
- `timezone.localdate()` partout dans le code applicatif.
- `apps/workflows/admin.py` : fichier vide à l'en-tête trompeur, remplacé par la justification du choix.
- Frontend : `src/utils/roles.ts` *(nouveau)* — `isAdmin`, `hasAnyRole`, `hasRole`, `detectRole`. 13 fichiers allégés, chaque prédicat annoté de la permission serveur correspondante.

### 3.3 Performance

| Correction | Avant → après (mesuré sur le jeu de démonstration) |
|---|---|
| `_active_roles()` filtre en mémoire et respecte le prefetch | `/auth/users/` : **23 → 3** requêtes |
| `GenericPrefetch` (Django 5.0) sur le registre d'approbation | `/workflows/` : **20 → 5** |
| Annotation + `Prefetch(to_attr=…)` sur les unités | `/units/` : **3** requêtes pour 5 unités |
| Cache de rôles par instance (sur le modèle de `_perm_cache` de Django) | ≤ 1 requête de rôles par appel |
| `select_related('user')` sur les journaux d'audit | `/audit/logs/` : **2** |
| `LOG_SQL` optionnel + `config/settings/test.py` | Suite de tests : **270 s → 2,4 s** |
| `useMemo` sur la valeur du contexte d'authentification | Re-rendus globaux supprimés |

### 3.4 Outillage

`config/settings/test.py`, `.coveragerc`, cibles `make test` / `make coverage` / `make check`, et intégration
continue enrichie de `check --deploy --fail-level WARNING` et de la mesure de couverture. `.env.example`
complété (`USE_POSTGRES`, `LOG_SQL`, quotas, CORS / CSRF, courriel).

---

## 4. Architecture et qualité

L'architecture d'origine est saine et n'a pas été touchée : séparation `config` / `core` / `apps`, modèle `User`
personnalisé, permissions par rôle fonctionnel, registre d'approbation générique. Les corrections l'ont
**resserrée** plutôt que modifiée : une seule fabrique de permissions, un seul prédicat de propriété, un seul
prédicat de rôle par couche, et les règles métier regroupées derrière leurs actions dédiées.

---

## 5. Vérifications exécutées

| Vérification | Résultat |
|---|---|
| `manage.py check` | aucun problème |
| `makemigrations --check --dry-run` | aucune migration oubliée |
| Schéma OpenAPI `--fail-on-warn` | 0 erreur, 0 avertissement |
| `check --deploy --fail-level WARNING` | aucun problème |
| Tests backend | **254 passés** en 2,4 s |
| Couverture | **76 %** (`apps` + `core`) |
| `tsc -b`, `eslint`, `vitest`, `vite build` | typage et lint propres, **45 tests passés**, build OK |
| `seed_demo` | exécuté de bout en bout sur la base de développement |

Aucune régression : les 230 tests préexistants passent sans modification de leurs assertions.

Les corrections de sécurité et de performance sont verrouillées par des tests qui échouent sur le code
d'avant :

- `tests/test_securite.py` — 19 tests : contournements de workflow, habilitations, mots de passe, journal
  d'audit, quota de connexion.
- `tests/test_performance_requetes.py` — 6 tests : le coût d'une liste ne doit pas dépendre du nombre de lignes.

---

## 6. Points restants à arbitrer

| Sujet | Pourquoi il n'a pas été traité |
|---|---|
| **Jetons JWT en `localStorage`** | Exposés à une XSS. Corriger impose des cookies `httpOnly` côté serveur et un flux CSRF : changement d'architecture, à décider |
| **Changement de mot de passe sans révocation** | Les refresh tokens émis avant restent valides. Correction simple, mais elle déconnecte toutes les sessions : c'est un choix produit |
| **Quotas par processus** | Le cache local donne un compteur par worker gunicorn. Un cache partagé (Redis) est nécessaire pour une limite globale |
| **Journal d'audit sans purge** | `AuditLog` croît sans limite ; la rétention relève de la politique d'archivage ASECNA |
| **Pas de linter backend en CI** | Ajouter `ruff` est une dépendance nouvelle. Un contrôle AST ponctuel a été utilisé à la place |
| **5 composants React > 450 lignes** | `DashboardPage` (655), `AgentDetailPage` (603)… Découpage utile mais sans bug associé |
| **Couverture inégale** | `workflows/views` 55 %, `core/exceptions` 66 % |
| **`rollback-django42.txt`** | Fichier de versions figées qui dérivera ; conservé, c'est un plan de repli documenté |

---

## 7. Recommandations

1. **L'intégration continue est le garde-fou.** `check --deploy` et les tests de comptage de requêtes échouent
   dès qu'une régression apparaît. Ne pas les désactiver.
2. **Toute transition d'état passe par une action dédiée.** Un nouveau champ de statut se met en
   `read_only_fields` dès sa création.
3. **Chaque règle d'habilitation de l'interface doit exister côté serveur.** Les prédicats de
   `src/utils/roles.ts` citent désormais la classe de permission correspondante : garder ce lien.
4. **Un seul contrôle d'accès par porte** — une classe de permission, jamais doublée d'un contrôle inline qui
   finira par la contredire.
5. **Jamais d'`except Exception: pass`** : nommer l'exception attendue et journaliser le reste.
6. **Mesurer avant d'optimiser** : `CaptureQueriesContext` dans un test est plus parlant qu'un `select_related`
   posé au hasard.
7. **Avant mise en production** : `SECRET_KEY` générée, `ALLOWED_HOSTS` et `CORS_ALLOWED_ORIGINS` renseignés,
   cache partagé pour les quotas, politique de rétention de l'audit.
