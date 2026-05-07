from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timezone

bp = Blueprint('timer', __name__, url_prefix='/timer')


@bp.route('/status', methods=['GET'])
@login_required
def get_timer_status():
    """Get current timer state for active list including active task session."""
    from ..models.list import get_active_list
    from ..models.time_tracking import get_active_session
    from ..models.task import get_task_by_id
    from flask import session
    active_list = get_active_list(current_user.id)

    if not active_list:
        return jsonify({'error': 'No active list'}), 404

    remaining = calculate_remaining_time(active_list)
    active_session = get_active_session(current_user.id)
    
    # Fallback to session-stored task if no active DB session exists
    selected_task_data = None
    if active_session:
        selected_task_data = {
            'id': active_session['task_id'],
            'content': active_session['task_content'],
            'started_at': active_session['started_at']
        }
    else:
        # Check if user had a task selected while idle/paused
        sess_task_id = session.get('selected_task_id')
        if sess_task_id:
            task = get_task_by_id(sess_task_id, current_user.id)
            if task:
                selected_task_data = {
                    'id': task['id'],
                    'content': task['content'],
                    'started_at': None
                }
    
    # Log timer status for debugging
    print(f"⏰ TIMER STATUS - User {current_user.id}: {active_list['timer_state']} ({active_list['current_phase']})")
    if active_session:
        print(f"⏱️ ACTIVE SESSION - Task {active_session['task_id']}: {active_session['started_at']}")
    elif selected_task_data:
        print(f"💾 STORED TASK - Task {selected_task_data['id']}: {selected_task_data['content']}")

    timer_data = {
        'success': True,
        'timer_state': active_list['timer_state'],
        'current_phase': active_list['current_phase'],
        'timer_remaining': remaining,
        'sessions_completed': active_list['sessions_completed'],
        'timer_started_at': active_list['timer_started_at'],
        'timer_last_updated': active_list['timer_last_updated'],
        'pomo_session': active_list['pomo_session'],
        'pomo_short_break': active_list['pomo_short_break'],
        'pomo_long_break': active_list['pomo_long_break'],
        'selected_task': selected_task_data
    }

    return jsonify(timer_data)

@bp.route('/start', methods=['POST'])
@login_required
def start_timer():
    """Start or resume timer using stored phase context."""
    from ..models.list import get_active_list
    from flask import session
    active_list = get_active_list(current_user.id)

    if not active_list:
        return jsonify({'error': 'No active list'}), 404

    # Prioritize: 1. POST body, 2. Flask session
    data = request.get_json() or {}
    selected_task_id = data.get('selected_task_id') or session.get('selected_task_id')

    if active_list['timer_state'] == 'idle':
        state = 'session'
        current_phase = 'session'
        remaining = active_list['pomo_session'] * 60
        sessions_completed = active_list['sessions_completed']
    elif active_list['timer_state'] == 'paused':
        current_phase = active_list['current_phase'] or 'session'
        state = current_phase
        remaining = calculate_remaining_time(active_list)
        sessions_completed = active_list['sessions_completed']
    else:
        state = active_list['timer_state']
        current_phase = active_list['current_phase'] or state
        remaining = calculate_remaining_time(active_list)
        sessions_completed = active_list['sessions_completed']

    print(f"🚀 TIMER START - User {current_user.id}: {state} (task: {selected_task_id})")
    updated_list = update_timer_state(
        active_list['id'],
        state,
        remaining=remaining,
        sessions_completed=sessions_completed,
        current_phase=current_phase,
        selected_task_id=selected_task_id
    )

    if not updated_list:
        return jsonify({'error': 'Failed to update timer'}), 500

    return jsonify({
        'success': True,
        'timer_state': updated_list['timer_state'],
        'current_phase': updated_list['current_phase'],
        'timer_remaining': updated_list['timer_remaining'],
        'sessions_completed': updated_list['sessions_completed'],
        'timer_started_at': updated_list['timer_started_at'],
        'timer_last_updated': updated_list['timer_last_updated']
    })

