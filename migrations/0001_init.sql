-- ClipsFlow D1 schema. Tags are stored as a JSON array in a TEXT column;
-- tag filtering uses SQLite json_each() (see src/d1.ts).
CREATE TABLE IF NOT EXISTS clips (
  id               TEXT PRIMARY KEY,
  title            TEXT NOT NULL,
  file_path        TEXT NOT NULL,
  duration_seconds INTEGER NOT NULL,
  tags             TEXT NOT NULL DEFAULT '[]'
                     CHECK (json_valid(tags) AND json_type(tags) = 'array'),
  created_at       TEXT NOT NULL,
  updated_at       TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_clips_created_at ON clips (created_at);
