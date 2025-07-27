-- Extended schema for better data management
-- Created: 2025-07-27

-- 1. Add cleaned description to models table
ALTER TABLE models ADD COLUMN cleaned_description TEXT;

-- 2. Create tags table
CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 3. Create model_tags junction table
CREATE TABLE IF NOT EXISTS model_tags (
    model_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (model_id) REFERENCES models(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id),
    PRIMARY KEY (model_id, tag_id)
);

-- 4. Create model_versions table
CREATE TABLE IF NOT EXISTS model_versions (
    id INTEGER PRIMARY KEY,
    model_id INTEGER NOT NULL,
    name TEXT,
    base_model TEXT,
    download_url TEXT,
    file_size INTEGER,
    created_at TEXT,
    updated_at TEXT,
    stats TEXT, -- JSON for download counts etc
    raw_data TEXT, -- JSON for full version data
    FOREIGN KEY (model_id) REFERENCES models(id) ON DELETE CASCADE
);

-- 5. Create stats table for aggregated statistics
CREATE TABLE IF NOT EXISTS model_stats (
    model_id INTEGER PRIMARY KEY,
    download_count INTEGER DEFAULT 0,
    likes_count INTEGER DEFAULT 0,
    rating REAL DEFAULT 0,
    view_count INTEGER DEFAULT 0,
    comment_count INTEGER DEFAULT 0,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (model_id) REFERENCES models(id) ON DELETE CASCADE
);

-- 6. Indexes for performance
CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name);
CREATE INDEX IF NOT EXISTS idx_model_tags_model_id ON model_tags(model_id);
CREATE INDEX IF NOT EXISTS idx_model_tags_tag_id ON model_tags(tag_id);
CREATE INDEX IF NOT EXISTS idx_model_versions_model_id ON model_versions(model_id);
CREATE INDEX IF NOT EXISTS idx_model_versions_base_model ON model_versions(base_model);
CREATE INDEX IF NOT EXISTS idx_model_stats_download_count ON model_stats(download_count);
CREATE INDEX IF NOT EXISTS idx_model_stats_likes_count ON model_stats(likes_count);