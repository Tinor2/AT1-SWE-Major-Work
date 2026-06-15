"""
Feature engineering for the DecisionTreeClassifier productivity model.

Each function below computes a single numeric feature from the
user_statistics and tasks tables. All database queries use
parameterised ? placeholders (OWASP A03: SQLi prevention).

Features are categorised into:
  - Productivity: task completion rate, break rate, session rate,
    daily focus time, consistency score
  - Temporal: preferred hour and weekday
  - Settings: current session/break durations from the user's active list
  - Engagement: avg sessions per day, break skip streak, pause rate,
    active day ratio

The aggregate feature dict is consumed by:
  1. trainer.py — to build day-level feature rows for model training
  2. predictor.py — to compute the 10-element vector passed to the
     DecisionTreeClassifier for inference
"""

import numpy as np
from datetime import datetime
from pomodoro.db import get_db


def compute_features_for_user(user_id, training_window_days=60):
    """
    Compute full feature dict for a user over the given window.

    The returned dict is used both for:
      - Training (trainer.py builds per-day rows from these features)
      - Inference (predictor.py selects the 10 features the model expects)

    All sub-functions follow the same pattern:
      db.execute("SELECT ... WHERE user_id = ? AND ...", (user_id, ...))
    which prevents SQL injection (OWASP A03).

    Args:
        user_id: User ID
        training_window_days: Number of days of history to consider

    Returns:
        dict: Feature vector with all computed features
    """
    features = {}
    db = get_db()

    # ── Productivity-Based Features ──────────────────────────────────
    # These directly describe the user's effectiveness and habits.
    features['avg_task_completion_time_seconds'] = compute_avg_task_completion_time(
        db, user_id, training_window_days
    )
    features['task_completion_rate'] = compute_task_completion_rate(
        db, user_id, training_window_days
    )
    features['break_completion_rate'] = compute_break_completion_rate(
        db, user_id, training_window_days
    )
    features['session_completion_rate'] = compute_session_completion_rate(
        db, user_id, training_window_days
    )
    features['avg_daily_focus_time_seconds'] = compute_avg_daily_focus_time(
        db, user_id, training_window_days
    )
    features['consistency_score'] = compute_consistency_score(
        db, user_id, training_window_days
    )

    # ── Temporal Features ────────────────────────────────────────────
    # When the user typically works — influences the peak_hour_norm and
    # weekday_norm elements of the feature vector.
    features['preferred_hour'] = compute_preferred_hour(db, user_id)
    features['preferred_weekday'] = compute_preferred_weekday(db, user_id)

    # ── Current Settings ─────────────────────────────────────────────
    # The user's configured session and break durations. Not directly used
    # in the current 10-element feature vector but available for future
    # model expansion.
    features['current_session_duration'] = get_current_session_duration(db, user_id)
    features['current_short_break_duration'] = get_current_short_break_duration(db, user_id)
    features['current_long_break_duration'] = get_current_long_break_duration(db, user_id)

    # ── Engagement Features ──────────────────────────────────────────
    # How actively the user engages with the app over time.
    features['avg_sessions_per_day'] = compute_avg_sessions_per_day(
        db, user_id, training_window_days
    )
    features['break_skip_streak'] = compute_break_skip_streak(db, user_id)
    features['session_pause_rate'] = compute_session_pause_rate(
        db, user_id, training_window_days
    )
    features['active_day_ratio'] = compute_active_day_ratio(
        db, user_id, training_window_days
    )

    return features


def compute_avg_task_completion_time(db, user_id, window_days):
    """Calculate average task completion time in seconds."""
    cutoff_timestamp = int(datetime.now().timestamp()) - (window_days * 86400)
    
    result = db.execute(
        """
        SELECT COALESCE(AVG(task_completion_time_seconds), 0) as avg_time
        FROM user_statistics
        WHERE user_id = ? AND event_type = 'task_completion' AND timestamp >= ?
        """,
        (user_id, cutoff_timestamp)
    ).fetchone()
    
    return float(result['avg_time'] or 3600.0)