@bp.route('/pause', methods=['POST'])
@login_required
def pause_timer():
    """Pause current timer while preserving phase context."""
    from ..models.list import get_active_list
    active_list = get_active_list(current_user.id)

    if not active_list:
        return jsonify({'error': 'No active list'}), 404

    if active_list['timer_state'] not in ('session', 'short_break', 'long_break'):
        return jsonify({'error': 'Timer is not running'}), 400

    remaining = calculate_remaining_time(active_list)
    current_phase = active_list['timer_state']

    updated_list = update_timer_state(
        active_list['id'],
        'paused',
        remaining=remaining,
        current_phase=current_phase
    )

    if not updated_list:
        return jsonify({'error': 'Failed to pause timer'}), 500

    return jsonify({
        'success': True,
        'timer_state': updated_list['timer_state'],
        'current_phase': updated_list['current_phase'],
        'timer_remaining': updated_list['timer_remaining'],
        'sessions_completed': updated_list['sessions_completed'],
        'timer_started_at': updated_list['timer_started_at'],
        'timer_last_updated': updated_list['timer_last_updated']
    })

@bp.route('/reset', methods=['POST'])
@login_required
def reset_timer():
    """Reset timer to beginning of current phase using stored phase context."""
    from ..models.list import get_active_list
    active_list = get_active_list(current_user.id)

    if not active_list:
        return jsonify({'error': 'No active list'}), 404

    current_phase = active_list['current_phase'] or 'session'

    if current_phase == 'session':
        remaining = active_list['pomo_session'] * 60
    elif current_phase == 'short_break':
        remaining = active_list['pomo_short_break'] * 60
    elif current_phase == 'long_break':
        remaining = active_list['pomo_long_break'] * 60
    else:
        remaining = active_list['pomo_session'] * 60

    updated_list = update_timer_state(
        active_list['id'],
        'paused',
        remaining=remaining,
        current_phase=current_phase
    )

    if not updated_list:
        return jsonify({'error': 'Failed to reset timer'}), 500

    return jsonify({
        'success': True,
        'timer_state': updated_list['timer_state'],
        'current_phase': updated_list['current_phase'],
        'timer_remaining': updated_list['timer_remaining'],
        'sessions_completed': updated_list['sessions_completed'],
        'timer_started_at': updated_list['timer_started_at'],
        'timer_last_updated': updated_list['timer_last_updated']
    })

@bp.route('/skip', methods=['POST'])
@login_required
def skip_timer():
    """Skip to next phase."""
    from ..models.list import get_active_list
    active_list = get_active_list(current_user.id)

    if not active_list:
        return jsonify({'error': 'No active list'}), 404

    # DEBUG: Log skip route call with stack trace
    import traceback
    print(f"🚨 SKIP ROUTE CALLED - User {current_user.id}")
    print("📋 Stack trace:")
    for line in traceback.format_stack()[-5:]:  # Last 5 stack frames
        print(f"  {line.strip()}")

    # Use proper skip logic instead of get_next_phase
    current_state = active_list['timer_state']
    sessions_completed = active_list['sessions_completed']
    
    if current_state == 'session':
        # Skip session -> go to break
        if (sessions_completed + 1) % 4 == 0:
            next_state = 'long_break'
        else:
            next_state = 'short_break'
        new_sessions = sessions_completed + 1
    elif current_state == 'short_break':
        # Skip short break -> go to session
        next_state = 'session'
        new_sessions = sessions_completed
    elif current_state == 'long_break':
        # Skip long break -> go to session
        next_state = 'session'
        new_sessions = sessions_completed
    elif current_state == 'paused':
        # When paused, use get_next_phase logic
        next_state, new_sessions = get_next_phase(current_state, sessions_completed)
    else:
        # Default to session
        next_state = 'session'
        new_sessions = sessions_completed
    
    print(f"🔄 SKIP LOGIC: {current_state} -> {next_state} (sessions: {new_sessions})")

    remaining = None
    if next_state == 'session':
        remaining = active_list['pomo_session'] * 60
    elif next_state == 'short_break':
        remaining = active_list['pomo_short_break'] * 60
    elif next_state == 'long_break':
        remaining = active_list['pomo_long_break'] * 60

    updated_list = update_timer_state(
        active_list['id'],
        next_state,
        remaining=remaining,
        sessions_completed=sessions_completed,
        current_phase=next_state
    )

    if not updated_list:
        return jsonify({'error': 'Failed to skip timer'}), 500

    return jsonify({
        'success': True,
        'timer_state': updated_list['timer_state'],
        'current_phase': updated_list['current_phase'],
        'timer_remaining': updated_list['timer_remaining'],
        'sessions_completed': updated_list['sessions_completed'],
        'timer_started_at': updated_list['timer_started_at'],
        'timer_last_updated': updated_list['timer_last_updated']
    })

