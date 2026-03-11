CREATE TABLE IF NOT EXISTS users (
  id           BIGSERIAL PRIMARY KEY,
  username     TEXT NOT NULL UNIQUE,
  name         TEXT NOT NULL,
  email        TEXT NOT NULL UNIQUE,
  role         TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('admin','support','user')),
  is_active    BOOLEAN NOT NULL DEFAULT TRUE,
  password_hash TEXT NOT NULL DEFAULT 'password',
  avatar       TEXT,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  pla_pagament TEXT NOT NULL DEFAULT 'basic' CHECK (pla_pagament IN ('basic', 'super', 'master'))
);

INSERT INTO users (name)
VALUES ('Arnau'), ('Eloi'), ('Miquel');
