import random
import sqlite3
import os
import time as time_module
from datetime import datetime
import click
from flask import current_app, g
from flask.cli import with_appcontext

# Custom timestamp adapters for SQLite
def adapt_datetime_iso(val):
    """Adapt datetime object to ISO format string."""
    return val.isoformat()

def convert_datetime(val):
    """Convert ISO format string to datetime object."""
    if isinstance(val, bytes):
        val = val.decode('utf-8')
    if isinstance(val, str):
        try:
            # Handle ISO format with timezone
            if 'T' in val:
                return datetime.fromisoformat(val.replace('Z', '+00:00'))
            else:
                # Handle other formats
                return datetime.fromisoformat(val)
        except (ValueError, AttributeError):
            # Fallback to current time if parsing fails
            return datetime.now()
    return val

# Register the adapters
sqlite3.register_adapter(datetime, adapt_datetime_iso)
sqlite3.register_converter("TIMESTAMP", convert_datetime)

def get_db():
    """Get database connection."""
    if 'db' not in g:
        # Ensure the instance folder exists
        os.makedirs(current_app.instance_path, exist_ok=True)
        
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        g.db.row_factory = sqlite3.Row
        
        # Fix timestamp handling for newer SQLite versions
        g.db.execute("PRAGMA busy_timeout = 30000")

        from .migrations import run_pending_migrations
        run_pending_migrations(g.db)

    return g.db

def close_db(e=None):
    """Close database connection."""
    db = g.pop('db', None)

    if db is not None:
        db.close()

def init_db():
    """Initialize the database with schema."""
    # Ensure the instance folder exists
    os.makedirs(current_app.instance_path, exist_ok=True)

    # Create a fresh connection for initialization (before get_db() runs migrations)
    db = sqlite3.connect(
        current_app.config['DATABASE'],
        detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
    )
    db.row_factory = sqlite3.Row

    # Get the path to the schema file in the project root
    schema_path = os.path.join(current_app.root_path, '..', 'schema.sql')

    with open(schema_path, 'r') as f:
        db.executescript(f.read())

    db.commit()

    # Mark all existing migrations as applied since schema.sql has all the latest columns
    from .migrations import mark_all_migrations_applied
    mark_all_migrations_applied(db)

    db.close()

@click.command('migrate-user-data')
@with_appcontext
def migrate_user_data_command():
    """Migrate existing lists and tasks to user accounts or clear if no users exist."""
    database = get_db()
    
    # Check if there are any users
    users = database.execute("SELECT id FROM users LIMIT 1").fetchall()
    
    if not users:
        # No users exist, clear all data
        click.echo('No users found. Clearing all lists and tasks...')
        database.execute("DELETE FROM tasks")
        database.execute("DELETE FROM lists")
        database.commit()
        click.echo('Cleared all lists and tasks.')
    else:
        # Get the first user ID
        first_user_id = users[0]['id']
        
        # Update existing lists to belong to the first user
        lists_updated = database.execute(
            "UPDATE lists SET user_id = ? WHERE user_id IS NULL",
            (first_user_id,)
        ).rowcount
        
        # Update existing tasks to belong to the first user
        tasks_updated = database.execute(
            "UPDATE tasks SET user_id = ? WHERE user_id IS NULL",
            (first_user_id,)
        ).rowcount
        
        database.commit()
        click.echo(f'Migrated {lists_updated} lists and {tasks_updated} tasks to user {first_user_id}.')
    
    # Run any pending migrations
    from .migrations import run_pending_migrations
    run_pending_migrations(database)
    click.echo('Database migration completed.')

@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo('Initialized the database.')

@click.command('seed-data')
@with_appcontext
def seed_data_command():
    """Seed default data for users who don't have any lists."""
    database = get_db()
    
    # Get users who don't have any lists
    users_without_lists = database.execute("""
        SELECT u.id, u.username 
        FROM users u 
        LEFT JOIN lists l ON u.id = l.user_id 
        WHERE l.id IS NULL
    """).fetchall()
    
    if not users_without_lists:
        click.echo('All users already have data. No seeding needed.')
        return
    
    for user in users_without_lists:
        try:
            seed_default_data(user['id'])
            click.echo(f'Seeded default data for user: {user["username"]}')
        except Exception as e:
            click.echo(f'Failed to seed data for user {user["username"]}: {e}')
    
    click.echo(f'Seeded data for {len(users_without_lists)} users.')

