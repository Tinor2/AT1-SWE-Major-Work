from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
import time

bp = Blueprint('lists', __name__, url_prefix='/lists')


# Security (SAST — bandit, flake8 run 2026-06-15):
#   - B608: f-string SQL construction with dynamic column names was flagged by
#     bandit. Fixed by whitelisting known-good column names via _ALLOWED_COLS
#     before building the INSERT statement.
#   - F841: unused local variables (except-as-e) removed per flake8.
#   - F401: unused imports (update_list) removed per flake8.
_ALLOWED_COLS = frozenset({
    "duration_seconds", "task_id", "sessions_completed_in_set",
    "break_type", "task_content", "task_completion_time_seconds",
})


def _log_event(db, user_id, event_type, **kwargs):
    """Insert one row into user_statistics. kwargs map to column names."""
    safe_kwargs = {k: v for k, v in kwargs.items() if k in _ALLOWED_COLS}
    cols = ["user_id", "event_type", "timestamp"] + list(safe_kwargs.keys())
    vals = [user_id, event_type, int(time.time())] + list(safe_kwargs.values())
    placeholders = ",".join("?" * len(cols))
    db.execute(
        f"INSERT INTO user_statistics ({','.join(cols)}) VALUES ({placeholders})",  # nosec - cols whitelist-filtered via _ALLOWED_COLS above
        vals
    )
    db.commit()


@bp.route('/')
@login_required
def index():
    from ..models.list import get_all_lists
    lists = get_all_lists(current_user.id)
    return render_template('lists/index.html', lists=lists)

@bp.route('/<int:id>', methods=('GET',))
@login_required
def detail(id):
    from ..models.list import get_list_by_id
    from ..db import get_db
    db = get_db()
    
    list_row = get_list_by_id(id, current_user.id)

    if list_row is None:
        flash('List not found or access denied.', 'error')
        return redirect(url_for('lists.index'))

    tasks = db.execute(
        'SELECT * FROM tasks WHERE list_id = ? AND user_id = ? ORDER BY position, created_at',
        (id, current_user.id)
    ).fetchall()

    return render_template('lists/detail.html', list=list_row, tasks=tasks)

@bp.route('/<int:id>/select', methods=('POST',))
@login_required
def select_list(id):
    from ..models.list import get_list_by_id, get_active_list, update_list_timer_state, set_list_active
    list_to_select = get_list_by_id(id, current_user.id)
    
    if not list_to_select:
        flash('List not found or access denied.', 'error')
        return redirect(url_for('lists.index'))
    
    # Get current active list to pause its timer if running
    current_active = get_active_list(current_user.id)
    
    # Pause timer on current active list if it's running
    if current_active and current_active['timer_state'] in ('session', 'short_break', 'long_break'):
        update_list_timer_state(current_active['id'], 'paused', None)
    
    # Set all of user's lists to inactive
    from ..models.list import set_all_lists_inactive
    set_all_lists_inactive(current_user.id)
    
    # Set the selected list to active
    set_list_active(id, current_user.id)
    
    return redirect(url_for('home.index'))

@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form.get('description', '')
        error = None
        
        if not name:
            error = 'List name is required.'
            
        if error is None:
            from ..models.list import create_list
            from ..db import get_db
            try:
                list_id = create_list(current_user.id, name, description)
                db = get_db()
                _log_event(db, current_user.id, 'list_creation', list_id=list_id)
                return redirect(url_for('lists.index'))
            except Exception:
                error = f"List '{name}' already exists."
        
        flash(error)
    
    return render_template('lists/create.html')

@bp.route('/<int:id>/edit', methods=('POST',))
@login_required
def edit_list(id):
    from ..models.list import get_list_by_id
    list_to_edit = get_list_by_id(id, current_user.id)
    
    if not list_to_edit:
        flash('List not found or access denied.', 'error')
        return redirect(url_for('lists.index'))
    
    if request.method == 'POST':
        name = request.form['name']
        description = request.form.get('description', '')
        error = None
        
        if not name:
            error = 'List name is required.'
            
        if error is None:
            try:
                from ..db import get_db
                db = get_db()
                db.execute(
                    'UPDATE lists SET name = ?, description = ? WHERE id = ? AND user_id = ?',
                    (name, description, id, current_user.id)
                )
                db.commit()
                flash('List updated successfully.')
                return redirect(url_for('lists.index'))
            except Exception:
                error = f"List '{name}' already exists."
        
        flash(error)
        return redirect(url_for('lists.index'))

@bp.route('/<int:id>/delete', methods=('POST',))
@login_required
def delete_list(id):
    from ..db import get_db
    db = get_db()
    
    # Check if this is the active list and verify ownership
    from ..models.list import get_list_by_id
    list_to_delete = get_list_by_id(id, current_user.id)
    
    if not list_to_delete:
        flash('List not found or access denied.', 'error')
        return redirect(url_for('lists.index'))
    
    was_active = list_to_delete['is_active']
    
    # Delete list (CASCADE will delete associated tasks)
    db.execute('DELETE FROM lists WHERE id = ? AND user_id = ?', (id, current_user.id))
    
    _log_event(db, current_user.id, 'list_deletion', list_id=id)
    
    # If we deleted the active list, make another list active for this user
    if was_active:
        from ..models.list import get_all_lists
        all_lists = get_all_lists(current_user.id)
        new_active = all_lists[0] if all_lists else None
        if new_active:
            db.execute('UPDATE lists SET is_active = 1 WHERE id = ? AND user_id = ?', (new_active['id'], current_user.id))
    
    db.commit()
    flash('List deleted successfully.')
    
    return redirect(url_for('lists.index'))
