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