@click.command('reset-tutorial')
@with_appcontext  
def reset_tutorial_command():
    """Reset tutorial list for all users (removes existing tutorial list and creates new one)."""
    database = get_db()
    
    # Get all users
    users = database.execute('SELECT id, username FROM users').fetchall()
    
    for user in users:
        try:
            # Remove existing tutorial list if it exists
            cursor = database.execute('DELETE FROM lists WHERE user_id = ? AND name LIKE ?', 
                                    (user['id'], '%Tutorial%'))
            
            # Seed new tutorial
            seed_default_data(user['id'])
            click.echo(f'Reset tutorial for user: {user["username"]}')
            
        except Exception as e:
            click.echo(f'Failed to reset tutorial for user {user["username"]}: {e}')
    
    click.echo(f'Reset tutorial for {len(users)} users.')

def init_app(app):
    """Register database functions with the Flask app."""
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(migrate_user_data_command)
    app.cli.add_command(seed_data_command)
    app.cli.add_command(reset_tutorial_command)

def seed_default_data(user_id):
    """Seed default list and tasks for a new user."""
    database = get_db()
    
    try:
        # Create default list
        cursor = database.execute(
            'INSERT INTO lists (user_id, name, description, is_active) VALUES (?, ?, ?, ?)',
            (user_id, '🎓 Tutorial: Learn the Basics', 'Follow these tasks to learn how to use all features of the Pomodoro Timer!', 1)
        )
        list_id = cursor.lastrowid
        
        # Tutorial tasks with hierarchical structure
        default_tasks = [
            # Main tutorial tasks (level 0)
            ('👋 Welcome!', 'Start here to learn the basics of your new Pomodoro Timer app', 0, None, 0),
            ('✏️ Try editing this task', 'Click the edit button to change task content - try it now!', 1, None, 0),
            ('🏷️ Add tags to organize', 'Click the tag buttons below to color-code your tasks', 2, None, 0),
            ('📋 Create subtasks', 'Learn to break down big tasks into smaller steps', 3, None, 0),
            ('⏱️ Start your first timer', 'Ready to focus? Start your first 25-minute Pomodoro session', 4, None, 0),
            ('📁 Create your own lists', 'Go to the Lists tab to organize different projects and categories', 5, None, 0),
            ('🎯 Mark tasks complete', 'Click the checkbox when you finish a task', 6, None, 0),
            ('📊 View your stats', 'Check out the Statistics tab to see your productivity patterns', 7, None, 0),
            ('💡 Pro tip: Use breaks wisely!', 'Remember to take short breaks to recharge and long breaks after 4 sessions', 8, None, 0),
            ('🚀 You\'re all set!', 'Now that you know the basics, start adding your own tasks and lists to boost your productivity!', 9, None, 0),
        ]
        
        # Insert tasks with hierarchical structure
        for i, (content, description, position, parent_id, level) in enumerate(default_tasks):
            cursor = database.execute(
                'INSERT INTO tasks (list_id, user_id, content, position, parent_id, level, path) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (list_id, user_id, content, position, parent_id, level, str(i + 1) if parent_id is None else f"{parent_id}.{i + 1}")
            )
            
            # Update path for root-level tasks
            if parent_id is None:
                task_id = cursor.lastrowid
                database.execute('UPDATE tasks SET path = ? WHERE id = ?', (str(task_id), task_id))
        
        # Create default user tags
        default_tags = [
            ('#FF6B6B', 'Red', 0),    # Urgent/Important
            ('#4ECDC4', 'Teal', 1),   # Work
            ('#45B7D1', 'Blue', 2),   # Personal
            ('#96CEB4', 'Green', 3),  # Health
            ('#FFEAA7', 'Yellow', 4), # Ideas
            ('#DDA0DD', 'Purple', 5), # Learning
        ]
        
        for color_hex, color_name, position in default_tags:
            database.execute(
                'INSERT INTO user_tags (user_id, color_hex, color_name, position) VALUES (?, ?, ?, ?)',
                (user_id, color_hex, color_name, position)
            )
        
        database.commit()
        print(f"Seeded default data for user {user_id}: 1 list, {len(default_tasks)} tasks, {len(default_tags)} tags")

    except sqlite3.Error as e:
        print(f"Error seeding data for user {user_id}: {e}")
        database.rollback()
        raise


