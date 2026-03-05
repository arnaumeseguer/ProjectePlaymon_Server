-- Migration: Add avatar column to users and create videos table

-- Add avatar column to users table if it doesn't exist
ALTER TABLE users
ADD COLUMN IF NOT EXISTS avatar TEXT;

-- Create videos table for storing multimedia content
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
CREATE INDEX IF NOT EXISTS idx_videos_user_id ON videos(user_id);

-- Create trigger for updated_at on videos (reuse existing function)
DROP TRIGGER IF EXISTS trg_videos_updated_at ON videos;
CREATE TRIGGER trg_videos_updated_at
BEFORE UPDATE ON videos
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();
