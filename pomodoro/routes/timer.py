from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timezone

bp = Blueprint('timer', __name__, url_prefix='/timer')


@bp.route('/status', methods=['GET'])
@login_required
def get_timer_status():
    """Get current timer state for active list."""
    from ..models.list import get_active_list
    active_list = get_active_list(current_user.id)

    if not active_list:
        return jsonify({'error': 'No active list'}), 404

    remaining = calculate_remaining_time(active_list)

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
        'pomo_long_break': active_list['pomo_long_break']
    }

    return jsonify(timer_data)

@bp.route('/start', methods=['POST'])
@login_required
def start_timer():
    """Start or resume timer using stored phase context."""
    from ..models.list import get_active_list
    active_list = get_active_list(current_user.id)

    if not active_list:
        return jsonify({'error': 'No active list'}), 404

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

    updated_list = update_timer_state(
        active_list['id'],
        state,
        remaining=remaining,
        sessions_completed=sessions_completed,
        current_phase=current_phase
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

    next_state, sessions_completed = get_next_phase(
        active_list['timer_state'],
        active_list['sessions_completed']
    )

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
    if current_state == 'session':
        if (sessions_completed + 1) % 4 == 0:
            return 'long_break', sessions_completed + 1
        else:
            return 'short_break', sessions_completed + 1
    elif current_state == 'paused':
        if sessions_completed % 4 == 0:
            return 'short_break', sessions_completed + 1
        elif sessions_completed % 4 == 1:
            return 'session', sessions_completed
        elif sessions_completed % 4 == 2:
            return 'short_break', sessions_completed + 1
        elif sessions_completed % 4 == 3:
            return 'session', sessions_completed
        else:
            return 'session', sessions_completed
    elif current_state in ('short_break', 'long_break'):
        return 'session', sessions_completed
    else:
        return 'session', sessions_completed

def update_timer_state(list_id, state, remaining=None, sessions_completed=None, current_phase=None):
    """Update timer state in database with phase context preservation."""
    from .. import db
    db = db.get_db()

    list_row = db.execute(
        'SELECT * FROM lists WHERE id = ? AND user_id = ?',
        (list_id, current_user.id)
    ).fetchone()

    if not list_row:
        return None

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

    return db.execute(
        'SELECT * FROM lists WHERE id = ? AND user_id = ?',
        (list_id, current_user.id)
    ).fetchone()
