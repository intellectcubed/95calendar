CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS day_snapshots (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  day DATE NOT NULL,
  command TEXT,
  description TEXT,
  csv_data TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  expires_at TIMESTAMP DEFAULT NOW() + INTERVAL '30 days'
);

-- Optional: index for fast cleanup
CREATE INDEX IF NOT EXISTS idx_expires_at ON day_snapshots (expires_at);