def compute_task_completion_rate(db, user_id, window_days):
    """Calculate percentage of tasks completed (uses tasks table, matches analytics page)."""
    result = db.execute(
        """
        SELECT 
            SUM(CASE WHEN is_done THEN 1 ELSE 0 END) as completed,
            COUNT(*) as total
        FROM tasks
        WHERE user_id = ?
          AND datetime(created_at) >= datetime('now', ?)
        """,
        (user_id, f'-{window_days} days'),
    ).fetchone()

    total = int(result['total'] or 0)
    if total == 0:
        return 0.5
    return min(float(result['completed'] or 0) / total, 1.0)


def compute_break_completion_rate(db, user_id, window_days):
    """Calculate percentage of breaks completed."""
    cutoff_timestamp = int(datetime.now().timestamp()) - (window_days * 86400)
    
    result = db.execute(
        """
        SELECT 
            SUM(CASE WHEN event_type = 'break_completion' THEN 1 ELSE 0 END) as completed,
            SUM(CASE WHEN event_type = 'break_skip' THEN 1 ELSE 0 END) as skipped
        FROM user_statistics
        WHERE user_id = ? AND timestamp >= ? AND event_type IN ('break_completion', 'break_skip')
        """,
        (user_id, cutoff_timestamp)
    ).fetchone()
    
    completed = int(result['completed'] or 0)
    skipped = int(result['skipped'] or 0)
    
    if completed + skipped == 0:
        return 0.5
    
    return min(float(completed) / float(completed + skipped), 1.0)


def compute_session_completion_rate(db, user_id, window_days):
    """Calculate percentage of sessions completed."""
    cutoff_timestamp = int(datetime.now().timestamp()) - (window_days * 86400)
    
    result = db.execute(
        """
        SELECT 
            SUM(CASE WHEN event_type = 'session_end' THEN 1 ELSE 0 END) as ended,
            SUM(CASE WHEN event_type = 'session_start' THEN 1 ELSE 0 END) as started
        FROM user_statistics
        WHERE user_id = ? AND timestamp >= ? AND event_type IN ('session_start', 'session_end')
        """,
        (user_id, cutoff_timestamp)
    ).fetchone()
    
    ended = int(result['ended'] or 0)
    started = int(result['started'] or 0)
    
    if started == 0:
        return 0.5
    
    return min(float(ended) / float(started), 1.0)


def compute_avg_daily_focus_time(db, user_id, window_days):
    """Calculate average daily focus time in seconds."""
    cutoff_timestamp = int(datetime.now().timestamp()) - (window_days * 86400)
    
    result = db.execute(
        """
        SELECT 
            AVG(daily_focus) as avg_focus
        FROM (
            SELECT 
                DATE(datetime(timestamp, 'unixepoch', 'localtime')) as day,
                COALESCE(SUM(duration_seconds), 0) as daily_focus
            FROM user_statistics
            WHERE user_id = ? AND timestamp >= ? AND event_type = 'session_end'
            GROUP BY DATE(datetime(timestamp, 'unixepoch', 'localtime'))
        )
        """,
        (user_id, cutoff_timestamp)
    ).fetchone()
    
    return float(result['avg_focus'] or 3600.0)


