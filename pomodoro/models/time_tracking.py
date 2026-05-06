"""Time tracking model for task sessions."""

from ..db import get_db
from time import time


def start_task_session(task_id, user_id):
    """Start a new time tracking session for a task."""
    db = get_db()
    
    # End any existing active sessions for this user
    db.execute(
        'UPDATE task_time_sessions SET ended_at = ?, duration_seconds = ? WHERE ended_at IS NULL AND user_id = ?',
        (int(time()), 0, user_id)
    )
    
    # Start new session
    cursor = db.execute(
        'INSERT INTO task_time_sessions (task_id, user_id, started_at) VALUES (?, ?, ?)',
        (task_id, user_id, int(time()))
    )
    db.commit()
    
    return cursor.lastrowid


def end_current_session(user_id):
    """End the current active time tracking session."""
    db = get_db()
    
    # Get current active session
    session = db.execute(
        'SELECT * FROM task_time_sessions WHERE ended_at IS NULL AND user_id = ?',
        (user_id,)
    ).fetchone()
    
    if session:
        end_time = int(time())
        duration = end_time - session['started_at']
        
        # Update session with end time and duration
        db.execute(
            'UPDATE task_time_sessions SET ended_at = ?, duration_seconds = ? WHERE id = ?',
            (end_time, duration, session['id'])
        )
        
        # Update task total time
        db.execute(
            'UPDATE tasks SET total_time_seconds = total_time_seconds + ? WHERE id = ?',
            (duration, session['task_id'])
        )
        db.commit()
        
        return duration
    
    return 0


def get_active_session(user_id):
    """Get the current active time tracking session."""
    db = get_db()
    return db.execute(
        'SELECT tts.*, t.content as task_content FROM task_time_sessions tts JOIN tasks t ON tts.task_id = t.id WHERE tts.ended_at IS NULL AND tts.user_id = ?',
        (user_id,)
    ).fetchone()


def get_task_time_summary(task_id, user_id):
    """Get total time spent on a task."""
    db = get_db()
    result = db.execute(
        'SELECT COALESCE(SUM(duration_seconds), 0) as total_seconds FROM task_time_sessions WHERE task_id = ? AND user_id = ?',
        (task_id, user_id)
    ).fetchone()
    return result['total_seconds'] if result else 0


def get_task_sessions(task_id, user_id, limit=10):
    """Get recent time sessions for a task."""
    db = get_db()
    return db.execute(
        'SELECT * FROM task_time_sessions WHERE task_id = ? AND user_id = ? ORDER BY started_at DESC LIMIT ?',
        (task_id, user_id, limit)
    ).fetchall()


def get_user_time_stats(user_id, days=7):
    """Get time tracking statistics for a user."""
    db = get_db()
    return db.execute(
        '''SELECT 
            COUNT(DISTINCT DATE(datetime(started_at, 'unixepoch')) as days_worked,
            SUM(duration_seconds) as total_seconds,
            COUNT(*) as total_sessions
         FROM task_time_sessions 
         WHERE user_id = ? AND started_at > ?''',
        (user_id, int(time() - (days * 24 * 60 * 60)))
    ).fetchone()
