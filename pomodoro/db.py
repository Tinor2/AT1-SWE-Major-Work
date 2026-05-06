import sqlite3
import os
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
            
            # Subtasks for "Try editing this task" (level 1)
            ('💡 Double-click to edit', 'You can edit tasks inline by double-clicking them', 0, 2, 1),
            ('💾 Changes save automatically', 'Your edits are saved instantly to the database', 1, 2, 1),
            ('↩️ Press Enter or Escape', 'Use Enter to save, Escape to cancel editing', 2, 2, 1),
            
            # Subtasks for "Add tags to organize" (level 1)
            ('🔴 Red = Urgent', 'Use red tags for important, time-sensitive tasks', 0, 3, 1),
            ('🔵 Blue = Personal', 'Blue tags work great for personal activities', 1, 3, 1),
            ('🟢 Green = Health', 'Green tags perfect for exercise and wellness', 2, 3, 1),
            ('🟡 Yellow = Ideas', 'Yellow tags for creative thoughts and brainstorming', 3, 3, 1),
            ('🟣 Purple = Learning', 'Purple tags for study and skill development', 4, 3, 1),
            ('🟦 Teal = Work', 'Teal tags for professional tasks and projects', 5, 3, 1),
            
            # Subtasks for "Create subtasks" (level 1)
            ('➕ Add subtask button', 'Click the "+" button on any task to add subtasks', 0, 4, 1),
            ('📂 Collapse/expand', 'Click the arrow to hide or show subtasks', 1, 4, 1),
            ('🔄 Drag to reorder', 'Drag tasks to change their order and hierarchy', 2, 4, 1),
            ('📊 Track progress', 'See parent task progress based on subtask completion', 3, 4, 1),
            
            # Subtasks for "Start your first timer" (level 1)
            ('▶️ Press Start button', 'Click the green Start button to begin your session', 0, 5, 1),
            ('⏸️ Pause when needed', 'Need a break? Pause the timer anytime', 1, 5, 1),
            ('⏰ 25-minute sessions', 'Each work session is 25 minutes by default', 2, 5, 1),
            ('☕ Short breaks', 'Get 5-minute breaks between work sessions', 3, 5, 1),
            ('🛌 Long breaks', 'After 4 sessions, enjoy a 15-minute long break', 4, 5, 1),
            
            # Subtasks for "Create your own lists" (level 1)
            ('📱 Click Lists tab', 'Navigate to the Lists tab in the top navigation', 0, 6, 1),
            ('➕ Create new list', 'Click the "Create New List" button to get started', 1, 6, 1),
            ('📝 Name your list', 'Give your list a descriptive name (e.g., "Work Projects")', 2, 6, 1),
            ('📄 Add description', 'Optional: Add a description to remind yourself of the list purpose', 3, 6, 1),
            ('🎨 Customize timer', 'Set custom Pomodoro durations for different types of work', 4, 6, 1),
            
            # Subtasks for "Mark tasks complete" (level 1)
            ('☑️ Click checkboxes', 'Check the box to mark tasks as complete', 0, 7, 1),
            ('📈 Progress tracking', 'Completed subtasks update parent progress automatically', 1, 7, 1),
            ('🎉 Celebrate wins', 'Enjoy the satisfaction of completing tasks!', 2, 7, 1),
            ('🔧 Customize settings', 'Adjust timer durations in list settings', 3, 7, 1),
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