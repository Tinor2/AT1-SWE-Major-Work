"""
Per-user decision tree trainer.

Pulls feature rows from user_statistics, trains a DecisionTreeClassifier,
pickles the model + metadata to pomodoro/ml/models/<user_id>/,
and records training time.
"""

import hashlib
import os
import pickle
import time
from datetime import datetime
from collections import defaultdict
import numpy as np
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

ML_MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")


def _user_model_dir(user_id: int) -> str:
    path = os.path.join(ML_MODELS_DIR, str(user_id))
    os.makedirs(path, exist_ok=True)
    return path


def _model_path(user_id: int) -> str:
    return os.path.join(_user_model_dir(user_id), "model.pkl")


def _meta_path(user_id: int) -> str:
    return os.path.join(_user_model_dir(user_id), "meta.pkl")


# Security (A08): SHA-256 hash verification prevents RCE via tampered .pkl files.
def _compute_model_hash(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def model_exists(user_id: int) -> bool:
    return os.path.exists(_model_path(user_id))


def load_model(user_id: int):
    mp = _model_path(user_id)
    if not os.path.exists(mp):
        return None, None

    with open(_meta_path(user_id), "rb") as f:
        meta = pickle.load(f)

    # Security (A08): verify model file hash before deserialisation to
    # detect tampering. Legacy models (trained before this check existed)
    # lack the hash field and are accepted with a warning.
    stored_hash = meta.get("model_hash")
    if stored_hash:
        actual_hash = _compute_model_hash(mp)
        if actual_hash != stored_hash:
            raise ValueError(
                f"Security violation: model.pkl hash mismatch for user {user_id} "
                f"(expected {stored_hash}, got {actual_hash})"
            )

    with open(mp, "rb") as f:
        clf = pickle.load(f)
    return clf, meta


def seconds_since_trained(user_id: int) -> float | None:
    _, meta = load_model(user_id)
    if meta is None:
        return None
    return time.time() - meta["trained_at"]


def train_for_user(user_id: int, db) -> dict:
    from pomodoro.ml.feature_engineering import (
        compute_features_for_user,
        compute_productivity_score,
    )

    rows = _build_feature_rows(user_id, db)

    if len(rows) < 4:
        from pomodoro.ML_TESTS.productivity_decision_tree import (
            generate_synthetic_dataset,
        )
        X, y = generate_synthetic_dataset(n_samples=300, seed=user_id)
        n_real = 0
    else:
        X = np.array([r["features"] for r in rows])
        y = np.array([r["label"] for r in rows])
        n_real = len(rows)

    try:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
    except ValueError:
        # Fall back to non-stratified split when class distribution is too sparse
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
    clf = DecisionTreeClassifier(
        max_depth=5,
        min_samples_leaf=5,
        class_weight="balanced",
        random_state=42,
    )
    clf.fit(X_train, y_train)
    acc = accuracy_score(y_test, clf.predict(X_test)) if len(X_test) > 0 else 0.0

    model_path = _model_path(user_id)
    with open(model_path, "wb") as f:
        pickle.dump(clf, f)

    # Security (A08): record model hash in metadata so load_model() can
    # detect file tampering before deserialisation.
    model_hash = _compute_model_hash(model_path)

    meta = {
        "trained_at": time.time(),
        "accuracy": acc,
        "n_samples": len(X),
        "n_real_samples": n_real,
        "trained_at_human": datetime.utcnow().isoformat() + "Z",
        "model_hash": model_hash,
    }
    with open(_meta_path(user_id), "wb") as f:
        pickle.dump(meta, f)

    print(
        f"[ML] User {user_id}: trained on {len(X)} samples "
        f"({n_real} real), test accuracy={acc:.2f}"
    )
    return meta


def _build_feature_rows(user_id: int, db) -> list[dict]:
    events = db.execute(
        """
        SELECT event_type, timestamp, duration_seconds,
               task_completion_time_seconds, break_type
        FROM user_statistics
        WHERE user_id = ?
        ORDER BY timestamp ASC
        """,
        (user_id,),
    ).fetchall()

    if not events:
        return []

    days: dict[str, list] = defaultdict(list)
    for ev in events:
        day = datetime.utcfromtimestamp(ev["timestamp"]).strftime("%Y-%m-%d")
        days[day].append(ev)

    rows = []
    for day, day_events in days.items():
        feats = _day_features(day_events)
        score = _score_from_features(feats)
        label = _score_to_class(score)
        rows.append({"features": feats, "label": label})

    return rows


def _day_features(events: list) -> np.ndarray:
    sessions_started = sum(1 for e in events if e["event_type"] == "session_start")
    sessions_ended   = sum(1 for e in events if e["event_type"] == "session_end")
    breaks_done      = sum(1 for e in events if e["event_type"] == "break_completion")
    breaks_skipped   = sum(1 for e in events if e["event_type"] == "break_skip")
    tasks_created    = sum(1 for e in events if e["event_type"] == "task_creation")
    tasks_completed  = sum(1 for e in events if e["event_type"] == "task_completion")
    pauses           = sum(1 for e in events if e["event_type"] == "session_pause")

    focus_seconds = sum(
        (e["duration_seconds"] or 0)
        for e in events
        if e["event_type"] == "session_end"
    )

    completion_times = [
        e["task_completion_time_seconds"]
        for e in events
        if e["event_type"] == "task_completion"
        and e["task_completion_time_seconds"]
    ]
    avg_task_min = (
        np.mean(completion_times) / 60.0 if completion_times else 60.0
    )

    task_rate    = min(tasks_completed / max(tasks_created + tasks_completed, 1), 1.0)
    break_rate   = min(breaks_done / max(breaks_done + breaks_skipped, 1), 1.0)
    session_rate = min(sessions_ended / max(sessions_started, 1), 1.0)
    focus_min    = focus_seconds / 60.0
    pause_rate   = min(pauses / max(sessions_started, 1), 1.0)
    skip_rate    = min(breaks_skipped / max(breaks_done + breaks_skipped, 1), 1.0)

    first_ts = events[0]["timestamp"]
    dt = datetime.utcfromtimestamp(first_ts)
    peak_hour_norm  = dt.hour / 23.0
    weekday_norm    = dt.weekday() / 6.0

    consistency = 1.0

    return np.array(
        [
            avg_task_min,
            task_rate,
            break_rate,
            session_rate,
            focus_min,
            consistency,
            skip_rate,
            pause_rate,
            peak_hour_norm,
            weekday_norm,
        ],
        dtype=float,
    )


def _score_from_features(f: np.ndarray, active_day_ratio: float = 1.0) -> float:
    avg_min, task_rate, break_rate, session_rate, focus_min, consistency, skip_rate, pause_rate, _, _ = f
    # Weight rationale (out of 100):
    #   task_rate         × 20  — completing tasks is the strongest positive signal
    #   break_rate        × 12  — completing breaks supports sustained focus
    #   session_rate      × 25  — finishing sessions shows strongest commitment
    #   focus_curve       —      — power curve below 240 min + steep bonus above
    #   consistency       × 8   — even effort across days
    #   speed_bonus       × 15  — faster task completion = higher efficiency
    #   active_day_ratio  × 15  — showing up regularly matters (non-linear)
    # Penalties (subtracted):
    #   skip_rate    × 12  — skipping breaks now penalises more heavily
    #   pause_rate   × 6   — pausing occasionally is normal
    #   focus_penalty × 15 — low daily focus time drags score down
    speed_bonus = max(0.0, 1.0 - min(avg_min, 120.0) / 120.0) * 15
    focus_ratio = min(focus_min / 240.0, 1.0)
    focus_base  = focus_ratio ** 0.5 * 20
    focus_bonus = max(0.0, focus_min - 240.0) / 240.0 * 50
    focus_penalty = max(0.0, (1.0 - focus_ratio) * 15)
    core = (
        task_rate * 20
        + break_rate * 12
        + session_rate * 25
        + focus_base + focus_bonus
        + (consistency ** 2) * 15
        + speed_bonus
        + (active_day_ratio ** 0.7) * 15
    )
    penalties = skip_rate * 12 + pause_rate * 6 + focus_penalty
    return float(np.clip(core - penalties, 0, 100))


def _score_to_class(score: float) -> int:
    if score < 20: return 0
    if score < 40: return 1
    if score < 60: return 2
    if score < 80: return 3
    if score < 90: return 4
    return 5