def compute_consistency_score(db, user_id, window_days):
    """
    Compute a blended consistency score in [0, 1].

    The score combines two signals:
      1. Variance consistency (30% weight): how similar the user's daily
         focus time is day-to-day. Low variance → high score.
         Formula: 1 / (1 + variance/10000). The /10000 divisor keeps the
         score in a reasonable range when focus varies by thousands of
         seconds.
      2. Streak consistency (70% weight): rewards consecutive active days
         and penalises randomly-spaced sessions. Uses a squared-streak
         approach — a streak of N days contributes N² to the total,
         so one long streak scores higher than many short ones.
         max_possible = len(days)², which would be achieved only if all
         active days are consecutive.

    The blend is then scaled down when the user has few active days
    relative to the window (day_ratio penalty).

    Returns float in [0, 1]; fallback 0.5 when no data exists.
    """
    cutoff_timestamp = int(datetime.now().timestamp()) - (window_days * 86400)
    
    daily_rows = db.execute(
        """
        SELECT
            DATE(datetime(timestamp, 'unixepoch', 'localtime')) as day,
            COALESCE(SUM(duration_seconds), 0) as daily_focus
        FROM user_statistics
        WHERE user_id = ? AND timestamp >= ? AND event_type = 'session_end'
        GROUP BY day
        ORDER BY day ASC
        """,
        (user_id, cutoff_timestamp)
    ).fetchall()
    
    if not daily_rows:
        return 0.5
    
    focus_times_min = [float(row['daily_focus']) / 60.0 for row in daily_rows]
    day_strings = [row['day'] for row in daily_rows]
    
    # Variance-based consistency: low variance in daily focus = consistent
    if len(focus_times_min) == 1:
        variance_consistency = 1.0
    else:
        variance = np.var(focus_times_min)
        variance_consistency = 1.0 / (1.0 + variance / 10000)
        variance_consistency = np.clip(variance_consistency, 0, 1)
    
    # Streak-based consistency: consecutive active days are rewarded
    # quadratically so that long streaks contribute much more than short ones.
    if len(day_strings) < 2:
        streak_score = 0.0
    else:
        prev = datetime.strptime(day_strings[0], "%Y-%m-%d")
        streak_count = 1
        total_streak_days = 0
        for ds in day_strings[1:]:
            curr = datetime.strptime(ds, "%Y-%m-%d")
            if (curr - prev).days == 1:
                streak_count += 1
            else:
                total_streak_days += streak_count * streak_count
                streak_count = 1
            prev = curr
        total_streak_days += streak_count * streak_count
        max_possible = len(day_strings) * len(day_strings)
        streak_score = total_streak_days / max_possible if max_possible > 0 else 0.0
        streak_score = np.clip(streak_score, 0, 1)
    
    # Blend: streak matters more than variance for perceived consistency
    consistency = 0.3 * variance_consistency + 0.7 * streak_score
    
    # Penalise sparse data: if only a few days have activity, reduce score
    active_days = len(focus_times_min)
    day_ratio = min(active_days / max(window_days, 1), 1.0)
    consistency = consistency * (0.3 + 0.7 * day_ratio)
    
    return np.clip(consistency, 0, 1)


def compute_preferred_hour(db, user_id):
    """Find the hour (0-23) when user starts most sessions."""
    result = db.execute(
        """
        SELECT 
            CAST(strftime('%H', datetime(timestamp, 'unixepoch', 'localtime')) AS INTEGER) as hour,
            COUNT(*) as count
        FROM user_statistics
        WHERE user_id = ? AND event_type = 'session_start'
        GROUP BY strftime('%H', datetime(timestamp, 'unixepoch', 'localtime'))
        ORDER BY count DESC
        LIMIT 1
        """,
        (user_id,)
    ).fetchone()
    
    return int(result['hour']) if result else 12


def compute_preferred_weekday(db, user_id):
    """Find the weekday (0=Monday, 6=Sunday) when user starts most sessions."""
    result = db.execute(
        """
        SELECT 
            (CAST(strftime('%w', datetime(timestamp, 'unixepoch', 'localtime')) AS INTEGER) + 6) % 7 as weekday,
            COUNT(*) as count
        FROM user_statistics
        WHERE user_id = ? AND event_type = 'session_start'
        GROUP BY strftime('%w', datetime(timestamp, 'unixepoch', 'localtime'))
        ORDER BY count DESC
        LIMIT 1
        """,
        (user_id,)
    ).fetchone()
    
    return int(result['weekday']) if result else 3


def get_current_session_duration(db, user_id):
    """Get user's current pomodoro_session setting from lists table."""
    result = db.execute(
        """
        SELECT COALESCE(AVG(pomo_session), 25) as avg_session
        FROM lists
        WHERE user_id = ? AND is_active = 1
        """,
        (user_id,)
    ).fetchone()
    
    return float(result['avg_session'] or 25.0)