@bp.route('/reset-sets', methods=['POST'])
@login_required
def reset_sets():
    """Reset the sessions_completed counter and go back to first focus session."""
    from ..models.list import get_active_list
    active_list = get_active_list(current_user.id)

    if not active_list:
        return jsonify({'error': 'No active list'}), 404

    updated_list = update_timer_state(
        active_list['id'],
        'paused',
        remaining=active_list['pomo_session'] * 60,
        sessions_completed=0,
        current_phase='session'
    )

    if not updated_list:
        return jsonify({'error': 'Failed to reset sets'}), 500

    return jsonify({
        'success': True,
        'timer_state': updated_list['timer_state'],
        'current_phase': updated_list['current_phase'],
        'timer_remaining': updated_list['timer_remaining'],
        'sessions_completed': updated_list['sessions_completed'],
        'timer_started_at': updated_list['timer_started_at'],
        'timer_last_updated': updated_list['timer_last_updated']
    })

def calculate_remaining_time(list_row):
    """Calculate remaining time based on server time."""
    if not list_row['timer_started_at'] or list_row['timer_state'] in ('idle', 'paused'):
        return list_row['timer_remaining']

    try:
        timer_started_at = list_row['timer_started_at']

        if isinstance(timer_started_at, bytes):
            timer_started_at = timer_started_at.decode('utf-8')

        if isinstance(timer_started_at, str):
            started_at = datetime.fromisoformat(timer_started_at.replace('Z', '+00:00'))
        elif isinstance(timer_started_at, datetime):
            started_at = timer_started_at
        else:
            return list_row['timer_remaining']

        now = datetime.now(timezone.utc)
        elapsed_seconds = int((now - started_at).total_seconds())
        remaining = list_row['timer_remaining'] - elapsed_seconds
        return max(0, remaining)
    except Exception as e:
        print(f"Timer calculation error: {e}")
        return list_row['timer_remaining']

def get_next_phase(current_state, sessions_completed):
    """Determine next phase and session count."""
    print(f"🔍 get_next_phase called - state: {current_state}, sessions: {sessions_completed}")
    
    if current_state == 'session':
        if (sessions_completed + 1) % 4 == 0:
            print(f"  → Session -> Long Break (sessions: {sessions_completed + 1})")
            return 'long_break', sessions_completed + 1
        else:
            print(f"  → Session -> Short Break (sessions: {sessions_completed + 1})")
            return 'short_break', sessions_completed + 1
    elif current_state == 'paused':
        if sessions_completed % 4 == 0:
            print(f"  → Paused -> Short Break (sessions: {sessions_completed + 1})")
            return 'short_break', sessions_completed + 1
        elif sessions_completed % 4 == 1:
            print(f"  → Paused -> Session (sessions: {sessions_completed})")
            return 'session', sessions_completed
        elif sessions_completed % 4 == 2:
            print(f"  → Paused -> Short Break (sessions: {sessions_completed + 1})")
            return 'short_break', sessions_completed + 1
        elif sessions_completed % 4 == 3:
            print(f"  → Paused -> Session (sessions: {sessions_completed})")
            return 'session', sessions_completed
        else:
            print(f"  → Paused -> Session (sessions: {sessions_completed})")
            return 'session', sessions_completed
    elif current_state in ('short_break', 'long_break'):
        print(f"  → Break -> Session (sessions: {sessions_completed})")
        return 'session', sessions_completed
    else:
        print(f"  → Default -> Session (sessions: {sessions_completed})")
        return 'session', sessions_completed

