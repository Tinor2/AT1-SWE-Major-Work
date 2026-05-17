from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

bp = Blueprint('lists', __name__, url_prefix='/lists')


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
            try:
                create_list(current_user.id, name, description)
                return redirect(url_for('lists.index'))
            except Exception as e:
                error = f"List '{name}' already exists."
        
        flash(error)
    
    return render_template('lists/create.html')

@bp.route('/<int:id>/edit', methods=('POST',))
@login_required
def edit_list(id):
    from ..models.list import get_list_by_id, update_list
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
            except Exception as e:
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