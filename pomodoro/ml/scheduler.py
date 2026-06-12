"""
Background retraining scheduler.
Uses a simple thread-based approach (no Celery required).

Add to create_app() in pomodoro/__init__.py:
    from .ml.scheduler import start_scheduler
    start_scheduler(app)
"""

import threading
import time

_scheduler_thread = None
_stop_event = threading.Event()

RETRAIN_INTERVAL_SECONDS = 3600


def _retrain_all_users(app):
    with app.app_context():
        from pomodoro.db import get_db
        from pomodoro.ml.trainer import train_for_user, seconds_since_trained

        db = get_db()
        active_users = db.execute(
            """
            SELECT DISTINCT user_id FROM user_statistics
            WHERE timestamp >= ?
            """,
            (int(time.time()) - 86400,),
        ).fetchall()

        for row in active_users:
            uid = row["user_id"]
            since = seconds_since_trained(uid)
            if since is None or since >= RETRAIN_INTERVAL_SECONDS:
                try:
                    train_for_user(uid, db)
                except Exception as e:
                    print(f"[ML Scheduler] Failed to retrain user {uid}: {e}")


def _scheduler_loop(app):
    while not _stop_event.is_set():
        _retrain_all_users(app)
        _stop_event.wait(RETRAIN_INTERVAL_SECONDS)


def start_scheduler(app):
    global _scheduler_thread
    if _scheduler_thread and _scheduler_thread.is_alive():
        return
    _stop_event.clear()
    _scheduler_thread = threading.Thread(
        target=_scheduler_loop,
        args=(app,),
        daemon=True,
        name="ml-retrain-scheduler",
    )
    _scheduler_thread.start()
    print("[ML Scheduler] Started — retraining every 1 hour.")
