from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user

bp = Blueprint('tasks', __name__)


@bp.route('/task/<int:id>', methods=['GET'])
@login_required
def task_detail(id):
    from ..models.task import get_task_by_id
    task = get_task_by_id(id, current_user.id)

    if task is None:
        flash('Task not found or access denied.', 'error')
        return redirect(url_for('home.index'))

    return render_template('home/task_detail.html', task=task)

@bp.route('/task/add', methods=['POST'])
@login_required
def add_task():
    content = request.form.get('content', '').strip()

    if not content:
        flash('Task content cannot be empty.')
        return redirect(url_for('home.index'))

    from ..models.list import get_active_list
    from ..models.task import get_next_position
    active_list = get_active_list(current_user.id)

    if not active_list:
        flash('No active list selected.')
        return redirect(url_for('home.index'))

    max_position = get_next_position(active_list['id'], current_user.id)

    from ..db import get_db
    db = get_db()
    cursor = db.execute(
        'INSERT INTO tasks (list_id, user_id, content, position, parent_id, level, path) VALUES (?, ?, ?, ?, ?, ?, ?)',
        (active_list['id'], current_user.id, content, max_position + 1, None, 0, None)
    )
    new_task_id = cursor.lastrowid

    db.execute('UPDATE tasks SET path = ? WHERE id = ?', (str(new_task_id), new_task_id))
    db.commit()

    return redirect(url_for('home.index'))

@bp.route('/task/<int:id>/toggle', methods=['POST'])
@login_required
def toggle_task(id):
    from ..models.task import get_task_by_id
    task = get_task_by_id(id, current_user.id)

    if task:
        new_status = 0 if task['is_done'] else 1
        from ..db import get_db
        db = get_db()
        db.execute('UPDATE tasks SET is_done = ? WHERE id = ? AND user_id = ?', (new_status, id, current_user.id))
        db.commit()
    else:
        flash('Task not found or access denied.', 'error')

    return redirect(url_for('home.index'))

@bp.route('/task/<int:id>/delete', methods=['POST'])
@login_required
def delete_task(id):
    from ..models.task import get_task_by_id
    from ..db import get_db
    db = get_db()
    
    task = get_task_by_id(id, current_user.id)
    
    if not task:
        flash('Task not found or access denied.', 'error')
        return redirect(url_for('home.index'))
    
    result = db.execute('DELETE FROM tasks WHERE id = ? AND user_id = ?', (id, current_user.id))
    db.commit()

    if result.rowcount == 0:
        flash('Task not found or access denied.', 'error')

    return redirect(url_for('home.index'))

@bp.route('/task/<int:id>/tags', methods=['POST'])
@login_required
def update_tags(id):
    """Update tags for a task. Accepts comma-separated colors in 'tags' field."""
    from ..models.task import get_task_by_id
    
    # Check if task exists and user has access
    task = get_task_by_id(id, current_user.id)
    if not task:
        flash('Task not found or access denied.', 'error')
        return redirect(url_for('home.index'))
    
    tags = request.form.get('tags', '').strip()
    colors = [c.strip() for c in tags.split(',') if c.strip()]
    seen = set()
    normalized = []
    for c in colors:
        if c not in seen:
            normalized.append(c)
            seen.add(c)
    tags_value = ','.join(normalized)

    from ..db import get_db
    db = get_db()
    result = db.execute('UPDATE tasks SET tags = ? WHERE id = ? AND user_id = ?', (tags_value, id, current_user.id))
    db.commit()

    if result.rowcount == 0:
        flash('Task not found or access denied.', 'error')

    return redirect(url_for('home.index'))