def update_timer_state(list_id, state, remaining=None, sessions_completed=None, current_phase=None, selected_task_id=None):
    """Update timer state in database with phase context preservation and task time tracking."""
    from .. import db
    from ..models.time_tracking import start_task_session, end_current_session
    db = db.get_db()

    list_row = db.execute(
        'SELECT * FROM lists WHERE id = ? AND user_id = ?',
        (list_id, current_user.id)
    ).fetchone()

    if not list_row:
        return None

    # Handle task session management
    if state == 'session' and selected_task_id and current_phase == 'session':
        # Start tracking time for selected task during work session
        start_task_session(selected_task_id, current_user.id)
    elif state in ('paused', 'idle', 'short_break', 'long_break'):
        # End time tracking when not in work session
        end_current_session(current_user.id)

    update_data = {
        'timer_state': state,
        'timer_last_updated': datetime.now(timezone.utc).isoformat()
    }

    if current_phase is not None:
        update_data['current_phase'] = current_phase
    elif state in ('session', 'short_break', 'long_break'):
        update_data['current_phase'] = state
    elif state in ('idle', 'paused'):
        if list_row['current_phase']:
            update_data['current_phase'] = list_row['current_phase']

    if state in ('session', 'short_break', 'long_break'):
        if list_row['timer_state'] not in ('session', 'short_break', 'long_break'):
            update_data['timer_started_at'] = datetime.now(timezone.utc).isoformat()
            if remaining is None:
                if update_data['current_phase'] == 'session':
                    update_data['timer_remaining'] = list_row['pomo_session'] * 60
                elif update_data['current_phase'] == 'short_break':
                    update_data['timer_remaining'] = list_row['pomo_short_break'] * 60
                elif update_data['current_phase'] == 'long_break':
                    update_data['timer_remaining'] = list_row['pomo_long_break'] * 60
    elif state in ('idle', 'paused'):
        update_data['timer_started_at'] = None
        if remaining is not None:
            update_data['timer_remaining'] = remaining

    if remaining is not None:
        update_data['timer_remaining'] = remaining

    if sessions_completed is not None:
        update_data['sessions_completed'] = sessions_completed

    set_clauses = []
    values = []
    for key, value in update_data.items():
        set_clauses.append(f"{key} = ?")
        values.append(value)
    values.append(list_id)
    values.append(current_user.id)

    db.execute(
        f"UPDATE lists SET {', '.join(set_clauses)} WHERE id = ? AND user_id = ?",
        values
    )
    db.commit()
    
    # Fetch and return the updated list record
    updated_list = db.execute(
        'SELECT * FROM lists WHERE id = ? AND user_id = ?',
        (list_id, current_user.id)
    ).fetchone()
    return updated_list

@bp.route('/select-task', methods=['POST'])
@login_required
def select_task():
    """Select a task for time tracking."""
    if not request.is_json:
        return jsonify({'error': 'Invalid request format'}), 400
    
    data = request.get_json()
    task_id = data.get('task_id')
    
    if not task_id:
        return jsonify({'error': 'Task ID required'}), 400
    
    from ..models.task import get_task_by_id
    task = get_task_by_id(task_id, current_user.id)
    
    if not task:
        print(f"❌ Task {task_id} not found for user {current_user.id}")
        return jsonify({'error': 'Task not found'}), 404
    
    # Store selected task in session
    from flask import session
    session['selected_task_id'] = task_id
    
    print(f"🎯 TASK SELECTED - User {current_user.id}: Task {task_id} ({task['content']})")
    
    return jsonify({
        'success': True,
        'task_id': task_id,
        'task_content': task['content']
    })

@bp.route('/deselect-task', methods=['POST'])
@login_required
def deselect_task():
    """Deselect current task."""
    from flask import session
    old_task_id = session.get('selected_task_id')
    session.pop('selected_task_id', None)
    
    # End any active time tracking session
    from ..models.time_tracking import end_current_session
    duration = end_current_session(current_user.id)
    
    print(f"🔴 TASK DESELECTED - User {current_user.id}: Task {old_task_id} (duration: {duration}s)")
    
    return jsonify({'success': True})

    return db.execute(
        'SELECT * FROM lists WHERE id = ? AND user_id = ?',
        (list_id, current_user.id)
    ).fetchone()
