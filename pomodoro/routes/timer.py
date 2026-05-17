"""
Timer routes — clean rewrite.

Design principles:
- Server stores: timer_state, current_phase, timer_remaining, sessions_completed,
  timer_started_at, timer_last_updated.
- timer_remaining is the number of seconds left AT THE MOMENT timer_started_at was set.
- Actual remaining = timer_remaining - (now - timer_started_at)  [only when running]
- On pause/reset we snapshot the real remaining back into timer_remaining and clear
  timer_started_at so the formula above isn't used.
- The client is the only thing that ticks. The server is the source of truth for state.
- No task-time-tracking logic lives here — that is a separate concern.
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timezone

bp = Blueprint('timer', __name__, url_prefix='/timer')

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_db():
    from ..db import get_db
    return get_db()


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _now_ts():
    """UTC datetime object."""
    return datetime.now(timezone.utc)


def _get_active_list(db, user_id):
    return db.execute(
        'SELECT * FROM lists WHERE is_active = 1 AND user_id = ?',
        (user_id,)
    ).fetchone()


def _calculate_remaining(row):
    """
    Return the number of seconds genuinely remaining on the clock.

    - If the timer is paused or idle, timer_remaining already holds the
      correct snapshot — return it directly.
    - If the timer is running, subtract elapsed seconds from timer_remaining.
    """
    state = row['timer_state']
    if state not in ('session', 'short_break', 'long_break'):
        return max(0, row['timer_remaining'] or 0)

    started_at = row['timer_started_at']
    if not started_at:
        return max(0, row['timer_remaining'] or 0)

    # Normalise to datetime
    if isinstance(started_at, bytes):
        started_at = started_at.decode('utf-8')
    if isinstance(started_at, str):
        try:
            # Handle ISO format with timezone properly
            if started_at.endswith('Z'):
                # UTC time - remove Z and parse as UTC
                started_at = datetime.fromisoformat(started_at[:-1])
            else:
                # Local time with timezone offset
                started_at = datetime.fromisoformat(started_at)
        except (ValueError, TypeError) as e:
            print(f"Warning: Could not parse timer_started_at '{started_at}': {e}")
            return max(0, row['timer_remaining'] or 0)
    
    elapsed = int((_now_ts() - started_at).total_seconds())
    return max(0, (row['timer_remaining'] or 0) - elapsed)


def _phase_duration(row, phase):
    """Return the full duration in seconds for a given phase name."""
    if phase == 'session':
        return (row['pomo_session'] or 25) * 60
    if phase == 'short_break':
        return (row['pomo_short_break'] or 5) * 60
    if phase == 'long_break':
        return (row['pomo_long_break'] or 15) * 60
    return (row['pomo_session'] or 25) * 60


def _next_phase(current_state, current_phase, sessions_completed):
    """
    Determine (next_phase, new_sessions_completed) after the current phase ends
    or is skipped.

    Cycle: session → short_break → session → short_break → session →
           short_break → session → long_break → (repeat)
    i.e. every 4th session is followed by a long break.
    """
    # Determine what we're actually in right now
    effective_phase = current_phase if current_state == 'paused' else current_state

    if effective_phase == 'session':
        new_sessions = sessions_completed + 1
        if new_sessions % 4 == 0:
            return 'long_break', new_sessions
        return 'short_break', new_sessions

    # After any break → back to session, sessions_completed unchanged
    return 'session', sessions_completed


def _save_state(db, list_id, user_id, *,
                state,
                current_phase,
                timer_remaining,
                sessions_completed,
                timer_started_at):
    """
    Write all timer fields atomically in one UPDATE.
    timer_started_at should be an ISO string or None.
    """
    db.execute(
        """UPDATE lists SET
               timer_state        = ?,
               current_phase      = ?,
               timer_remaining    = ?,
               sessions_completed = ?,
               timer_started_at   = ?,
               timer_last_updated = ?
           WHERE id = ? AND user_id = ?""",
        (
            state,
            current_phase,
            timer_remaining,
            sessions_completed,
            timer_started_at,
            _now_iso(),
            list_id,
            user_id,
        )
    )
    db.commit()


def _handle_task_time_tracking(user_id, new_state, old_state=None):
    """
    Handle task time tracking based on timer state changes.
    Only tracks time during work sessions (state == 'session').
    """
    from flask import session
    
    selected_task_id = session.get('selected_task_id')
    if not selected_task_id:
        return
    
    # Import here to avoid circular imports
    from ..models.time_tracking import start_task_session, end_current_session
    
    if new_state == 'session' and old_state != 'session':
        # Starting work session - begin task tracking
        start_task_session(selected_task_id, user_id)
        print(f"🎯 Started tracking task {selected_task_id}")
        
    elif new_state != 'session' and old_state == 'session':
        # Ending work session - stop task tracking
        duration = end_current_session(user_id)
        if duration > 0:
            print(f"⏹️ Stopped tracking task {selected_task_id} ({duration}s)")
        else:
            print(f"⏹️ Stopped tracking task {selected_task_id}")


def _read_list(db, list_id, user_id):
    return db.execute(
        'SELECT * FROM lists WHERE id = ? AND user_id = ?',
        (list_id, user_id)
    ).fetchone()


def _timer_response(row, remaining):
    """Build the standard JSON payload returned by every timer endpoint."""
    return jsonify({
        'success': True,
        'timer_state':        row['timer_state'],
        'current_phase':      row['current_phase'],
        'timer_remaining':    remaining,
        'sessions_completed': row['sessions_completed'],
        'timer_started_at':   row['timer_started_at'],
        'timer_last_updated': row['timer_last_updated'],
        'pomo_session':       row['pomo_session'],
        'pomo_short_break':   row['pomo_short_break'],
        'pomo_long_break':    row['pomo_long_break'],
    })


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@bp.route('/status', methods=['GET'])
@login_required
def get_timer_status():
    """Return the current timer state, with accurate remaining time."""
    db = _get_db()
    row = _get_active_list(db, current_user.id)
    if not row:
        return jsonify({'error': 'No active list'}), 404

    remaining = _calculate_remaining(row)
    return _timer_response(row, remaining)


@bp.route('/start', methods=['POST'])
@login_required
def start_timer():
    """
    Start or resume the timer.

    - idle   → begin a brand-new session phase
    - paused → resume from where we left off (timer_remaining already holds the snapshot)
    - running → no-op, return current state
    """
    db = _get_db()
    row = _get_active_list(db, current_user.id)
    if not row:
        return jsonify({'error': 'No active list'}), 404

    old_state = row['timer_state']

    if old_state in ('session', 'short_break', 'long_break'):
        # Already running — just return current state
        remaining = _calculate_remaining(row)
        return _timer_response(row, remaining)

    if old_state == 'idle':
        # Fresh start — begin a focus session
        phase     = 'session'
        remaining = _phase_duration(row, phase)
    else:
        # Paused — resume from snapshot
        phase     = row['current_phase'] or 'session'
        remaining = row['timer_remaining'] or _phase_duration(row, phase)

    new_state = phase  # 'session', 'short_break', or 'long_break'
    
    # Handle task time tracking
    _handle_task_time_tracking(current_user.id, new_state, old_state)

    _save_state(
        db, row['id'], current_user.id,
        state            = new_state,        # e.g. 'session'
        current_phase    = phase,
        timer_remaining  = remaining,
        sessions_completed = row['sessions_completed'],
        timer_started_at = _now_iso(),       # clock starts now
    )

    updated = _read_list(db, row['id'], current_user.id)
    return _timer_response(updated, remaining)


@bp.route('/pause', methods=['POST'])
@login_required
def pause_timer():
    """
    Pause the running timer.
    Snapshots the real remaining time into timer_remaining and clears
    timer_started_at so the running formula isn't applied while paused.
    """
    db = _get_db()
    row = _get_active_list(db, current_user.id)
    if not row:
        return jsonify({'error': 'No active list'}), 404

    old_state = row['timer_state']
    if old_state not in ('session', 'short_break', 'long_break'):
        return jsonify({'error': 'Timer is not running'}), 400

    # Snapshot actual remaining before we clear started_at
    remaining = _calculate_remaining(row)

    # Handle task time tracking (stop tracking when pausing)
    _handle_task_time_tracking(current_user.id, 'paused', old_state)

    _save_state(
        db, row['id'], current_user.id,
        state            = 'paused',
        current_phase    = old_state,       # remember what we were doing
        timer_remaining  = remaining,       # snapshot
        sessions_completed = row['sessions_completed'],
        timer_started_at = None,            # not running
    )

    updated = _read_list(db, row['id'], current_user.id)
    return _timer_response(updated, remaining)


@bp.route('/reset', methods=['POST'])
@login_required
def reset_timer():
    """
    Reset to the beginning of the current phase (paused).
    Does NOT advance the phase or change sessions_completed.
    """
    db = _get_db()
    row = _get_active_list(db, current_user.id)
    if not row:
        return jsonify({'error': 'No active list'}), 404

    # The phase we're resetting is whichever phase is active right now.
    # If running: use timer_state. If paused: use current_phase.
    state = row['timer_state']
    phase = row['current_phase'] if state == 'paused' else state
    if not phase or phase not in ('session', 'short_break', 'long_break'):
        phase = 'session'

    remaining = _phase_duration(row, phase)

    _save_state(
        db, row['id'], current_user.id,
        state            = 'paused',
        current_phase    = phase,
        timer_remaining  = remaining,
        sessions_completed = row['sessions_completed'],
        timer_started_at = None,
    )

    updated = _read_list(db, row['id'], current_user.id)
    return _timer_response(updated, remaining)


@bp.route('/skip', methods=['POST'])
@login_required
def skip_timer():
    """
    Skip to next phase (paused, ready to start).
    Advances sessions_completed if we were in a session.
    """
    db = _get_db()
    row = _get_active_list(db, current_user.id)
    if not row:
        return jsonify({'error': 'No active list'}), 404

    old_state = row['timer_state']
    next_phase, new_sessions = _next_phase(
        old_state,
        row['current_phase'],
        row['sessions_completed'],
    )

    remaining = _phase_duration(row, next_phase)

    # Handle task time tracking (stop tracking when skipping)
    _handle_task_time_tracking(current_user.id, 'paused', old_state)

    # Land in 'paused' so the user consciously starts the next phase.
    # This also prevents the "auto-advance on refresh" bug because
    # paused state never triggers startCountdown() on load.
    _save_state(
        db, row['id'], current_user.id,
        state            = 'paused',
        current_phase    = next_phase,
        timer_remaining  = remaining,
        sessions_completed = new_sessions,
        timer_started_at = None,
    )

    updated = _read_list(db, row['id'], current_user.id)
    return _timer_response(updated, remaining)


@bp.route('/reset-sets', methods=['POST'])
@login_required
def reset_sets():
    """
    Reset session counter to 0 and return to the beginning of a focus session.
    Lands in 'paused' so the user starts deliberately.
    """
    db = _get_db()
    row = _get_active_list(db, current_user.id)
    if not row:
        return jsonify({'error': 'No active list'}), 404

    remaining = _phase_duration(row, 'session')

    _save_state(
        db, row['id'], current_user.id,
        state            = 'paused',
        current_phase    = 'session',
        timer_remaining  = remaining,
        sessions_completed = 0,
        timer_started_at = None,
    )

    updated = _read_list(db, row['id'], current_user.id)
    return _timer_response(updated, remaining)


@bp.route('/select-task', methods=['POST'])
@login_required
def select_task():
    """
    Select a task for time tracking.
    Only parent tasks (level 0) can be selected.
    """
    db = _get_db()
    
    # Get task ID from request
    data = request.get_json()
    if not data or 'task_id' not in data:
        return jsonify({'error': 'task_id required'}), 400
    
    task_id = data['task_id']
    
    # Verify task exists and belongs to user
    task = db.execute(
        'SELECT * FROM tasks WHERE id = ? AND user_id = ?',
        (task_id, current_user.id)
    ).fetchone()
    
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    
    # Only allow selection of parent tasks (level 0)
    if task['level'] != 0:
        return jsonify({'error': 'Only parent tasks can be selected'}), 400
    
    # Store selected task in lists table (we can repurpose an existing column or add new one)
    # For now, we'll use a session-based approach
    from flask import session
    session['selected_task_id'] = task_id
    
    return jsonify({
        'success': True,
        'selected_task': {
            'id': task['id'],
            'content': task['content'],
            'total_time_seconds': task['total_time_seconds'] if task['total_time_seconds'] is not None else 0
        }
    })


@bp.route('/deselect-task', methods=['POST'])
@login_required
def deselect_task():
    """
    Deselect the current task for time tracking.
    """
    from flask import session
    
    # Stop any active time tracking session
    selected_task_id = session.get('selected_task_id')
    if selected_task_id:
        from ..models.time_tracking import end_current_session
        duration = end_current_session(current_user.id)
        if duration > 0:
            print(f"⏹️ Stopped tracking task {selected_task_id} ({duration}s)")
        else:
            print(f"⏹️ Stopped tracking task {selected_task_id}")
    
    session.pop('selected_task_id', None)
    
    return jsonify({
        'success': True,
        'selected_task': None
    })


@bp.route('/current-task', methods=['GET'])
@login_required
def get_current_task():
    """
    Get the currently selected task for time tracking.
    """
    from flask import session
    selected_task_id = session.get('selected_task_id')
    
    if not selected_task_id:
        return jsonify({
            'success': True,
            'selected_task': None
        })
    
    db = _get_db()
    task = db.execute(
        'SELECT id, content, total_time_seconds FROM tasks WHERE id = ? AND user_id = ?',
        (selected_task_id, current_user.id)
    ).fetchone()
    
    if not task:
        # Task was deleted, clear selection
        session.pop('selected_task_id', None)
        return jsonify({
            'success': True,
            'selected_task': None
        })
    
    return jsonify({
        'success': True,
        'selected_task': {
            'id': task['id'],
            'content': task['content'],
            'total_time_seconds': task['total_time_seconds'] if task['total_time_seconds'] is not None else 0
        }
    })