@bp.route('/update-tags-ajax/<int:id>', methods=['POST'])
@login_required
def update_tags_ajax(id):
    """AJAX endpoint for real-time tag updates."""
    from ..models.task import get_task_by_id
    
    # Check if task exists and user has access
    task = get_task_by_id(id, current_user.id)
    if not task:
        return jsonify({'success': False, 'error': 'Task not found or access denied'})
    
    tags = request.form.get('tags', '').strip()

    colors = [c.strip() for c in tags.split(',') if c.strip()]
    seen = set()
    normalized = []
    for c in colors:
        if c not in seen:
            normalized.append(c)
            seen.add(c)
    tags_value = ','.join(normalized)

    from ..db import get_db
    db = get_db()
    result = db.execute('UPDATE tasks SET tags = ? WHERE id = ? AND user_id = ?', (tags_value, id, current_user.id))
    db.commit()

    if result.rowcount == 0:
        return jsonify({'success': False, 'error': 'Task not found or access denied'})

    return jsonify({'success': True, 'tags': tags_value})

@bp.route('/api/tags', methods=['GET', 'POST'])
@login_required
def manage_tags():
    """API endpoint for tag CRUD operations."""
    from ..db import get_db
    db = get_db()

    if request.method == 'GET':
        tags = db.execute(
            'SELECT * FROM user_tags WHERE user_id = ? ORDER BY position ASC, color_name ASC',
            (current_user.id,)
        ).fetchall()

        return jsonify({
            'success': True,
            'tags': [dict(tag) for tag in tags]
        })

    elif request.method == 'POST':
        color_hex = request.form.get('color_hex', '').strip()
        color_name = request.form.get('color_name', '').strip()

        if not color_hex:
            return jsonify({'success': False, 'error': 'Color is required'})

        try:
            max_position = db.execute(
                'SELECT MAX(position) FROM user_tags WHERE user_id = ?',
                (current_user.id,)
            ).fetchone()[0] or 0

            db.execute(
                'INSERT INTO user_tags (user_id, color_hex, color_name, position) VALUES (?, ?, ?, ?)',
                (current_user.id, color_hex, color_name or None, max_position + 1)
            )
            db.commit()

            return jsonify({'success': True, 'message': 'Tag added successfully'})

        except Exception as e:
            if 'UNIQUE constraint failed' in str(e):
                return jsonify({'success': False, 'error': 'Tag color already exists'})
            return jsonify({'success': False, 'error': 'Failed to add tag'})

