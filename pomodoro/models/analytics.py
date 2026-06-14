"""Aggregated analytics for the dashboard (tasks, time sessions, optional user_statistics)."""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Any

from ..db import get_db


def _table_exists(db, name: str) -> bool:
    row = db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (name,),
    ).fetchone()
    return row is not None


# Security (OWASP A03): whitelist prevents SQL injection via PRAGMA table
# interpolation — PRAGMA does not support parameterised queries, so the
# allowlist is the correct architectural control.
_ALLOWED_TABLES = frozenset({
    "tasks", "lists", "user_tags", "task_time_sessions", "user_statistics"
})

def _columns(db, table: str) -> set[str]:
    if table not in _ALLOWED_TABLES:
        raise ValueError(f"Unknown table: {table}")
    if not _table_exists(db, table):
        return set()
    return {r["name"] for r in db.execute(f"PRAGMA table_info({table})")}


def _period_cutoff_ts(days: int) -> int:
    return int(time.time()) - max(1, days) * 86400


def _fill_date_range(
    entries: list[dict[str, float | str]], period_days: int
) -> list[dict[str, float | str]]:
    entry_map = {e["day"]: e["minutes"] for e in entries}
    today = datetime.now(timezone.utc).date()
    filled = []
    for i in range(period_days - 1, -1, -1):
        d = today - timedelta(days=i)
        day_str = d.isoformat()
        filled.append({
            "day": day_str,
            "minutes": entry_map.get(day_str, 0.0),
        })
    return filled


def _fill_date_range_count(
    entries: list[dict], period_days: int
) -> list[dict]:
    """Fill missing dates with 0s for multi-field daily data."""
    entry_map = {}
    for e in entries:
        entry_map[e["day"]] = {k: v for k, v in e.items() if k != "day"}
    today = datetime.now(timezone.utc).date()
    filled = []
    keys = set()
    if entries:
        keys = {k for k in entries[0] if k != "day"}
    default = {k: 0 for k in keys}
    for i in range(period_days - 1, -1, -1):
        d = today - timedelta(days=i)
        day_str = d.isoformat()
        row = {"day": day_str}
        row.update(entry_map.get(day_str, dict(default)))
        filled.append(row)
    return filled


