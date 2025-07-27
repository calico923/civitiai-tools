#!/usr/bin/env python3
"""Apply database schema migration for extended schema."""

import sqlite3
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def apply_migration(db_path: str):
    """Apply the extended schema migration to existing database."""
    
    migration_file = Path("src/data/migrations/add_extended_schema.sql")
    db_path = Path(db_path)
    
    if not migration_file.exists():
        logger.error(f"Migration file not found: {migration_file}")
        return False
    
    if not db_path.exists():
        logger.error(f"Database file not found: {db_path}")
        return False
    
    # Read migration SQL
    with open(migration_file, 'r', encoding='utf-8') as f:
        migration_sql = f.read()
    
    # Split into individual statements
    statements = [stmt.strip() for stmt in migration_sql.split(';') if stmt.strip()]
    
    logger.info(f"Applying {len(statements)} migration statements to {db_path}")
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Execute each statement
        for i, statement in enumerate(statements, 1):
            try:
                logger.info(f"Executing statement {i}/{len(statements)}: {statement[:50]}...")
                cursor.execute(statement)
            except sqlite3.OperationalError as e:
                # Handle "already exists" errors gracefully
                if "already exists" in str(e) or "duplicate column name" in str(e):
                    logger.info(f"Statement {i} skipped (already exists): {e}")
                else:
                    logger.error(f"Error in statement {i}: {e}")
                    raise
        
        conn.commit()
        logger.info("Migration completed successfully!")
        
        # Verify tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        logger.info(f"Tables in database: {tables}")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    # Apply to main database
    success = apply_migration("data/civitai.db")
    if success:
        print("Schema migration applied successfully!")
    else:
        print("Migration failed!")