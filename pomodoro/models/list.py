from ..db import get_db

def get_active_list(user_id):
    db = get_db()
    return db.execute(
        'SELECT * FROM lists WHERE is_active = 1 AND user_id = ?',
        (user_id,)
    ).fetchone()

def get_all_lists(user_id):
    db = get_db()
    return db.execute(
        'SELECT * FROM lists WHERE user_id = ? ORDER BY name',
        (user_id,)
    ).fetchall()

def get_list_by_id(list_id, user_id):
    db = get_db()
    return db.execute(
        'SELECT * FROM lists WHERE id = ? AND user_id = ?',
        (list_id, user_id)
    ).fetchone()

def set_active_list(list_id, user_id):
    db = get_db()
    db.execute('UPDATE lists SET is_active = 0 WHERE user_id = ?', (user_id,))
    db.execute('UPDATE lists SET is_active = 1 WHERE id = ? AND user_id = ?', (list_id, user_id))
    db.commit()

def set_all_lists_inactive(user_id):
    db = get_db()
    db.execute('UPDATE lists SET is_active = 0 WHERE user_id = ?', (user_id,))

def create_list(user_id, name, description):
    db = get_db()
    db.execute(
        'INSERT INTO lists (user_id, name, description) VALUES (?, ?, ?)',
        (user_id, name, description)
    )
    db.commit()

def update_list(list_id, user_id, name, description):
    db = get_db()
    db.execute(
        'UPDATE lists SET name = ?, description = ? WHERE id = ? AND user_id = ?',
        (name, description, list_id, user_id)
    )
    db.commit()
