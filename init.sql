-- NOTE: "password_hash" aquí porta valors simples per proves (NO per producció).

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
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_users_updated_at ON users;
CREATE TRIGGER trg_users_updated_at
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

INSERT INTO users (id, username, name, email, role, is_active, password_hash)
VALUES
  (1, 'arnau',  'Arnau',  'arnau@playmon.local',  'admin',   TRUE, 'admin'),
  (2, 'eloi',   'Eloi',   'eloi@playmon.local',   'admin', TRUE, 'admin'),
  (3, 'miquel', 'Miquel', 'miquel@playmon.local', 'admin',    TRUE, 'admin'),
  (4, 'dummie01', 'Dummie', 'dummie@dummie.com', 'user', TRUE, 'password')

ON CONFLICT (id) DO NOTHING;


-- Videos table for multimedia content
CREATE TABLE IF NOT EXISTS videos (
  id           BIGSERIAL PRIMARY KEY,
  user_id      BIGINT NOT NULL,
  title        TEXT NOT NULL,
  description  TEXT,
  video_url    TEXT NOT NULL,
  thumbnail_url TEXT,
  duration     INTEGER,
  file_size    BIGINT,
  is_public    BOOLEAN NOT NULL DEFAULT FALSE,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT fk_videos_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create index on user_id for faster queries
CREATE INDEX idx_videos_user_id ON videos(user_id);

-- Create trigger for updated_at on videos
DROP TRIGGER IF EXISTS trg_videos_updated_at ON videos;
CREATE TRIGGER trg_videos_updated_at
BEFORE UPDATE ON videos
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();