def get_analytics_dashboard(user_id: int, period_days: int = 30) -> dict[str, Any]:
    """Build summary dict for the analytics page."""
    db = get_db()
    cutoff = _period_cutoff_ts(period_days)
    modifier = f"-{int(period_days)} days"

    task_cols = _columns(db, "tasks")
    if {"number_of_full_breaks", "number_of_skipped_breaks"} <= task_cols:
        task_row = db.execute(
            """
            SELECT
                COUNT(*) AS total_tasks,
                SUM(CASE WHEN is_done THEN 1 ELSE 0 END) AS completed_tasks,
                SUM(CASE WHEN NOT is_done THEN 1 ELSE 0 END) AS open_tasks,
                COALESCE(SUM(number_of_full_breaks), 0) AS full_breaks,
                COALESCE(SUM(number_of_skipped_breaks), 0) AS skipped_breaks
            FROM tasks
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()
    else:
        task_row = db.execute(
            """
            SELECT
                COUNT(*) AS total_tasks,
                SUM(CASE WHEN is_done THEN 1 ELSE 0 END) AS completed_tasks,
                SUM(CASE WHEN NOT is_done THEN 1 ELSE 0 END) AS open_tasks,
                0 AS full_breaks,
                0 AS skipped_breaks
            FROM tasks
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

    created_in_period = db.execute(
        """
        SELECT COUNT(*) AS c
        FROM tasks
        WHERE user_id = ?
          AND datetime(created_at) >= datetime('now', ?)
        """,
        (user_id, modifier),
    ).fetchone()

    lists_row = db.execute(
        "SELECT COUNT(*) AS c FROM lists WHERE user_id = ?",
        (user_id,),
    ).fetchone()

    if _table_exists(db, "task_time_sessions"):
        focus_row = db.execute(
            """
            SELECT
                COALESCE(SUM(duration_seconds), 0) AS total_seconds,
                COUNT(*) AS session_count,
                COUNT(DISTINCT date(datetime(started_at, 'unixepoch'))) AS active_days
            FROM task_time_sessions
            WHERE user_id = ?
              AND started_at >= ?
              AND ended_at IS NOT NULL
            """,
            (user_id, cutoff),
        ).fetchone()

        daily_focus = db.execute(
            """
            SELECT day, SUM(total_seconds) AS total_seconds FROM (
                SELECT
                    date(datetime(started_at, 'unixepoch')) AS day,
                    COALESCE(SUM(duration_seconds), 0) AS total_seconds
                FROM task_time_sessions
                WHERE user_id = ?
                  AND started_at >= ?
                  AND ended_at IS NOT NULL
                GROUP BY day
                UNION ALL
                SELECT
                    date(datetime(timestamp, 'unixepoch', 'localtime')) AS day,
                    COALESCE(SUM(duration_seconds), 0) AS total_seconds
                FROM user_statistics
                WHERE user_id = ?
                  AND timestamp >= ?
                  AND event_type = 'session_end'
                  AND duration_seconds IS NOT NULL
                GROUP BY day
            ) GROUP BY day ORDER BY day ASC
            """,
            (user_id, cutoff, user_id, cutoff),
        ).fetchall()

        recent_sessions = db.execute(
            """
            SELECT
                tts.started_at,
                datetime(tts.started_at, 'unixepoch', 'localtime') AS started_label,
                tts.duration_seconds,
                t.content AS task_content
            FROM task_time_sessions tts
            JOIN tasks t ON tts.task_id = t.id
            WHERE tts.user_id = ?
              AND tts.ended_at IS NOT NULL
            ORDER BY tts.started_at DESC
            LIMIT 12
            """,
            (user_id,),
        ).fetchall()
    else:
        # Fall back to user_statistics if task_time_sessions table is missing
        if _table_exists(db, "user_statistics"):
            focus_row = db.execute(
                """
                SELECT
                    COALESCE(SUM(duration_seconds), 0) AS total_seconds,
                    COUNT(*) AS session_count,
                    COUNT(DISTINCT date(datetime(timestamp, 'unixepoch', 'localtime'))) AS active_days
                FROM user_statistics
                WHERE user_id = ?
                  AND timestamp >= ?
                  AND event_type = 'session_end'
                  AND duration_seconds IS NOT NULL
                """,
                (user_id, cutoff),
            ).fetchone()
            daily_focus = db.execute(
                """
                SELECT
                    date(datetime(timestamp, 'unixepoch', 'localtime')) AS day,
                    COALESCE(SUM(duration_seconds), 0) AS total_seconds
                FROM user_statistics
                WHERE user_id = ?
                  AND timestamp >= ?
                  AND event_type = 'session_end'
                  AND duration_seconds IS NOT NULL
                GROUP BY day ORDER BY day ASC
                """,
                (user_id, cutoff),
            ).fetchall()
        else:
            focus_row = {
                "total_seconds": 0,
                "session_count": 0,
                "active_days": 0,
            }
            daily_focus = []
        recent_sessions = []

    has_stats = _table_exists(db, "user_statistics")
    event_counts: dict[str, int] = {}
    recent_events: list = []
    if has_stats:
        rows = db.execute(
            """
            SELECT event_type, COUNT(*) AS c
            FROM user_statistics
            WHERE user_id = ? AND timestamp >= ?
            GROUP BY event_type
            ORDER BY c DESC
            """,
            (user_id, cutoff),
        ).fetchall()
        event_counts = {r["event_type"]: r["c"] for r in rows}

        recent_events = db.execute(
            """
            SELECT
                event_type,
                timestamp,
                datetime(timestamp, 'unixepoch', 'localtime') AS ts_label,
                duration_seconds,
                task_content,
                break_type
            FROM user_statistics
            WHERE user_id = ? AND timestamp >= ?
            ORDER BY timestamp DESC
            LIMIT 20
            """,
            (user_id, cutoff),
        ).fetchall()

        # Daily break completions vs skips
        daily_breaks_raw = db.execute(
            """
            SELECT
                date(datetime(timestamp, 'unixepoch', 'localtime')) AS day,
                SUM(CASE WHEN event_type = 'break_completion' THEN 1 ELSE 0 END) AS completed,
                SUM(CASE WHEN event_type = 'break_skip' THEN 1 ELSE 0 END) AS skipped
            FROM user_statistics
            WHERE user_id = ?
              AND timestamp >= ?
              AND event_type IN ('break_completion', 'break_skip')
            GROUP BY day ORDER BY day ASC
            """,
            (user_id, cutoff),
        ).fetchall()

        daily_breaks = _fill_date_range_count(
            [{ "day": r["day"], "completed": r["completed"], "skipped": r["skipped"] } for r in daily_breaks_raw],
            period_days,
        )

        # Daily sessions started vs ended
        daily_sessions_raw = db.execute(
            """
            SELECT
                date(datetime(timestamp, 'unixepoch', 'localtime')) AS day,
                SUM(CASE WHEN event_type = 'session_end' THEN 1 ELSE 0 END) AS ended,
                SUM(CASE WHEN event_type = 'session_start' THEN 1 ELSE 0 END) AS started
            FROM user_statistics
            WHERE user_id = ?
              AND timestamp >= ?
              AND event_type IN ('session_start', 'session_end')
            GROUP BY day ORDER BY day ASC
            """,
            (user_id, cutoff),
        ).fetchall()

        daily_sessions = _fill_date_range_count(
            [{ "day": r["day"], "started": r["started"], "ended": r["ended"] } for r in daily_sessions_raw],
            period_days,
        )

    total_tasks = int(task_row["total_tasks"] or 0)
    completed = int(task_row["completed_tasks"] or 0)

    # Count breaks from user_statistics when available (more accurate)
    if has_stats:
        brk = db.execute(
            """
            SELECT
                SUM(CASE WHEN event_type = 'break_completion' THEN 1 ELSE 0 END) AS completed,
                SUM(CASE WHEN event_type = 'break_skip' THEN 1 ELSE 0 END) AS skipped
            FROM user_statistics
            WHERE user_id = ? AND timestamp >= ?
            """,
            (user_id, cutoff),
        ).fetchone()
        full_b = int(brk["completed"] or 0)
        skip_b = int(brk["skipped"] or 0)
    else:
        full_b = int(task_row["full_breaks"] or 0)
        skip_b = int(task_row["skipped_breaks"] or 0)
    break_total = full_b + skip_b
    break_skip_rate = round(100 * skip_b / break_total, 1) if break_total else None

    return {
        "period_days": period_days,
        "tasks": {
            "total": total_tasks,
            "completed": completed,
            "open": int(task_row["open_tasks"] or 0),
            "created_in_period": int(created_in_period["c"] or 0),
            "completion_rate": round(100 * completed / total_tasks, 1) if total_tasks else None,
        },
        "lists": {"total": int(lists_row["c"] or 0)},
        "focus": {
            "total_seconds_period": int(focus_row["total_seconds"] or 0),
            "session_count_period": int(focus_row["session_count"] or 0),
            "active_days_period": int(focus_row["active_days"] or 0),
        },
        "breaks": {
            "completed": full_b,
            "skipped": skip_b,
            "skip_rate": break_skip_rate,
        },
        "user_statistics": {
            "enabled": has_stats,
            "event_counts": event_counts,
            "recent_events": recent_events,
            "total_events_period": sum(event_counts.values()) if event_counts else 0,
            "daily_breaks": daily_breaks if has_stats else [],
            "has_any_breaks": has_stats and any(r.get("completed", 0) or r.get("skipped", 0) for r in daily_breaks),
            "daily_sessions": daily_sessions if has_stats else [],
            "has_any_sessions": has_stats and any(r.get("started", 0) or r.get("ended", 0) for r in daily_sessions),
        },
        "daily_focus": _fill_date_range(
            [
                {"day": r["day"], "minutes": round(r["total_seconds"] / 60, 1)}
                for r in daily_focus
            ],
            period_days,
        ),
        "recent_sessions": recent_sessions,
    }
