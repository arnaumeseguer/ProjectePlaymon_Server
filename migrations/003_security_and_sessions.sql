-- Migration: Security & session tracking
-- Adds: extra user fields (telefon, idioma, password_changed_at, 2FA, alerts, recovery)
--       login_history table
--       active_sessions table

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. Extend users table
-- ─────────────────────────────────────────────────────────────────────────────
ALTER TABLE users
  ADD COLUMN IF NOT EXISTS telefon              TEXT,
  ADD COLUMN IF NOT EXISTS idioma               TEXT,
  ADD COLUMN IF NOT EXISTS password_changed_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  ADD COLUMN IF NOT EXISTS two_factor_enabled   BOOLEAN     NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS two_factor_secret    TEXT,
  ADD COLUMN IF NOT EXISTS login_alerts_enabled BOOLEAN     NOT NULL DEFAULT TRUE,
  ADD COLUMN IF NOT EXISTS recovery_email       TEXT,
  ADD COLUMN IF NOT EXISTS recovery_phone       TEXT;

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. login_history table
--    Append-only log of every login attempt (success or failure)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS login_history (
  id           BIGSERIAL PRIMARY KEY,
  user_id      BIGINT NOT NULL,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  ip_address   TEXT,
  user_agent   TEXT,
  success      BOOLEAN NOT NULL DEFAULT TRUE,
  country      TEXT,
  CONSTRAINT fk_login_history_user_id
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_login_history_user_id
  ON login_history (user_id, created_at DESC);

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. active_sessions table
--    One row per issued JWT (jti). Revocation via revoked_at timestamp.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS active_sessions (
  id           BIGSERIAL PRIMARY KEY,
  user_id      BIGINT NOT NULL,
  jti          TEXT NOT NULL UNIQUE,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_seen    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  ip_address   TEXT,
  user_agent   TEXT,
  revoked_at   TIMESTAMPTZ,
  CONSTRAINT fk_active_sessions_user_id
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_active_sessions_user_active
  ON active_sessions (user_id)
  WHERE revoked_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_active_sessions_jti
  ON active_sessions (jti);