def seed_analytics_data(user_id, db):
    """Seed realistic task_time_sessions and user_statistics for a new user,
    based on a real average-good user profile extracted from production data."""

    already = db.execute(
        "SELECT 1 FROM user_statistics WHERE user_id = ? LIMIT 1", (user_id,)
    ).fetchone()
    if already:
        return

    rng = random.Random(user_id)
    now = int(time_module.time())
    DAY = 86400

    # ── 1. Create 2 non-tutorial lists ──
    list_specs = [
        ("University Project", "Coursework and assignments", 25, 5, 15),
        ("Personal Development", "Learning and wellness", 30, 7, 20),
    ]
    list_ids = []
    for name, desc, session_dur, short_br, long_br in list_specs:
        c = db.execute(
            "INSERT INTO lists (user_id, name, description, is_active, pomo_session, pomo_short_break, pomo_long_break) VALUES (?,?,?,?,?,?,?)",
            (user_id, name, desc, 0, session_dur, short_br, long_br),
        )
        list_ids.append(c.lastrowid)

    # ── 2. Create 14 realistic tasks ──
    task_specs = [
        (0, "Research paper outline",     "Draft the initial outline for the term paper"),
        (0, "Literature review",          "Read and summarize 5 academic sources"),
        (0, "Draft introduction",         "Write the introduction section"),
        (0, "Methodology section",        "Describe the research methodology used"),
        (0, "Data analysis",              "Process the collected dataset"),
        (0, "Final edits",                "Review and polish the entire paper"),
        (0, "References formatting",      "Format all citations in APA style"),
        (0, "Lab report",                 "Complete the weekly lab report"),
        (1, "Morning workout",            "30-minute exercise routine"),
        (1, "Read chapter 5",            "Continue reading the textbook"),
        (1, "Practice coding",            "Work on the side project"),
        (1, "Journal entry",              "Write daily reflections"),
        (1, "Plan meals",                 "Plan meals for the week"),
        (1, "Watch tutorial",             "Complete the online course module"),
    ]
    task_ids = []
    for i, (li, content, desc) in enumerate(task_specs):
        lid = list_ids[li]
        c = db.execute(
            "INSERT INTO tasks (list_id, user_id, content, position, is_done, level) VALUES (?,?,?,?,0,0)",
            (lid, user_id, content, i + 1),
        )
        task_ids.append(c.lastrowid)

    # ── 3. Generate session schedule (deterministic per user) ──

    # Duration buckets (seconds) — mirroring sample distribution
    SHORT =   [60, 120, 180, 300, 420, 540]         # 1-9 min     (48%)
    MEDIUM =  [600, 720, 900, 1080, 1500, 1800]      # 10-30 min   (32%)
    LONG =    [2100, 2700, 3600, 5400, 7200]          # 35-120 min  (20%)

    # Gap buckets (seconds)
    QUICK_GAP =    [60, 120, 180, 300, 600]                # 1-10 min    (55%)
    NORMAL_GAP =   [600, 900, 1200, 1800]                   # 10-30 min   (15%)
    EXTENDED_GAP = [1800, 2400, 3600]                       # 30-60 min   (10%)
    LONG_GAP =     [3600, 5400, 7200, 9000, 14400]          # 1-4 hours   (20%)

    # Day profiles: (days_ago, num_sessions, base_hour_utc)
    # Trainer requires >=10 daily feature rows to avoid synthetic fallback.
    # Balanced distribution keeps consistency_score high enough for "Average" band.
    day_profiles = [
        (17, 4, 8),   # Tue morning
        (15, 3, 14),  # Thu afternoon
        (14, 2, 10),  # Fri late morning
        (12, 5, 7),   # Sun morning (most active)
        (11, 3, 15),  # Mon afternoon
        (9,  4, 9),   # Wed late morning
        (7,  3, 6),   # Fri early
        (6,  2, 11),  # Sat late morning
        (5,  2, 16),  # Sun afternoon
        (4,  4, 7),   # Mon morning
        (2,  3, 10),  # Wed late morning
        (0,  4, 8),   # Fri morning (today)
    ]

    schedule = []
    task_idx = 0
    for days_ago, n_sessions, base_hour in day_profiles:
        day_start = now - days_ago * DAY + base_hour * 3600
        cur = day_start

        for _ in range(n_sessions):
            roll = rng.random()
            if roll < 0.48:
                dur = rng.choice(SHORT)
            elif roll < 0.80:
                dur = rng.choice(MEDIUM)
            else:
                dur = rng.choice(LONG)

            tid = task_ids[task_idx % len(task_ids)]
            task_idx += 1

            gap = None
            break_ok = None
            if _ < n_sessions - 1:
                gap_roll = rng.random()
                if gap_roll < 0.55:
                    gap = rng.choice(QUICK_GAP)
                elif gap_roll < 0.70:
                    gap = rng.choice(NORMAL_GAP)
                elif gap_roll < 0.80:
                    gap = rng.choice(EXTENDED_GAP)
                else:
                    gap = rng.choice(LONG_GAP)
                break_ok = rng.random() < 0.68   # 68% break completion rate

            schedule.append((tid, cur, dur, gap, break_ok))
            cur += dur
            if gap is not None:
                cur += gap

    # ── 4. Insert task_time_sessions + compute per-task totals ──
    task_totals = {tid: 0 for tid in task_ids}
    task_first_ts = {}
    task_last_ts = {}

    for tid, started_at, dur, _, _ in schedule:
        ended_at = started_at + dur
        db.execute(
            "INSERT INTO task_time_sessions (task_id, user_id, started_at, ended_at, duration_seconds) VALUES (?,?,?,?,?)",
            (tid, user_id, started_at, ended_at, dur),
        )
        task_totals[tid] = task_totals.get(tid, 0) + dur
        if tid not in task_first_ts or started_at < task_first_ts[tid]:
            task_first_ts[tid] = started_at
        if tid not in task_last_ts or ended_at > task_last_ts[tid]:
            task_last_ts[tid] = ended_at

    # ── 5. Insert user_statistics events ──
    set_counter = 0
    for tid, started_at, dur, gap, break_ok in schedule:
        # session_start
        set_counter += 1
        db.execute(
            "INSERT INTO user_statistics (user_id, event_type, timestamp, duration_seconds, task_id, sessions_completed_in_set) VALUES (?,?,?,?,?,?)",
            (user_id, "session_start", started_at, 0, tid, set_counter),
        )

        # session_end
        ended_at = started_at + dur
        if set_counter >= 4:
            set_counter = 0  # reset sets after 4
        db.execute(
            "INSERT INTO user_statistics (user_id, event_type, timestamp, duration_seconds, task_id, sessions_completed_in_set) VALUES (?,?,?,?,?,?)",
            (user_id, "session_end", ended_at, dur, tid, set_counter or 4),
        )

        # gap → break event
        if gap is not None:
            break_type = "short_break" if gap <= 1800 else "long_break"
            event = "break_completion" if break_ok else "break_skip"
            db.execute(
                "INSERT INTO user_statistics (user_id, event_type, timestamp, duration_seconds, break_type) VALUES (?,?,?,?,?)",
                (user_id, event, ended_at + 1, gap, break_type),
            )

    # task_creation events (1 hour before first session on that task)
    for i, (_, content, _) in enumerate(task_specs):
        tid = task_ids[i]
        first_ts = task_first_ts.get(tid, now)
        db.execute(
            "INSERT INTO user_statistics (user_id, event_type, timestamp, task_id, task_content) VALUES (?,?,?,?,?)",
            (user_id, "task_creation", first_ts - 3600, tid, content),
        )

    # task_completion events for ~57% of tasks (first 8)
    completed = task_ids[:8]
    for tid in completed:
        last_ts = task_last_ts.get(tid)
        if last_ts:
            db.execute(
                "INSERT INTO user_statistics (user_id, event_type, timestamp, task_id, task_completion_time_seconds) VALUES (?,?,?,?,?)",
                (user_id, "task_completion", last_ts, tid, task_totals[tid]),
            )

    break_counts: dict[int, dict[str, int]] = {tid: {"full": 0, "skipped": 0} for tid in task_ids}
    for tid, _, _, gap, break_ok in schedule:
        if gap is not None:
            if break_ok:
                break_counts[tid]["full"] += 1
            else:
                break_counts[tid]["skipped"] += 1

    # ── 6. Update tasks with total_time_seconds, completion flags, and break counts ──
    for tid in task_ids:
        db.execute("UPDATE tasks SET total_time_seconds = ? WHERE id = ?", (task_totals[tid], tid))
        bc = break_counts[tid]
        db.execute(
            "UPDATE tasks SET number_of_full_breaks = ?, number_of_skipped_breaks = ? WHERE id = ?",
            (bc["full"], bc["skipped"], tid),
        )
    for tid in completed:
        db.execute("UPDATE tasks SET is_done = 1 WHERE id = ?", (tid,))

    db.commit()

    event_count = len(schedule) * 2 + sum(1 for _, _, _, g, _ in schedule if g is not None) + len(task_ids) + len(completed)
    print(f"Seeded analytics for user {user_id}: {len(schedule)} sessions, {len(task_ids)} tasks, ~{event_count} events")