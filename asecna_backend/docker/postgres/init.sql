"""
Script SQL PostgreSQL d'initialisation de la base de données ASECNA.
À exécuter après `createdb asecna_dev` et avant les migrations Django.

Extensions, index avancés et vue de synthèse dashboard.
"""

-- =============================================================================
-- Extensions
-- =============================================================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";   -- Recherche full-text optimisée

-- =============================================================================
-- Vue de synthèse — dashboard agent
-- =============================================================================
-- (Crée après les migrations Django)
-- CREATE OR REPLACE VIEW v_agent_summary AS
-- SELECT
--     u.id,
--     u.matricule,
--     u.first_name || ' ' || u.last_name AS full_name,
--     p.status              AS career_status,
--     un.code               AS unit_code,
--     un.name               AS unit_name,
--     s.name                AS specialty,
--     (SELECT COUNT(*) FROM evaluations_exam_session es
--      WHERE es.agent_id = u.id AND es.is_passed = true)  AS exams_passed,
--     (SELECT COUNT(*) FROM evaluations_exam_session es
--      WHERE es.agent_id = u.id AND es.is_passed = false) AS exams_failed
-- FROM accounts_user u
-- LEFT JOIN accounts_agent_profile p  ON p.user_id = u.id
-- LEFT JOIN units_unit un              ON un.id = p.unit_id
-- LEFT JOIN training_specialty s       ON s.id = p.specialty_id
-- WHERE u.is_active = true;

-- =============================================================================
-- Données de configuration initiales (spécialités ASECNA)
-- =============================================================================
-- Ces données sont aussi disponibles dans fixtures/initial_data.json

-- À exécuter manuellement si besoin avant les fixtures :
-- INSERT INTO training_specialty (code, name, description, is_active) VALUES
--   ('ATC',  'Contrôle de la circulation aérienne', 'Spécialité ATC', true),
--   ('MET',  'Météorologie aéronautique',            'Spécialité MET', true),
--   ('COM',  'Télécommunications aéronautiques',     'Spécialité COM', true),
--   ('ELEC', 'Électronique et maintenance',          'Spécialité ELEC', true),
--   ('INFO', 'Informatique aéronautique',            'Spécialité INFO', true);