@bp.route('/api/tags/<int:tag_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def manage_single_tag(tag_id):
    """API endpoint for individual tag operations."""
    from ..db import get_db
    db = get_db()

    tag = db.execute(
        'SELECT * FROM user_tags WHERE id = ? AND user_id = ?',
        (tag_id, current_user.id)
    ).fetchone()

    if not tag:
        return jsonify({'success': False, 'error': 'Tag not found'})

    if request.method == 'PUT':
        color_hex = request.form.get('color_hex', '').strip()
        color_name = request.form.get('color_name', '').strip()

        if not color_hex:
            return jsonify({'success': False, 'error': 'Color is required'})

        try:
            db.execute(
                'UPDATE user_tags SET color_hex = ?, color_name = ? WHERE id = ?',
                (color_hex, color_name or None, tag_id)
            )
            db.commit()

            return jsonify({'success': True, 'message': 'Tag updated successfully'})

        except Exception as e:
            if 'UNIQUE constraint failed' in str(e):
                return jsonify({'success': False, 'error': 'Tag color already exists'})
            return jsonify({'success': False, 'error': 'Failed to update tag'})

    elif request.method == 'DELETE':
        try:
            db.execute('DELETE FROM user_tags WHERE id = ?', (tag_id,))
            db.commit()

            return jsonify({'success': True, 'message': 'Tag deleted successfully'})

        except Exception as e:
            return jsonify({'success': False, 'error': 'Failed to delete tag'})

@bp.route('/task/reorder', methods=['POST'])
@login_required
def reorder_tasks():
    """Update task positions based on drag-and-drop."""
    if not request.is_json:
        return jsonify({'error': 'Invalid request format'}), 400

    data = request.get_json()
    task_order = data.get('task_order', [])
    list_id = data.get('list_id')

    if not task_order or not list_id:
        return jsonify({'error': 'Missing required data'}), 400

    try:
        task_order = [int(task_id) for task_id in task_order]
        list_id = int(list_id)
    except (ValueError, TypeError) as e:
        return jsonify({'error': 'Invalid data format'}), 400

    from ..db import get_db
    db = get_db()

    list_check = db.execute(
        'SELECT id FROM lists WHERE id = ? AND user_id = ?',
        (list_id, current_user.id)
    ).fetchone()

    if not list_check:
        return jsonify({'error': 'Unauthorized access'}), 403

    try:
        for index, task_id in enumerate(task_order):
            result = db.execute(
                'UPDATE tasks SET position = ? WHERE id = ? AND user_id = ? AND list_id = ?',
                (index, task_id, current_user.id, list_id)
            )
            if result.rowcount == 0:
                print(f"Warning: No rows updated for task_id={task_id}, index={index}")
                return jsonify({'error': f'Task {task_id} not found or access denied'}), 404

        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.rollback()
        print(f"Database error in reorder_tasks: {e}")
        return jsonify({'error': f'Database error: {str(e)}'}), 500

@bp.route('/task/update_hierarchy', methods=['POST'])
@login_required
def update_task_hierarchy():
    """Update task hierarchy (parent_id and position)."""
    if not request.is_json:
        return jsonify({'error': 'Invalid request format'}), 400

    data = request.get_json()
    task_id = data.get('task_id')
    new_parent_id = data.get('parent_id')
    position_after_id = data.get('position_after_id')
    list_id = data.get('list_id')

    if not task_id or list_id is None:
        return jsonify({'error': 'Missing required fields'}), 400

    from ..db import get_db
    db = get_db()

    task_check = db.execute(
        'SELECT id FROM tasks WHERE id = ? AND user_id = ?',
        (task_id, current_user.id)
    ).fetchone()

    if not task_check:
        return jsonify({'error': 'Task not found or unauthorized'}), 404

    list_check = db.execute(
        'SELECT id FROM lists WHERE id = ? AND user_id = ?',
        (list_id, current_user.id)
    ).fetchone()

    if not list_check:
        return jsonify({'error': 'Unauthorized access'}), 403

    try:
        if new_parent_id is None:
            new_level = 0
            new_path = str(task_id)
            db.execute(
                'UPDATE tasks SET parent_id = ?, level = ?, path = ? WHERE id = ? AND user_id = ?',
                (new_parent_id, new_level, new_path, task_id, current_user.id)
            )
            update_descendants_paths(task_id, new_path, new_level, db)
        else:
            new_parent = db.execute(
                'SELECT level, path FROM tasks WHERE id = ? AND user_id = ?',
                (new_parent_id, current_user.id)
            ).fetchone()

            if not new_parent:
                return jsonify({'error': 'Parent task not found or access denied'}), 403

            if is_descendant(new_parent_id, task_id, db):
                return jsonify({'error': 'Cannot create circular reference'}), 400

            new_level = new_parent['level'] + 1
            new_path = f"{new_parent['path']}/{task_id}"

            db.execute(
                'UPDATE tasks SET parent_id = ?, level = ?, path = ? WHERE id = ? AND user_id = ?',
                (new_parent_id, new_level, new_path, task_id, current_user.id)
            )
            update_descendants_paths(task_id, new_path, new_level, db)

        if position_after_id:
            after_task = db.execute(
                'SELECT position FROM tasks WHERE id = ? AND user_id = ? AND list_id = ?',
                (position_after_id, current_user.id, list_id)
            ).fetchone()

            if after_task:
                new_position = after_task['position'] + 1
                db.execute(
                    'UPDATE tasks SET position = position + 1 WHERE position > ? AND user_id = ? AND list_id = ?',
                    (after_task['position'], current_user.id, list_id)
                )

                db.execute(
                    'UPDATE tasks SET position = ? WHERE id = ? AND user_id = ?',
                    (new_position, task_id, current_user.id)
                )
        else:
            db.execute(
                'UPDATE tasks SET position = position + 1 WHERE user_id = ? AND list_id = ?',
                (current_user.id, list_id)
            )

            db.execute(
                'UPDATE tasks SET position = 0 WHERE id = ? AND user_id = ?',
                (task_id, current_user.id)
            )

        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.rollback()
        print(f"Database error in update_task_hierarchy: {e}")
        return jsonify({'error': f'Database error: {str(e)}'}), 500

@bp.route('/task/<int:id>/update', methods=['PUT'])
@login_required
def update_task(id):
    """Update task content via AJAX."""
    if not request.is_json:
        return jsonify({'error': 'Invalid request format'}), 400

    data = request.get_json()
    content = data.get('content', '').strip()

    if not content:
        return jsonify({'error': 'Task content cannot be empty'}), 400

    from ..models.task import get_task_by_id
    task = get_task_by_id(id, current_user.id)

    if not task:
        return jsonify({'error': 'Task not found or access denied'}), 404

    try:
        from ..db import get_db
        db = get_db()
        db.execute(
            'UPDATE tasks SET content = ? WHERE id = ? AND user_id = ?',
            (content, id, current_user.id)
        )
        db.commit()

        return jsonify({
            'success': True,
            'message': 'Task updated successfully',
            'content': content
        })

    except Exception as e:
        db.rollback()
        print(f"Database error in update_task: {e}")
        return jsonify({'error': 'Failed to update task'}), 500

@bp.route('/task/<int:parent_id>/subtask', methods=['POST'])
@login_required
def create_subtask(parent_id):
    """Create a new subtask under the specified parent task."""
    content = request.form.get('content', '').strip()

    if not content:
        flash('Subtask content cannot be empty.')
        return redirect(url_for('home.index'))

    from ..models.task import get_task_by_id
    from ..db import get_db
    db = get_db()
    parent_task = get_task_by_id(parent_id, current_user.id)

    if not parent_task:
        flash('Parent task not found or access denied.', 'error')
        return redirect(url_for('home.index'))

    max_position = db.execute(
        'SELECT COALESCE(MAX(position), -1) FROM tasks WHERE list_id = ? AND user_id = ? AND parent_id = ?',
        (parent_task['list_id'], current_user.id, parent_id)
    ).fetchone()[0]

    cursor = db.execute(
        'INSERT INTO tasks (list_id, user_id, content, position, parent_id, level, path) VALUES (?, ?, ?, ?, ?, ?, ?)',
        (parent_task['list_id'], current_user.id, content, max_position + 1, parent_id, parent_task['level'] + 1, None)
    )
    new_task_id = cursor.lastrowid

    new_path = f"{parent_task['path']}/{new_task_id}"
    db.execute('UPDATE tasks SET path = ? WHERE id = ?', (new_path, new_task_id))
    db.commit()

    return redirect(url_for('home.index'))

@bp.route('/task/<int:id>/move', methods=['POST'])
@login_required
def move_task(id):
    """Move a task to a new parent or reorder within the same level."""
    if not request.is_json:
        return jsonify({'error': 'Invalid request format'}), 400

    data = request.get_json()
    new_parent_id = data.get('new_parent_id')
    operation = data.get('operation', 'move')

    from ..models.task import get_task_by_id
    from ..db import get_db
    db = get_db()
    task = get_task_by_id(id, current_user.id)

    if not task:
        return jsonify({'error': 'Task not found or access denied'}), 403

    try:
        if operation == 'make_subtask' and new_parent_id:
            new_parent = db.execute(
                'SELECT * FROM tasks WHERE id = ? AND user_id = ?',
                (new_parent_id, current_user.id)
            ).fetchone()

            if not new_parent:
                return jsonify({'error': 'Parent task not found or access denied'}), 403

            if is_descendant(new_parent_id, id, db):
                return jsonify({'error': 'Cannot create circular reference'}), 400

            new_level = new_parent['level'] + 1
            new_path = f"{new_parent['path']}/{id}"

            db.execute(
                'UPDATE tasks SET parent_id = ?, level = ?, path = ? WHERE id = ?',
                (new_parent_id, new_level, new_path, id)
            )

            update_descendants_paths(id, new_path, new_level, db)

        elif operation == 'move_to_root':
            db.execute(
                'UPDATE tasks SET parent_id = NULL, level = 0, path = ? WHERE id = ?',
                (str(id), id)
            )

            update_descendants_paths(id, str(id), 0, db)

        db.commit()
        return jsonify({'success': True})

    except Exception as e:
        db.rollback()
        print(f"Database error in move_task: {e}")
        return jsonify({'error': f'Database error: {str(e)}'}), 500

@bp.route('/tasks/tree', methods=['GET'])
@login_required
def get_task_tree():
    """Get the hierarchical task structure for the active list."""
    from ..models.list import get_active_list
    active_list = get_active_list(current_user.id)

    if not active_list:
        return jsonify({'error': 'No active list'}), 404

    tasks = get_tasks_with_hierarchy(active_list['id'], current_user.id)
    return jsonify({'tasks': tasks})

def get_tasks_with_hierarchy(list_id, user_id):
    """Get tasks ordered hierarchically with proper nesting."""
    from ..db import get_db
    db = get_db()
    query = '''
    WITH RECURSIVE task_tree AS (
        SELECT id, content, is_done, tags, position, parent_id, level, path, created_at
        FROM tasks 
        WHERE list_id = ? AND user_id = ? AND parent_id IS NULL
        
        UNION ALL
        
        SELECT t.id, t.content, t.is_done, t.tags, t.position, 
               t.parent_id, t.level, t.path, t.created_at
        FROM tasks t
        JOIN task_tree tt ON t.parent_id = tt.id
        WHERE t.list_id = ? AND t.user_id = ?
    )
    SELECT * FROM task_tree ORDER BY 
        CASE WHEN parent_id IS NULL THEN position ELSE 999999 END,
        path,
        CASE WHEN parent_id IS NOT NULL THEN position ELSE 999999 END;
    '''
    return db.execute(query, (list_id, user_id, list_id, user_id)).fetchall()

def is_descendant(potential_ancestor_id, potential_descendant_id, db):
    """Check if potential_ancestor_id is a descendant of potential_descendant_id."""
    descendant = db.execute(
        'SELECT path FROM tasks WHERE id = ?',
        (potential_descendant_id,)
    ).fetchone()

    if not descendant:
        return False

    ancestor_path = str(potential_ancestor_id)
    descendant_path = descendant['path']

    return ancestor_path in descendant_path.split('/')

def update_descendants_paths(parent_id, new_parent_path, new_parent_level, db):
    """Recursively update paths and levels of all descendants."""
    descendants = db.execute(
        'SELECT id, level FROM tasks WHERE parent_id = ?',
        (parent_id,)
    ).fetchall()
    
    for descendant in descendants:
        new_path = f"{new_parent_path}/{descendant['id']}"
        new_level = new_parent_level + 1
        
        db.execute(
            'UPDATE tasks SET path = ?, level = ? WHERE id = ?',
            (new_path, new_level, descendant['id'])
        )
        
        update_descendants_paths(descendant['id'], new_path, new_level, db)

@bp.route('/task/<int:id>/time-summary', methods=['GET'])
@login_required
def task_time_summary(id):
    """Get time tracking summary for a task."""
    from ..models.time_tracking import get_task_sessions, get_task_time_summary
    from ..models.task import get_task_by_id
    
    task = get_task_by_id(id, current_user.id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    
    sessions = get_task_sessions(id, current_user.id)
    total_seconds = get_task_time_summary(id, current_user.id)
    
    return jsonify({
        'task_id': id,
        'total_seconds': total_seconds,
        'sessions': [dict(session) for session in sessions]
    })