def get_current_short_break_duration(db, user_id):
    """Get user's current short break setting."""
    result = db.execute(
        """
        SELECT COALESCE(AVG(pomo_short_break), 5) as avg_short_break
        FROM lists
        WHERE user_id = ? AND is_active = 1
        """,
        (user_id,)
    ).fetchone()
    
    return float(result['avg_short_break'] or 5.0)


def get_current_long_break_duration(db, user_id):
    """Get user's current long break setting."""
    result = db.execute(
        """
        SELECT COALESCE(AVG(pomo_long_break), 15) as avg_long_break
        FROM lists
        WHERE user_id = ? AND is_active = 1
        """,
        (user_id,)
    ).fetchone()
    
    return float(result['avg_long_break'] or 15.0)


def compute_avg_sessions_per_day(db, user_id, window_days):
    """Calculate average sessions per day."""
    cutoff_timestamp = int(datetime.now().timestamp()) - (window_days * 86400)
    
    result = db.execute(
        """
        SELECT 
            AVG(session_count) as avg_sessions
        FROM (
            SELECT 
                DATE(datetime(timestamp, 'unixepoch', 'localtime')) as day,
                COUNT(*) as session_count
            FROM user_statistics
            WHERE user_id = ? AND timestamp >= ? AND event_type = 'session_start'
            GROUP BY DATE(datetime(timestamp, 'unixepoch', 'localtime'))
        )
        """,
        (user_id, cutoff_timestamp)
    ).fetchone()
    
    return float(result['avg_sessions'] or 4.0)


def compute_break_skip_streak(db, user_id):
    """Calculate the count of consecutive breaks skipped recently (last 7 days)."""
    cutoff_timestamp = int(datetime.now().timestamp()) - (7 * 86400)
    
    skips = db.execute(
        """
        SELECT timestamp
        FROM user_statistics
        WHERE user_id = ? AND event_type = 'break_skip' AND timestamp >= ?
        ORDER BY timestamp DESC
        LIMIT 20
        """,
        (user_id, cutoff_timestamp)
    ).fetchall()
    
    if not skips:
        return 0
    
    # Count consecutive recent skips (within 1 day apart)
    consecutive = 0
    prev_timestamp = None
    
    for skip in skips:
        curr_timestamp = skip['timestamp']
        
        if prev_timestamp is None:
            consecutive = 1
        elif prev_timestamp - curr_timestamp <= 86400:  # Within 1 day
            consecutive += 1
        else:
            break
        
        prev_timestamp = curr_timestamp
    
    return consecutive


def compute_session_pause_rate(db, user_id, window_days):
    """Calculate fraction of sessions that were paused."""
    cutoff_timestamp = int(datetime.now().timestamp()) - (window_days * 86400)
    result = db.execute(
        """
        SELECT
            SUM(CASE WHEN event_type = 'session_pause' THEN 1 ELSE 0 END) AS pauses,
            SUM(CASE WHEN event_type = 'session_start' THEN 1 ELSE 0 END) AS starts
        FROM user_statistics
        WHERE user_id = ? AND timestamp >= ?
          AND event_type IN ('session_pause', 'session_start')
        """,
        (user_id, cutoff_timestamp),
    ).fetchone()
    pauses = int(result["pauses"] or 0)
    starts = int(result["starts"] or 0)
    if starts == 0:
        return 0.0
    return pauses / starts


def compute_active_day_ratio(db, user_id, window_days):
    """Fraction of days in the window that had at least one session (start or end)."""
    cutoff_timestamp = int(datetime.now().timestamp()) - (window_days * 86400)
    result = db.execute(
        """
        SELECT COUNT(DISTINCT DATE(datetime(timestamp, 'unixepoch', 'localtime'))) AS active_days
        FROM user_statistics
        WHERE user_id = ? AND timestamp >= ? AND event_type IN ('session_start', 'session_end')
        """,
        (user_id, cutoff_timestamp),
    ).fetchone()
    active = int(result["active_days"] or 0)
    return min(active / max(window_days, 1), 1.0)
