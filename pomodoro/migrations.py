# pomodoro/migrations.py
import os
import sqlite3

MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), '..', 'migrations')

def _ensure_migrations_table(db: sqlite3.Connection):
    """Create the schema_migrations tracking table if it doesn't exist."""
    db.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            filename TEXT PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db.commit()

def run_pending_migrations(db: sqlite3.Connection):
    """Apply any migration SQL files that have not been run yet."""
    _ensure_migrations_table(db)

    applied = {row[0] for row in db.execute("SELECT filename FROM schema_migrations")}

    migration_files = sorted(
        f for f in os.listdir(MIGRATIONS_DIR)
        if f.endswith('.sql') and f not in applied
    )

    for filename in migration_files:
        path = os.path.join(MIGRATIONS_DIR, filename)
        with open(path) as f:
            sql = f.read()
        try:
            db.executescript(sql)
            db.execute("INSERT INTO schema_migrations (filename) VALUES (?)", (filename,))
            db.commit()
            print(f"Applied migration: {filename}")
        except sqlite3.Error as e:
            print(f"Migration failed ({filename}): {e}")
            raise

def mark_all_migrations_applied(db: sqlite3.Connection):
    """Mark all existing migration files as applied (for fresh database initialization)."""
    _ensure_migrations_table(db)

    migration_files = sorted(
        f for f in os.listdir(MIGRATIONS_DIR)
        if f.endswith('.sql')
    )

    for filename in migration_files:
        # Insert or ignore if already exists
        db.execute(
            "INSERT OR IGNORE INTO schema_migrations (filename) VALUES (?)",
            (filename,)
        )

    db.commit()
    print(f"Marked {len(migration_files)} migrations as applied for fresh database")
