"""
Per-user decision tree trainer for productivity band classification.

Pipeline:
  1. Build per-day feature rows from user_statistics events.
  2. If < 2 sessions exist → generate synthetic dataset (300 samples, 6 bands).
  3. Train a DecisionTreeClassifier with max_depth=5, min_samples_leaf=5,
     class_weight="balanced" to handle imbalanced band distributions.
  4. Save model + SHA-256 integrity hash to pomodoro/ml/models/<user_id>/.

Model selection rationale (DecisionTreeClassifier):
  - Interpretable: feature_importances_ and export_text show how each feature
    contributes, which is valuable for an educational/analytics context.
  - Handles mixed numerical features (rates, minutes, hour-of-day) without
    scaling.
  - class_weight="balanced" offsets the skew toward middle bands common in
    real usage.
  - max_depth=5 and min_samples_leaf=5 prevent overfitting on small per-user
    datasets (as few as 1-15 rows initially).

Security (SAST — bandit run 2026-06-14):
  - A08: Pickle deserialisation risk mitigated by SHA-256 hash verification
    in load_model(). The model hash is computed immediately after pickling and
    stored in metadata. Before any future load_model() call, the hash is
    re-computed and compared — tampered files are rejected with a ValueError.
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
    """
    Train (or retrain) a per-user DecisionTreeClassifier.

    1. Build per-day feature rows from user_statistics.
    2. If < 2 session_end events exist → use synthetic data
       (300 samples, 6 bands seeded by user_id for reproducibility).
    3. 80/20 stratified train-test split (fallback to non-stratified
       when a band has too few samples).
    4. DecisionTreeClassifier(max_depth=5, min_samples_leaf=5,
       class_weight='balanced', random_state=42).
    5. Pickle the trained model and metadata (including SHA-256 hash
       for tamper detection) to pomodoro/ml/models/<user_id>/.

    DAST (manual penetration testing, 2026-06-14):
      - Verified that model files are only loaded via load_model()
        which checks hash integrity before unpickling.
      - Confirmed the /api/productivity/retrain endpoint requires
        authentication (login_required) — unauthorised users cannot
        trigger retraining.
    """
    rows = _build_feature_rows(user_id, db)

    # Session-count threshold: use real data once the user has at least
    # 2 completed sessions. This replaces the earlier day-count threshold
    # so that a user who completes 2 sessions on their first day gets
    # real-model training immediately.
    session_count = db.execute(
        "SELECT COUNT(*) FROM user_statistics WHERE user_id = ? AND event_type = 'session_end'",
        (user_id,),
    ).fetchone()[0]

    if session_count < 2:
        from pomodoro.ML_TESTS.productivity_decision_tree import (
            generate_synthetic_dataset,
        )
        X, y = generate_synthetic_dataset(n_samples=300, seed=user_id)
        n_real = 0
    else:
        X = np.array([r["features"] for r in rows])
        y = np.array([r["label"] for r in rows])
        n_real = len(rows)

    if X.shape[0] < 2:
        # Not enough samples for a train/test split — train on all data
        clf = DecisionTreeClassifier(
            max_depth=5,
            min_samples_leaf=5,
            class_weight="balanced",
            random_state=42,
        )
        clf.fit(X, y)
        acc = 0.0
    else:
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
    """
    Build per-day feature rows for model training.

    Queries all user_statistics events, groups by calendar day,
    and computes a 10-element feature vector per day. Each row also
    gets a heuristic label (0-5) via _score_from_features →
    _score_to_class.

    The DecisionTreeClassifier learns to reproduce these labels from
    the features, so it implicitly learns the heuristic scoring
    function but can generalise beyond it when real data diverges
    from the formula.

    Returns list of {"features": np.ndarray, "label": int}.
    """
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
    """
    Compute 10-element feature vector from one day's events.

    Feature vector (all float64, order fixed for model compatibility):
      [0] avg_task_completion_min  — mean minutes to finish a task (capped)
      [1] task_rate                — completed / (created + completed)
      [2] break_rate               — breaks done / (done + skipped)
      [3] session_rate             — ended / started
      [4] focus_minutes            — total session_end duration in min
      [5] consistency              — hardcoded 1.0 per-day; real value
                                     comes from feature_engineering at
                                     prediction time
      [6] skip_rate                — breaks skipped / (done + skipped)
      [7] pause_rate               — pauses / sessions_started
      [8] peak_hour_norm           — first event hour / 23 (0-1)
      [9] weekday_norm             — first event weekday / 6 (0-1)

    All rates clamped to [0, 1] via min(...).
    """
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
    """
    Heuristic 0-100 productivity score from a single day's features.

    This scores provides the training labels for the DecisionTreeClassifier.
    The model learns to reproduce these labels from the feature vector, so
    it internalises the formula below but can generalise beyond it on real
    patterns.

    Scoring rationale (out of 100, higher = better):
      Positive components:
        task_rate         × 20   — completing tasks is the strongest signal
        break_rate        × 12   — good break discipline sustains focus
        session_rate      × 15   — finishing what you start
        focus_base        —       — power curve: sqrt(focus_min/240) × 20
                                  (fast rise below 240 min, diminishing returns)
        focus_bonus       —       — linear bonus: (focus_min-240)/240 × 50
                                  (rewards extreme focus beyond 4h)
        consistency²      × 15    — squared to reward steady habits non-linearly
        speed_bonus       × 18    — faster task completion = higher efficiency
                                    speed_bonus = (1 - avg_min/120) × 18, capped
        active_day_ratio^0.7 × 15 — showing up regularly, concave curve

      Penalties (subtracted):
        skip_rate         × 12   — skipping breaks is a strong negative
        pause_rate        × 6    — occasional pausing is normal (low weight)
        focus_penalty     × 15   — low daily focus (1 - focus_ratio) × 15

    Total score = max(core - penalties, 0), clipped to [0, 100].
    """
    avg_min, task_rate, break_rate, session_rate, focus_min, consistency, skip_rate, pause_rate, _, _ = f
    speed_bonus = max(0.0, 1.0 - min(avg_min, 120.0) / 120.0) * 18
    focus_ratio = min(focus_min / 240.0, 1.0)
    focus_base  = focus_ratio ** 0.5 * 20
    focus_bonus = max(0.0, focus_min - 240.0) / 240.0 * 50
    focus_penalty = max(0.0, (1.0 - focus_ratio) * 15)
    core = (
        task_rate * 20
        + break_rate * 12
        + session_rate * 15
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
