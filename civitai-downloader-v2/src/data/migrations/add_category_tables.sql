-- カテゴリマスタテーブル（第三正規形に従った設計）
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 999,  -- 優先順位（小さいほど優先）
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- カテゴリの初期データ（優先順位順）
INSERT OR IGNORE INTO categories (name, display_name, priority) VALUES
    ('character', 'Character', 1),
    ('style', 'Style', 2),
    ('concept', 'Concept', 3),
    ('clothing', 'Clothing', 4),
    ('background', 'Background', 5),
    ('tool', 'Tool', 6),
    ('building', 'Building', 7),
    ('vehicle', 'Vehicle', 8),
    ('object', 'Object', 9),
    ('animal', 'Animal', 10),
    ('body', 'Body', 11),
    ('outfit', 'Outfit', 12),
    ('base', 'Base', 13),
    ('action', 'Action', 14),
    ('workflow', 'Workflow', 15),
    ('wildcards', 'Wildcards', 16),
    ('other', 'Other', 999);

-- モデル-カテゴリ中間テーブル
CREATE TABLE IF NOT EXISTS model_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    is_primary BOOLEAN DEFAULT FALSE,  -- 主カテゴリフラグ
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (model_id) REFERENCES models(id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories(id),
    UNIQUE(model_id, category_id)
);

-- 主カテゴリの一意性を保証するインデックス
CREATE UNIQUE INDEX idx_model_primary_category 
ON model_categories(model_id) 
WHERE is_primary = TRUE;

-- パフォーマンス用インデックス
CREATE INDEX idx_model_categories_model_id ON model_categories(model_id);
CREATE INDEX idx_model_categories_category_id ON model_categories(category_id);
CREATE INDEX idx_categories_priority ON categories(priority);

-- ビュー：モデルと主カテゴリの結合
CREATE VIEW IF NOT EXISTS v_models_with_primary_category AS
SELECT 
    m.*,
    c.name as primary_category,
    c.display_name as primary_category_display,
    c.priority as primary_category_priority
FROM models m
LEFT JOIN model_categories mc ON m.id = mc.model_id AND mc.is_primary = TRUE
LEFT JOIN categories c ON mc.category_id = c.id;

-- ビュー：モデルの全カテゴリリスト
CREATE VIEW IF NOT EXISTS v_model_all_categories AS
SELECT 
    m.id as model_id,
    m.name as model_name,
    GROUP_CONCAT(c.name, ';') as categories,
    GROUP_CONCAT(CASE WHEN mc.is_primary THEN c.name ELSE NULL END) as primary_category
FROM models m
LEFT JOIN model_categories mc ON m.id = mc.model_id
LEFT JOIN categories c ON mc.category_id = c.id
GROUP BY m.id;