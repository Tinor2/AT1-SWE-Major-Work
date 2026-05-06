from ..db import get_db

def get_tasks_for_list(list_id, user_id):
    db = get_db()
    return db.execute(
        '''SELECT * FROM tasks WHERE list_id = ? AND user_id = ?
           ORDER BY level ASC, position ASC''',
        (list_id, user_id)
    ).fetchall()

def get_task_by_id(task_id, user_id):
    db = get_db()
    return db.execute(
        'SELECT * FROM tasks WHERE id = ? AND user_id = ?',
        (task_id, user_id)
    ).fetchone()

def get_next_position(list_id, user_id, parent_id=None):
    db = get_db()
    result = db.execute(
        'SELECT COALESCE(MAX(position), -1) FROM tasks WHERE list_id = ? AND user_id = ? AND parent_id IS ?',
        (list_id, user_id, parent_id)
    ).fetchone()
    return result[0] + 1

def get_tasks_with_time(list_id, user_id):
    """Get tasks with their total time included."""
    db = get_db()
    return db.execute(
        '''SELECT t.*, COALESCE(tts.total_time, 0) as total_time_seconds
           FROM tasks t 
           LEFT JOIN (
               SELECT task_id, SUM(duration_seconds) as total_time 
               FROM task_time_sessions 
               WHERE user_id = ? 
               GROUP BY task_id
           ) tts ON t.id = tts.task_id
           WHERE t.list_id = ? AND t.user_id = ?
           ORDER BY t.level ASC, t.position ASC''',
        (user_id, list_id, user_id)
    ).fetchall()

def update_task_total_time(task_id, user_id):
    """Recalculate and update total time for a task."""
    from .time_tracking import get_task_time_summary
    db = get_db()
    total_time = get_task_time_summary(task_id, user_id)
    db.execute(
        'UPDATE tasks SET total_time_seconds = ? WHERE id = ? AND user_id = ?',
        (total_time, task_id, user_id)
    )
    db.commit()
